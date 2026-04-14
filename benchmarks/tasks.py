"""Benchmark tasks with ground-truth required context."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Task:
    id: str
    description: str
    required_files: list[str]
    token_budget: int = 5000


TASKS = [
    Task(
        id="add_neo4j_source",
        description="Add a new graph source that reads nodes and edges from a Neo4j database",
        required_files=[
            "src/anneal/graph/base.py",
            "src/anneal/graph/anneal_source.py",
            "src/anneal/graph/detector.py",
        ],
        token_budget=4000,
    ),
    Task(
        id="fix_budget_trimming",
        description="Fix a bug where budget trimming breaks dependency chains by dropping required imports",
        required_files=[
            "src/anneal/assembly/budget_manager.py",
            "src/anneal/assembly/result_builder.py",
        ],
        token_budget=3000,
    ),
    Task(
        id="add_kotlin_parser",
        description="Add Kotlin language support to the tree-sitter parser",
        required_files=[
            "src/anneal/indexer/parser.py",
            "src/anneal/indexer/graph_builder.py",
        ],
        token_budget=4000,
    ),
    Task(
        id="streaming_results",
        description="Change the MCP server to stream context results progressively instead of returning all at once",
        required_files=[
            "src/anneal/server.py",
            "src/anneal/assembly/result_builder.py",
        ],
        token_budget=5000,
    ),
    Task(
        id="add_embeddings",
        description="Add semantic embedding-based scoring to the candidate generator using sentence-transformers",
        required_files=[
            "src/anneal/formulation/candidate_generator.py",
            "src/anneal/formulation/coefficient_builder.py",
        ],
        token_budget=4000,
    ),
    Task(
        id="qubo_strategy_config",
        description="Allow users to configure custom QUBO strategy weights in the config.toml file",
        required_files=[
            "src/anneal/formulation/context_qubo_builder.py",
            "src/anneal/formulation/coefficient_builder.py",
            "src/anneal/server.py",
        ],
        token_budget=5000,
    ),
    Task(
        id="incremental_index",
        description="Implement incremental graph updates so only changed files are re-indexed instead of rebuilding the whole graph",
        required_files=[
            "src/anneal/indexer/graph_builder.py",
            "src/anneal/indexer/parser.py",
            "src/anneal/cli.py",
        ],
        token_budget=5000,
    ),
    Task(
        id="composite_dedup",
        description="Fix duplicate node detection in the composite graph source when multiple sources contain the same file",
        required_files=[
            "src/anneal/graph/base.py",
            "src/anneal/graph/anneal_source.py",
            "src/anneal/graph/code_review_graph.py",
        ],
        token_budget=4000,
    ),
    Task(
        id="tracing_analysis",
        description="Add a trace analysis command that shows latency breakdown and usage statistics per stage",
        required_files=[
            "src/anneal/tracing.py",
            "src/anneal/server.py",
            "src/anneal/cli.py",
        ],
        token_budget=4000,
    ),
    Task(
        id="stability_confidence",
        description="Return actual stability confidence scores instead of binary 1.0 for all selected chunks",
        required_files=[
            "src/anneal/assembly/result_builder.py",
            "src/anneal/server.py",
        ],
        token_budget=3000,
    ),
]
