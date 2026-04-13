import sqlite3
from pathlib import Path
import pytest
from anneal.graph.code_review_graph import CodeReviewGraphSource


def _make_db(tmp_path: Path) -> Path:
    db_dir = tmp_path / ".code-review-graph"
    db_dir.mkdir()
    db_path = db_dir / "graph.db"
    conn = sqlite3.connect(db_path)
    conn.executescript("""
        CREATE TABLE nodes (
            id TEXT PRIMARY KEY,
            path TEXT NOT NULL,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            start_line INTEGER DEFAULT 0,
            end_line INTEGER DEFAULT 0
        );
        CREATE TABLE edges (
            source_id TEXT NOT NULL,
            target_id TEXT NOT NULL,
            type TEXT NOT NULL,
            weight REAL DEFAULT 1.0
        );
        INSERT INTO nodes VALUES ('n1', 'src/auth.py', 'authenticate', 'function', 10, 30);
        INSERT INTO nodes VALUES ('n2', 'src/auth.py', 'hash_password', 'function', 32, 45);
        INSERT INTO nodes VALUES ('n3', 'src/user.py', 'UserModel', 'class', 1, 80);
        INSERT INTO edges VALUES ('n1', 'n2', 'calls', 1.0);
        INSERT INTO edges VALUES ('n3', 'n1', 'depends_on', 0.8);
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


def test_get_edges(tmp_path):
    project_root = _make_db(tmp_path)
    src = CodeReviewGraphSource(project_root)
    edges = src.get_edges()
    assert len(edges) == 2
    types = {e.edge_type for e in edges}
    assert "calls" in types


def test_get_edges_for_node(tmp_path):
    project_root = _make_db(tmp_path)
    src = CodeReviewGraphSource(project_root)
    edges = src.get_edges_for_node("n1")
    assert len(edges) == 2


def test_name(tmp_path):
    project_root = _make_db(tmp_path)
    src = CodeReviewGraphSource(project_root)
    assert src.name == "code-review-graph"
