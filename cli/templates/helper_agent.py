"""__AGENT_CLASS__ Agent — Helper Template

A helper agent provides cognitive/utility functions.
Inherits from BaseAgent and loads capabilities from JSON skills.
Does not dispatch to other agents (terminal node).
"""

from core.base_agent import BaseAgent
from core.result_schema import ExecutionResult


class __AGENT_CLASS__Agent(BaseAgent):
    """
    __AGENT_CLASS__ Helper Agent
    
    Provides cognitive support for __AGENT_NAME__ tasks.
    Does not delegate to other agents.
    Loads capabilities from skills/__AGENT_NAME__.json
    """
    
    def __init__(self, verbose: bool = False):
        super().__init__(
            skill_name="__AGENT_NAME__",
            domain="helpers",
            verbose=verbose
        )
    
    def execute_task(self, task: str, context: dict = None) -> ExecutionResult:
        """
        Execute a cognitive task.
        
        Args:
            task: The task description or instruction
            context: Optional context dict with additional inputs
        
        Returns:
            ExecutionResult with status, message, and output data
        """
        return super().execute_task(task, context)
    
    def think(self, prompt: str, context: dict = None) -> str:
        """
        Think through a problem and return analysis.
        
        Args:
            prompt: The problem or question to analyze
            context: Optional context for analysis
        
        Returns:
            Analysis or thinking result as string
        """
        result = self.execute_task(prompt, context)
        return result.message if result.status == "success" else result.data or ""
    
    def run_interactive(self):
        """Run the agent in interactive mode"""
        print(f"\n{'='*50}")
        print(f"  {self.skill.name} (Helper)")
        print(f"{'='*50}\n")
        
        while True:
            prompt = input(f"[{self.skill.name}] Ask or think about: ").strip()
            
            if prompt.lower() in ["quit", "exit", "q"]:
                break
            
            if not prompt:
                continue
            
            result = self.execute_task(prompt)
            
            print(f"\n[Analysis]\n{result.message}\n")
