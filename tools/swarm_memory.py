"""
tools/swarm_memory.py
=====================
Small shared-memory object for swarm handoffs.

Agents use this as a blackboard: SERAPH can add keywords, SCOUT can add sourced
products, and FORGE can read the selected product without relying on prose.
"""

import json
from pathlib import Path
from typing import Any


class SwarmMemory:
    """Dot-path addressable dictionary with optional JSON persistence."""

    def __init__(self, data: dict[str, Any] | None = None, path: str | Path | None = None):
        self.data = data or {}
        self.path = Path(path) if path else None

    @classmethod
    def load(cls, path: str | Path) -> "SwarmMemory":
        memory_path = Path(path)
        if not memory_path.exists():
            return cls(path=memory_path)
        with open(memory_path, "r", encoding="utf-8") as f:
            return cls(json.load(f), path=memory_path)

    def save(self, path: str | Path | None = None) -> str | None:
        target = Path(path) if path else self.path
        if not target:
            return None
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)
        self.path = target
        return str(target)

    def get(self, dotted_path: str, default: Any = None) -> Any:
        current: Any = self.data
        for part in dotted_path.split("."):
            if not isinstance(current, dict) or part not in current:
                return default
            current = current[part]
        return current

    def set(self, dotted_path: str, value: Any) -> Any:
        current = self.data
        parts = dotted_path.split(".")
        for part in parts[:-1]:
            current = current.setdefault(part, {})
        current[parts[-1]] = value
        return value

    def append(self, dotted_path: str, value: Any) -> list[Any]:
        existing = self.get(dotted_path)
        if not isinstance(existing, list):
            existing = []
            self.set(dotted_path, existing)
        existing.append(value)
        return existing

    def merge(self, dotted_path: str, values: dict[str, Any]) -> dict[str, Any]:
        existing = self.get(dotted_path)
        if not isinstance(existing, dict):
            existing = {}
            self.set(dotted_path, existing)
        existing.update(values)
        return existing
