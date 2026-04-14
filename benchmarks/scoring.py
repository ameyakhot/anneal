"""Score benchmark results against ground truth."""

from __future__ import annotations

from benchmarks.methods.base import TaskResult
from benchmarks.tasks import Task


def score_result(result: TaskResult, task: Task) -> dict:
    """Compute recall, precision, and utilization metrics."""
    selected = set(result.selected_files)
    required = set(task.required_files)

    true_positives = selected & required
    recall = len(true_positives) / len(required) if required else 1.0
    precision = len(true_positives) / len(selected) if selected else 0.0
    utilization = result.tokens_used / task.token_budget if task.token_budget > 0 else 0.0

    return {
        "recall": recall,
        "precision": precision,
        "f1": 2 * recall * precision / (recall + precision) if (recall + precision) > 0 else 0.0,
        "utilization": utilization,
        "selected_count": len(selected),
        "required_count": len(required),
        "true_positives": len(true_positives),
        "missing": sorted(required - selected),
    }
