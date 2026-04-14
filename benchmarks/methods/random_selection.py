"""Random selection — floor baseline."""

from __future__ import annotations

import random
from pathlib import Path

from anneal.graph.detector import detect_sources, CompositeGraphSource
from anneal.formulation.candidate_generator import CandidateGenerator

from benchmarks.methods.base import TaskResult
from benchmarks.tasks import Task


class RandomSelection:
    name = "random"

    def __init__(self, seed: int = 42):
        self.seed = seed

    def run(self, task: Task, project_root: str) -> TaskResult:
        root = Path(project_root)
        sources = detect_sources(root)
        composite = CompositeGraphSource(sources)

        gen = CandidateGenerator(composite, project_root=root)
        candidates = gen.generate(task.description, max_candidates=200)

        rng = random.Random(hash(task.id) ^ self.seed)
        rng.shuffle(candidates)

        selected_files = []
        tokens_used = 0
        seen_files = set()

        for cand in candidates:
            if tokens_used + cand.tokens > task.token_budget:
                continue
            fp = cand.node.path
            if fp not in seen_files:
                selected_files.append(fp)
                seen_files.add(fp)
            tokens_used += cand.tokens

        return TaskResult(
            method=self.name,
            selected_files=selected_files,
            tokens_used=tokens_used,
        )
