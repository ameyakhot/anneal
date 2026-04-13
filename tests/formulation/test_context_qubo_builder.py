import dimod
import pytest
from anneal.graph.base import Edge, Node
from anneal.formulation.candidate_generator import Candidate
from anneal.formulation.context_qubo_builder import ContextQUBOBuilder

_STRATEGIES = ["minimal", "balanced", "thorough"]


def _make_candidates(n=4):
    return [
        Candidate(
            node=Node(id=f"n{i}", path=f"src/file{i}.py",
                      name=f"func_{i}", node_type="function"),
            relevance_score=0.8 - i * 0.1,
            content="x" * (100 * (i + 1)),
            tokens=100 * (i + 1),
        )
        for i in range(n)
    ]


def test_build_returns_bqm():
    builder = ContextQUBOBuilder()
    candidates = _make_candidates()
    bqm = builder.build(candidates, edges=[], budget=1000)
    assert isinstance(bqm, dimod.BinaryQuadraticModel)


def test_bqm_variable_count():
    builder = ContextQUBOBuilder()
    candidates = _make_candidates(4)
    bqm = builder.build(candidates, edges=[], budget=1000)
    assert len(bqm.variables) == 4


def test_bqm_is_binary():
    builder = ContextQUBOBuilder()
    candidates = _make_candidates(3)
    bqm = builder.build(candidates, edges=[], budget=500)
    assert bqm.vartype == dimod.BINARY


@pytest.mark.parametrize("strategy", _STRATEGIES)
def test_strategy_produces_valid_bqm(strategy):
    builder = ContextQUBOBuilder(strategy=strategy)
    candidates = _make_candidates(5)
    bqm = builder.build(candidates, edges=[], budget=2000)
    assert len(bqm.variables) == 5


def test_with_edges():
    builder = ContextQUBOBuilder()
    candidates = _make_candidates(3)
    edges = [Edge(source_id="n0", target_id="n1", edge_type="calls", weight=1.0)]
    bqm = builder.build(candidates, edges=edges, budget=1000)
    assert isinstance(bqm, dimod.BinaryQuadraticModel)
