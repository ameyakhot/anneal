import pytest
from anneal.graph.base import Node
from anneal.formulation.candidate_generator import Candidate
from anneal.assembly.budget_manager import BudgetManager


def _make_candidate(nid, tokens, relevance=0.5):
    return Candidate(
        node=Node(id=nid, path=f"src/{nid}.py", name=nid, node_type="function"),
        relevance_score=relevance, content="x" * (tokens * 4), tokens=tokens,
    )


def test_count_tokens():
    bm = BudgetManager()
    assert bm.count_tokens("hello world") == 2


def test_trim_within_budget():
    bm = BudgetManager()
    candidates = [
        _make_candidate("a", 100, 0.9),
        _make_candidate("b", 200, 0.7),
        _make_candidate("c", 300, 0.5),
    ]
    trimmed = bm.trim_to_budget(candidates, budget=450)
    total = sum(c.tokens for c in trimmed)
    assert total <= 450


def test_trim_keeps_high_relevance():
    bm = BudgetManager()
    candidates = [
        _make_candidate("high", 100, 0.9),
        _make_candidate("low", 100, 0.1),
    ]
    trimmed = bm.trim_to_budget(candidates, budget=150)
    ids = {c.node.id for c in trimmed}
    assert "high" in ids


def test_trim_returns_all_if_within_budget():
    bm = BudgetManager()
    candidates = [_make_candidate("a", 100), _make_candidate("b", 50)]
    trimmed = bm.trim_to_budget(candidates, budget=1000)
    assert len(trimmed) == 2
