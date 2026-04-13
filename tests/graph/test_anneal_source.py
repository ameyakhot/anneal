import sqlite3
from pathlib import Path
from anneal.graph.anneal_source import AnnealGraphSource


def _make_db(tmp_path: Path) -> Path:
    anneal_dir = tmp_path / ".anneal"
    anneal_dir.mkdir()
    db_path = anneal_dir / "graph.db"
    conn = sqlite3.connect(db_path)
    conn.executescript("""
        CREATE TABLE nodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            qualified_name TEXT NOT NULL UNIQUE,
            file_path TEXT NOT NULL,
            name TEXT NOT NULL,
            kind TEXT NOT NULL,
            language TEXT,
            line_start INTEGER,
            line_end INTEGER,
            parent_qualified TEXT
        );
        CREATE TABLE edges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_qualified TEXT NOT NULL,
            target_qualified TEXT NOT NULL,
            kind TEXT NOT NULL
        );
        INSERT INTO nodes (qualified_name, file_path, name, kind, language, line_start, line_end)
            VALUES ('src/auth.py::authenticate', 'src/auth.py', 'authenticate', 'function', 'python', 3, 5);
        INSERT INTO nodes (qualified_name, file_path, name, kind, language, line_start, line_end)
            VALUES ('src/user.py::User', 'src/user.py', 'User', 'class', 'python', 1, 6);
        INSERT INTO edges (source_qualified, target_qualified, kind)
            VALUES ('src/auth.py::authenticate', 'src/user.py::User', 'imports');
    """)
    conn.commit()
    conn.close()
    return tmp_path


def test_is_available(tmp_path):
    project_root = _make_db(tmp_path)
    src = AnnealGraphSource(project_root)
    assert src.is_available() is True

def test_is_unavailable_when_missing(tmp_path):
    src = AnnealGraphSource(tmp_path)
    assert src.is_available() is False

def test_get_nodes(tmp_path):
    project_root = _make_db(tmp_path)
    src = AnnealGraphSource(project_root)
    nodes = src.get_nodes()
    assert len(nodes) == 2
    ids = {n.id for n in nodes}
    assert "src/auth.py::authenticate" in ids

def test_get_edges(tmp_path):
    project_root = _make_db(tmp_path)
    src = AnnealGraphSource(project_root)
    edges = src.get_edges()
    assert len(edges) == 1
    assert edges[0].edge_type == "imports"

def test_name(tmp_path):
    src = AnnealGraphSource(tmp_path)
    assert src.name == "anneal"
