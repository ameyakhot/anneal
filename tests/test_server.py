import json
import sqlite3
from pathlib import Path

from anneal.graph.code_review_graph import CodeReviewGraphSource
from anneal.formulation.candidate_generator import CandidateGenerator
from anneal.formulation.context_qubo_builder import ContextQUBOBuilder
from anneal.assembly.result_builder import ResultBuilder, stability_ranking
from spinchain.solvers.simulated_annealing import SimulatedAnnealingSolver


def _make_crg_db(tmp_path: Path) -> None:
    db_dir = tmp_path / ".code-review-graph"
    db_dir.mkdir()
    conn = sqlite3.connect(db_dir / "graph.db")
    conn.executescript("""
        CREATE TABLE nodes (id TEXT, path TEXT, name TEXT, type TEXT,
                            start_line INTEGER, end_line INTEGER);
        CREATE TABLE edges (source_id TEXT, target_id TEXT, type TEXT, weight REAL);
        INSERT INTO nodes VALUES ('n1', 'src/auth.py', 'authenticate', 'function', 1, 30);
        INSERT INTO nodes VALUES ('n2', 'src/auth.py', 'hash_password', 'function', 32, 60);
        INSERT INTO nodes VALUES ('n3', 'src/user.py', 'UserModel', 'class', 1, 80);
        INSERT INTO edges VALUES ('n1', 'n2', 'calls', 1.0);
    """)
    conn.commit()
    conn.close()


def test_full_pipeline_runs(tmp_path):
    _make_crg_db(tmp_path)
    source = CodeReviewGraphSource(tmp_path)
    assert source.is_available()
    gen = CandidateGenerator(source, project_root=tmp_path)
    candidates = gen.generate("fix authentication", max_candidates=20)
    assert len(candidates) > 0
    qubo_builder = ContextQUBOBuilder(strategy="balanced")
    edges = source.get_edges()
    budget = qubo_builder.default_budget()
    bqm = qubo_builder.build(candidates, edges, budget)
    solver = SimulatedAnnealingSolver(num_reads=20, num_sweeps=100)
    sample_set = solver.solve(bqm)
    selected_indices = stability_ranking(sample_set, len(candidates))
    stability_scores = {i: 1.0 for i in selected_indices}
    rb = ResultBuilder()
    result = rb.build(
        candidates=candidates, selected_indices=selected_indices,
        stability_scores=stability_scores, edges=edges, budget=budget,
    )
    assert "selected_chunks" in result
    assert result["total_tokens"] <= budget
    assert 0.0 <= result["budget_utilization"] <= 1.0


def test_pipeline_returns_valid_json(tmp_path):
    _make_crg_db(tmp_path)
    source = CodeReviewGraphSource(tmp_path)
    gen = CandidateGenerator(source, project_root=tmp_path)
    candidates = gen.generate("test something", max_candidates=10)
    qubo_builder = ContextQUBOBuilder()
    edges = source.get_edges()
    bqm = qubo_builder.build(candidates, edges, budget=5000)
    solver = SimulatedAnnealingSolver(num_reads=10, num_sweeps=50)
    sample_set = solver.solve(bqm)
    selected = stability_ranking(sample_set, len(candidates))
    result = ResultBuilder().build(
        candidates=candidates, selected_indices=selected,
        stability_scores={i: 1.0 for i in selected}, edges=edges, budget=5000,
    )
    json.dumps(result)  # Should not raise
