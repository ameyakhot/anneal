"""Orchestrate coefficient building and BQM assembly for context selection."""

from __future__ import annotations

import dimod

from spinchain.formulation.qubo_builder import QUBOBuilder

from anneal.graph.base import Edge
from anneal.formulation.candidate_generator import Candidate
from anneal.formulation.coefficient_builder import ContextCoefficientBuilder

_STRATEGY_PARAMS: dict[str, dict] = {
    "minimal": dict(mu=3.0, alpha=1.5, beta=0.5, gamma=0.5, penalty=8.0),
    "balanced": dict(mu=3.0, alpha=0.5, beta=1.0, gamma=0.8, penalty=3.0),
    "thorough": dict(mu=4.0, alpha=0.2, beta=1.5, gamma=0.3, penalty=1.0),
}

_STRATEGY_BUDGETS: dict[str, int] = {
    "minimal": 2000,
    "balanced": 5000,
    "thorough": 10000,
}


class ContextQUBOBuilder:
    """Builds a dimod BQM for context chunk selection.

    Uses SpinChain's QUBOBuilder internally after computing context-specific
    linear and quadratic weights via ContextCoefficientBuilder.
    """

    def __init__(self, strategy: str = "balanced"):
        if strategy not in _STRATEGY_PARAMS:
            raise ValueError(f"Unknown strategy: {strategy!r}. Choose from {list(_STRATEGY_PARAMS)}")
        self._strategy = strategy
        self._coeff_params = _STRATEGY_PARAMS[strategy]

    def default_budget(self) -> int:
        return _STRATEGY_BUDGETS[self._strategy]

    def build(self, candidates: list[Candidate], edges: list[Edge],
              budget: int) -> dimod.BinaryQuadraticModel:
        coeff = ContextCoefficientBuilder(**self._coeff_params)
        linear = coeff.compute_linear_weights(candidates, budget)
        quadratic = coeff.compute_quadratic_weights(candidates, edges, budget)
        builder = QUBOBuilder(penalty_strength=self._coeff_params["penalty"])
        return builder.build(linear, quadratic)
