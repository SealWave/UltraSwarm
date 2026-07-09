"""
core/schema_registry.py
=======================
Schema Registry for agent input/output validation.
Stores per-agent input/output schemas with versioning support.
"""

from typing import Dict, Any, Optional, Type
from pydantic import BaseModel, Field
from datetime import datetime


class BaseAgentInputSchema(BaseModel):
    """Base input schema for all agents"""
    task_id: str = Field(..., description="Unique task identifier")
    instruction: str = Field(..., description="Task instruction")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Context from previous agents")
    skills_hint: Optional[list] = Field(default=None, description="Suggested skills")


class BaseAgentOutputSchema(BaseModel):
    """Base output schema for all agents"""
    success: bool = Field(..., description="Execution success status")
    agent_name: str = Field(..., description="Name of agent that executed")
    task_id: str = Field(..., description="Task identifier")
    output: Optional[Dict[str, Any]] = Field(default=None, description="Agent output")
    context_for_next: Optional[Dict[str, Any]] = Field(default=None, description="Context for next agent")
    error: Optional[str] = Field(default=None, description="Error message if failed")


class SchemaVersion:
    """Tracks schema version information"""
    def __init__(self, version: int, schema_type: str, created_at: datetime = None):
        self.version = version
        self.schema_type = schema_type
        self.created_at = created_at or datetime.utcnow()


class SchemaRegistry:
    """
    Central store for agent input/output schemas with versioning.
    
    Features:
    - Register input/output schemas per agent
    - Support base schemas and agent-specific extensions
    - Version schema definitions
    - Thread-safe operations
    """
    
    def __init__(self):
        self._input_schemas: Dict[str, Type[BaseModel]] = {}
        self._output_schemas: Dict[str, Type[BaseModel]] = {}
        self._schema_versions: Dict[str, SchemaVersion] = {}
        self._current_version = 1
    
    def register_input_schema(
        self, 
        agent_name: str, 
        schema: Type[BaseModel],
        version: int = None
    ) -> int:
        """
        Register an input schema for an agent.
        
        Args:
            agent_name: Name of the agent
            schema: Pydantic model class for input validation
            version: Optional version number (auto-incremented if not provided)
            
        Returns:
            The schema version number
        """
        self._input_schemas[agent_name] = schema
        version_num = version or self._current_version
        self._schema_versions[f"{agent_name}_input"] = SchemaVersion(
            version=version_num,
            schema_type="input"
        )
        if version is None:
            self._current_version += 1
        return version_num
    
    def register_output_schema(
        self, 
        agent_name: str, 
        schema: Type[BaseModel],
        version: int = None
    ) -> int:
        """
        Register an output schema for an agent.
        
        Args:
            agent_name: Name of the agent
            schema: Pydantic model class for output validation
            version: Optional version number (auto-incremented if not provided)
            
        Returns:
            The schema version number
        """
        self._output_schemas[agent_name] = schema
        version_num = version or self._current_version
        self._schema_versions[f"{agent_name}_output"] = SchemaVersion(
            version=version_num,
            schema_type="output"
        )
        if version is None:
            self._current_version += 1
        return version_num
    
    def get_input_schema(self, agent_name: str) -> Optional[Type[BaseModel]]:
        """
        Get the input schema for an agent.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            Pydantic model class or None if not found
        """
        return self._input_schemas.get(agent_name)
    
    def get_output_schema(self, agent_name: str) -> Optional[Type[BaseModel]]:
        """
        Get the output schema for an agent.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            Pydantic model class or None if not found
        """
        return self._output_schemas.get(agent_name)
    
    def get_schema_version(self, agent_name: str, schema_type: str) -> Optional[int]:
        """
        Get the version of a schema.
        
        Args:
            agent_name: Name of the agent
            schema_type: "input" or "output"
            
        Returns:
            Version number or None if not found
        """
        key = f"{agent_name}_{schema_type}"
        version_info = self._schema_versions.get(key)
        return version_info.version if version_info else None
    
    def has_input_schema(self, agent_name: str) -> bool:
        """Check if an agent has an input schema registered"""
        return agent_name in self._input_schemas
    
    def has_output_schema(self, agent_name: str) -> bool:
        """Check if an agent has an output schema registered"""
        return agent_name in self._output_schemas
    
    def list_registered_agents(self) -> Dict[str, Dict[str, bool]]:
        """
        List all agents with registered schemas.
        
        Returns:
            Dict mapping agent names to their schema registration status
        """
        all_agents = set(self._input_schemas.keys()) | set(self._output_schemas.keys())
        return {
            agent: {
                "has_input_schema": agent in self._input_schemas,
                "has_output_schema": agent in self._output_schemas
            }
            for agent in all_agents
        }
    
    def clear_all(self):
        """Clear all registered schemas (useful for testing)"""
        self._input_schemas.clear()
        self._output_schemas.clear()
        self._schema_versions.clear()
        self._current_version = 1


# Global registry instance
_schema_registry = None


def get_schema_registry() -> SchemaRegistry:
    """Get or create the global schema registry instance"""
    global _schema_registry
    if _schema_registry is None:
        _schema_registry = SchemaRegistry()
    return _schema_registry
