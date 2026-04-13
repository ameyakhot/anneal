"""Reads codebase graph from code-review-graph's SQLite database.

Schema reference: https://github.com/tirth8205/code-review-graph
    nodes(id INTEGER, kind TEXT, name TEXT, qualified_name TEXT UNIQUE,
          file_path TEXT, line_start INTEGER, line_end INTEGER,
          language TEXT, community_id INTEGER, ...)
    edges(id INTEGER, kind TEXT, source_qualified TEXT, target_qualified TEXT,
          file_path TEXT, line INTEGER, ...)
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

from anneal.graph.base import Edge, GraphSource, Node

logger = logging.getLogger("anneal.graph.code_review_graph")

_DB_PATH = ".code-review-graph/graph.db"


class CodeReviewGraphSource(GraphSource):
    """Reads dependency graph from .code-review-graph/graph.db (SQLite)."""

    def __init__(self, project_root: Path):
        self._db_path = project_root / _DB_PATH
        self._nodes: list[Node] | None = None
        self._edges: list[Edge] | None = None

    @property
    def name(self) -> str:
        return "code-review-graph"

    def is_available(self) -> bool:
        return self._db_path.exists() and self._db_path.is_file()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def get_nodes(self) -> list[Node]:
        if self._nodes is not None:
            return self._nodes
        if not self.is_available():
            return []
        try:
            with self._connect() as conn:
                rows = conn.execute(
                    "SELECT qualified_name, file_path, name, kind, "
                    "COALESCE(line_start, 0) AS line_start, "
                    "COALESCE(line_end, 0) AS line_end, "
                    "community_id "
                    "FROM nodes"
                ).fetchall()
            self._nodes = [
                Node(
                    id=r["qualified_name"],
                    path=r["file_path"],
                    name=r["name"],
                    node_type=r["kind"],
                    start_line=r["line_start"],
                    end_line=r["line_end"],
                    cluster_id=str(r["community_id"]) if r["community_id"] is not None else None,
                )
                for r in rows
            ]
        except sqlite3.OperationalError as e:
            logger.warning("code-review-graph schema error: %s", e)
            self._detect_tables()
            self._nodes = []
        return self._nodes

    def get_edges(self) -> list[Edge]:
        if self._edges is not None:
            return self._edges
        if not self.is_available():
            return []
        try:
            with self._connect() as conn:
                rows = conn.execute(
                    "SELECT source_qualified, target_qualified, kind "
                    "FROM edges"
                ).fetchall()
            self._edges = [
                Edge(
                    source_id=r["source_qualified"],
                    target_id=r["target_qualified"],
                    edge_type=r["kind"],
                    weight=1.0,
                )
                for r in rows
            ]
        except sqlite3.OperationalError as e:
            logger.warning("code-review-graph schema error: %s", e)
            self._edges = []
        return self._edges

    def get_edges_for_node(self, node_id: str) -> list[Edge]:
        return [
            e for e in self.get_edges()
            if e.source_id == node_id or e.target_id == node_id
        ]

    @property
    def node_count(self) -> int:
        return len(self.get_nodes())

    def _detect_tables(self) -> None:
        try:
            with self._connect() as conn:
                tables = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            logger.info("code-review-graph tables found: %s", [t["name"] for t in tables])
        except Exception:
            pass
