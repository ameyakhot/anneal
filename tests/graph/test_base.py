from anneal.graph.base import Node, Edge, GraphSource
import pytest

def test_node_defaults():
    n = Node(id="f1", path="src/foo.py", name="foo", node_type="function")
    assert n.start_line == 0
    assert n.tokens == 0
    assert n.cluster_id is None
    assert n.metadata == {}

def test_edge_defaults():
    e = Edge(source_id="a", target_id="b", edge_type="imports")
    assert e.weight == 1.0

def test_graph_source_is_abstract():
    with pytest.raises(TypeError):
        GraphSource()  # cannot instantiate abstract class
