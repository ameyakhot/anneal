from anneal.graph.base import Edge, Node
from anneal.formulation.candidate_generator import Candidate
from anneal.formulation.coefficient_builder import ContextCoefficientBuilder


def _make_candidates() -> list[Candidate]:
    return [
        Candidate(
            node=Node(id="n1", path="src/a.py", name="func_a",
                      node_type="function", cluster_id="c1"),
            relevance_score=0.9, content="x" * 400, tokens=100,
        ),
        Candidate(
            node=Node(id="n2", path="src/a.py", name="func_b",
                      node_type="function", cluster_id="c1"),
            relevance_score=0.5, content="x" * 200, tokens=50,
        ),
        Candidate(
            node=Node(id="n3", path="src/b.py", name="func_c",
                      node_type="function", cluster_id="c2"),
            relevance_score=0.3, content="x" * 100, tokens=25,
        ),
    ]


def _make_edges() -> list[Edge]:
    return [Edge(source_id="n1", target_id="n2", edge_type="calls", weight=1.0)]


def test_linear_weights_shape():
    cb = ContextCoefficientBuilder()
    candidates = _make_candidates()
    linear = cb.compute_linear_weights(candidates, budget=500)
    assert linear.shape == (3,)


def test_linear_high_relevance_lower_weight():
    cb = ContextCoefficientBuilder(mu=1.0, alpha=0.0, penalty=0.0)
    candidates = _make_candidates()
    linear = cb.compute_linear_weights(candidates, budget=500)
    assert linear[0] < linear[2]


def test_linear_high_tokens_higher_weight():
    cb = ContextCoefficientBuilder(mu=0.0, alpha=1.0, penalty=0.0)
    candidates = _make_candidates()
    linear = cb.compute_linear_weights(candidates, budget=500)
    assert linear[0] > linear[2]


def test_quadratic_shape():
    cb = ContextCoefficientBuilder()
    candidates = _make_candidates()
    edges = _make_edges()
    quadratic = cb.compute_quadratic_weights(candidates, edges, budget=500)
    assert quadratic.shape == (3, 3)


def test_quadratic_same_file_redundancy():
    cb = ContextCoefficientBuilder(gamma=1.0, beta=0.0, penalty=0.0)
    candidates = _make_candidates()
    quadratic = cb.compute_quadratic_weights(candidates, [], budget=500)
    assert quadratic[0, 1] > 0.0


def test_quadratic_dependency_reward():
    cb = ContextCoefficientBuilder(gamma=0.0, beta=1.0, penalty=0.0)
    candidates = _make_candidates()
    edges = _make_edges()
    quadratic = cb.compute_quadratic_weights(candidates, edges, budget=500)
    assert quadratic[0, 1] < 0.0


def test_budget_penalty_linear_term():
    """Normalized: penalty * (t/B) * (t/B - 2)"""
    cb = ContextCoefficientBuilder(mu=0.0, alpha=0.0, penalty=1.0)
    candidates = [
        Candidate(node=Node(id="x", path="a.py", name="f", node_type="function"),
                  relevance_score=0.0, content="", tokens=100)
    ]
    linear = cb.compute_linear_weights(candidates, budget=500)
    t_norm = 100 / 500  # 0.2
    expected = 1.0 * t_norm * (t_norm - 2)  # 0.2 * -1.8 = -0.36
    assert abs(linear[0] - expected) < 1e-6


def test_budget_penalty_quadratic_term():
    """Normalized: 2 * penalty * (t_i/B) * (t_j/B)"""
    cb = ContextCoefficientBuilder(mu=0.0, alpha=0.0, gamma=0.0, beta=0.0, penalty=1.0)
    candidates = [
        Candidate(node=Node(id="x", path="a.py", name="f", node_type="function"),
                  relevance_score=0.0, content="", tokens=100),
        Candidate(node=Node(id="y", path="b.py", name="g", node_type="function"),
                  relevance_score=0.0, content="", tokens=50),
    ]
    quadratic = cb.compute_quadratic_weights(candidates, [], budget=500)
    expected = 2.0 * 1.0 * (100 / 500) * (50 / 500)  # 2 * 0.2 * 0.1 = 0.04
    assert abs(quadratic[0, 1] - expected) < 1e-6
