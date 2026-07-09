import json
from typing import Optional, Dict, Any, Type
from pydantic import BaseModel

from tools.skill_loader import load_skill, AgentSkill
from core.result_schema import ExecutionResult
from core.__init__ import make_client
from core.rag_manager import query_knowledge
from core.schema_registry import SchemaRegistry, get_schema_registry
from core.validation_middleware import ValidationMiddleware, get_validation_middleware
from core.dependencies import DependencyResolver, get_dependency_resolver
from core.versioned_state import VersionedState, get_versioned_state


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
    _schema_registry: Optional[SchemaRegistry] = None
    _validation_middleware: Optional[ValidationMiddleware] = None
    _dependency_resolver: Optional[DependencyResolver] = None
    _versioned_state: Optional[VersionedState] = None
    _initialized: bool = False
    
    def __init__(self, skill_name: str, domain: str = "ecommerce", verbose: bool = False):
        self.skill_name = skill_name
        self.domain = domain
        self.verbose = verbose
        self.skill: AgentSkill = load_skill(skill_name, domain)
        
        # Inject RAG Context into the system prompt if applicable
        self.system_prompt = self.skill.system_prompt
        self.client = make_client(system_prompt=self.system_prompt, agent_name=self.skill.name)
        
        # Initialize class-level components on first agent instantiation
        self._initialize_shared_components()
    
    @classmethod
    def _initialize_shared_components(cls):
        """Initialize shared components once for all agent instances"""
        if not cls._initialized:
            cls._schema_registry = get_schema_registry()
            cls._validation_middleware = get_validation_middleware()
            cls._dependency_resolver = get_dependency_resolver()
            cls._versioned_state = get_versioned_state()
            cls._initialized = True
    
    @classmethod
    def get_schema_registry(cls) -> SchemaRegistry:
        """Get the shared schema registry"""
        if cls._schema_registry is None:
            cls._initialize_shared_components()
        return cls._schema_registry
    
    @classmethod
    def get_validation_middleware(cls) -> ValidationMiddleware:
        """Get the shared validation middleware"""
        if cls._validation_middleware is None:
            cls._initialize_shared_components()
        return cls._validation_middleware
    
    @classmethod
    def get_dependency_resolver(cls) -> DependencyResolver:
        """Get the shared dependency resolver"""
        if cls._dependency_resolver is None:
            cls._initialize_shared_components()
        return cls._dependency_resolver
    
    @classmethod
    def get_versioned_state(cls) -> VersionedState:
        """Get the shared versioned state"""
        if cls._versioned_state is None:
            cls._initialize_shared_components()
        return cls._versioned_state
    
    def validate_input(self, data: dict) -> tuple:
        """
        Validate agent input before execution.
        
        Args:
            data: Input data to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        return self.get_validation_middleware().validate_input(self.skill_name, data)
    
    def validate_output(self, result: dict) -> tuple:
        """
        Validate agent output after execution.
        
        Args:
            result: Output result to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        return self.get_validation_middleware().validate_output(self.skill_name, result)
    
    def check_dependencies(self, available_outputs: Dict[str, Any]) -> tuple:
        """
        Check if all required dependencies are met.
        
        Args:
            available_outputs: Dict mapping agent names to their outputs
            
        Returns:
            Tuple of (all_met, list_of_missing)
        """
        return self.get_dependency_resolver().check_dependencies_met(
            self.skill_name, available_outputs
        )
    
    def get_shared_state(self, key: str) -> tuple:
        """
        Read from shared versioned state.
        
        Args:
            key: The key to read
            
        Returns:
            Tuple of (value, version) or (None, None) if not found
        """
        return self.get_versioned_state().read(key)
    
    def set_shared_state(self, key: str, value: Any) -> int:
        """
        Write to shared versioned state.
        
        Args:
            key: The key to write
            value: The value to store
            
        Returns:
            New version number
        """
        return self.get_versioned_state().write(key, value, self.skill_name)

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
        # Create input data for validation
        input_data = {
            "task_id": f"task_{id(self)}_{id(task)}",
            "instruction": task,
            "context": context or {},
            "skills_hint": self.skill.tools
        }
        
        # Validate input
        valid, error = self.validate_input(input_data)
        if not valid and self.verbose:
            print(f"[BaseAgent] Input validation failed: {error}")
        
        # Build prompt
        prompt = f"Task: {task}\n"
        if context:
            prompt += f"Context: {json.dumps(context, indent=2)}\n"
            
        # Optional: Ask RAG Manager if any specific domain knowledge is relevant
        rag_context = query_knowledge(task)
        if rag_context:
            prompt += f"\nRelevant Domain Knowledge:\n{rag_context}\n"

        schema_hint = ExecutionResult.schema_json()
        
        response_dict = self.client.ask_json(prompt, schema_hint=schema_hint)
        
        # Validate output
        valid, error = self.validate_output(response_dict)
        if not valid and self.verbose:
            print(f"[BaseAgent] Output validation failed: {error}")
        
        # Parse into execution result, handle partial parsing gracefully
        try:
            return ExecutionResult(**response_dict)
        except Exception as e:
            return ExecutionResult(
                status="error",
                data={"raw": response_dict, "error": str(e)},
                message="Failed to parse response into standard schema."
            )

    def reset(self):
        """Reset the agent's memory/history."""
        self.client.reset()
