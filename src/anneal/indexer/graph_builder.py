"""Graph builder — walks project source files, parses with tree-sitter,
builds a code graph stored in `.anneal/graph.db` (SQLite) and writes
`.anneal/config.toml` with project defaults.
"""

from __future__ import annotations

import fnmatch
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from anneal.indexer.parser import Import, detect_language, parse_file

# Directories to always skip when walking project trees.
_SKIP_DIRS: set[str] = {
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    ".tox",
    ".mypy_cache",
    ".pytest_cache",
    ".anneal",
    "dist",
    "build",
    ".eggs",
    "*.egg-info",
}

# ---------------------------------------------------------------------------
# SQLite schema
# ---------------------------------------------------------------------------

_SCHEMA = """\
CREATE TABLE IF NOT EXISTS nodes (
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

CREATE TABLE IF NOT EXISTS edges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_qualified TEXT NOT NULL,
    target_qualified TEXT NOT NULL,
    kind TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

# ---------------------------------------------------------------------------
# Default config.toml content
# ---------------------------------------------------------------------------

_DEFAULT_CONFIG = """\
[anneal]
version = "0.1.0"

[index]
# File extensions to index (empty = auto-detect all supported)
extensions = []

# Additional directories to skip
skip_dirs = []
"""

# ---------------------------------------------------------------------------
# Gitignore parsing (simplified)
# ---------------------------------------------------------------------------


def _load_gitignore_patterns(project_root: Path) -> list[str]:
    """Load ignore patterns from .gitignore if it exists."""
    gitignore = project_root / ".gitignore"
    if not gitignore.exists():
        return []
    patterns: list[str] = []
    for line in gitignore.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        patterns.append(line)
    return patterns


def _is_ignored(path: Path, project_root: Path, patterns: list[str]) -> bool:
    """Check whether *path* matches any gitignore pattern."""
    rel = path.relative_to(project_root)
    rel_str = str(rel)
    name = path.name

    for pat in patterns:
        pat_clean = pat.rstrip("/")
        # Match directory name or full relative path
        if fnmatch.fnmatch(name, pat_clean):
            return True
        if fnmatch.fnmatch(rel_str, pat_clean):
            return True
        # Pattern with trailing slash means directory only
        if pat.endswith("/") and path.is_dir() and fnmatch.fnmatch(name, pat_clean):
            return True
    return False


# ---------------------------------------------------------------------------
# File walking
# ---------------------------------------------------------------------------


def _collect_source_files(project_root: Path) -> list[Path]:
    """Recursively collect source files, respecting skip dirs and .gitignore."""
    ignore_patterns = _load_gitignore_patterns(project_root)
    files: list[Path] = []

    def _walk(directory: Path) -> None:
        try:
            entries = sorted(directory.iterdir())
        except PermissionError:
            return
        for entry in entries:
            if entry.is_dir():
                dirname = entry.name
                # Check hardcoded skip dirs
                if dirname in _SKIP_DIRS or any(
                    fnmatch.fnmatch(dirname, pat) for pat in _SKIP_DIRS
                ):
                    continue
                # Check gitignore
                if _is_ignored(entry, project_root, ignore_patterns):
                    continue
                _walk(entry)
            elif entry.is_file():
                if _is_ignored(entry, project_root, ignore_patterns):
                    continue
                if detect_language(entry.name) is not None:
                    files.append(entry)

    _walk(project_root)
    return files


# ---------------------------------------------------------------------------
# Import resolution
# ---------------------------------------------------------------------------


def _resolve_import(
    imp: Import,
    project_root: Path,
    file_index: dict[str, str],
) -> str | None:
    """Try to resolve an import module path to a relative file path in the project.

    *file_index* maps relative file paths (e.g. ``src/user.py``) to themselves
    for quick lookup.
    """
    # Convert dotted module path to potential file paths
    # e.g. "src.user" -> "src/user.py" or "src/user/__init__.py"
    parts = imp.module.replace(".", "/")
    candidates = [
        f"{parts}.py",
        f"{parts}/__init__.py",
    ]
    for candidate in candidates:
        if candidate in file_index:
            return candidate
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_graph(project_root: Path) -> dict[str, Any]:
    """Walk *project_root*, parse source files, and build a code graph.

    Creates ``.anneal/graph.db`` (SQLite) and ``.anneal/config.toml``.

    Returns a dict with keys:
        ``db_path``, ``config_path``, ``file_count``, ``node_count``,
        ``edge_count``, ``languages``.
    """
    project_root = Path(project_root).resolve()
    anneal_dir = project_root / ".anneal"
    anneal_dir.mkdir(exist_ok=True)

    db_path = anneal_dir / "graph.db"
    config_path = anneal_dir / "config.toml"

    # Write default config if missing
    if not config_path.exists():
        config_path.write_text(_DEFAULT_CONFIG)

    # Collect source files
    source_files = _collect_source_files(project_root)

    # Build a quick lookup of relative paths
    rel_paths: dict[Path, str] = {}
    file_index: dict[str, str] = {}
    for f in source_files:
        rel = str(f.relative_to(project_root))
        rel_paths[f] = rel
        file_index[rel] = rel

    # Connect to DB — drop old tables for idempotency
    conn = sqlite3.connect(str(db_path))
    conn.execute("DROP TABLE IF EXISTS nodes")
    conn.execute("DROP TABLE IF EXISTS edges")
    conn.execute("DROP TABLE IF EXISTS metadata")
    conn.executescript(_SCHEMA)

    languages: set[str] = set()
    node_count = 0
    edge_count = 0
    file_count = len(source_files)

    # Deferred edges: (source_qualified, import)
    pending_edges: list[tuple[str, Import]] = []

    for fpath in source_files:
        rel = rel_paths[fpath]
        lang = detect_language(fpath.name)
        if lang:
            languages.add(lang)

        definitions, imports = parse_file(fpath)

        # Insert module-level node
        module_qname = rel
        conn.execute(
            "INSERT OR REPLACE INTO nodes "
            "(qualified_name, file_path, name, kind, language, line_start, line_end, parent_qualified) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (module_qname, rel, fpath.stem, "module", lang, 1, None, None),
        )
        node_count += 1

        # Insert definition nodes
        for defn in definitions:
            qname = f"{rel}::{defn.name}"
            parent_q = f"{rel}::{defn.parent}" if defn.parent else module_qname
            conn.execute(
                "INSERT OR REPLACE INTO nodes "
                "(qualified_name, file_path, name, kind, language, line_start, line_end, parent_qualified) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (qname, rel, defn.name, defn.kind, lang, defn.line_start, defn.line_end, parent_q),
            )
            node_count += 1

        # Collect imports for edge resolution
        for imp in imports:
            pending_edges.append((module_qname, imp))

    # Resolve import edges
    for source_qname, imp in pending_edges:
        target_rel = _resolve_import(imp, project_root, file_index)
        if target_rel is not None:
            target_qname = target_rel  # module-level node
            conn.execute(
                "INSERT INTO edges (source_qualified, target_qualified, kind) VALUES (?, ?, ?)",
                (source_qname, target_qname, "imports"),
            )
            edge_count += 1

    # Write metadata
    conn.execute(
        "INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)",
        ("indexed_at", datetime.now(timezone.utc).isoformat()),
    )
    conn.execute(
        "INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)",
        ("file_count", str(file_count)),
    )

    conn.commit()
    conn.close()

    return {
        "db_path": str(db_path),
        "config_path": str(config_path),
        "file_count": file_count,
        "node_count": node_count,
        "edge_count": edge_count,
        "languages": sorted(languages),
    }
