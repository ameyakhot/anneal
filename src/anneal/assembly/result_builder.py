# src/anneal/assembly/result_builder.py
"""Assemble final results: order chunks, compute stability, build dependency map."""

from __future__ import annotations
import numpy as np
import dimod
from anneal.graph.base import Edge
from anneal.formulation.candidate_generator import Candidate
from anneal.assembly.budget_manager import BudgetManager


def stability_ranking(
    sample_set: dimod.SampleSet, num_fragments: int,
    selection_threshold: float = 0.25, inclusion_threshold: float = 0.50,
) -> list[int]:
    """Select chunks by inclusion frequency in low-energy solutions (QCR-LLM pattern)."""
    samples = list(sample_set.samples())
    energies = [float(d.energy) for d in sample_set.data()]
    sorted_idx = np.argsort(energies)
    cutoff = max(1, int(len(sorted_idx) * selection_threshold))
    low_energy = sorted_idx[:cutoff]
    freq = np.zeros(num_fragments)
    for idx in low_energy:
        sample = samples[idx]
        for vi in range(num_fragments):
            if sample.get(vi, 0) == 1:
                freq[vi] += 1
    freq /= cutoff
    selected = [i for i in range(num_fragments) if freq[i] >= inclusion_threshold]
    selected.sort(key=lambda i: -freq[i])
    return selected


class ResultBuilder:
    def build(self, candidates: list[Candidate], selected_indices: list[int],
              stability_scores: dict[int, float], edges: list[Edge], budget: int) -> dict:
        selected = [candidates[i] for i in selected_indices]
        bm = BudgetManager()
        selected = bm.trim_to_budget(selected, budget)
        selected = self._order_by_dependency(selected, edges)
        agg_stability = (
            float(np.mean([stability_scores.get(i, 0.0) for i in selected_indices]))
            if selected_indices else 0.0
        )
        total_tokens = sum(c.tokens for c in selected)
        utilization = total_tokens / max(budget, 1)
        selected_ids = {c.node.id for c in selected}
        dep_graph: dict[str, list[str]] = {c.node.id: [] for c in selected}
        for edge in edges:
            if edge.source_id in selected_ids and edge.target_id in selected_ids:
                dep_graph[edge.source_id].append(edge.target_id)
        chunks = [
            {"path": c.node.path, "content": c.content,
             "relevance_score": c.relevance_score, "tokens": c.tokens}
            for c in selected
        ]
        return {
            "selected_chunks": chunks,
            "total_tokens": total_tokens,
            "budget_utilization": round(utilization, 4),
            "stability_score": round(agg_stability, 4),
            "dependency_graph": dep_graph,
        }

    def _order_by_dependency(self, candidates: list[Candidate], edges: list[Edge]) -> list[Candidate]:
        id_to_cand = {c.node.id: c for c in candidates}
        selected_ids = set(id_to_cand)
        in_degree: dict[str, int] = {nid: 0 for nid in selected_ids}
        for edge in edges:
            if edge.source_id in selected_ids and edge.target_id in selected_ids:
                in_degree[edge.target_id] = in_degree.get(edge.target_id, 0) + 1
        queue = sorted(
            [nid for nid in selected_ids if in_degree[nid] == 0],
            key=lambda nid: -id_to_cand[nid].relevance_score,
        )
        result: list[Candidate] = []
        visited: set[str] = set()
        while queue:
            nid = queue.pop(0)
            if nid in visited:
                continue
            visited.add(nid)
            result.append(id_to_cand[nid])
            for edge in edges:
                if edge.source_id == nid and edge.target_id in selected_ids:
                    in_degree[edge.target_id] -= 1
                    if in_degree[edge.target_id] == 0:
                        queue.append(edge.target_id)
        for c in candidates:
            if c.node.id not in visited:
                result.append(c)
        return result
