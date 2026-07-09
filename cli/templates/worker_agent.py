"""__AGENT_CLASS__ Agent — Worker Template

A worker agent executes domain-specific tasks.
Inherits from BaseAgent and loads capabilities from JSON skills.
"""

from core.base_agent import BaseAgent
from core.result_schema import ExecutionResult


class __AGENT_CLASS__Agent(BaseAgent):
    """
    __AGENT_CLASS__ Worker Agent
    
    Executes tasks in the __AGENT_NAME__ domain.
    Loads capabilities from skills/__AGENT_NAME__.json
    """
    
    def __init__(self, verbose: bool = False):
        super().__init__(
            skill_name="__AGENT_NAME__",
            domain="workers",
            verbose=verbose
        )
    
    def execute_task(self, task: str, context: dict = None) -> ExecutionResult:
        """
        Execute a task in this agent's domain.
        
        Args:
            task: The task description or instruction
            context: Optional context dict with additional inputs
        
        Returns:
            ExecutionResult with status, message, and output data
        """
        return super().execute_task(task, context)
    
    def run_interactive(self):
        """Run the agent in interactive mode"""
        print(f"\n{'='*50}")
        print(f"  {self.skill.name}")
        print(f"{'='*50}\n")
        
        while True:
            task = input(f"[{self.skill.name}] Enter task (or 'quit'): ").strip()
            
            if task.lower() in ["quit", "exit", "q"]:
                break
            
            if not task:
                continue
            
            result = self.execute_task(task)
            
            print(f"\n[Status] {result.status}")
            print(f"[Message] {result.message}")
            if result.data:
                print(f"[Output] {result.data}")
            print()
