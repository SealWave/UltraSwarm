from pydantic import BaseModel, Field
from typing import List

class AgentPlan(BaseModel):
    """Standardized plan structure for agent execution."""
    goal: str = Field(..., description="The overall goal to achieve.")
    steps: List[str] = Field(..., description="A step-by-step breakdown of actions required.")
    estimated_complexity: str = Field(..., description="Complexity estimate: 'low', 'medium', 'high'")
