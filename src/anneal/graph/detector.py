"""Auto-detect available graph sources and provide a composite view."""

from __future__ import annotations

import logging
from pathlib import Path

from anneal.graph.anneal_source import AnnealGraphSource
from anneal.graph.base import Edge, GraphSource, Node
from anneal.graph.code_review_graph import CodeReviewGraphSource
from anneal.graph.graphify import GraphifySource

logger = logging.getLogger("anneal.graph.detector")


def detect_sources(project_root: Path) -> list[GraphSource]:
    """Return all available graph sources for the given project root."""
    candidates = [
        AnnealGraphSource(project_root),
        CodeReviewGraphSource(project_root),
        GraphifySource(project_root),
    ]
    available = [s for s in candidates if s.is_available()]
    for s in available:
        logger.info("Graph source available: %s (%d nodes)", s.name, s.node_count)
    return available


class CompositeGraphSource(GraphSource):
    """Merges nodes and edges from multiple graph sources, deduplicating by node id."""

    def __init__(self, sources: list[GraphSource]):
        self._sources = sources

    @property
    def name(self) -> str:
        return "+".join(s.name for s in self._sources)

    def is_available(self) -> bool:
        return len(self._sources) > 0

    def get_nodes(self) -> list[Node]:
        seen: dict[str, Node] = {}
        for source in self._sources:
            for node in source.get_nodes():
                if node.id not in seen:
                    seen[node.id] = node
        return list(seen.values())

    def get_edges(self) -> list[Edge]:
        seen: set[tuple] = set()
        result: list[Edge] = []
        for source in self._sources:
            for edge in source.get_edges():
                key = (edge.source_id, edge.target_id, edge.edge_type)
                if key not in seen:
                    seen.add(key)
                    result.append(edge)
        return result

    def get_edges_for_node(self, node_id: str) -> list[Edge]:
        return [
            e for e in self.get_edges()
            if e.source_id == node_id or e.target_id == node_id
        ]

    @property
    def node_count(self) -> int:
        return len(self.get_nodes())
