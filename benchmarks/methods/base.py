"""Base types for benchmark methods."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from benchmarks.tasks import Task


@dataclass
class TaskResult:
    method: str
    selected_files: list[str]
    tokens_used: int
    metadata: dict = field(default_factory=dict)


class Method(Protocol):
    name: str

    def run(self, task: Task, project_root: str) -> TaskResult: ...
