"""End-to-end test: anneal init → get_optimal_context pipeline."""
from anneal.indexer.graph_builder import build_graph
from anneal.graph.detector import detect_sources, CompositeGraphSource
from anneal.formulation.candidate_generator import CandidateGenerator
from anneal.formulation.context_qubo_builder import ContextQUBOBuilder
from anneal.assembly.result_builder import ResultBuilder, stability_ranking
from spinchain.solvers.simulated_annealing import SimulatedAnnealingSolver


def _make_project(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "auth.py").write_text(
        "from src.user import User\n\n"
        "def authenticate(username: str) -> bool:\n"
        "    user = User(username)\n"
        "    return user.is_valid()\n\n"
        "def hash_password(pw: str) -> str:\n"
        "    return pw[::-1]\n"
    )
    (src / "user.py").write_text(
        "class User:\n"
        "    def __init__(self, name: str):\n"
        "        self.name = name\n\n"
        "    def is_valid(self) -> bool:\n"
        "        return len(self.name) > 0\n"
    )
    return tmp_path


def test_init_to_context_pipeline(tmp_path):
    project = _make_project(tmp_path)
    result = build_graph(project)
    assert result["node_count"] >= 3

    sources = detect_sources(project)
    assert len(sources) >= 1
    assert any(s.name == "anneal" for s in sources)

    composite = CompositeGraphSource(sources)
    gen = CandidateGenerator(composite, project_root=project)
    candidates = gen.generate("fix authentication bug", max_candidates=20)
    assert len(candidates) > 0

    edges = composite.get_edges()
    bqm = ContextQUBOBuilder().build(candidates, edges, budget=2000)
    sample_set = SimulatedAnnealingSolver(num_reads=20, num_sweeps=100).solve(bqm)
    selected = stability_ranking(sample_set, len(candidates))

    rb_result = ResultBuilder().build(
        candidates=candidates, selected_indices=selected,
        stability_scores={i: 1.0 for i in selected},
        edges=edges, budget=2000,
    )
    assert len(rb_result["selected_chunks"]) > 0
    paths = {c["path"] for c in rb_result["selected_chunks"]}
    assert any("auth" in p for p in paths)
