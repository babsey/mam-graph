# mam-graph

A JupyterLab 4 MIME-renderer extension that draws interactive d3 graphs:

- **Force-directed graphs** ([d3-force](https://d3js.org/d3-force)), via
  `ForceGraph` / `%forcegraph`.
- **Hierarchical edge bundling** ([d3.cluster](https://d3js.org/d3-hierarchy/cluster)
  + [curveBundle](https://d3js.org/d3-shape/curve#curveBundle)), via
  `EdgeBundle` / `%edgebundle`.

Force graphs:

- Drag nodes, drag the background to pan, **Ctrl/⌘ + wheel** to zoom (a plain
  wheel scrolls the notebook).
- Nodes are coloured by `group` (or an explicit `color`); hovering shows the label.
- Directed graphs get arrowheads.
- `*.forcegraph.json` / `*.fgraph` files open in a "Force Graph Viewer".

Edge bundles:

- Leaves sit on a circle, ordered by a hierarchy; links are bundled along it.
- Each group gets a labelled arc around its leaves, one ring per hierarchy
  level (top-level groups outermost).
- With arcs, leaf labels drop the group names the arcs already show
  ("V1 II/IIIE" under V1 / II/III shows as "E"); the tooltip keeps the full label.
- Hover a leaf or a group arc to highlight its links (directed: red = outgoing,
  blue = incoming).
- Leaves are coloured by top-level group (or `group` / `color`).
- `*.edgebundle.json` files open in an "Edge Bundle Viewer".

## Usage

### Render a variable from an earlier cell

```python
%load_ext mam_graph
```

```python
import networkx as nx

G = nx.karate_club_graph()
```

```python
%forcegraph G --labels --charge -200 --height 600
```

The variable can be a networkx graph, a mapping with `nodes` and `links` (or
`edges`, as from `nx.node_link_data`), or a `ForceGraph`. Expressions without
spaces work too (`%forcegraph graphs['a']`). Options: `--height`, `--charge`,
`--link-distance`, `--node-radius`, `--labels`, `--directed`, `--no-zoom`
(see `%forcegraph?`).

### Python API

```python
from mam_graph import ForceGraph

ForceGraph(
    nodes=[{"id": "a", "group": 1}, {"id": "b", "group": 2, "label": "B"}],
    links=[{"source": "a", "target": "b", "value": 2}],
    show_labels=True,
)

# or from networkx (node/edge attributes are kept, `weight` -> `value`)
import networkx as nx

ForceGraph.from_networkx(nx.karate_club_graph(), charge=-200, height=600)

# or from a dict / node_link_data / networkx graph
ForceGraph.from_data(nx.node_link_data(nx.path_graph(5)), show_labels=True)
```

Any kernel can emit the MIME type `application/vnd.mam.forcegraph+json`
with a payload of the form:

```json
{
  "nodes": [{"id": "a", "label": "A", "group": 1, "size": 6, "color": "#f00"}],
  "links": [{"source": "a", "target": "a", "value": 1, "color": "#999"}],
  "options": {
    "height": 500, "charge": -120, "linkDistance": 40, "nodeRadius": 6,
    "showLabels": false, "directed": false, "zoom": true
  }
}
```

### Hierarchical edge bundling

```python
%edgebundle M --levels area layer --directed --color-links
```

The hierarchy comes either from `--levels` / `levels=` (node attributes,
outermost first: `area -> layer -> node`), or from `parent` ids on the nodes.
Nodes without a parent are attached to a synthetic root. Options: `--size`,
`--beta` (0 = straight, 1 = fully bundled), `--node-radius`, `--label-padding`,
`--no-labels`, `--directed`, `--color-links`, `--no-arcs`, `--arc-width`,
`--no-zoom` (see `%edgebundle?`).

```python
from mam_graph import EdgeBundle

EdgeBundle.from_networkx(M, levels=["area", "layer"], beta=0.9)
EdgeBundle(
    nodes=[
        {"id": "root"},
        {"id": "V1", "parent": "root"},
        {"id": "V2", "parent": "root"},
    ],
    links=[{"source": "V1", "target": "V2"}],
)
```

Its MIME type is `application/vnd.mam.edgebundle+json`, with the same
`nodes` / `links` / `options` layout (nodes may carry `parent`).

See [examples/demo.ipynb](examples/demo.ipynb),
[examples/sample.forcegraph.json](examples/sample.forcegraph.json) and
[examples/sample.edgebundle.json](examples/sample.edgebundle.json).

## Development

Requires Node.js and uv.

```bash
uv sync                                   # builds the extension (editable)
uv run jupyter labextension develop . --overwrite
uv run jlpm watch                         # rebuild on change, then reload the browser
uv run jupyter lab
```

Tests and lint:

```bash
uv run pytest
uv run ruff check . && uv run ruff format --check .
```

Build a distributable wheel with `uv build`.
