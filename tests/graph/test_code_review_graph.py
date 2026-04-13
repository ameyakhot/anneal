"""Tests for CodeReviewGraphSource using real code-review-graph schema."""

import sqlite3
from pathlib import Path

from anneal.graph.code_review_graph import CodeReviewGraphSource


def _make_db(tmp_path: Path) -> Path:
    """Create a code-review-graph SQLite DB matching the real schema."""
    db_dir = tmp_path / ".code-review-graph"
    db_dir.mkdir()
    db_path = db_dir / "graph.db"
    conn = sqlite3.connect(db_path)
    conn.executescript("""
        CREATE TABLE nodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kind TEXT NOT NULL,
            name TEXT NOT NULL,
            qualified_name TEXT NOT NULL UNIQUE,
            file_path TEXT NOT NULL,
            line_start INTEGER,
            line_end INTEGER,
            language TEXT,
            parent_name TEXT,
            community_id INTEGER
        );
        CREATE TABLE edges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kind TEXT NOT NULL,
            source_qualified TEXT NOT NULL,
            target_qualified TEXT NOT NULL,
            file_path TEXT NOT NULL,
            line INTEGER DEFAULT 0
        );
        INSERT INTO nodes (kind, name, qualified_name, file_path, line_start, line_end, language, community_id)
            VALUES ('function', 'authenticate', 'src/auth.py::authenticate', 'src/auth.py', 10, 30, 'python', 1);
        INSERT INTO nodes (kind, name, qualified_name, file_path, line_start, line_end, language, community_id)
            VALUES ('function', 'hash_password', 'src/auth.py::hash_password', 'src/auth.py', 32, 45, 'python', 1);
        INSERT INTO nodes (kind, name, qualified_name, file_path, line_start, line_end, language, community_id)
            VALUES ('class', 'UserModel', 'src/user.py::UserModel', 'src/user.py', 1, 80, 'python', 2);
        INSERT INTO edges (kind, source_qualified, target_qualified, file_path)
            VALUES ('calls', 'src/auth.py::authenticate', 'src/auth.py::hash_password', 'src/auth.py');
        INSERT INTO edges (kind, source_qualified, target_qualified, file_path)
            VALUES ('imports', 'src/user.py::UserModel', 'src/auth.py::authenticate', 'src/user.py');
    """)
    conn.commit()
    conn.close()
    return db_dir.parent


def test_is_available(tmp_path):
    project_root = _make_db(tmp_path)
    src = CodeReviewGraphSource(project_root)
    assert src.is_available() is True


def test_is_unavailable_when_missing(tmp_path):
    src = CodeReviewGraphSource(tmp_path)
    assert src.is_available() is False


def test_get_nodes(tmp_path):
    project_root = _make_db(tmp_path)
    src = CodeReviewGraphSource(project_root)
    nodes = src.get_nodes()
    assert len(nodes) == 3
    paths = {n.path for n in nodes}
    assert "src/auth.py" in paths
    assert "src/user.py" in paths


def test_node_uses_qualified_name_as_id(tmp_path):
    project_root = _make_db(tmp_path)
    src = CodeReviewGraphSource(project_root)
    nodes = src.get_nodes()
    ids = {n.id for n in nodes}
    assert "src/auth.py::authenticate" in ids


def test_node_has_community_as_cluster(tmp_path):
    project_root = _make_db(tmp_path)
    src = CodeReviewGraphSource(project_root)
    nodes = src.get_nodes()
    clusters = {n.cluster_id for n in nodes}
    assert "1" in clusters
    assert "2" in clusters


def test_node_kind_maps_to_node_type(tmp_path):
    project_root = _make_db(tmp_path)
    src = CodeReviewGraphSource(project_root)
    nodes = src.get_nodes()
    types = {n.node_type for n in nodes}
    assert "function" in types
    assert "class" in types


def test_get_edges(tmp_path):
    project_root = _make_db(tmp_path)
    src = CodeReviewGraphSource(project_root)
    edges = src.get_edges()
    assert len(edges) == 2
    types = {e.edge_type for e in edges}
    assert "calls" in types
    assert "imports" in types


def test_edges_use_qualified_names(tmp_path):
    project_root = _make_db(tmp_path)
    src = CodeReviewGraphSource(project_root)
    edges = src.get_edges()
    sources = {e.source_id for e in edges}
    assert "src/auth.py::authenticate" in sources


def test_get_edges_for_node(tmp_path):
    project_root = _make_db(tmp_path)
    src = CodeReviewGraphSource(project_root)
    edges = src.get_edges_for_node("src/auth.py::authenticate")
    assert len(edges) == 2


def test_name(tmp_path):
    project_root = _make_db(tmp_path)
    src = CodeReviewGraphSource(project_root)
    assert src.name == "code-review-graph"
