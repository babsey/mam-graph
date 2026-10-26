"""IPython magics that render a graph stored in a notebook variable."""

from __future__ import annotations

import re
from typing import Any

from IPython.core.error import UsageError
from IPython.core.magic import Magics, line_magic, magics_class
from IPython.core.magic_arguments import argument, magic_arguments, parse_argstring

from .edgebundle import EdgeBundle
from .forcegraph import ForceGraph

_VARIABLE_HELP = (
    "Variable (or expression without spaces) holding the graph: a networkx "
    "graph, a {{'nodes', 'links'}} mapping or a {cls}."
)


@magics_class
class GraphMagics(Magics):
    def _render(self, magic: Any, line: str, cls: Any) -> Any:
        # IPython does not strip trailing comments from line magics.
        args = parse_argstring(magic, re.sub(r"\s+#.*$", "", line))
        name = magic.__name__
        ns = self.shell.user_ns
        if args.variable in ns:
            data = ns[args.variable]
        else:
            try:
                data = self.shell.ev(args.variable)
            except NameError as err:
                raise UsageError(f"%{name}: {err}") from None
        kwargs = {
            k: v for k, v in vars(args).items() if k != "variable" and v is not None
        }
        try:
            return cls.from_data(data, **kwargs)
        except (TypeError, ValueError, KeyError) as err:
            raise UsageError(f"%{name} {args.variable}: {err}") from None

    @magic_arguments()
    @argument("variable", help=_VARIABLE_HELP.format(cls="ForceGraph"))
    @argument("--height", type=int, help="Height in pixels.")
    @argument("--charge", type=float, help="Many-body force strength.")
    @argument("--link-distance", type=float, help="Target link length.")
    @argument("--node-radius", type=float, help="Default node radius.")
    @argument(
        "--labels",
        dest="show_labels",
        action="store_true",
        default=None,
        help="Show node labels.",
    )
    @argument("--directed", action="store_true", default=None, help="Draw arrowheads.")
    @argument(
        "--no-zoom",
        dest="zoom",
        action="store_false",
        default=None,
        help="Disable pan and zoom.",
    )
    @line_magic
    def forcegraph(self, line: str) -> ForceGraph:
        """Render a graph defined in an earlier cell, e.g. ``%forcegraph G``."""
        return self._render(self.forcegraph, line, ForceGraph)

    @magic_arguments()
    @argument("variable", help=_VARIABLE_HELP.format(cls="EdgeBundle"))
    @argument(
        "--levels",
        nargs="+",
        metavar="ATTR",
        help="Node attributes defining the hierarchy, outermost first.",
    )
    @argument("--size", type=int, help="Diameter in pixels.")
    @argument("--beta", type=float, help="Bundling strength between 0 and 1.")
    @argument("--node-radius", type=float, help="Leaf node radius.")
    @argument("--label-padding", type=float, help="Space reserved for labels.")
    @argument(
        "--no-labels",
        dest="show_labels",
        action="store_false",
        default=None,
        help="Hide leaf labels.",
    )
    @argument(
        "--directed",
        action="store_true",
        default=None,
        help="Highlight incoming and outgoing links separately.",
    )
    @argument(
        "--color-links",
        action="store_true",
        default=None,
        help="Colour links by their source group.",
    )
    @argument(
        "--no-arcs",
        dest="group_arcs",
        action="store_false",
        default=None,
        help="Hide the group arcs around the circle.",
    )
    @argument("--arc-width", type=float, help="Thickness of each group arc ring.")
    @argument(
        "--no-zoom",
        dest="zoom",
        action="store_false",
        default=None,
        help="Disable pan and zoom.",
    )
    @line_magic
    def edgebundle(self, line: str) -> EdgeBundle:
        """Render a hierarchical edge bundle, e.g. ``%edgebundle G --levels area``."""
        return self._render(self.edgebundle, line, EdgeBundle)
