import json
import sqlite3
from pathlib import Path
import pytest
from anneal.graph.detector import detect_sources, CompositeGraphSource


def _add_crg(tmp_path: Path) -> None:
    db_dir = tmp_path / ".code-review-graph"
    db_dir.mkdir(exist_ok=True)
    conn = sqlite3.connect(db_dir / "graph.db")
    conn.executescript("""
        CREATE TABLE nodes (id TEXT, path TEXT, name TEXT, type TEXT,
                            start_line INTEGER, end_line INTEGER);
        CREATE TABLE edges (source_id TEXT, target_id TEXT, type TEXT, weight REAL);
        INSERT INTO nodes VALUES ('n1', 'src/a.py', 'func_a', 'function', 1, 10);
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
    assert "n1" in ids
    assert "n2" in ids


def test_composite_deduplicates_nodes(tmp_path):
    _add_crg(tmp_path)
    data = {
        "nodes": [{"id": "n1", "path": "src/a.py", "name": "func_a", "type": "function"}],
        "edges": [],
    }
    (tmp_path / "graph.json").write_text(json.dumps(data))
    sources = detect_sources(tmp_path)
    composite = CompositeGraphSource(sources)
    nodes = composite.get_nodes()
    ids = [n.id for n in nodes]
    assert ids.count("n1") == 1
