"""Anneal QUBO method — full pipeline."""

from __future__ import annotations

from pathlib import Path

from spinchain.solvers.simulated_annealing import SimulatedAnnealingSolver

from anneal.graph.detector import detect_sources, CompositeGraphSource
from anneal.formulation.candidate_generator import CandidateGenerator
from anneal.formulation.context_qubo_builder import ContextQUBOBuilder
from anneal.assembly.result_builder import ResultBuilder, stability_ranking

from benchmarks.methods.base import TaskResult
from benchmarks.tasks import Task


class AnnealQUBO:
    name = "anneal_qubo"

    def run(self, task: Task, project_root: str) -> TaskResult:
        root = Path(project_root)
        sources = detect_sources(root)
        composite = CompositeGraphSource(sources)

        gen = CandidateGenerator(composite, project_root=root)
        candidates = gen.generate(task.description, max_candidates=200)

        if not candidates:
            return TaskResult(method=self.name, selected_files=[], tokens_used=0)

        qubo_builder = ContextQUBOBuilder(strategy="balanced")
        edges = composite.get_edges()
        bqm = qubo_builder.build(candidates, edges, task.token_budget)

        solver = SimulatedAnnealingSolver(num_reads=100, num_sweeps=1000)
        sample_set = solver.solve(bqm)

        selected_indices = stability_ranking(sample_set, len(candidates))

        rb = ResultBuilder()
        result = rb.build(
            candidates=candidates, selected_indices=selected_indices,
            stability_scores={i: 1.0 for i in selected_indices},
            edges=edges, budget=task.token_budget,
        )

        selected_files = list({
            chunk["path"] for chunk in result["selected_chunks"]
        })

        return TaskResult(
            method=self.name,
            selected_files=selected_files,
            tokens_used=result["total_tokens"],
            metadata={"num_candidates": len(candidates), "num_selected": len(selected_indices)},
        )
