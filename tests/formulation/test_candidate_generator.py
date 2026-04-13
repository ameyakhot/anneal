from pathlib import Path
import pytest
from anneal.graph.base import Node, Edge, GraphSource
from anneal.formulation.candidate_generator import Candidate, CandidateGenerator


class FakeGraphSource(GraphSource):
    def __init__(self, nodes, edges):
        self._nodes = nodes
        self._edges = edges

    @property
    def name(self): return "fake"
    def is_available(self): return True
    def get_nodes(self): return self._nodes
    def get_edges(self): return self._edges
    def get_edges_for_node(self, node_id):
        return [e for e in self._edges
                if e.source_id == node_id or e.target_id == node_id]


def _make_nodes():
    return [
        Node(id="n1", path="src/auth.py", name="authenticate",
             node_type="function", start_line=10, end_line=30),
        Node(id="n2", path="src/auth.py", name="hash_password",
             node_type="function", start_line=32, end_line=45),
        Node(id="n3", path="src/user.py", name="UserModel",
             node_type="class", start_line=1, end_line=80),
        Node(id="n4", path="src/database.py", name="connect",
             node_type="function", start_line=5, end_line=20),
    ]


def _make_edges():
    return [
        Edge(source_id="n1", target_id="n2", edge_type="calls", weight=1.0),
        Edge(source_id="n3", target_id="n1", edge_type="depends_on", weight=0.8),
    ]


def test_candidate_keyword_match(tmp_path):
    source = FakeGraphSource(_make_nodes(), _make_edges())
    gen = CandidateGenerator(source, project_root=tmp_path)
    candidates = gen.generate("fix bug in authenticate function", max_candidates=10)
    assert len(candidates) > 0
    assert candidates[0].node.id == "n1"


def test_candidate_dependency_expansion(tmp_path):
    source = FakeGraphSource(_make_nodes(), _make_edges())
    gen = CandidateGenerator(source, project_root=tmp_path)
    candidates = gen.generate("fix authenticate", max_candidates=10)
    ids = {c.node.id for c in candidates}
    assert "n2" in ids


def test_candidate_exclude_files(tmp_path):
    source = FakeGraphSource(_make_nodes(), _make_edges())
    gen = CandidateGenerator(source, project_root=tmp_path)
    candidates = gen.generate(
        "fix authenticate", exclude_files=["src/auth.py"], max_candidates=10,
    )
    paths = {c.node.path for c in candidates}
    assert "src/auth.py" not in paths


def test_candidate_include_files(tmp_path):
    source = FakeGraphSource(_make_nodes(), _make_edges())
    gen = CandidateGenerator(source, project_root=tmp_path)
    candidates = gen.generate(
        "fix something", include_files=["src/database.py"], max_candidates=10,
    )
    ids = {c.node.id for c in candidates}
    assert "n4" in ids


def test_relevance_score_range(tmp_path):
    source = FakeGraphSource(_make_nodes(), _make_edges())
    gen = CandidateGenerator(source, project_root=tmp_path)
    candidates = gen.generate("authenticate user model", max_candidates=10)
    for c in candidates:
        assert 0.0 <= c.relevance_score <= 1.0


def test_candidate_tokens_nonnegative(tmp_path):
    source = FakeGraphSource(_make_nodes(), _make_edges())
    gen = CandidateGenerator(source, project_root=tmp_path)
    candidates = gen.generate("authenticate", max_candidates=10)
    for c in candidates:
        assert c.tokens >= 0
