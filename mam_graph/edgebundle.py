"""Hierarchical edge bundling (d3.cluster + d3.curveBundle)."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from ._common import check_links, is_networkx, mapping_parts, networkx_parts

EDGE_BUNDLE_MIME_TYPE = "application/vnd.mam.edgebundle+json"

# Id of the synthetic root added when the nodes do not have a single root.
ROOT_ID = "::"

# Frontend option names (camelCase) -> EdgeBundle keyword arguments.
_OPTION_KWARGS = {
    "size": "size",
    "beta": "beta",
    "showLabels": "show_labels",
    "nodeRadius": "node_radius",
    "labelPadding": "label_padding",
    "directed": "directed",
    "colorLinks": "color_links",
    "groupArcs": "group_arcs",
    "arcWidth": "arc_width",
    "zoom": "zoom",
}


def _build_hierarchy(nodes: list[dict], levels: Sequence[str]) -> list[dict]:
    """Add group nodes for ``levels`` and a root, so every node has one parent.

    With ``levels``, each node is placed under the group path given by its
    attribute values, e.g. ``levels=["area", "layer"]`` yields ``area -> layer
    -> node``; a missing or ``None`` value ends the path early. Without
    ``levels``, existing ``parent`` fields are used.
    """
    if levels:
        groups: dict[str, dict] = {}
        leaves = []
        for node in nodes:
            parent = None
            path: list[str] = []
            for level in levels:
                if node.get(level) is None:
                    break
                path.append(str(node[level]))
                gid = "::" + "/".join(path)
                if gid not in groups:
                    groups[gid] = {"id": gid, "parent": parent, "label": path[-1]}
                parent = gid
            leaves.append({**node, "parent": parent})
        nodes = [*groups.values(), *leaves]
    if sum(n.get("parent") is None for n in nodes) == 1:
        return nodes
    return [
        {"id": ROOT_ID},
        *({**n, "parent": ROOT_ID} if n.get("parent") is None else n for n in nodes),
    ]


class EdgeBundle:
    """A hierarchical edge bundling diagram rendered by mam-graph.

    Leaves of the hierarchy are placed on a circle and links are drawn as
    bundled curves following the hierarchy.

    Parameters
    ----------
    nodes:
        Node dicts with an ``id`` and optional ``parent`` (id of the parent
        node), ``label``, ``group`` and ``color``.
    links:
        Link dicts with ``source`` and ``target`` (node ids) and optional
        ``value`` (stroke width) and ``color``.
    levels:
        Node attribute name(s) that define the hierarchy, outermost first,
        e.g. ``["area", "layer"]``. Overrides ``parent`` fields.
    size:
        Diameter of the diagram in pixels.
    beta:
        Bundling strength, from 0 (straight lines) to 1 (fully bundled).
    group_arcs:
        Draw an arc around the leaves of every group, one ring per hierarchy
        level (top-level groups outermost), labelled with the group name.
    arc_width:
        Thickness of each arc ring in pixels.
    show_labels, node_radius, label_padding, directed, color_links, zoom:
        Rendering options forwarded to the frontend. ``label_padding`` is the
        space reserved for leaf labels (0 picks it from the label lengths);
        ``color_links`` colours links by their source group.
    """

    def __init__(
        self,
        nodes: Iterable[Mapping[str, Any]],
        links: Iterable[Mapping[str, Any]],
        *,
        levels: str | Sequence[str] | None = None,
        size: int = 600,
        beta: float = 0.85,
        show_labels: bool = True,
        node_radius: float = 2.5,
        label_padding: float = 0,
        directed: bool = False,
        color_links: bool = False,
        group_arcs: bool = True,
        arc_width: float = 14,
        zoom: bool = True,
    ) -> None:
        if isinstance(levels, str):
            levels = [levels]
        self.nodes = _build_hierarchy([dict(n) for n in nodes], levels or [])
        self.links = [dict(link) for link in links]
        ids = [n["id"] for n in self.nodes]
        id_set = set(ids)
        if len(id_set) != len(ids):
            raise ValueError("node ids must be unique")
        for node in self.nodes:
            parent = node.get("parent")
            if parent is not None and parent not in id_set:
                raise ValueError(
                    f"parent {parent!r} of {node['id']!r} is not a node id"
                )
        check_links(self.links, id_set)
        self.options = {
            "size": size,
            "beta": beta,
            "showLabels": show_labels,
            "nodeRadius": node_radius,
            "labelPadding": label_padding,
            "directed": directed,
            "colorLinks": color_links,
            "groupArcs": group_arcs,
            "arcWidth": arc_width,
            "zoom": zoom,
        }

    @classmethod
    def from_networkx(cls, graph: Any, **kwargs: Any) -> EdgeBundle:
        """Build an EdgeBundle from a networkx graph; attributes are kept.

        Pass ``levels`` to group nodes by attributes. ``weight`` edge attributes
        are mapped to ``value``; ``directed`` defaults to ``graph.is_directed()``.
        """
        nodes, links = networkx_parts(graph)
        kwargs.setdefault("directed", graph.is_directed())
        return cls(nodes, links, **kwargs)

    @classmethod
    def from_data(cls, data: Any, **kwargs: Any) -> EdgeBundle:
        """Build an EdgeBundle from a networkx graph, an EdgeBundle, or a mapping.

        A mapping needs ``nodes`` and ``links`` (or ``edges``, as produced by
        ``networkx.node_link_data``) and may carry frontend ``options``.
        ``kwargs`` override any options found in ``data``.
        """
        if isinstance(data, EdgeBundle):
            data = data.to_dict()
        elif is_networkx(data):
            return cls.from_networkx(data, **kwargs)
        nodes, links, options = mapping_parts(data, _OPTION_KWARGS)
        return cls(nodes, links, **{**options, **kwargs})

    def to_dict(self) -> dict[str, Any]:
        return {"nodes": self.nodes, "links": self.links, "options": self.options}

    def _repr_mimebundle_(self, include=None, exclude=None) -> dict[str, Any]:
        parents = {n.get("parent") for n in self.nodes}
        n_leaves = sum(n["id"] not in parents for n in self.nodes)
        return {
            EDGE_BUNDLE_MIME_TYPE: self.to_dict(),
            "text/plain": (f"<EdgeBundle: {n_leaves} leaves, {len(self.links)} links>"),
        }
