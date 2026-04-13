"""Base types for graph-based codebase understanding."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Node:
    """A node in the codebase graph — function, class, file, or module."""

    id: str
    path: str           # repo-relative file path
    name: str           # function/class/file name
    node_type: str      # "function" | "class" | "file" | "module"
    start_line: int = 0
    end_line: int = 0
    tokens: int = 0
    cluster_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Edge:
    """A directed edge between two graph nodes."""

    source_id: str
    target_id: str
    edge_type: str      # "imports" | "calls" | "depends_on" | "same_cluster"
    weight: float = 1.0


class GraphSource(ABC):
    """Abstract interface for reading codebase graph data."""

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if this source's data files exist and are readable."""
        ...

    @abstractmethod
    def get_nodes(self) -> list[Node]:
        """Return all nodes in the graph."""
        ...

    @abstractmethod
    def get_edges(self) -> list[Edge]:
        """Return all edges in the graph."""
        ...

    @abstractmethod
    def get_edges_for_node(self, node_id: str) -> list[Edge]:
        """Return all edges incident to the given node (both directions)."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable source name."""
        ...

    @property
    def node_count(self) -> int:
        """Number of nodes (override for efficiency)."""
        return len(self.get_nodes())
