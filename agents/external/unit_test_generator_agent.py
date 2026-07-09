"""
agents/external/unit_test_generator_agent.py
==============================================
Unit Test Generator Agent — adapted from 500-AI-Agents / 15-unit-test-generator
This version: Gemini 2.5 Flash — generates pytest/unittest/Jest tests from code.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from core import make_client
from tools.output_manager import save_output
from tools.agent_skill_loader import load_skills_for_task, get_skill_loader
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

console = Console()

SYSTEM_PROMPT = """
You are a software testing expert who writes clean, comprehensive unit tests.

You generate test files that follow best practices:
- Arrange-Act-Assert (AAA) pattern
- Descriptive test names: test_<function>_<condition>_<expected_result>
- Happy path + edge cases + error/exception cases
- Proper mocking for external dependencies
- One assertion focus per test

Supported frameworks: pytest, unittest (Python), Jest/Vitest (JS/TS)
Auto-detect language from code unless explicitly specified.

Output: Return the complete test file as a JSON object:
{
  "language": "python | javascript | typescript",
  "framework": "pytest | unittest | jest | vitest",
  "test_file": "// Full test file content as a string",
  "test_count": 5,
  "coverage_areas": ["happy path", "edge cases", "error handling"],
  "mock_strategy": "Description of what was mocked and why",
  "run_command": "pytest tests/test_module.py -v"
}

Rules:
- Test names must be descriptive — no test_1, test_2.
- Every test must have exactly one assertion focus.
- Mocks must be properly cleaned up (fixtures or context managers).
- Never test implementation details — test observable behavior only.
- Add a one-line docstring to each test explaining what it verifies.
"""


class UnitTestGeneratorAgent:
    """
    Unit Test Generator Agent.
    Generates comprehensive unit tests from code snippets.
    """

    name = "unit_test_generator_agent"
    role = "worker"
    description = (
        "Generates unit tests for any function, class, or module. "
        "Supports Python (pytest/unittest) and JavaScript/TypeScript (Jest/Vitest). "
        "Creates happy path, edge case, and error condition tests with proper mocking. "
        "Best for: adding test coverage, TDD, code review support."
    )
    skill_id = "unit_test_generator_skill"

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.client = make_client(SYSTEM_PROMPT, "TEST-GEN")

    def get_metadata(self) -> dict:
        return {
            "name": self.name,
            "role": self.role,
            "description": self.description,
            "skills": [self.skill_id],
        }

    def generate_tests(
        self,
        code: str,
        language: str = "auto",
        framework: str = "auto",
        module_name: str = "module",
    ) -> dict:
        """
        Generate unit tests for the provided code.

        Args:
            code: Source code to write tests for.
            language: "python" | "javascript" | "typescript" | "auto"
            framework: "pytest" | "unittest" | "jest" | "vitest" | "auto"
            module_name: Module or class name for import statements.

        Returns:
            dict with test_file (string), framework, test_count, coverage_areas, run_command.
        """
        console.print(f"\n[cyan]TEST GENERATOR:[/cyan] Generating tests for {module_name}")

        # Load skill guidance
        skills = load_skills_for_task(f"unit test {module_name}", top_k=1)
        skill_block = ""
        if skills:
            loader = get_skill_loader()
            skill_block = loader.build_skill_prompt(skills)

        prompt = (
            f"Generate unit tests for this code:\n\n"
            f"```{language if language != 'auto' else ''}\n{code}\n```\n\n"
            f"Module/class name: {module_name}\n"
            f"Language: {language}\n"
            f"Framework: {framework}\n\n"
            f"{skill_block}\n"
            f"Generate comprehensive unit tests covering: happy path, edge cases, "
            f"error handling, and any external dependency mocking."
        )

        result = self.client.ask_json(prompt)
        save_output("unit_test_generator", f"tests_{module_name}", result, "json")
        return result

    def run(self, input_data: dict) -> dict:
        """BaseAgent-compatible run() method."""
        task_id = input_data.get("task_id", "test_task")
        instruction = input_data.get("instruction", "")
        context_data = input_data.get("context", {})

        # The instruction may contain code directly, or code may be in context
        code = context_data.get("code", instruction)
        language = context_data.get("language", "auto")
        framework = context_data.get("framework", "auto")
        module_name = context_data.get("module_name", "module")

        try:
            result = self.generate_tests(
                code=code,
                language=language,
                framework=framework,
                module_name=module_name,
            )
            return {
                "success": True,
                "agent_name": self.name,
                "task_id": task_id,
                "output": result,
                "error": None,
                "metadata": {"test_count": result.get("test_count", 0)},
                "context_for_next": {"test_file": result.get("test_file", "")},
            }
        except Exception as e:
            return {
                "success": False,
                "agent_name": self.name,
                "task_id": task_id,
                "output": None,
                "error": str(e),
                "metadata": {},
                "context_for_next": {},
            }

    def run_interactive(self):
        """Standalone interactive mode."""
        console.print(Panel(
            "[bold cyan]UNIT TEST GENERATOR[/bold cyan]\n"
            "[dim]Powered by Gemini 2.5 Flash[/dim]",
            border_style="cyan"
        ))

        while True:
            console.print("\nPaste your code below. Type 'END' on a new line when done (or 'exit' to quit):")
            lines = []
            while True:
                line = input()
                if line.strip().lower() == "exit":
                    return
                if line.strip() == "END":
                    break
                lines.append(line)

            code = "\n".join(lines).strip()
            if not code:
                continue

            module_name = input("Module/function name: ").strip() or "module"
            language = input("Language [auto]: ").strip() or "auto"
            framework = input("Framework [auto]: ").strip() or "auto"

            result = self.generate_tests(code, language=language, framework=framework, module_name=module_name)
            test_file = result.get("test_file", "")
            if test_file:
                syntax = Syntax(test_file, result.get("language", "python"), theme="monokai", line_numbers=True)
                console.print(syntax)
                console.print(f"\n[dim]Run: {result.get('run_command', '')}[/dim]")
