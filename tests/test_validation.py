"""
tests/test_validation.py
========================
Tests for validation middleware fundamentals.
Tests schema registry, validation middleware, dependency resolver, and versioned state.
"""

import pytest
from datetime import datetime

from core.schema_registry import (
    SchemaRegistry, 
    BaseAgentInputSchema, 
    BaseAgentOutputSchema,
    get_schema_registry
)
from core.validation_middleware import (
    ValidationMiddleware,
    get_validation_middleware
)
from core.dependencies import (
    DependencyResolver,
    get_dependency_resolver
)
from core.versioned_state import (
    VersionedState,
    VersionedValue,
    get_versioned_state
)


# =============================================================================
# Schema Registry Tests
# =============================================================================

class TestSchemaRegistry:
    """Test schema registration and retrieval"""

    def test_schema_registry_creation(self):
        """Test that schema registry can be created"""
        registry = SchemaRegistry()
        assert registry is not None

    def test_input_schema_registration(self):
        """Test that input schemas can be registered"""
        registry = SchemaRegistry()
        
        # Create a custom schema
        from pydantic import BaseModel, Field
        from typing import Optional, Dict, Any
        
        class CustomInputSchema(BaseModel):
            task_id: str = Field(..., description="Task ID")
            instruction: str = Field(..., description="Instruction")
            custom_field: Optional[str] = Field(default=None, description="Custom field")
        
        # Register the schema
        version = registry.register_input_schema("test_agent", CustomInputSchema)
        
        assert version is not None
        assert registry.has_input_schema("test_agent")
        assert registry.get_input_schema("test_agent") == CustomInputSchema

    def test_output_schema_registration(self):
        """Test that output schemas can be registered"""
        registry = SchemaRegistry()
        
        from pydantic import BaseModel, Field
        from typing import Optional, Dict, Any
        
        class CustomOutputSchema(BaseModel):
            success: bool = Field(..., description="Success status")
            agent_name: str = Field(..., description="Agent name")
            task_id: str = Field(..., description="Task ID")
            custom_output: Optional[str] = Field(default=None, description="Custom output")
        
        version = registry.register_output_schema("test_agent", CustomOutputSchema)
        
        assert version is not None
        assert registry.has_output_schema("test_agent")
        assert registry.get_output_schema("test_agent") == CustomOutputSchema

    def test_missing_schema_returns_none(self):
        """Test that missing schemas return None"""
        registry = SchemaRegistry()
        
        assert registry.get_input_schema("nonexistent_agent") is None
        assert registry.get_output_schema("nonexistent_agent") is None
        assert registry.has_input_schema("nonexistent_agent") is False
        assert registry.has_output_schema("nonexistent_agent") is False

    def test_schema_version_tracking(self):
        """Test that schema versions are tracked"""
        registry = SchemaRegistry()
        
        from pydantic import BaseModel
        
        class TestSchema(BaseModel):
            field: str
        
        version = registry.register_input_schema("versioned_agent", TestSchema)
        assert version is not None
        
        retrieved_version = registry.get_schema_version("versioned_agent", "input")
        assert retrieved_version == version

    def test_list_registered_agents(self):
        """Test listing all registered agents"""
        registry = SchemaRegistry()
        
        from pydantic import BaseModel
        
        class InputSchema(BaseModel):
            field: str
        
        class OutputSchema(BaseModel):
            result: str
        
        registry.register_input_schema("agent1", InputSchema)
        registry.register_output_schema("agent1", OutputSchema)
        registry.register_input_schema("agent2", InputSchema)
        
        registered = registry.list_registered_agents()
        
        assert "agent1" in registered
        assert "agent2" in registered
        assert registered["agent1"]["has_input_schema"] is True
        assert registered["agent1"]["has_output_schema"] is True
        assert registered["agent2"]["has_input_schema"] is True
        assert registered["agent2"]["has_output_schema"] is False

    def test_clear_all(self):
        """Test clearing all schemas"""
        registry = SchemaRegistry()
        
        from pydantic import BaseModel
        
        class TestSchema(BaseModel):
            field: str
        
        registry.register_input_schema("agent1", TestSchema)
        registry.register_output_schema("agent2", TestSchema)
        
        registry.clear_all()
        
        assert registry.get_input_schema("agent1") is None
        assert registry.get_output_schema("agent2") is None

    def test_global_schema_registry(self):
        """Test global schema registry singleton"""
        registry1 = get_schema_registry()
        registry2 = get_schema_registry()
        
        assert registry1 is registry2


# =============================================================================
# Validation Middleware Tests
# =============================================================================

class TestValidationMiddleware:
    """Test validation middleware functionality"""

    def test_middleware_creation(self):
        """Test that middleware can be created"""
        registry = SchemaRegistry()
        middleware = ValidationMiddleware(registry)
        
        assert middleware is not None
        assert middleware.schema_registry is registry

    def test_valid_base_input_validation(self):
        """Test that valid input passes validation with base schema"""
        registry = SchemaRegistry()
        middleware = ValidationMiddleware(registry)
        
        valid_data = {
            "task_id": "test_task_123",
            "instruction": "Do something"
        }
        
        is_valid, error = middleware.validate_input("test_agent", valid_data)
        
        assert is_valid is True
        assert error == ""

    def test_invalid_input_validation_strict_mode(self):
        """Test that invalid input fails validation in strict mode"""
        registry = SchemaRegistry()
        middleware = ValidationMiddleware(registry, strict_mode=True)
        
        # Missing required field 'task_id'
        invalid_data = {
            "instruction": "Do something"
        }
        
        is_valid, error = middleware.validate_input("test_agent", invalid_data)
        
        assert is_valid is False
        assert "validation failed" in error.lower()

    def test_invalid_input_validation_lenient_mode(self):
        """Test that invalid input is recovered in lenient mode"""
        registry = SchemaRegistry()
        middleware = ValidationMiddleware(registry, strict_mode=False)
        
        # Missing required field 'task_id'
        invalid_data = {
            "instruction": "Do something"
        }
        
        is_valid, error = middleware.validate_input("test_agent", invalid_data)
        
        # In lenient mode, should recover
        assert is_valid is True
        assert "Recovered" in error

    def test_valid_base_output_validation(self):
        """Test that valid output passes validation with base schema"""
        registry = SchemaRegistry()
        middleware = ValidationMiddleware(registry)
        
        valid_output = {
            "success": True,
            "agent_name": "test_agent",
            "task_id": "test_task_123"
        }
        
        is_valid, error = middleware.validate_output("test_agent", valid_output)
        
        assert is_valid is True
        assert error == ""

    def test_invalid_output_validation_strict_mode(self):
        """Test that invalid output fails validation in strict mode"""
        registry = SchemaRegistry()
        middleware = ValidationMiddleware(registry, strict_mode=True)
        
        # Missing required field 'success'
        invalid_output = {
            "agent_name": "test_agent",
            "task_id": "test_task_123"
        }
        
        is_valid, error = middleware.validate_output("test_agent", invalid_output)
        
        assert is_valid is False
        assert "validation failed" in error.lower()

    def test_validation_stats_tracking(self):
        """Test that validation statistics are tracked"""
        registry = SchemaRegistry()
        middleware = ValidationMiddleware(registry)
        
        # Perform some validations
        middleware.validate_input("agent1", {"task_id": "1", "instruction": "test"})
        middleware.validate_input("agent2", {"task_id": "2", "instruction": "test"})
        middleware.validate_output("agent1", {"success": True, "agent_name": "agent1", "task_id": "1"})
        
        stats = middleware.get_stats()
        
        assert stats["input_validations"] == 2
        assert stats["output_validations"] == 1

    def test_validation_stats_reset(self):
        """Test that validation statistics can be reset"""
        registry = SchemaRegistry()
        middleware = ValidationMiddleware(registry)
        
        middleware.validate_input("agent1", {"task_id": "1", "instruction": "test"})
        
        middleware.reset_stats()
        stats = middleware.get_stats()
        
        assert stats["input_validations"] == 0

    def test_global_validation_middleware(self):
        """Test global validation middleware singleton"""
        middleware1 = get_validation_middleware()
        middleware2 = get_validation_middleware()
        
        assert middleware1 is middleware2


# =============================================================================
# Dependency Resolver Tests
# =============================================================================

class TestDependencyResolver:
    """Test dependency resolution"""

    def test_resolver_creation(self):
        """Test that resolver can be created"""
        resolver = DependencyResolver()
        assert resolver is not None

    def test_dependency_registration(self):
        """Test that dependencies can be registered"""
        resolver = DependencyResolver()
        
        resolver.register_dependency("agent_a", ["agent_b", "agent_c"])
        
        deps = resolver.get_dependencies("agent_a")
        assert "agent_b" in deps
        assert "agent_c" in deps

    def test_reverse_dependencies(self):
        """Test reverse dependency tracking"""
        resolver = DependencyResolver()
        
        resolver.register_dependency("agent_a", ["agent_b"])
        resolver.register_dependency("agent_c", ["agent_b"])
        
        dependents = resolver.get_dependents("agent_b")
        
        assert "agent_a" in dependents
        assert "agent_c" in dependents

    def test_dependencies_met(self):
        """Test dependency check with available outputs"""
        resolver = DependencyResolver()
        resolver.register_dependency("agent_a", ["agent_b"])
        
        available = {"agent_b": {"output": "data"}}
        met, missing = resolver.check_dependencies_met("agent_a", available)
        
        assert met is True
        assert missing == []

    def test_dependencies_not_met(self):
        """Test dependency check with missing outputs"""
        resolver = DependencyResolver()
        resolver.register_dependency("agent_a", ["agent_b", "agent_c"])
        
        available = {"agent_b": {"output": "data"}}
        met, missing = resolver.check_dependencies_met("agent_a", available)
        
        assert met is False
        assert "agent_c" in missing

    def test_no_dependencies(self):
        """Test dependency check for agent with no dependencies"""
        resolver = DependencyResolver()
        
        met, missing = resolver.check_dependencies_met("standalone_agent", {})
        
        assert met is True
        assert missing == []

    def test_circular_dependency_detection(self):
        """Test that circular dependencies are detected"""
        resolver = DependencyResolver()
        
        # Create a circular dependency: A -> B -> C -> A
        resolver.register_dependency("agent_a", ["agent_b"])
        resolver.register_dependency("agent_b", ["agent_c"])
        resolver.register_dependency("agent_c", ["agent_a"])
        
        conflicts = resolver.detect_conflicts(["agent_a", "agent_b", "agent_c"])
        
        assert len(conflicts) > 0
        assert "Circular dependency" in conflicts[0]

    def test_no_circular_dependency(self):
        """Test that no conflicts are detected for valid dependencies"""
        resolver = DependencyResolver()
        
        # Linear dependencies: A -> B -> C
        resolver.register_dependency("agent_a", ["agent_b"])
        resolver.register_dependency("agent_b", ["agent_c"])
        
        conflicts = resolver.detect_conflicts(["agent_a", "agent_b", "agent_c"])
        
        assert len(conflicts) == 0

    def test_topological_sort(self):
        """Test topological sorting of agents"""
        resolver = DependencyResolver()
        
        # A depends on B, B depends on C
        resolver.register_dependency("agent_a", ["agent_b"])
        resolver.register_dependency("agent_b", ["agent_c"])
        
        sorted_agents, cycles = resolver.topological_sort(
            ["agent_a", "agent_b", "agent_c"]
        )
        
        # C should come before B, B before A
        assert sorted_agents.index("agent_c") < sorted_agents.index("agent_b")
        assert sorted_agents.index("agent_b") < sorted_agents.index("agent_a")
        assert len(cycles) == 0

    def test_topological_sort_with_cycle(self):
        """Test topological sort with circular dependency"""
        resolver = DependencyResolver()
        
        # Circular: A -> B -> A
        resolver.register_dependency("agent_a", ["agent_b"])
        resolver.register_dependency("agent_b", ["agent_a"])
        
        sorted_agents, cycles = resolver.topological_sort(["agent_a", "agent_b"])
        
        # Should not sort completely due to cycle
        assert len(cycles) > 0

    def test_get_required_outputs(self):
        """Test getting required outputs"""
        resolver = DependencyResolver()
        resolver.register_dependency("agent_a", ["agent_b", "agent_c"])
        
        available = {
            "agent_b": {"data": "b_output"},
            "agent_c": {"data": "c_output"},
            "agent_d": {"data": "d_output"}
        }
        
        required = resolver.get_required_outputs("agent_a", available)
        
        assert "agent_b" in required
        assert "agent_c" in required
        assert "agent_d" not in required

    def test_clear_all_dependencies(self):
        """Test clearing all dependencies"""
        resolver = DependencyResolver()
        
        resolver.register_dependency("agent_a", ["agent_b"])
        resolver.clear_all()
        
        assert resolver.get_dependencies("agent_a") == []

    def test_global_dependency_resolver(self):
        """Test global dependency resolver singleton"""
        resolver1 = get_dependency_resolver()
        resolver2 = get_dependency_resolver()
        
        assert resolver1 is resolver2


# =============================================================================
# Versioned State Tests
# =============================================================================

class TestVersionedState:
    """Test versioned state management"""

    def test_state_creation(self):
        """Test that versioned state can be created"""
        state = VersionedState()
        assert state is not None

    def test_write_and_read(self):
        """Test basic write and read operations"""
        state = VersionedState()
        
        version = state.write("test_key", "test_value", "agent1")
        value, stored_version = state.read("test_key")
        
        assert value == "test_value"
        assert stored_version == version

    def test_version_increment(self):
        """Test that version increments on write"""
        state = VersionedState()
        
        v1 = state.write("key", "value1", "agent1")
        v2 = state.write("key", "value2", "agent2")
        
        assert v2 > v1
        assert v2 == v1 + 1

    def test_read_nonexistent_key(self):
        """Test reading a key that doesn't exist"""
        state = VersionedState()
        
        value, version = state.read("nonexistent_key")
        
        assert value is None
        assert version is None

    def test_conflict_detection(self):
        """Test that version conflicts are detected"""
        state = VersionedState()
        
        state.write("key", "value1", "agent1")
        state.write("key", "value2", "agent2")
        
        # Check for conflict with old version
        conflict = state.get_conflict("key", 1)
        
        assert conflict is not None
        assert "Version mismatch" in conflict

    def test_no_conflict(self):
        """Test that no conflict is detected for matching versions"""
        state = VersionedState()
        
        version = state.write("key", "value", "agent1")
        
        conflict = state.get_conflict("key", version)
        
        assert conflict is None

    def test_check_conflict_free_success(self):
        """Test atomic conflict-free write succeeds"""
        state = VersionedState()
        
        v1 = state.write("key", "value1", "agent1")
        
        # Should succeed - version matches
        success = state.check_conflict_free("key", v1, "value2", "agent2")
        
        assert success is True
        
        # Verify write happened
        value, version = state.read("key")
        assert value == "value2"
        assert version == v1 + 1

    def test_check_conflict_free_failure(self):
        """Test atomic conflict-free write fails on conflict"""
        state = VersionedState()
        
        state.write("key", "value1", "agent1")
        state.write("key", "value2", "agent2")  # Now at version 2
        
        # Try to write with stale version 1
        success = state.check_conflict_free("key", 1, "value3", "agent3")
        
        assert success is False

    def test_key_exists(self):
        """Test checking if a key exists"""
        state = VersionedState()
        
        assert state.exists("key") is False
        
        state.write("key", "value", "agent1")
        
        assert state.exists("key") is True

    def test_delete_key(self):
        """Test deleting a key"""
        state = VersionedState()
        
        state.write("key", "value", "agent1")
        
        result = state.delete("key", "agent1")
        
        assert result is True
        assert state.exists("key") is False

    def test_delete_nonexistent_key(self):
        """Test deleting a nonexistent key"""
        state = VersionedState()
        
        result = state.delete("nonexistent_key", "agent1")
        
        assert result is False

    def test_get_all_keys(self):
        """Test getting all keys"""
        state = VersionedState()
        
        state.write("key1", "value1", "agent1")
        state.write("key2", "value2", "agent1")
        state.write("key3", "value3", "agent1")
        
        keys = state.get_all_keys()
        
        assert len(keys) == 3
        assert "key1" in keys
        assert "key2" in keys
        assert "key3" in keys

    def test_access_log(self):
        """Test access logging"""
        state = VersionedState()
        
        state.write("key", "value", "agent1")
        state.read("key")
        
        log = state.get_access_log("key")
        
        assert len(log) >= 2
        actions = [entry["action"] for entry in log]
        assert "write" in actions
        assert "read" in actions

    def test_snapshot(self):
        """Test getting state snapshot"""
        state = VersionedState()
        
        state.write("key1", "value1", "agent1")
        state.write("key2", "value2", "agent2")
        
        snapshot = state.snapshot()
        
        assert "key1" in snapshot
        assert "key2" in snapshot
        assert snapshot["key1"]["value"] == "value1"
        assert snapshot["key2"]["value"] == "value2"

    def test_read_with_metadata(self):
        """Test reading value with full metadata"""
        state = VersionedState()
        
        state.write("key", "value", "agent1", {"custom": "metadata"})
        
        versioned_value = state.read_with_metadata("key")
        
        assert versioned_value is not None
        assert versioned_value.value == "value"
        assert versioned_value.writer == "agent1"
        assert versioned_value.metadata == {"custom": "metadata"}

    def test_clear_all_state(self):
        """Test clearing all state"""
        state = VersionedState()
        
        state.write("key1", "value1", "agent1")
        state.write("key2", "value2", "agent1")
        
        state.clear_all()
        
        assert state.get_all_keys() == []

    def test_global_versioned_state(self):
        """Test global versioned state singleton"""
        state1 = get_versioned_state()
        state2 = get_versioned_state()
        
        assert state1 is state2


class TestVersionedValue:
    """Test VersionedValue dataclass"""

    def test_versioned_value_creation(self):
        """Test creating a versioned value"""
        timestamp = datetime.utcnow()
        
        value = VersionedValue(
            value="test_value",
            version=1,
            timestamp=timestamp,
            writer="agent1"
        )
        
        assert value.value == "test_value"
        assert value.version == 1
        assert value.timestamp == timestamp
        assert value.writer == "agent1"

    def test_versioned_value_with_metadata(self):
        """Test versioned value with metadata"""
        value = VersionedValue(
            value="test_value",
            version=1,
            timestamp=datetime.utcnow(),
            writer="agent1",
            metadata={"key": "value"}
        )
        
        assert value.metadata == {"key": "value"}


# =============================================================================
# Integration Tests
# =============================================================================

class TestValidationIntegration:
    """Test integration between validation components"""

    def test_full_validation_flow(self):
        """Test complete validation flow with all components"""
        # Create fresh instances
        registry = SchemaRegistry()
        middleware = ValidationMiddleware(registry)
        resolver = DependencyResolver()
        state = VersionedState()
        
        # Register a custom schema
        from pydantic import BaseModel, Field
        from typing import Optional, Dict, Any
        
        class TestInputSchema(BaseModel):
            task_id: str = Field(..., description="Task ID")
            instruction: str = Field(..., description="Instruction")
            context: Optional[Dict[str, Any]] = Field(default=None)
        
        class TestOutputSchema(BaseModel):
            success: bool = Field(..., description="Success")
            agent_name: str = Field(..., description="Agent name")
            task_id: str = Field(..., description="Task ID")
            result: Optional[str] = Field(default=None)
        
        # Register schemas
        registry.register_input_schema("integrated_agent", TestInputSchema)
        registry.register_output_schema("integrated_agent", TestOutputSchema)
        
        # Register dependencies
        resolver.register_dependency("integrated_agent", ["prerequisite_agent"])
        
        # Store prerequisite output in versioned state
        state.write("prerequisite_output", {"data": "prerequisite_data"}, "prerequisite_agent")
        
        # Validate input
        input_data = {
            "task_id": "integrated_task",
            "instruction": "Execute integrated task"
        }
        valid, error = middleware.validate_input("integrated_agent", input_data)
        assert valid is True
        
        # Check dependencies
        prereq_value, _ = state.read("prerequisite_output")
        available = {"prerequisite_agent": prereq_value}
        met, missing = resolver.check_dependencies_met("integrated_agent", available)
        assert met is True
        
        # Validate output
        output_data = {
            "success": True,
            "agent_name": "integrated_agent",
            "task_id": "integrated_task",
            "result": "Task completed"
        }
        valid, error = middleware.validate_output("integrated_agent", output_data)
        assert valid is True

    def test_dependency_resolution_flow(self):
        """Test dependency resolution for agent execution order"""
        resolver = DependencyResolver()
        
        # Define a dependency graph
        # Final -> Intermediate -> Base
        resolver.register_dependency("final_agent", ["intermediate_agent"])
        resolver.register_dependency("intermediate_agent", ["base_agent"])
        
        agents = ["final_agent", "intermediate_agent", "base_agent"]
        
        # Check no circular dependencies
        conflicts = resolver.detect_conflicts(agents)
        assert len(conflicts) == 0
        
        # Get execution order
        sorted_agents, _ = resolver.topological_sort(agents)
        
        # Verify order
        assert sorted_agents.index("base_agent") < sorted_agents.index("intermediate_agent")
        assert sorted_agents.index("intermediate_agent") < sorted_agents.index("final_agent")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
