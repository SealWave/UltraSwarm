"""
core/validation_middleware.py
=============================
Middleware for agent input/output validation.
Validates agent inputs before execution and outputs after execution.
"""

from typing import Tuple, Optional, Dict, Any
from core.schema_registry import SchemaRegistry, BaseAgentInputSchema, BaseAgentOutputSchema


class ValidationMiddleware:
    """
    Middleware for agent input/output validation.
    
    Features:
    - Validate agent inputs before execution
    - Validate agent outputs after execution
    - Configurable validation mode (strict/lenient)
    - Graceful error handling (try to recover, execute anyway per design)
    """
    
    def __init__(self, schema_registry: SchemaRegistry, strict_mode: bool = False):
        """
        Initialize the validation middleware.
        
        Args:
            schema_registry: SchemaRegistry instance for schema lookups
            strict_mode: If True, fail on validation errors; if False, try to recover
        """
        self.schema_registry = schema_registry
        self.strict_mode = strict_mode
        self._validation_stats = {
            "input_validations": 0,
            "output_validations": 0,
            "input_failures": 0,
            "output_failures": 0,
            "recoveries": 0
        }
    
    def validate_input(self, agent_name: str, data: dict) -> Tuple[bool, str]:
        """
        Validate agent input before execution.
        
        On failure: Log error, try to recover, execute anyway (per design choice Q2)
        
        Args:
            agent_name: Name of the agent
            data: Input data to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        self._validation_stats["input_validations"] += 1
        
        # Try agent-specific schema first
        schema = self.schema_registry.get_input_schema(agent_name)
        
        # Fall back to base schema if no agent-specific schema
        if schema is None:
            schema = BaseAgentInputSchema
        
        try:
            # Validate the data against the schema
            validated = schema(**data)
            return True, ""
        except Exception as e:
            error_msg = f"Input validation failed for {agent_name}: {str(e)}"
            self._validation_stats["input_failures"] += 1
            
            # Per design: Log error, try to recover, execute anyway
            if self.strict_mode:
                return False, error_msg
            else:
                print(f"[WARNING] {error_msg}")
                print("[RECOVERY] Executing agent anyway with provided input...")
                self._validation_stats["recoveries"] += 1
                return True, f"Recovered from validation error: {error_msg}"
    
    def validate_output(self, agent_name: str, result: dict) -> Tuple[bool, str]:
        """
        Validate agent output after execution.
        
        On failure: Log error, try to recover, execute anyway (per design choice Q2)
        
        Args:
            agent_name: Name of the agent
            result: Output result to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        self._validation_stats["output_validations"] += 1
        
        # Try agent-specific schema first
        schema = self.schema_registry.get_output_schema(agent_name)
        
        # Fall back to base schema if no agent-specific schema
        if schema is None:
            schema = BaseAgentOutputSchema
        
        try:
            # Validate the result against the schema
            validated = schema(**result)
            return True, ""
        except Exception as e:
            error_msg = f"Output validation failed for {agent_name}: {str(e)}"
            self._validation_stats["output_failures"] += 1
            
            # Per design: Log error, try to recover, execute anyway
            if self.strict_mode:
                return False, error_msg
            else:
                print(f"[WARNING] {error_msg}")
                print("[RECOVERY] Returning partial result from agent...")
                self._validation_stats["recoveries"] += 1
                return True, f"Recovered from validation error: {error_msg}"
    
    def set_strict_mode(self, enabled: bool):
        """Enable or disable strict validation mode"""
        self.strict_mode = enabled
    
    def get_stats(self) -> Dict[str, int]:
        """Get validation statistics"""
        return self._validation_stats.copy()
    
    def reset_stats(self):
        """Reset validation statistics"""
        self._validation_stats = {
            "input_validations": 0,
            "output_validations": 0,
            "input_failures": 0,
            "output_failures": 0,
            "recoveries": 0
        }


# Global middleware instance
_validation_middleware = None


def get_validation_middleware() -> ValidationMiddleware:
    """Get or create the global validation middleware instance"""
    global _validation_middleware
    if _validation_middleware is None:
        from core.schema_registry import get_schema_registry
        _validation_middleware = ValidationMiddleware(get_schema_registry())
    return _validation_middleware
