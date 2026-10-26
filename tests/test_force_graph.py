import pytest

from mam_graph import MIME_TYPE, ForceGraph


def test_mimebundle_contains_graph_and_options():
    g = ForceGraph([{"id": "a"}, {"id": "b"}], [{"source": "a", "target": "b"}])
    bundle = g._repr_mimebundle_()
    assert bundle["text/plain"] == "<ForceGraph: 2 nodes, 1 links>"
    data = bundle[MIME_TYPE]
    assert data["nodes"] == [{"id": "a"}, {"id": "b"}]
    assert data["links"] == [{"source": "a", "target": "b"}]
    assert data["options"]["linkDistance"] == 40


def test_unknown_link_endpoint_raises():
    with pytest.raises(ValueError, match="target 'c'"):
        ForceGraph([{"id": "a"}], [{"source": "a", "target": "c"}])


def test_from_networkx():
    nx = pytest.importorskip("networkx")
    g = nx.DiGraph()
    g.add_node(1, group="x")
    g.add_edge(1, 2, weight=3)
    fg = ForceGraph.from_networkx(g)
    assert fg.nodes == [{"id": 1, "group": "x"}, {"id": 2}]
    assert fg.links == [{"source": 1, "target": 2, "weight": 3, "value": 3}]
    assert fg.options["directed"] is True


def test_from_data_accepts_node_link_mapping():
    data = {
        "directed": True,
        "nodes": [{"id": "a"}, {"id": "b"}],
        "edges": [{"source": "a", "target": "b"}],
        "options": {"showLabels": True, "linkDistance": 80},
    }
    fg = ForceGraph.from_data(data, height=300)
    assert fg.links == [{"source": "a", "target": "b"}]
    assert fg.options["directed"] is True
    assert fg.options["showLabels"] is True
    assert fg.options["linkDistance"] == 80
    assert fg.options["height"] == 300


def test_from_data_rejects_other_objects():
    with pytest.raises(TypeError, match="got list"):
        ForceGraph.from_data([1, 2])


@pytest.fixture
def ip():
    from IPython.core.interactiveshell import InteractiveShell

    shell = InteractiveShell.instance()
    shell.run_line_magic("load_ext", "mam_graph")
    yield shell
    InteractiveShell.clear_instance()


def test_magic_reads_variable_from_namespace(ip):
    nx = pytest.importorskip("networkx")
    ip.run_cell("import networkx as nx\nG = nx.path_graph(3)")
    fg = ip.run_line_magic("forcegraph", "G --labels --height 300 --no-zoom")
    assert isinstance(fg, ForceGraph)
    assert len(fg.nodes) == 3
    assert fg.options["showLabels"] is True
    assert fg.options["height"] == 300
    assert fg.options["zoom"] is False
    assert fg.options["directed"] is nx.path_graph(3).is_directed()


def test_magic_evaluates_expression(ip):
    ip.user_ns["graphs"] = {"g": {"nodes": [{"id": 1}], "links": []}}
    fg = ip.run_line_magic("forcegraph", "graphs['g']")
    assert fg.nodes == [{"id": 1}]


def test_magic_unknown_variable(ip):
    from IPython.core.error import UsageError

    with pytest.raises(UsageError, match="missing"):
        ip.run_line_magic("forcegraph", "missing")


def test_magic_ignores_trailing_comment(ip):
    ip.user_ns["g"] = {"nodes": [{"id": 1}], "links": []}
    fg = ip.run_line_magic("forcegraph", "g --labels  # show it")
    assert fg.options["showLabels"] is True
