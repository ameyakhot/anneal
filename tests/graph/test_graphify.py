import json
import pytest
from pathlib import Path
from anneal.graph.graphify import GraphifySource


def _make_graph_json(tmp_path: Path) -> Path:
    data = {
        "nodes": [
            {"id": "n1", "path": "src/auth.py", "name": "authenticate",
             "type": "function", "start_line": 10, "end_line": 30, "cluster_id": "c1"},
            {"id": "n2", "path": "src/auth.py", "name": "hash_password",
             "type": "function", "start_line": 32, "end_line": 45, "cluster_id": "c1"},
            {"id": "n3", "path": "src/user.py", "name": "UserModel",
             "type": "class", "start_line": 1, "end_line": 80, "cluster_id": "c2"},
        ],
        "edges": [
            {"source": "n1", "target": "n2", "type": "calls", "weight": 1.0},
            {"source": "n3", "target": "n1", "type": "depends_on", "weight": 0.8},
        ],
    }
    graph_path = tmp_path / "graph.json"
    graph_path.write_text(json.dumps(data))
    return tmp_path


def test_is_available(tmp_path):
    project_root = _make_graph_json(tmp_path)
    src = GraphifySource(project_root)
    assert src.is_available() is True


def test_is_unavailable_when_missing(tmp_path):
    src = GraphifySource(tmp_path)
    assert src.is_available() is False


def test_get_nodes(tmp_path):
    project_root = _make_graph_json(tmp_path)
    src = GraphifySource(project_root)
    nodes = src.get_nodes()
    assert len(nodes) == 3
    clusters = {n.cluster_id for n in nodes}
    assert "c1" in clusters


def test_get_edges(tmp_path):
    project_root = _make_graph_json(tmp_path)
    src = GraphifySource(project_root)
    edges = src.get_edges()
    assert len(edges) == 2
    assert edges[0].weight == 1.0


def test_get_edges_for_node(tmp_path):
    project_root = _make_graph_json(tmp_path)
    src = GraphifySource(project_root)
    edges = src.get_edges_for_node("n1")
    assert len(edges) == 2


def test_name(tmp_path):
    src = GraphifySource(tmp_path)
    assert src.name == "graphify"
