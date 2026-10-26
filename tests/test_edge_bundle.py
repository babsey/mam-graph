import pytest

from mam_graph import EDGE_BUNDLE_MIME_TYPE, EdgeBundle
from mam_graph.edgebundle import ROOT_ID

LEAVES = [
    {"id": "v1e", "area": "V1", "layer": "4"},
    {"id": "v1i", "area": "V1", "layer": "4"},
    {"id": "v2e", "area": "V2", "layer": "2/3"},
    {"id": "free"},
]
LINKS = [{"source": "v1e", "target": "v2e"}, {"source": "v2e", "target": "free"}]


def parents(eb):
    return {n["id"]: n.get("parent") for n in eb.nodes}


def test_levels_build_group_nodes_and_root():
    eb = EdgeBundle(LEAVES, LINKS, levels=["area", "layer"])
    p = parents(eb)
    assert p[ROOT_ID] is None
    assert p["::V1"] == ROOT_ID
    assert p["::V1/4"] == "::V1"
    assert p["v1e"] == p["v1i"] == "::V1/4"
    assert p["v2e"] == "::V2/2/3"
    # a node without the level attributes hangs off the root
    assert p["free"] == ROOT_ID
    group = next(n for n in eb.nodes if n["id"] == "::V1/4")
    assert group["label"] == "4"


def test_single_level_as_string():
    eb = EdgeBundle(LEAVES, LINKS, levels="area")
    assert parents(eb)["v2e"] == "::V2"


def test_parent_fields_are_used_without_levels():
    nodes = [
        {"id": "root"},
        {"id": "g", "parent": "root"},
        {"id": "a", "parent": "g"},
        {"id": "b", "parent": "root"},
    ]
    eb = EdgeBundle(nodes, [{"source": "a", "target": "b"}])
    assert parents(eb) == {"root": None, "g": "root", "a": "g", "b": "root"}


def test_flat_nodes_get_synthetic_root():
    eb = EdgeBundle([{"id": 1}, {"id": 2}], [{"source": 1, "target": 2}])
    assert parents(eb) == {ROOT_ID: None, 1: ROOT_ID, 2: ROOT_ID}


def test_validation():
    with pytest.raises(ValueError, match="parent 'x'"):
        EdgeBundle([{"id": "a", "parent": "x"}, {"id": "b"}], [])
    with pytest.raises(ValueError, match="unique"):
        EdgeBundle([{"id": "a"}, {"id": "a"}], [])
    with pytest.raises(ValueError, match="target 'z'"):
        EdgeBundle([{"id": "a"}], [{"source": "a", "target": "z"}])


def test_mimebundle():
    eb = EdgeBundle(LEAVES, LINKS, levels="area", beta=0.5, color_links=True)
    bundle = eb._repr_mimebundle_()
    assert bundle["text/plain"] == "<EdgeBundle: 4 leaves, 2 links>"
    options = bundle[EDGE_BUNDLE_MIME_TYPE]["options"]
    assert options["beta"] == 0.5
    assert options["colorLinks"] is True


def test_from_data_roundtrip_keeps_hierarchy():
    eb = EdgeBundle(LEAVES, LINKS, levels=["area", "layer"])
    again = EdgeBundle.from_data(eb.to_dict(), size=400)
    assert parents(again) == parents(eb)
    assert again.options["size"] == 400


def test_from_networkx_with_levels():
    nx = pytest.importorskip("networkx")
    g = nx.DiGraph()
    g.add_node("a", area="V1")
    g.add_node("b", area="V2")
    g.add_edge("a", "b", weight=2)
    eb = EdgeBundle.from_networkx(g, levels="area")
    assert parents(eb)["a"] == "::V1"
    assert eb.links == [{"source": "a", "target": "b", "weight": 2, "value": 2}]
    assert eb.options["directed"] is True


@pytest.fixture
def ip():
    from IPython.core.interactiveshell import InteractiveShell

    shell = InteractiveShell.instance()
    shell.run_line_magic("load_ext", "mam_graph")
    yield shell
    InteractiveShell.clear_instance()


def test_edgebundle_magic(ip):
    ip.user_ns["data"] = {"nodes": LEAVES, "links": LINKS}
    eb = ip.run_line_magic(
        "edgebundle",
        "data --levels area layer --beta 0.6 --no-labels --color-links  # hi",
    )
    assert isinstance(eb, EdgeBundle)
    assert parents(eb)["v1e"] == "::V1/4"
    assert eb.options["beta"] == 0.6
    assert eb.options["showLabels"] is False
    assert eb.options["colorLinks"] is True


def test_edgebundle_magic_bad_data(ip):
    from IPython.core.error import UsageError

    ip.user_ns["x"] = 42
    with pytest.raises(UsageError, match="got int"):
        ip.run_line_magic("edgebundle", "x")


def test_group_arc_options():
    eb = EdgeBundle(LEAVES, LINKS, levels="area")
    assert eb.options["groupArcs"] is True
    assert eb.options["arcWidth"] == 14
    again = EdgeBundle.from_data(
        {"nodes": LEAVES, "links": LINKS, "options": {"groupArcs": False}}
    )
    assert again.options["groupArcs"] is False


def test_edgebundle_magic_arc_flags(ip):
    ip.user_ns["data"] = {"nodes": LEAVES, "links": LINKS}
    eb = ip.run_line_magic("edgebundle", "data --levels area --no-arcs")
    assert eb.options["groupArcs"] is False
    eb = ip.run_line_magic("edgebundle", "data --levels area --arc-width 20")
    assert eb.options["groupArcs"] is True
    assert eb.options["arcWidth"] == 20
