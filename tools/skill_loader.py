import json
import os
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class AgentSkill(BaseModel):
    name: str
    role: str
    system_prompt: str
    tools: List[str] = []
    context: Dict[str, Any] = {}

def load_skill(skill_name: str, domain: str = "ecommerce") -> AgentSkill:
    """
    Load an agent skill definition from a JSON file.
    Example: load_skill("seo_agent", "ecommerce") will load skills/ecommerce/seo_agent.json
    """
    skills_dir = Path(__file__).parent.parent / "skills" / domain
    skill_file = skills_dir / f"{skill_name}.json"
    
    if not skill_file.exists():
        raise FileNotFoundError(f"Skill file not found: {skill_file}")
        
    with open(skill_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    return AgentSkill(**data)
