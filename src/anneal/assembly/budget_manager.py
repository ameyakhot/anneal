# src/anneal/assembly/budget_manager.py
"""Token counting and hard budget enforcement."""

from __future__ import annotations
from anneal.formulation.candidate_generator import Candidate

_CHARS_PER_TOKEN = 4


class BudgetManager:
    def count_tokens(self, text: str) -> int:
        return max(0, len(text) // _CHARS_PER_TOKEN)

    def trim_to_budget(self, candidates: list[Candidate], budget: int) -> list[Candidate]:
        total = sum(c.tokens for c in candidates)
        if total <= budget:
            return candidates
        sorted_cands = sorted(candidates, key=lambda c: -c.relevance_score)
        result = []
        used = 0
        for c in sorted_cands:
            if used + c.tokens <= budget:
                result.append(c)
                used += c.tokens
        return result
