# Input/Output Validation Layer - Design Spec

## Overview

This spec defines the architecture for an Input/Output Validation Layer that will be added to the UltraSwarm multi-agent system. The layer provides:

1. **Input validation** - Ensures agent inputs conform to expected schemas
2. **Output validation** - Ensures agent outputs conform to expected schemas  
3. **Dependency resolution** - Handles agent output dependencies between agents
4. **Versioned state management** - Thread-safe shared state with conflict detection

## Design Choices

| Question | Choice | Rationale |
|----------|--------|-----------|
| Validation Timing | Mixed (BaseAgent + Registry) | BaseAgent for basic validation, Registry for complex dependency checking |
| Schema Definition | Pydantic Models | Type-safe, runtime validated, integrate with existing Pydantic usage |
| Dependency Detection | Explicit Declaration | Clear, maintainable, easy to understand |
| Critical Section | Versioned State | Handles concurrent access, detects conflicts without deadlocks |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Validation Middleware                            │
│  • InputValidator: Validates agent inputs against schemas           │
│  • OutputValidator: Validates agent outputs against schemas         │
│  • DependencyResolver: Checks agent output dependencies             │
│  • SchemaRegistry: Stores per-agent input/output schemas            │
└─────────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌──────────────┐  ┌──────────────────┐  ┌─────────────────┐
│ Orchestrator │  │     Agents       │  │   Schema Store  │
│   (Entrypoint)│  │  (execute_task)  │  │  (per-agent)    │
└──────────────┘  └──────────────────┘  └─────────────────┘
```

---

## Components

### 1. Schema Registry (`core/schema_registry.py`)

**Purpose**: Central store for agent input/output schemas with versioning

**Key Features**:
- Register input/output schemas per agent
- Support base schemas and agent-specific extensions
- Version schema definitions

**Schema Definition (Agent-Specific)**:
```python
# agents/seo_agent.py
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

class SEOAgentInputSchema(BaseModel):
    """Input schema for SEO Agent"""
    task_id: str = Field(..., description="Unique task identifier")
    instruction: str = Field(..., description="Task instruction (e.g., keyword research)")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Context from previous agents")
    skills_hint: Optional[List[str]] = Field(default=None, description="Suggested skills to use")
    store_url: Optional[str] = Field(default=None, description="Store URL for SEO analysis")
    niche: Optional[str] = Field(default=None, description="Store niche/industry")

class SEOAgentOutputSchema(BaseModel):
    """Output schema for SEO Agent"""
    success: bool = Field(..., description="Execution success status")
    agent_name: str = Field(..., description="Name of agent that executed")
    task_id: str = Field(..., description="Task identifier")
    output: Optional[Dict[str, Any]] = Field(default=None, description="Agent output")
    context_for_next: Optional[Dict[str, Any]] = Field(default=None, description="Context for next agent")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    seo_data: Optional[Dict[str, Any]] = Field(default=None, description="SEO-specific output data")
```

**Base Schema**:
```python
# core/schema_registry.py
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

class BaseAgentInputSchema(BaseModel):
    """Base input schema for all agents"""
    task_id: str = Field(..., description="Unique task identifier")
    instruction: str = Field(..., description="Task instruction")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Context from previous agents")
    skills_hint: Optional[List[str]] = Field(default=None, description="Suggested skills")

class BaseAgentOutputSchema(BaseModel):
    """Base output schema for all agents"""
    success: bool = Field(..., description="Execution success status")
    agent_name: str = Field(..., description="Name of agent that executed")
    task_id: str = Field(..., description="Task identifier")
    output: Optional[Dict[str, Any]] = Field(default=None, description="Agent output")
    context_for_next: Optional[Dict[str, Any]] = Field(default=None, description="Context for next agent")
    error: Optional[str] = Field(default=None, description="Error message if failed")
```

---

### 2. Validation Middleware (`core/validation_middleware.py`)

**Purpose**: Hook into agent execution to validate inputs/outputs

**Key Features**:
- Validate agent inputs before execution
- Validate agent outputs after execution
- Configurable validation mode (strict/lenient)
- Graceful error handling (per design: try to recover, execute anyway)

**Implementation**:
```python
from typing import Tuple, Optional
from core.schema_registry import SchemaRegistry, BaseAgentInputSchema, BaseAgentOutputSchema


class ValidationMiddleware:
    """Middleware for agent input/output validation"""
    
    def __init__(self, schema_registry: SchemaRegistry, strict_mode: bool = False):
        self.schema_registry = schema_registry
        self.strict_mode = strict_mode
    
    def validate_input(self, agent_name: str, data: dict) -> Tuple[bool, str]:
        """
        Validate agent input before execution.
        
        On failure: Log error, try to recover, execute anyway (per design choice Q2)
        """
        # Try agent-specific schema first
        schema = self.schema_registry.get_input_schema(agent_name)
        
        if not schema:
            # Fall back to base schema
            schema = BaseAgentInputSchema
        
        try:
            schema(**data)
            return True, ""
        except Exception as e:
            error_msg = f"Input validation failed for {agent_name}: {str(e)}"
            
            # Per design: Log error, try to recover, execute anyway
            if self.strict_mode:
                return False, error_msg
            else:
                print(f"[WARNING] {error_msg}")
                print("[RECOVERY] Executing agent anyway with provided input...")
                return True, "Recovered from validation error"
    
    def validate_output(self, agent_name: str, result: dict) -> Tuple[bool, str]:
        """
        Validate agent output after execution.
        
        On failure: Log error, try to recover, execute anyway (per design choice Q2)
        """
        # Try agent-specific schema first
        schema = self.schema_registry.get_output_schema(agent_name)
        
        if not schema:
            # Fall back to base schema
            schema = BaseAgentOutputSchema
        
        try:
            schema(**result)
            return True, ""
        except Exception as e:
            error_msg = f"Output validation failed for {agent_name}: {str(e)}"
            
            # Per design: Log error, try to recover, execute anyway
            if self.strict_mode:
                return False, error_msg
            else:
                print(f"[WARNING] {error_msg}")
                print("[RECOVERY] Returning partial result from agent...")
                return True, "Recovered from validation error"
```

---

### 3. Dependency Resolver (`core/dependencies.py`)

**Purpose**: Handle agent dependencies and detect conflicts

**Key Features**:
- Register dependencies between agents
- Check if dependencies are met before execution
- Detect circular dependencies in execution plans
- Support explicit declaration (per design choice Q3)

**Implementation**:
```python
from typing import Dict, List, Tuple, Optional
from collections import defaultdict


class DependencyResolver:
    """Resolves dependencies between agents and detects conflicts"""
    
    def __init__(self):
        self.dependencies: Dict[str, List[str]] = {}  # agent -> [required_agents]
        self.reverse_dependencies: Dict[str, List[str]] = defaultdict(list)  # agent -> [agents_that_depend_on_me]
    
    def register_dependency(self, agent_name: str, requires: List[str]):
        """
        Register which agents an agent depends on.
        
        Args:
            agent_name: The agent that has dependencies
            requires: List of agent names this agent depends on
        """
        self.dependencies[agent_name] = requires
        for req in requires:
            self.reverse_dependencies[req].append(agent_name)
    
    def get_dependencies(self, agent_name: str) -> List[str]:
        """Get agents that the given agent depends on"""
        return self.dependencies.get(agent_name, [])
    
    def get_dependents(self, agent_name: str) -> List[str]:
        """Get agents that depend on the given agent"""
        return self.reverse_dependencies.get(agent_name, [])
    
    def check_dependencies_met(
        self, 
        agent_name: str, 
        available_outputs: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        """
        Check if all required agent outputs are available.
        
        Returns:
            Tuple of (all_met, list_of_missing)
        """
        requires = self.dependencies.get(agent_name, [])
        missing = [req for req in requires if req not in available_outputs]
        return len(missing) == 0, missing
    
    def detect_conflicts(self, agent_plan: List[str]) -> List[str]:
        """
        Detect circular dependencies in execution plan using DFS.
        
        Args:
            agent_plan: List of agent names in execution order
            
        Returns:
            List of conflict descriptions (empty if no conflicts)
        """
        visited = set()
        rec_stack = set()
        conflicts = []
        
        def dfs(agent: str, path: List[str]) -> bool:
            if agent in rec_stack:
                # Found cycle
                cycle_start = path.index(agent)
                cycle = path[cycle_start:] + [agent]
                conflicts.append(f"Circular dependency: {' -> '.join(cycle)}")
                return True
            
            if agent in visited:
                return False
            
            visited.add(agent)
            rec_stack.add(agent)
            path.append(agent)
            
            for dep in self.dependencies.get(agent, []):
                if dfs(dep, path.copy()):
                    if agent not in rec_stack:
                        return False  # Cycle already detected
            
            path.pop()
            rec_stack.remove(agent)
            return False
        
        for agent in agent_plan:
            if agent not in visited:
                dfs(agent, [])
        
        return conflicts
    
    def topological_sort(self, agent_plan: List[str]) -> Tuple[List[str], List[str]]:
        """
        Sort agents in topological order based on dependencies.
        
        Returns:
            Tuple of (sorted_agents, cycles_found)
        """
        # Calculate in-degrees
        in_degree = defaultdict(int)
        for agent in agent_plan:
            if agent not in in_degree:
                in_degree[agent] = 0
            for dep in self.dependencies.get(agent, []):
                if dep in agent_plan:
                    in_degree[agent] += 1
        
        # Find agents with no dependencies
        queue = [a for a in agent_plan if in_degree[a] == 0]
        sorted_agents = []
        
        while queue:
            agent = queue.pop(0)
            sorted_agents.append(agent)
            
            for dependent in self.reverse_dependencies.get(agent, []):
                if dependent in agent_plan:
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        queue.append(dependent)
        
        # Check for cycles
        cycles = []
        if len(sorted_agents) != len(agent_plan):
            remaining = [a for a in agent_plan if a not in sorted_agents]
            cycles.append(f"Agents with unresolved dependencies: {remaining}")
        
        return sorted_agents, cycles
```

---

### 4. Versioned State with Conflict Resolution (`core/versioned_state.py`)

**Purpose**: Thread-safe shared state with versioning for conflict detection

**Key Features**:
- Version tracking per key
- Lock-based critical section handling
- Conflict detection on read/write
- Thread-safe operations

**Implementation**:
```python
import threading
from datetime import datetime
from typing import Tuple, Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class VersionedValue:
    """A versioned value with metadata"""
    value: Any
    version: int
    timestamp: datetime
    writer: str


class VersionedState:
    """
    Thread-safe versioned state for agents.
    Handles shared state safely with versioning and conflict detection.
    """
    
    def __init__(self):
        self._state: Dict[str, VersionedValue] = {}
        self._locks: Dict[str, threading.Lock] = {}
        self._global_lock = threading.Lock()
    
    def acquire_lock(self, resource_name: str, timeout: float = 0.1) -> bool:
        """
        Acquire lock on a shared resource.
        
        Args:
            resource_name: Name of the resource to lock
            timeout: Lock acquisition timeout in seconds
            
        Returns:
            True if lock acquired, False otherwise
        """
        with self._global_lock:
            if resource_name not in self._locks:
                self._locks[resource_name] = threading.Lock()
        
        return self._locks[resource_name].acquire(blocking=True, timeout=timeout)
    
    def release_lock(self, resource_name: str):
        """Release lock on a shared resource"""
        if resource_name in self._locks:
            try:
                self._locks[resource_name].release()
            except RuntimeError:
                pass  # Lock not held
    
    def read(self, key: str) -> Tuple[Optional[Any], Optional[int]]:
        """
        Read value with version.
        
        Args:
            key: The key to read
            
        Returns:
            Tuple of (value, version) or (None, None) if not found
        """
        with self._global_lock:
            if key in self._state:
                val = self._state[key]
                return val.value, val.version
            return None, None
    
    def write(self, key: str, value: Any, writer: str) -> int:
        """
        Write value with version increment.
        
        Args:
            key: The key to write
            value: The value to store
            writer: Name of the agent writing the value
            
        Returns:
            New version number
        """
        with self._global_lock:
            current = self._state.get(key)
            current_version = current.version if current else 0
            new_version = current_version + 1
            
            self._state[key] = VersionedValue(
                value=value,
                version=new_version,
                timestamp=datetime.utcnow(),
                writer=writer
            )
            return new_version
    
    def get_conflict(self, key: str, expected_version: int) -> Optional[str]:
        """
        Check if there's a conflict (version mismatch).
        
        Args:
            key: The key to check
            expected_version: The version expected by the reader
            
        Returns:
            Error message if conflict, None if no conflict
        """
        with self._global_lock:
            if key in self._state:
                current_version = self._state[key].version
                if current_version != expected_version:
                    return f"Version mismatch for '{key}': expected {expected_version}, got {current_version}"
            return None
    
    def check_conflict_free(self, key: str, expected_version: int, new_value: Any, writer: str) -> bool:
        """
        Atomically check for conflict and write if no conflict.
        
        Args:
            key: The key to check and write
            expected_version: The version expected by the reader
            new_value: The new value to write
            writer: Name of the agent writing
            
        Returns:
            True if write succeeded, False if conflict detected
        """
        with self._global_lock:
            if key in self._state:
                current_version = self._state[key].version
                if current_version != expected_version:
                    return False
            
            self._state[key] = VersionedValue(
                value=new_value,
                version=expected_version + 1,
                timestamp=datetime.utcnow(),
                writer=writer
            )
            return True
```

---

### 5. Integration with BaseAgent (`core/base_agent.py`)

**Changes to existing code**:
```python
# core/base_agent.py
import json
from typing import Optional, Dict, Any
from pydantic import BaseModel

from tools.skill_loader import load_skill, AgentSkill
from core.result_schema import ExecutionResult
from core.__init__ import make_client
from core.rag_manager import query_knowledge
from core.schema_registry import SchemaRegistry
from core.validation_middleware import ValidationMiddleware
from core.dependencies import DependencyResolver
from core.versioned_state import VersionedState


class BaseAgent:
    """
    Dynamically loads capabilities from JSON skills.
    Serves as the foundation for Orchestrator, Allocator, and Worker agents.
    
    Features:
    - Input/output validation via middleware
    - Dependency checking before execution
    - Versioned state management
    """
    
    # Class-level registry and middleware (shared across all instances)
    _schema_registry = None
    _validation_middleware = None
    _dependency_resolver = None
    _versioned_state = None
    
    def __init__(self, skill_name: str, domain: str = "ecommerce"):
        self.skill_name = skill_name
        self.domain = domain
        self.skill: AgentSkill = load_skill(skill_name, domain)
        
        # Inject RAG Context into the system prompt if applicable
        self.system_prompt = self.skill.system_prompt
        self.client = make_client(system_prompt=self.system_prompt, agent_name=self.skill.name)
        
        # Initialize class-level components on first agent instantiation
        if BaseAgent._schema_registry is None:
            BaseAgent._schema_registry = SchemaRegistry()
            BaseAgent._validation_middleware = ValidationMiddleware(BaseAgent._schema_registry)
            BaseAgent._dependency_resolver = DependencyResolver()
            BaseAgent._versioned_state = VersionedState()
    
    @classmethod
    def get_schema_registry(cls) -> SchemaRegistry:
        return cls._schema_registry
    
    @classmethod
    def get_validation_middleware(cls) -> ValidationMiddleware:
        return cls._validation_middleware
    
    @classmethod
    def get_dependency_resolver(cls) -> DependencyResolver:
        return cls._dependency_resolver
    
    @classmethod
    def get_versioned_state(cls) -> VersionedState:
        return cls._versioned_state
    
    def execute_task(self, task: str, context: Optional[Dict[str, Any]] = None) -> ExecutionResult:
        """
        Executes a task and ensures the output matches ExecutionResult schema.
        
        Flow:
        1. Validate input against schema
        2. Check dependencies (if required outputs from other agents are available)
        3. Execute task
        4. Validate output against schema
        5. Return result
        """
        # Create input data
        input_data = {
            "task_id": f"task_{id(self)}_{id(task)}",
            "instruction": task,
            "context": context or {},
            "skills_hint": self.skill.tools
        }
        
        # Validate input
        valid, error = self.get_validation_middleware().validate_input(self.skill_name, input_data)
        if not valid:
            return ExecutionResult(
                status="error",
                data={"input_validation_error": error},
                message="Input validation failed"
            )
        
        # Check dependencies (if this agent requires outputs from other agents)
        available_outputs = {agent_name: None for agent_name in self.skill.context.get("requires", [])}
        deps_met, missing = self.get_dependency_resolver().check_dependencies_met(
            self.skill_name, available_outputs
        )
        
        if not deps_met:
            return ExecutionResult(
                status="error",
                data={"missing_dependencies": missing},
                message=f"Required outputs from agents {missing} are not available"
            )
        
        # Optional: Ask RAG Manager if any specific domain knowledge is relevant
        rag_context = query_knowledge(task)
        if rag_context:
            prompt = f"Task: {task}\nContext: {json.dumps(context, indent=2)}\n\nRelevant Domain Knowledge:\n{rag_context}\n"
        else:
            prompt = f"Task: {task}\n"
            if context:
                prompt += f"Context: {json.dumps(context, indent=2)}\n"
        
        schema_hint = ExecutionResult.schema_json()
        response_dict = self.client.ask_json(prompt, schema_hint=schema_hint)
        
        # Parse into execution result
        try:
            result = ExecutionResult(**response_dict)
            
            # Validate output
            valid, error = self.get_validation_middleware().validate_output(self.skill_name, response_dict)
            if not valid:
                return ExecutionResult(
                    status="error",
                    data={"output_validation_error": error},
                    message="Output validation failed"
                )
            
            return result
        except Exception as e:
            return ExecutionResult(
                status="error",
                data={"raw": response_dict, "error": str(e)},
                message="Failed to parse response into standard schema."
            )
    
    def reset(self):
        """Reset the agent's memory/history."""
        self.client.reset()
```

---

### 6. Integration with Registry (`agents/registry.py`)

**Changes to existing code**:
```python
# agents/registry.py
from __future__ import annotations
import logging
from typing import Type, Dict, List, Any

logger = logging.getLogger("AgentRegistry")


def build_registry(verbose: bool = False) -> Dict[str, Any]:
    """
    Instantiates every available agent and returns a dict keyed by agent name.
    
    Features:
    - Registers dependencies between agents
    - Detects circular dependencies
    - Logs any conflicts found
    """
    all_classes = (
        _load_helpers()
        + _load_external()
        + _load_outreach()
        + _load_ecommerce()
        + _load_fiverr()
        + _load_browser()
    )
    
    registry: Dict[str, Any] = {}
    
    # Import dependency resolver and validation middleware
    from core.dependencies import DependencyResolver
    from core.versioned_state import VersionedState
    
    # Import base agent to access class-level components
    from core.base_agent import BaseAgent
    
    resolver = BaseAgent.get_dependency_resolver()
    versioned_state = BaseAgent.get_versioned_state()
    
    for cls in all_classes:
        try:
            try:
                instance = cls(verbose=verbose)
            except TypeError:
                instance = cls()
            
            name = getattr(instance, "name", cls.__name__.lower())
            registry[name] = instance
            logger.debug(f"[Registry] Loaded: {name}")
            
            # Register dependencies explicitly (per design choice Q3)
            # Example: Each agent class can define its own dependencies
            if hasattr(cls, "dependencies"):
                for dep in cls.dependencies:
                    resolver.register_dependency(name, dep)
        
        except Exception as e:
            logger.warning(f"[Registry] Could not instantiate {cls.__name__}: {e}")
    
    # Detect conflicts after all agents are loaded
    agent_names = list(registry.keys())
    conflicts = resolver.detect_conflicts(agent_names)
    
    if conflicts:
        logger.warning(f"[Registry] Dependency conflicts detected: {conflicts}")
    else:
        logger.info("[Registry] No dependency conflicts detected")
    
    logger.info(f"[Registry] {len(registry)} agents loaded successfully.")
    return registry
```

---

## Testing Strategy

**Per design choice Q4**: Only test fundamentals

### Test Categories:

1. **RAG Tests** - Verify RAG returns relevant context
   - Query known knowledge base
   - Verify retrieval of stored documents

2. **Skill Tests** - Verify skills load correctly
   - Load existing skills
   - Verify schema matches expected format

3. **Tool Tests** - Verify tools work correctly
   - Browser search
   - Page fetching
   - Output saving

### Test Files:

```
tests/
├── test_rag.py           # RAG integration tests
├── test_skills.py        # Skill loading tests
├── test_tools.py         # Tool functionality tests
└── test_validation.py    # Validation middleware tests
```

### Example Tests:

```python
# tests/test_validation.py
"""Tests for validation middleware fundamentals"""

import pytest
from core.schema_registry import SchemaRegistry
from core.validation_middleware import ValidationMiddleware
from core.versioned_state import VersionedState
from core.dependencies import DependencyResolver


class TestSchemaRegistry:
    """Test schema registration and retrieval"""
    
    def test_schema_registration(self):
        """Test that schemas can be registered"""
        registry = SchemaRegistry()
        # Test registration
        registry.register_input_schema("test_agent", {"field": str})
        registry.register_output_schema("test_agent", {"field": str})
        
        # Test retrieval
        assert registry.get_input_schema("test_agent") is not None
        assert registry.get_output_schema("test_agent") is not None
    
    def test_missing_schema(self):
        """Test that missing schemas return None"""
        registry = SchemaRegistry()
        assert registry.get_input_schema("nonexistent_agent") is None
        assert registry.get_output_schema("nonexistent_agent") is None


class TestValidationMiddleware:
    """Test validation middleware functionality"""
    
    def test_valid_input(self):
        """Test that valid input passes validation"""
        registry = SchemaRegistry()
        middleware = ValidationMiddleware(registry)
        
        valid, error = middleware.validate_input("test_agent", {"field": "value"})
        assert valid is True
        assert error == ""
    
    def test_invalid_input(self):
        """Test that invalid input fails validation"""
        registry = SchemaRegistry()
        middleware = ValidationMiddleware(registry)
        
        valid, error = middleware.validate_input("test_agent", {"field": 123})
        assert valid is False
        assert error != ""


class TestVersionedState:
    """Test versioned state management"""
    
    def test_write_and_read(self):
        """Test basic write and read operations"""
        state = VersionedState()
        
        version = state.write("key", "value", "agent1")
        value, stored_version = state.read("key")
        
        assert value == "value"
        assert stored_version == version
    
    def test_version_increment(self):
        """Test that version increments on write"""
        state = VersionedState()
        
        v1 = state.write("key", "value1", "agent1")
        v2 = state.write("key", "value2", "agent2")
        
        assert v2 > v1
    
    def test_conflict_detection(self):
        """Test that version conflicts are detected"""
        state = VersionedState()
        
        state.write("key", "value1", "agent1")
        state.write("key", "value2", "agent2")
        
        conflict = state.get_conflict("key", 1)
        assert conflict is not None
        assert "Version mismatch" in conflict


class TestDependencyResolver:
    """Test dependency resolution"""
    
    def test_dependency_registration(self):
        """Test that dependencies can be registered"""
        resolver = DependencyResolver()
        
        resolver.register_dependency("agent_a", ["agent_b"])
        
        assert resolver.get_dependencies("agent_a") == ["agent_b"]
        assert resolver.get_dependents("agent_b") == ["agent_a"]
    
    def test_dependencies_met(self):
        """Test dependency check with available outputs"""
        resolver = DependencyResolver()
        resolver.register_dependency("agent_a", ["agent_b"])
        
        available = {"agent_b": "output"}
        met, missing = resolver.check_dependencies_met("agent_a", available)
        
        assert met is True
        assert missing == []
    
    def test_dependencies_not_met(self):
        """Test dependency check with missing outputs"""
        resolver = DependencyResolver()
        resolver.register_dependency("agent_a", ["agent_b", "agent_c"])
        
        available = {"agent_b": "output"}
        met, missing = resolver.check_dependencies_met("agent_a", available)
        
        assert met is False
        assert missing == ["agent_c"]
    
    def test_circular_dependency_detection(self):
        """Test detection of circular dependencies"""
        resolver = DependencyResolver()
        
        # Create circular: A -> B -> C -> A
        resolver.register_dependency("agent_a", ["agent_b"])
        resolver.register_dependency("agent_b", ["agent_c"])
        resolver.register_dependency("agent_c", ["agent_a"])
        
        agents = ["agent_a", "agent_b", "agent_c"]
        conflicts = resolver.detect_conflicts(agents)
        
        assert len(conflicts) > 0
        assert any("Circular" in c for c in conflicts)
```

---

## Implementation Checklist

- [ ] Create `core/schema_registry.py` with SchemaRegistry class
- [ ] Create `core/validation_middleware.py` with ValidationMiddleware class
- [ ] Create `core/dependencies.py` with DependencyResolver class
- [ ] Create `core/versioned_state.py` with VersionedState class
- [ ] Update `core/base_agent.py` to use middleware and dependency resolver
- [ ] Update `agents/registry.py` to detect conflicts
- [ ] Create `tests/test_validation.py` with fundamental tests
- [ ] Create `tests/test_rag.py` with RAG tests
- [ ] Create `tests/test_skills.py` with skill loading tests
- [ ] Create `tests/test_tools.py` with tool tests

---

## Next Steps

1. Write design doc (this file)
2. Implement schema registry
3. Implement validation middleware
4. Implement dependency resolver
5. Implement versioned state
6. Integrate with BaseAgent and Registry
7. Write tests for fundamentals (RAG, skills, tools)
8. Test full pipeline

---

## References

- Current codebase: `/home/jaasiel/Documents/Agents/UltraSwarm-main`
- BaseAgent: `core/base_agent.py`
- Registry: `agents/registry.py`
- Orchestrator: `agents/managers/orchestrator_agent.py`
