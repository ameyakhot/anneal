from anneal.graph.base import Node, Edge, GraphSource
import pytest


def test_node_defaults():
    n = Node(id="f1", path="src/foo.py", name="foo", node_type="function")
    assert n.start_line == 0
    assert n.end_line == 0
    assert n.tokens == 0
    assert n.cluster_id is None
    assert n.metadata == {}


def test_edge_defaults():
    e = Edge(source_id="a", target_id="b", edge_type="imports")
    assert e.weight == 1.0


def test_graph_source_is_abstract():
    with pytest.raises(TypeError):
        GraphSource()  # cannot instantiate abstract class


def test_graph_source_abstract_methods():
    assert {"is_available", "get_nodes", "get_edges", "get_edges_for_node", "name"} == GraphSource.__abstractmethods__


def test_node_count_delegates_to_get_nodes():
    class _ConcreteSource(GraphSource):
        @property
        def name(self): return "test"
        def is_available(self): return True
        def get_nodes(self): return [
            Node(id="x", path="p.py", name="f", node_type="function")
        ]
        def get_edges(self): return []
        def get_edges_for_node(self, node_id): return []

    src = _ConcreteSource()
    assert src.node_count == 1
