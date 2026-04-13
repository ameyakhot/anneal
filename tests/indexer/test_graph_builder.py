import sqlite3
from pathlib import Path
from anneal.indexer.graph_builder import build_graph


def _make_project(tmp_path: Path) -> Path:
    src = tmp_path / "src"
    src.mkdir()
    (src / "auth.py").write_text(
        "from src.user import User\n\n"
        "def authenticate(username: str) -> bool:\n"
        "    user = User(username)\n"
        "    return user.is_valid()\n\n"
        "def hash_password(pw: str) -> str:\n"
        "    return pw[::-1]\n"
    )
    (src / "user.py").write_text(
        "class User:\n"
        "    def __init__(self, name: str):\n"
        "        self.name = name\n\n"
        "    def is_valid(self) -> bool:\n"
        "        return len(self.name) > 0\n"
    )
    return tmp_path


def test_build_creates_db(tmp_path):
    project = _make_project(tmp_path)
    result = build_graph(project)
    db_path = Path(result["db_path"])
    assert db_path.exists()
    assert db_path.name == "graph.db"
    assert db_path.parent.name == ".anneal"


def test_build_creates_config(tmp_path):
    project = _make_project(tmp_path)
    result = build_graph(project)
    config_path = Path(result["config_path"])
    assert config_path.exists()
    assert config_path.name == "config.toml"


def test_build_counts(tmp_path):
    project = _make_project(tmp_path)
    result = build_graph(project)
    assert result["file_count"] == 2
    assert result["node_count"] >= 3
    assert result["edge_count"] >= 0


def test_build_node_content(tmp_path):
    project = _make_project(tmp_path)
    result = build_graph(project)
    conn = sqlite3.connect(result["db_path"])
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM nodes WHERE name = 'authenticate'").fetchall()
    assert len(rows) == 1
    assert rows[0]["kind"] == "function"
    assert rows[0]["line_start"] == 3
    conn.close()


def test_build_languages(tmp_path):
    project = _make_project(tmp_path)
    result = build_graph(project)
    assert "python" in result["languages"]


def test_build_idempotent(tmp_path):
    project = _make_project(tmp_path)
    r1 = build_graph(project)
    r2 = build_graph(project)
    assert r1["node_count"] == r2["node_count"]


def test_respects_gitignore(tmp_path):
    project = _make_project(tmp_path)
    (project / ".gitignore").write_text("ignored/\n")
    ignored = project / "ignored"
    ignored.mkdir()
    (ignored / "skip.py").write_text("def skipped(): pass\n")
    result = build_graph(project)
    conn = sqlite3.connect(result["db_path"])
    rows = conn.execute("SELECT * FROM nodes WHERE name = 'skipped'").fetchall()
    assert len(rows) == 0
    conn.close()
