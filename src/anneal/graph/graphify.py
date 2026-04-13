"""Reads codebase graph from Graphify's graph.json output."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from anneal.graph.base import Edge, GraphSource, Node

logger = logging.getLogger("anneal.graph.graphify")

_GRAPH_FILE = "graph.json"


class GraphifySource(GraphSource):
    """Reads knowledge graph from graph.json (Graphify output).

    Expected format:
        {
          "nodes": [{"id", "path", "name", "type", "start_line",
                     "end_line", "cluster_id"?, ...}, ...],
          "edges": [{"source", "target", "type", "weight"?}, ...]
        }
    """

    def __init__(self, project_root: Path):
        self._graph_path = project_root / _GRAPH_FILE
        self._nodes: list[Node] | None = None
        self._edges: list[Edge] | None = None

    @property
    def name(self) -> str:
        return "graphify"

    def is_available(self) -> bool:
        return self._graph_path.exists() and self._graph_path.is_file()

    def _load(self) -> dict:
        try:
            return json.loads(self._graph_path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning("Failed to read graph.json: %s", e)
            return {"nodes": [], "edges": []}

    def get_nodes(self) -> list[Node]:
        if self._nodes is not None:
            return self._nodes
        if not self.is_available():
            return []
        data = self._load()
        self._nodes = [
            Node(
                id=n["id"],
                path=n.get("path", ""),
                name=n.get("name", n["id"]),
                node_type=n.get("type", "unknown"),
                start_line=n.get("start_line", 0),
                end_line=n.get("end_line", 0),
                cluster_id=n.get("cluster_id"),
                metadata={k: v for k, v in n.items()
                          if k not in ("id", "path", "name", "type",
                                       "start_line", "end_line", "cluster_id")},
            )
            for n in data.get("nodes", [])
        ]
        return self._nodes

    def get_edges(self) -> list[Edge]:
        if self._edges is not None:
            return self._edges
        if not self.is_available():
            return []
        data = self._load()
        self._edges = [
            Edge(
                source_id=e["source"],
                target_id=e["target"],
                edge_type=e.get("type", "related"),
                weight=float(e.get("weight", 1.0)),
            )
            for e in data.get("edges", [])
        ]
        return self._edges

    def get_edges_for_node(self, node_id: str) -> list[Edge]:
        return [
            e for e in self.get_edges()
            if e.source_id == node_id or e.target_id == node_id
        ]

    @property
    def node_count(self) -> int:
        return len(self.get_nodes())
