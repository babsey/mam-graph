"""Display d3 force-directed graphs and hierarchical edge bundles in JupyterLab."""

from __future__ import annotations

from typing import Any

from .edgebundle import EDGE_BUNDLE_MIME_TYPE, EdgeBundle
from .forcegraph import MIME_TYPE, ForceGraph

try:
    from ._version import __version__
except ImportError:  # pragma: no cover - only when the extension is not built
    __version__ = "dev"

__all__ = [
    "EDGE_BUNDLE_MIME_TYPE",
    "MIME_TYPE",
    "EdgeBundle",
    "ForceGraph",
    "__version__",
]


def _jupyter_labextension_paths() -> list[dict[str, str]]:
    return [{"src": "labextension", "dest": "mam-graph"}]


def load_ipython_extension(ipython: Any) -> None:
    """Register ``%forcegraph`` and ``%edgebundle`` (``%load_ext mam_graph``)."""
    from .magics import GraphMagics

    ipython.register_magics(GraphMagics)
