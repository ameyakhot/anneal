import pytest
import dimod
import numpy as np
from anneal.graph.base import Node, Edge
from anneal.formulation.candidate_generator import Candidate
from anneal.assembly.result_builder import ResultBuilder, stability_ranking


def _make_candidates(n=3):
    return [
        Candidate(
            node=Node(id=f"n{i}", path=f"src/f{i}.py", name=f"f{i}", node_type="function"),
            relevance_score=0.9 - i * 0.2,
            content=f"# content {i}\ndef f{i}(): pass",
            tokens=20,
        )
        for i in range(n)
    ]


def _make_sample_set(n_vars, selected_indices, num_reads=10):
    samples = []
    for _ in range(num_reads):
        sample = {i: (1 if i in selected_indices else 0) for i in range(n_vars)}
        samples.append(sample)
    energies = [-1.0] * num_reads
    return dimod.SampleSet.from_samples(samples, dimod.BINARY, energy=energies)


def test_stability_ranking_selects_consistent():
    sample_set = _make_sample_set(n_vars=3, selected_indices={0, 2})
    selected = stability_ranking(sample_set, num_fragments=3)
    assert 0 in selected
    assert 2 in selected
    assert 1 not in selected


def test_build_result_structure():
    candidates = _make_candidates(3)
    edges = [Edge(source_id="n0", target_id="n1", edge_type="calls")]
    rb = ResultBuilder()
    result = rb.build(
        candidates=candidates, selected_indices=[0, 2],
        stability_scores={0: 1.0, 2: 0.9}, edges=edges, budget=1000,
    )
    assert "selected_chunks" in result
    assert "total_tokens" in result
    assert "budget_utilization" in result
    assert "stability_score" in result
    assert "dependency_graph" in result
    assert len(result["selected_chunks"]) == 2


def test_build_result_chunk_fields():
    candidates = _make_candidates(2)
    rb = ResultBuilder()
    result = rb.build(
        candidates=candidates, selected_indices=[0],
        stability_scores={0: 1.0}, edges=[], budget=500,
    )
    chunk = result["selected_chunks"][0]
    assert "path" in chunk
    assert "content" in chunk
    assert "relevance_score" in chunk
    assert "tokens" in chunk


def test_budget_utilization_range():
    candidates = _make_candidates(3)
    rb = ResultBuilder()
    result = rb.build(
        candidates=candidates, selected_indices=[0, 1, 2],
        stability_scores={0: 1.0, 1: 0.8, 2: 0.6}, edges=[], budget=1000,
    )
    assert 0.0 <= result["budget_utilization"] <= 1.0
