"""Compute QUBO coefficients for context selection.

Linear: w_i = -mu * relevance_i + alpha * (tokens_i / budget)
             + penalty * (tokens_i/budget) * (tokens_i/budget - 2)

Quadratic: w_ij = gamma * redundancy_ij - beta * dependency_ij
                 + 2 * penalty * (tokens_i/budget) * (tokens_j/budget)

Budget penalty is normalized by budget so all terms are O(1), not O(budget^2).
"""

from __future__ import annotations

import numpy as np

from anneal.graph.base import Edge
from anneal.formulation.candidate_generator import Candidate


class ContextCoefficientBuilder:
    """Builds QUBO coefficients for context chunk selection."""

    def __init__(self, mu: float = 1.0, alpha: float = 0.5, beta: float = 1.0,
                 gamma: float = 0.8, penalty: float = 5.0):
        self.mu = mu
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma
        self.penalty = penalty

    def compute_linear_weights(self, candidates: list[Candidate], budget: int) -> np.ndarray:
        n = len(candidates)
        weights = np.zeros(n)
        safe_budget = max(budget, 1)
        for i, c in enumerate(candidates):
            weights[i] = -self.mu * c.relevance_score + self.alpha * (c.tokens / safe_budget)
            # Normalized budget penalty: (t_i/B) * (t_i/B - 2)
            ti_norm = c.tokens / safe_budget
            weights[i] += self.penalty * ti_norm * (ti_norm - 2)
        return weights

    def compute_quadratic_weights(
        self, candidates: list[Candidate], edges: list[Edge], budget: int = 5000
    ) -> np.ndarray:
        n = len(candidates)
        weights = np.zeros((n, n))
        safe_budget = max(budget, 1)
        id_to_idx = {c.node.id: i for i, c in enumerate(candidates)}

        for i in range(n):
            for j in range(i + 1, n):
                ci, cj = candidates[i], candidates[j]
                if ci.node.path == cj.node.path:
                    redundancy = 1.0
                elif (ci.node.cluster_id and cj.node.cluster_id
                      and ci.node.cluster_id == cj.node.cluster_id):
                    redundancy = 0.5
                else:
                    redundancy = 0.0
                weights[i, j] += self.gamma * redundancy
                weights[j, i] += self.gamma * redundancy

        for edge in edges:
            i = id_to_idx.get(edge.source_id)
            j = id_to_idx.get(edge.target_id)
            if i is None or j is None or i == j:
                continue
            lo, hi = min(i, j), max(i, j)
            weights[lo, hi] -= self.beta * edge.weight
            weights[hi, lo] -= self.beta * edge.weight

        for i in range(n):
            for j in range(i + 1, n):
                ti_norm = candidates[i].tokens / safe_budget
                tj_norm = candidates[j].tokens / safe_budget
                bp = 2.0 * self.penalty * ti_norm * tj_norm
                weights[i, j] += bp
                weights[j, i] += bp

        return weights
