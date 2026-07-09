# SKILL: Unit Test Generator Agent
**Agent ID:** `unit_test_generator_agent`
**Source:** 500-AI-Agents / 15-unit-test-generator
**Domain:** software-development
**Best For:** Generating unit tests for any function, class, or module — pytest, unittest, Jest, etc.

## When to Load This Skill
Load this skill when the task involves:
- Writing unit tests for a function or module
- Generating test cases from a code snippet
- Creating pytest/unittest test files
- Adding test coverage to existing code
- Writing edge case and boundary condition tests
- Generating mock/fixture code for testing
- Any software testing or QA task

## Capabilities
1. **Language detection** — adapts to Python (pytest/unittest), JavaScript (Jest/Vitest), TypeScript
2. **Test case generation** — creates happy path, edge cases, and error cases
3. **Mock generation** — creates mocks for external dependencies
4. **Assertion quality** — uses specific assertions, not just `assert True`
5. **Coverage focus** — identifies untested branches and generates tests for them
6. **Docstring integration** — reads docstrings and type hints to infer expected behavior

## Output Format
```python
# Generated test file following project conventions
import pytest
from module import function_under_test

class TestFunctionName:
    def test_happy_path(self):
        # Arrange
        ...
        # Act
        result = function_under_test(...)
        # Assert
        assert result == expected

    def test_edge_case_empty_input(self):
        ...

    def test_raises_on_invalid_input(self):
        with pytest.raises(ValueError):
            ...
```

## Instructions for Agent
1. Parse the provided code to identify functions, inputs, outputs, and error conditions.
2. Generate at minimum: one happy path test, two edge case tests, one error/exception test.
3. Use Arrange-Act-Assert structure for clarity.
4. Create mocks for any external calls (API, file I/O, database).
5. Name tests descriptively: `test_<function>_<condition>_<expected_result>`.
6. Add a brief docstring to each test explaining what it verifies.

## Constraints
- Test names must be descriptive — no `test_1`, `test_2`.
- Each test must have exactly one `assert` focus (not multiple unrelated assertions).
- Mocks must be properly cleaned up (use fixtures or context managers).
- Never test implementation details — test observable behavior only.

## Keywords (for task matching)
unit test, test, testing, pytest, unittest, jest, test cases, test coverage,
write tests, generate tests, QA, assertions, mock, fixture, code testing
