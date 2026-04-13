"""Anneal MCP server. Exposes get_optimal_context and get_status tools via stdio transport."""

from __future__ import annotations

import json
import logging
import tomllib
from dataclasses import dataclass
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from spinchain.solvers.simulated_annealing import SimulatedAnnealingSolver

from anneal.graph.detector import detect_sources, CompositeGraphSource
from anneal.formulation.candidate_generator import CandidateGenerator
from anneal.formulation.context_qubo_builder import ContextQUBOBuilder
from anneal.assembly.result_builder import ResultBuilder, stability_ranking
from anneal.tracing import get_tracer

logger = logging.getLogger("anneal.server")

mcp = FastMCP(
    "Anneal",
    instructions=(
        "Anneal selects the mathematically optimal context for AI coding tasks. "
        "Call get_optimal_context at the start of any coding task to receive the "
        "minimum set of relevant code chunks within your token budget, selected "
        "via QUBO optimization over the codebase dependency graph."
    ),
)


@dataclass
class _Config:
    default_tokens: int = 5000
    strategy: str = "balanced"
    solver_backend: str = "simulated-annealing"
    num_reads: int = 100
    num_sweeps: int = 1000


def _load_config(project_root: Path) -> _Config:
    config_path = project_root / ".anneal" / "config.toml"
    if not config_path.exists():
        return _Config()
    try:
        with open(config_path, "rb") as f:
            data = tomllib.load(f)
        budget_sec = data.get("budget", {})
        solver_sec = data.get("solver", {})
        return _Config(
            default_tokens=budget_sec.get("default_tokens", 5000),
            strategy=budget_sec.get("strategy", "balanced"),
            solver_backend=solver_sec.get("backend", "simulated-annealing"),
            num_reads=solver_sec.get("num_reads", 100),
            num_sweeps=solver_sec.get("num_sweeps", 1000),
        )
    except Exception as e:
        logger.warning("Failed to load config: %s — using defaults", e)
        return _Config()


@mcp.tool()
def get_optimal_context(
    task_description: str,
    token_budget: int | None = None,
    include_files: list[str] | None = None,
    exclude_files: list[str] | None = None,
    strategy: str = "balanced",
) -> str:
    """Return the optimal context for a coding task within a token budget.

    Reads the codebase graph (Graphify and/or code-review-graph), formulates context
    selection as a QUBO problem, and solves via simulated annealing to find the minimum
    token set that maximizes task relevance.

    Args:
        task_description: What the user wants to accomplish.
        token_budget: Max tokens to return. Defaults to config value (5000).
        include_files: File paths to always include regardless of relevance.
        exclude_files: File paths to never include.
        strategy: "balanced" | "minimal" | "thorough"
    """
    tracer = get_tracer()
    trace_id = tracer.start_trace({
        "task_description": task_description[:200],
        "token_budget": token_budget,
        "strategy": strategy,
        "include_files": include_files,
        "exclude_files": exclude_files,
    })

    try:
        project_root = Path.cwd()
        config = _load_config(project_root)

        stage = tracer.start_stage(trace_id, "graph_detection")
        sources = detect_sources(project_root)
        if not sources:
            tracer.finish_trace(trace_id, {"error": "no_graph_sources"})
            return json.dumps({
                "error": "No graph sources found. Install Graphify or code-review-graph.",
                "selected_chunks": [], "total_tokens": 0,
                "budget_utilization": 0.0, "stability_score": 0.0, "dependency_graph": {},
            })
        composite = CompositeGraphSource(sources)
        stage.metadata["sources"] = [s.name for s in sources]
        stage.metadata["node_count"] = composite.node_count
        tracer.end_stage(trace_id, stage)

        stage = tracer.start_stage(trace_id, "candidate_generation")
        gen = CandidateGenerator(composite, project_root=project_root)
        candidates = gen.generate(
            task_description,
            include_files=include_files or [],
            exclude_files=exclude_files or [],
            max_candidates=200,
        )
        stage.metadata["num_candidates"] = len(candidates)
        tracer.end_stage(trace_id, stage)

        if not candidates:
            tracer.finish_trace(trace_id, {"num_candidates": 0})
            return json.dumps({
                "selected_chunks": [], "total_tokens": 0,
                "budget_utilization": 0.0, "stability_score": 0.0,
                "dependency_graph": {}, "fallback": True,
                "reason": "No candidates generated from graph.",
            })

        stage = tracer.start_stage(trace_id, "qubo_formulation")
        eff_strategy = strategy if strategy in ("minimal", "balanced", "thorough") else config.strategy
        qubo_builder = ContextQUBOBuilder(strategy=eff_strategy)
        budget = token_budget if token_budget is not None else config.default_tokens
        edges = composite.get_edges()
        bqm = qubo_builder.build(candidates, edges, budget)
        stage.metadata["num_linear_terms"] = len(bqm.linear)
        stage.metadata["num_quadratic_terms"] = len(bqm.quadratic)
        tracer.end_stage(trace_id, stage)

        stage = tracer.start_stage(trace_id, "simulated_annealing")
        solver = SimulatedAnnealingSolver(
            num_reads=config.num_reads, num_sweeps=config.num_sweeps,
        )
        sample_set = solver.solve(bqm)
        energies = [float(d.energy) for d in sample_set.data()]
        stage.metadata["min_energy"] = min(energies) if energies else None
        stage.metadata["num_samples"] = len(energies)
        tracer.end_stage(trace_id, stage)

        stage = tracer.start_stage(trace_id, "stability_ranking")
        selected_indices = stability_ranking(sample_set, len(candidates))
        stability_scores = {i: 1.0 for i in selected_indices}
        stage.metadata["num_selected"] = len(selected_indices)
        tracer.end_stage(trace_id, stage)

        stage = tracer.start_stage(trace_id, "result_assembly")
        rb = ResultBuilder()
        result = rb.build(
            candidates=candidates, selected_indices=selected_indices,
            stability_scores=stability_scores, edges=edges, budget=budget,
        )
        stage.metadata["total_tokens"] = result["total_tokens"]
        tracer.end_stage(trace_id, stage)

        tracer.finish_trace(trace_id, {
            "num_selected": len(result["selected_chunks"]),
            "total_tokens": result["total_tokens"],
        })
        return json.dumps(result)

    except Exception as e:
        tracer.finish_trace(trace_id, {}, error=str(e))
        raise


@mcp.tool()
def get_status() -> str:
    """Return Anneal status: graph sources, node counts, solver, config path."""
    project_root = Path.cwd()
    sources = detect_sources(project_root)
    config_path = project_root / ".anneal" / "config.toml"
    source_status = {}
    node_counts = {}
    for s in sources:
        source_status[s.name] = True
        node_counts[s.name] = s.node_count
    for known in ("graphify", "code-review-graph"):
        if known not in source_status:
            source_status[known] = False
            node_counts[known] = 0
    return json.dumps({
        "graph_sources": source_status,
        "node_counts": node_counts,
        "solver": "simulated_annealing",
        "config_path": str(config_path),
        "config_exists": config_path.exists(),
    })


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
