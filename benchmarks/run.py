"""CLI orchestrator for Anneal benchmarks."""

from __future__ import annotations

import os

from benchmarks.tasks import TASKS
from benchmarks.methods import get_methods
from benchmarks.scoring import score_result
from benchmarks.results import ResultsAccumulator


def main() -> None:
    project_root = os.getcwd()
    methods = get_methods()
    accumulator = ResultsAccumulator()

    print(f"Running {len(TASKS)} tasks × {len(methods)} methods = {len(TASKS) * len(methods)} evaluations")
    print(f"Project root: {project_root}")
    print()

    for task in TASKS:
        for method in methods:
            result = method.run(task, project_root)
            scores = score_result(result, task)
            accumulator.add(task.id, method.name, scores)

    accumulator.print_summary()
