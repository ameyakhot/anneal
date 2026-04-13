"""Generate and score candidate chunks from graph sources.

v0.1: keyword matching + graph topology. No embeddings.
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass
from pathlib import Path

from anneal.graph.base import GraphSource, Node

logger = logging.getLogger("anneal.formulation.candidate_generator")

_CHARS_PER_TOKEN = 4
_STOP_WORDS = frozenset({
    "the", "a", "an", "in", "to", "for", "of", "with", "and", "or",
    "this", "that", "is", "are", "was", "be", "it", "on", "at", "by",
    "fix", "bug", "add", "update", "change", "create", "implement",
    "write", "file", "function", "class", "method", "module",
})


@dataclass
class Candidate:
    node: Node
    relevance_score: float
    content: str
    tokens: int


def _parse_keywords(task_description: str) -> list[str]:
    words = re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*", task_description.lower())
    return [w for w in words if w not in _STOP_WORDS and len(w) > 2]


def _keyword_score(node: Node, keywords: list[str]) -> float:
    if not keywords:
        return 0.0
    text = f"{node.path} {node.name}".lower()
    hits = sum(1 for kw in keywords if kw in text)
    if hits == 0:
        return 0.0
    # Score based on hits vs a cap of 3, not total keywords.
    # This prevents noise words from diluting strong matches.
    return min(1.0, hits / min(3, len(keywords)))


def _read_content(node: Node, project_root: Path) -> str:
    file_path = project_root / node.path
    if not file_path.exists():
        return ""
    try:
        text = file_path.read_text(encoding="utf-8", errors="replace")
        if node.start_line > 0 and node.end_line >= node.start_line:
            lines = text.splitlines()
            return "\n".join(lines[node.start_line - 1: node.end_line])
        return text
    except Exception:
        return ""


class CandidateGenerator:
    def __init__(self, graph_source: GraphSource, project_root: Path,
                 keyword_weight: float = 0.85, centrality_weight: float = 0.15):
        self._source = graph_source
        self._project_root = project_root
        self._kw_w = keyword_weight
        self._cent_w = centrality_weight

    def generate(self, task_description: str, include_files: list[str] | None = None,
                 exclude_files: list[str] | None = None, max_candidates: int = 200) -> list[Candidate]:
        keywords = _parse_keywords(task_description)
        all_nodes = self._source.get_nodes()
        all_edges = self._source.get_edges()

        degree: dict[str, int] = {}
        for e in all_edges:
            degree[e.source_id] = degree.get(e.source_id, 0) + 1
            degree[e.target_id] = degree.get(e.target_id, 0) + 1
        max_degree = max(degree.values()) if degree else 1

        include_set = set(include_files) if include_files else set()
        exclude_set = set(exclude_files) if exclude_files else set()

        scored: list[tuple[float, Node]] = []
        for node in all_nodes:
            if node.path in exclude_set:
                continue
            kw = _keyword_score(node, keywords)
            cent = degree.get(node.id, 0) / max_degree
            rel = self._kw_w * kw + self._cent_w * cent
            if any(node.path == p or node.path.startswith(p) for p in include_set):
                rel = max(rel, 0.9)
            scored.append((rel, node))

        scored.sort(key=lambda x: -x[0])

        top_ids = {node.id for _, node in scored[:20]}
        neighbor_ids: set[str] = set()
        for nid in top_ids:
            for e in all_edges:
                if e.source_id == nid:
                    neighbor_ids.add(e.target_id)
                elif e.target_id == nid:
                    neighbor_ids.add(e.source_id)
        neighbor_ids -= top_ids

        node_map = {n.id: n for n in all_nodes}
        for nid in neighbor_ids:
            node = node_map.get(nid)
            if node is None or node.path in exclude_set:
                continue
            kw = _keyword_score(node, keywords)
            cent = degree.get(nid, 0) / max_degree
            rel = min(1.0, self._kw_w * kw + self._cent_w * cent + 0.05)
            scored.append((rel, node))

        seen: set[str] = set()
        unique: list[tuple[float, Node]] = []
        for rel, node in sorted(scored, key=lambda x: -x[0]):
            if node.id not in seen:
                seen.add(node.id)
                unique.append((rel, node))

        candidates: list[Candidate] = []
        for rel, node in unique[:max_candidates]:
            content = _read_content(node, self._project_root)
            tokens = max(0, len(content) // _CHARS_PER_TOKEN)
            candidates.append(Candidate(
                node=node, relevance_score=round(rel, 4),
                content=content, tokens=tokens,
            ))
        return candidates
