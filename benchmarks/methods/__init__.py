"""Method registry."""

from __future__ import annotations

from benchmarks.methods.base import Method, TaskResult
from benchmarks.methods.anneal_qubo import AnnealQUBO
from benchmarks.methods.top_k_relevance import TopKRelevance
from benchmarks.methods.top_k_tokens import TopKTokens
from benchmarks.methods.random_selection import RandomSelection


def get_methods() -> list[Method]:
    return [AnnealQUBO(), TopKRelevance(), TopKTokens(), RandomSelection()]


__all__ = ["Method", "TaskResult", "get_methods"]
