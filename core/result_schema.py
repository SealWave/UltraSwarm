from pydantic import BaseModel, Field
from typing import Optional, Any, Dict

class ExecutionResult(BaseModel):
    """Standardized output for all agents across all domains."""
    status: str = Field(..., description="Status of the execution: 'success', 'error', 'partial'")
    data: Dict[str, Any] = Field(default_factory=dict, description="The payload of the result.")
    message: str = Field(..., description="A human-readable summary of the execution outcome.")
    next_steps: Optional[str] = Field(None, description="Recommended next steps or actions.")
