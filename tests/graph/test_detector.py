import json
import sqlite3
from pathlib import Path
from anneal.graph.detector import detect_sources, CompositeGraphSource


def _add_crg(tmp_path: Path) -> None:
    db_dir = tmp_path / ".code-review-graph"
    db_dir.mkdir(exist_ok=True)
    conn = sqlite3.connect(db_dir / "graph.db")
    conn.executescript("""
        CREATE TABLE nodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kind TEXT NOT NULL, name TEXT NOT NULL,
            qualified_name TEXT NOT NULL UNIQUE,
            file_path TEXT NOT NULL,
            line_start INTEGER, line_end INTEGER,
            community_id INTEGER
        );
        CREATE TABLE edges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kind TEXT NOT NULL,
            source_qualified TEXT NOT NULL, target_qualified TEXT NOT NULL,
            file_path TEXT NOT NULL
        );
        INSERT INTO nodes (kind, name, qualified_name, file_path, line_start, line_end)
            VALUES ('function', 'func_a', 'src/a.py::func_a', 'src/a.py', 1, 10);
    """)
    conn.commit()
    conn.close()


def _add_graphify(tmp_path: Path) -> None:
    data = {
        "nodes": [{"id": "n2", "path": "src/b.py", "name": "func_b",
                   "type": "function", "start_line": 1, "end_line": 5}],
        "edges": [],
    }
    (tmp_path / "graph.json").write_text(json.dumps(data))


def test_detect_none(tmp_path):
    sources = detect_sources(tmp_path)
    assert sources == []


def test_detect_crg_only(tmp_path):
    _add_crg(tmp_path)
    sources = detect_sources(tmp_path)
    assert len(sources) == 1
    assert sources[0].name == "code-review-graph"


def test_detect_both(tmp_path):
    _add_crg(tmp_path)
    _add_graphify(tmp_path)
    sources = detect_sources(tmp_path)
    assert len(sources) == 2


def test_composite_merges_nodes(tmp_path):
    _add_crg(tmp_path)
    _add_graphify(tmp_path)
    sources = detect_sources(tmp_path)
    composite = CompositeGraphSource(sources)
    nodes = composite.get_nodes()
    ids = {n.id for n in nodes}
    assert "src/a.py::func_a" in ids  # from crg
    assert "n2" in ids                 # from graphify


def test_composite_deduplicates_nodes(tmp_path):
    _add_crg(tmp_path)
    # graphify reports same id as crg's qualified_name
    data = {
        "nodes": [{"id": "src/a.py::func_a", "path": "src/a.py", "name": "func_a", "type": "function"}],
        "edges": [],
    }
    (tmp_path / "graph.json").write_text(json.dumps(data))
    sources = detect_sources(tmp_path)
    composite = CompositeGraphSource(sources)
    nodes = composite.get_nodes()
    ids = [n.id for n in nodes]
    assert ids.count("src/a.py::func_a") == 1
