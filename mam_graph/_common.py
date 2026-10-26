"""Helpers shared by the graph display classes."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any


def is_networkx(obj: Any) -> bool:
    return hasattr(obj, "is_directed") and hasattr(obj, "edges")


def networkx_parts(graph: Any) -> tuple[list[dict], list[dict]]:
    """Nodes and links of a networkx graph; ``weight`` is mapped to ``value``."""
    nodes = [{"id": n, **attrs} for n, attrs in graph.nodes(data=True)]
    links = []
    for u, v, attrs in graph.edges(data=True):
        link = {"source": u, "target": v, **attrs}
        if "weight" in attrs and "value" not in attrs:
            link["value"] = attrs["weight"]
        links.append(link)
    return nodes, links


def mapping_parts(
    data: Any, option_kwargs: Mapping[str, str]
) -> tuple[list, list, dict[str, Any]]:
    """Nodes, links and keyword options of a ``{"nodes", "links"}`` mapping.

    ``edges`` (as produced by ``networkx.node_link_data``) is accepted in place
    of ``links``; frontend ``options`` are mapped via ``option_kwargs``.
    """
    if not isinstance(data, Mapping) or "nodes" not in data:
        raise TypeError(
            "expected a networkx graph or a mapping with 'nodes' and 'links', "
            f"got {type(data).__name__}"
        )
    links = data.get("links", data.get("edges", []))
    options = {
        option_kwargs[k]: v
        for k, v in (data.get("options") or {}).items()
        if k in option_kwargs
    }
    if "directed" in data and "directed" not in options:
        options["directed"] = bool(data["directed"])
    return data["nodes"], links, options


def check_links(links: Iterable[Mapping[str, Any]], ids: set) -> None:
    for link in links:
        for end in ("source", "target"):
            if link[end] not in ids:
                raise ValueError(f"link {end} {link[end]!r} is not a node id")
