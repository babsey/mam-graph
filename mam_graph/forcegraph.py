"""Force-directed graphs (d3-force)."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from ._common import check_links, is_networkx, mapping_parts, networkx_parts

MIME_TYPE = "application/vnd.mam.forcegraph+json"

# Frontend option names (camelCase) -> ForceGraph keyword arguments.
_OPTION_KWARGS = {
    "height": "height",
    "charge": "charge",
    "linkDistance": "link_distance",
    "nodeRadius": "node_radius",
    "showLabels": "show_labels",
    "directed": "directed",
    "zoom": "zoom",
}


class ForceGraph:
    """A force-directed graph rendered by the mam-graph JupyterLab extension.

    Parameters
    ----------
    nodes:
        Node dicts with an ``id`` and optional ``label``, ``group``, ``size``
        and ``color``.
    links:
        Link dicts with ``source`` and ``target`` (node ids) and optional
        ``value`` (stroke width) and ``color``.
    height, charge, link_distance, node_radius, show_labels, directed, zoom:
        Rendering options forwarded to the frontend.
    """

    def __init__(
        self,
        nodes: Iterable[Mapping[str, Any]],
        links: Iterable[Mapping[str, Any]],
        *,
        height: int = 500,
        charge: float = -120,
        link_distance: float = 40,
        node_radius: float = 6,
        show_labels: bool = False,
        directed: bool = False,
        zoom: bool = True,
    ) -> None:
        self.nodes = [dict(n) for n in nodes]
        self.links = [dict(link) for link in links]
        check_links(self.links, {n["id"] for n in self.nodes})
        self.options = {
            "height": height,
            "charge": charge,
            "linkDistance": link_distance,
            "nodeRadius": node_radius,
            "showLabels": show_labels,
            "directed": directed,
            "zoom": zoom,
        }

    @classmethod
    def from_networkx(cls, graph: Any, **kwargs: Any) -> ForceGraph:
        """Build a ForceGraph from a networkx graph; node/edge attributes are kept.

        ``weight`` edge attributes are mapped to ``value``. ``directed`` defaults
        to ``graph.is_directed()``.
        """
        nodes, links = networkx_parts(graph)
        kwargs.setdefault("directed", graph.is_directed())
        return cls(nodes, links, **kwargs)

    @classmethod
    def from_data(cls, data: Any, **kwargs: Any) -> ForceGraph:
        """Build a ForceGraph from a networkx graph, a ForceGraph, or a mapping.

        A mapping needs ``nodes`` and ``links`` (or ``edges``, as produced by
        ``networkx.node_link_data``) and may carry frontend ``options``.
        ``kwargs`` override any options found in ``data``.
        """
        if isinstance(data, ForceGraph):
            data = data.to_dict()
        elif is_networkx(data):
            return cls.from_networkx(data, **kwargs)
        nodes, links, options = mapping_parts(data, _OPTION_KWARGS)
        return cls(nodes, links, **{**options, **kwargs})

    def to_dict(self) -> dict[str, Any]:
        return {"nodes": self.nodes, "links": self.links, "options": self.options}

    def _repr_mimebundle_(self, include=None, exclude=None) -> dict[str, Any]:
        n, m = len(self.nodes), len(self.links)
        return {
            MIME_TYPE: self.to_dict(),
            "text/plain": f"<ForceGraph: {n} nodes, {m} links>",
        }
