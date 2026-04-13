"""Reads codebase graph from Anneal's own .anneal/graph.db."""
from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

from anneal.graph.base import Edge, GraphSource, Node

logger = logging.getLogger("anneal.graph.anneal_source")
_DB_PATH = ".anneal/graph.db"


class AnnealGraphSource(GraphSource):
    """Reads graph from .anneal/graph.db (built by anneal init)."""

    def __init__(self, project_root: Path):
        self._db_path = project_root / _DB_PATH
        self._nodes: list[Node] | None = None
        self._edges: list[Edge] | None = None

    @property
    def name(self) -> str:
        return "anneal"

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
                    "COALESCE(line_end, 0) AS line_end "
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
                )
                for r in rows
            ]
        except sqlite3.OperationalError as e:
            logger.warning("anneal graph.db schema error: %s", e)
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
                    "SELECT source_qualified, target_qualified, kind FROM edges"
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
            logger.warning("anneal graph.db schema error: %s", e)
            self._edges = []
        return self._edges

    def get_edges_for_node(self, node_id: str) -> list[Edge]:
        return [
            e
            for e in self.get_edges()
            if e.source_id == node_id or e.target_id == node_id
        ]

    @property
    def node_count(self) -> int:
        return len(self.get_nodes())
