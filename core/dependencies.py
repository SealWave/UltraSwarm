"""
core/dependencies.py
====================
Dependency resolver for agent output dependencies.
Handles agent dependencies and detects conflicts.
"""

from typing import Dict, List, Tuple, Any, Optional
from collections import defaultdict


class DependencyResolver:
    """
    Resolves dependencies between agents and detects conflicts.
    
    Features:
    - Register dependencies between agents
    - Check if dependencies are met before execution
    - Detect circular dependencies in execution plans
    - Support explicit declaration (per design choice Q3)
    """
    
    def __init__(self):
        self.dependencies: Dict[str, List[str]] = {}  # agent -> [required_agents]
        self.reverse_dependencies: Dict[str, List[str]] = defaultdict(list)  # agent -> [agents_that_depend_on_me]
        self._dependency_metadata: Dict[str, Dict[str, Any]] = {}  # Additional metadata per dependency
    
    def register_dependency(
        self, 
        agent_name: str, 
        requires: List[str],
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Register which agents an agent depends on.
        
        Args:
            agent_name: The agent that has dependencies
            requires: List of agent names this agent depends on
            metadata: Optional metadata about the dependency (e.g., required fields)
        """
        self.dependencies[agent_name] = requires
        for req in requires:
            self.reverse_dependencies[req].append(agent_name)
        
        if metadata:
            for req in requires:
                self._dependency_metadata[f"{agent_name}->{req}"] = metadata
    
    def get_dependencies(self, agent_name: str) -> List[str]:
        """Get agents that the given agent depends on"""
        return self.dependencies.get(agent_name, [])
    
    def get_dependents(self, agent_name: str) -> List[str]:
        """Get agents that depend on the given agent"""
        return self.reverse_dependencies.get(agent_name, [])
    
    def get_dependency_metadata(self, agent_name: str, required_agent: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a specific dependency"""
        return self._dependency_metadata.get(f"{agent_name}->{required_agent}")
    
    def check_dependencies_met(
        self, 
        agent_name: str, 
        available_outputs: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        """
        Check if all required agent outputs are available.
        
        Args:
            agent_name: Name of the agent to check
            available_outputs: Dict mapping agent names to their outputs
            
        Returns:
            Tuple of (all_met, list_of_missing)
        """
        requires = self.dependencies.get(agent_name, [])
        missing = [req for req in requires if req not in available_outputs]
        return len(missing) == 0, missing
    
    def get_required_outputs(self, agent_name: str, available_outputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get the actual outputs required by an agent.
        
        Args:
            agent_name: Name of the agent
            available_outputs: Dict mapping agent names to their outputs
            
        Returns:
            Dict mapping required agent names to their outputs (only available ones)
        """
        requires = self.dependencies.get(agent_name, [])
        return {
            req: available_outputs[req] 
            for req in requires 
            if req in available_outputs
        }
    
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
        
        Args:
            agent_plan: List of agent names to sort
            
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
    
    def get_execution_order(self, agent_names: List[str]) -> List[str]:
        """
        Get the optimal execution order for a set of agents.
        
        Args:
            agent_names: List of agent names to execute
            
        Returns:
            List of agent names in optimal execution order
        """
        sorted_agents, _ = self.topological_sort(agent_names)
        return sorted_agents
    
    def clear_all(self):
        """Clear all registered dependencies (useful for testing)"""
        self.dependencies.clear()
        self.reverse_dependencies.clear()
        self._dependency_metadata.clear()
    
    def get_all_dependencies(self) -> Dict[str, List[str]]:
        """Get a copy of all registered dependencies"""
        return self.dependencies.copy()


# Global dependency resolver instance
_dependency_resolver = None


def get_dependency_resolver() -> DependencyResolver:
    """Get or create the global dependency resolver instance"""
    global _dependency_resolver
    if _dependency_resolver is None:
        _dependency_resolver = DependencyResolver()
    return _dependency_resolver
