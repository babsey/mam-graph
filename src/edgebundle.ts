import { IRenderMime } from '@jupyterlab/rendermime-interfaces';
import { Widget } from '@lumino/widgets';
import * as d3 from 'd3';

import { parseData, wheelZoomFilter } from './utils';

/**
 * The MIME type rendered as a hierarchical edge bundle.
 */
export const EDGE_BUNDLE_MIME_TYPE = 'application/vnd.mam.edgebundle+json';

const CLASS_NAME = 'jp-EdgeBundle';

type Id = string | number;

export interface IBundleNode {
  id: Id;
  parent?: Id | null;
  label?: string;
  group?: string | number;
  color?: string;
  [key: string]: unknown;
}

export interface IBundleLink {
  source: Id;
  target: Id;
  value?: number;
  color?: string;
  [key: string]: unknown;
}

export interface IBundleOptions {
  size?: number;
  beta?: number;
  showLabels?: boolean;
  nodeRadius?: number;
  labelPadding?: number;
  directed?: boolean;
  colorLinks?: boolean;
  groupArcs?: boolean;
  arcWidth?: number;
  zoom?: boolean;
}

export interface IBundleData {
  nodes: IBundleNode[];
  links: IBundleLink[];
  options?: IBundleOptions;
}

const DEFAULTS: Required<IBundleOptions> = {
  size: 600,
  beta: 0.85,
  showLabels: true,
  nodeRadius: 2.5,
  labelPadding: 0,
  directed: false,
  colorLinks: false,
  groupArcs: true,
  arcWidth: 14,
  zoom: true
};

const ARC_GAP = 2;
// Rough widths of a 10px leaf / 9px arc label character, used before the
// SVG is attached to the page.
const CHAR_WIDTH = 6;
const ARC_CHAR_WIDTH = 5;

type HNode = d3.HierarchyPointNode<IBundleNode>;

interface IBundledLink {
  link: IBundleLink;
  source: HNode;
  target: HNode;
  path: HNode[];
}

const label = (d: d3.HierarchyNode<IBundleNode>) =>
  d.data.label ?? String(d.data.id);

const SEPARATORS = /^[\s\-_/:.,|]+/;

/**
 * A leaf's label without the leading labels of its groups, which the arcs
 * already show: "V1 II/IIIE" under V1 / II/III becomes "E". Falls back to the
 * full label when nothing would be left.
 */
const shortLabel = (d: d3.HierarchyNode<IBundleNode>): string => {
  const full = label(d);
  let rest = full;
  for (const group of d.ancestors().reverse().slice(1, -1)) {
    const prefix = label(group);
    const trimmed = rest.replace(SEPARATORS, '');
    if (prefix && trimmed.startsWith(prefix) && trimmed.length > prefix.length) {
      rest = trimmed.slice(prefix.length);
    }
  }
  return rest.replace(SEPARATORS, '') || full;
};

/**
 * A widget that renders a hierarchical edge bundling diagram with d3.
 */
export class EdgeBundleRenderer
  extends Widget
  implements IRenderMime.IRenderer
{
  constructor(options: IRenderMime.IRendererOptions) {
    super();
    this._mimeType = options.mimeType;
    this.addClass(CLASS_NAME);
  }

  renderModel(model: IRenderMime.IMimeModel): Promise<void> {
    this.node.textContent = '';
    try {
      this._draw(parseData<IBundleData>(model.data[this._mimeType]));
    } catch (err) {
      this.node.textContent = `Unable to render edge bundle: ${err}`;
    }
    return Promise.resolve();
  }

  private _draw(data: IBundleData): void {
    if (!data || !Array.isArray(data.nodes) || !Array.isArray(data.links)) {
      throw new Error('expected an object with "nodes" and "links" arrays');
    }
    const opts = { ...DEFAULTS, ...(data.options ?? {}) };
    const size = opts.size;

    const stratified = d3
      .stratify<IBundleNode>()
      .id(d => String(d.id))
      .parentId(d =>
        d.parent === undefined || d.parent === null ? null : String(d.parent)
      )(data.nodes)
      .sort(
        (a, b) =>
          d3.ascending(a.height, b.height) ||
          String(a.data.label ?? a.data.id).localeCompare(
            String(b.data.label ?? b.data.id),
            undefined,
            { numeric: true }
          )
      );

    // Ring space: labels, then one arc ring per group level.
    const groups = stratified
      .descendants()
      .filter(d => d.depth > 0 && d.children);
    const levels = opts.groupArcs ? d3.max(groups, d => d.depth) ?? 0 : 0;
    // Arcs already name the groups, so leaves only show their own part.
    const leafLabel = levels ? shortLabel : label;
    const longest =
      d3.max(stratified.leaves(), d => leafLabel(d).length) ?? 0;
    const labelSpace = opts.showLabels
      ? opts.labelPadding ||
        Math.min(longest * CHAR_WIDTH + opts.nodeRadius + 6, size * 0.2)
      : opts.nodeRadius + 4;
    const ringSpace = levels * (opts.arcWidth + ARC_GAP);
    const radius = Math.max(size / 2 - labelSpace - ringSpace - 4, 20);

    const root = d3.cluster<IBundleNode>().size([2 * Math.PI, radius])(
      stratified
    );
    const byId = new Map(root.descendants().map(d => [String(d.data.id), d]));
    const leaves = root.leaves();

    const bundled: IBundledLink[] = data.links.map(link => {
      const source = byId.get(String(link.source));
      const target = byId.get(String(link.target));
      if (!source || !target) {
        throw new Error(
          `unknown link endpoint ${link.source} -> ${link.target}`
        );
      }
      return { link, source, target, path: source.path(target) };
    });

    const outgoing = new Map<HNode, Set<HNode>>();
    const incoming = new Map<HNode, Set<HNode>>();
    for (const { source, target } of bundled) {
      Private.add(outgoing, source, target);
      Private.add(incoming, target, source);
    }

    // Colour by the explicit group, else by the top-level ancestor.
    const color = d3.scaleOrdinal<string>(d3.schemeTableau10);
    const groupOf = (d: HNode): string => {
      if (d.data.group !== undefined) {
        return String(d.data.group);
      }
      const top = d.ancestors().find(a => a.depth === 1);
      return top && top !== d ? String(top.data.id) : '';
    };
    const nodeColor = (d: HNode) => d.data.color ?? color(groupOf(d));

    const svg = d3
      .select(this.node)
      .append('svg')
      .attr('viewBox', [-size / 2, -size / 2, size, size].join(' '))
      .attr('height', size)
      .attr('class', `${CLASS_NAME}-svg`);
    const content = svg.append('g');

    const line = d3
      .lineRadial<HNode>()
      .curve(d3.curveBundle.beta(opts.beta))
      .radius(d => d.y)
      .angle(d => d.x);

    const link = content
      .append('g')
      .attr('class', `${CLASS_NAME}-links`)
      .selectAll<SVGPathElement, IBundledLink>('path')
      .data(bundled)
      .join('path')
      .attr('d', d => line(d.path))
      .attr('stroke-width', d => Math.sqrt(d.link.value ?? 1))
      .style(
        'stroke',
        d => d.link.color ?? (opts.colorLinks ? nodeColor(d.source) : null)
      );

    const arc = content
      .append('g')
      .attr('class', `${CLASS_NAME}-arcs`)
      .selectAll<SVGGElement, HNode>('g')
      .data(levels ? root.descendants().filter(d => d.depth > 0 && d.children) : [])
      .join('g');
    if (levels) {
      this._drawArcs(arc, leaves, radius + labelSpace, levels, opts, nodeColor);
    }

    const leaf = content
      .append('g')
      .attr('class', `${CLASS_NAME}-nodes`)
      .selectAll<SVGGElement, HNode>('g')
      .data(leaves)
      .join('g')
      .attr(
        'transform',
        d => `rotate(${(d.x * 180) / Math.PI - 90}) translate(${d.y},0)`
      );

    leaf
      .append('circle')
      .attr('r', opts.nodeRadius)
      .attr('fill', nodeColor);

    if (opts.showLabels) {
      const offset = opts.nodeRadius + 3;
      leaf
        .append('text')
        .attr('dy', '0.31em')
        .attr('x', d => (d.x < Math.PI ? offset : -offset))
        .attr('text-anchor', d => (d.x < Math.PI ? 'start' : 'end'))
        .attr('transform', d => (d.x >= Math.PI ? 'rotate(180)' : null))
        .text(leafLabel);
    }

    leaf.append('title').text(d => {
      const nIn = incoming.get(d)?.size ?? 0;
      const nOut = outgoing.get(d)?.size ?? 0;
      return opts.directed
        ? `${label(d)}\n${nOut} outgoing, ${nIn} incoming`
        : `${label(d)}\n${new Set([...(incoming.get(d) ?? []), ...(outgoing.get(d) ?? [])]).size} linked`;
    });

    // Highlight the links of the hovered leaf or group.
    const focus = `${CLASS_NAME}-focus`;
    const touches = (l: IBundledLink, members: Set<HNode>) =>
      members.has(l.source) || members.has(l.target);
    const highlight = (members: Set<HNode>) => {
      svg.classed(focus, true);
      const outs = new Set<HNode>();
      const ins = new Set<HNode>();
      for (const l of bundled) {
        if (members.has(l.source)) {
          outs.add(l.target);
        }
        if (members.has(l.target)) {
          ins.add(l.source);
        }
      }
      link
        .classed('jp-mod-outgoing', l => opts.directed && members.has(l.source))
        .classed(
          'jp-mod-incoming',
          l => opts.directed && !members.has(l.source) && members.has(l.target)
        )
        .classed('jp-mod-linked', l => !opts.directed && touches(l, members))
        .filter(l => touches(l, members))
        .raise();
      const other = (n: HNode) => !members.has(n);
      leaf
        .classed('jp-mod-active', n => members.has(n))
        .classed('jp-mod-outgoing', n => opts.directed && other(n) && outs.has(n))
        .classed(
          'jp-mod-incoming',
          n => opts.directed && other(n) && !outs.has(n) && ins.has(n)
        )
        .classed(
          'jp-mod-linked',
          n => !opts.directed && other(n) && (outs.has(n) || ins.has(n))
        );
      arc.classed('jp-mod-active', g => g.leaves().some(n => members.has(n)));
    };
    const clear = () => {
      svg.classed(focus, false);
      for (const sel of [link, leaf, arc] as d3.Selection<any, any, any, any>[]) {
        sel
          .classed('jp-mod-outgoing', false)
          .classed('jp-mod-incoming', false)
          .classed('jp-mod-linked', false)
          .classed('jp-mod-active', false);
      }
    };
    leaf
      .on('mouseenter', (_event, d) => highlight(new Set([d])))
      .on('mouseleave', clear);
    arc
      .on('mouseenter', (_event, g) => highlight(new Set(g.leaves())))
      .on('mouseleave', clear);

    if (opts.zoom) {
      svg.call(
        d3
          .zoom<SVGSVGElement, unknown>()
          .scaleExtent([0.2, 10])
          .filter(wheelZoomFilter)
          .on('zoom', event => content.attr('transform', event.transform))
      );
    }
  }

  /**
   * Draw one arc per group around the leaves, a ring per hierarchy level
   * with top-level groups outermost, and write the group name along it.
   */
  private _drawArcs(
    arc: d3.Selection<SVGGElement, HNode, SVGGElement, unknown>,
    leaves: HNode[],
    inner: number,
    levels: number,
    opts: Required<IBundleOptions>,
    nodeColor: (d: HNode) => string
  ): void {
    const xs = leaves.map(d => d.x).sort(d3.ascending);
    const minStep = d3.min(d3.pairs(xs), ([a, b]) => b - a) || Math.PI;
    const half = Math.min(minStep * 0.45, Math.PI);
    const width = opts.arcWidth;
    const span = (g: HNode) => {
      const [x0, x1] = d3.extent(g.leaves(), d => d.x) as [number, number];
      return [x0 - half, x1 + half];
    };
    const r0 = (g: HNode) => inner + (levels - g.depth) * (width + ARC_GAP);
    const shape = d3
      .arc<HNode>()
      .innerRadius(r0)
      .outerRadius(g => r0(g) + width)
      .startAngle(g => span(g)[0])
      .endAngle(g => span(g)[1]);
    const top = (g: HNode) => g.ancestors().find(a => a.depth === 1) ?? g;

    arc
      .append('path')
      .attr('class', `${CLASS_NAME}-arc`)
      .attr('d', shape)
      .attr('fill', g => g.data.color ?? nodeColor(top(g).leaves()[0]))
      .attr('fill-opacity', g => (g.depth === 1 ? 0.9 : 0.6));

    arc.append('title').text(g => {
      const path = g
        .ancestors()
        .reverse()
        .slice(1)
        .map(label)
        .join(' ');
      return `${path}\n${g.leaves().length} nodes`;
    });

    // Text follows the arc's centre line, reversed on the lower half so it
    // reads left to right.
    const uid = `eb-${Private.nextId++}`;
    arc.each(function (g, i) {
      const [a0, a1] = span(g);
      const r = r0(g) + width / 2;
      const length = r * (a1 - a0);
      const maxChars = Math.floor(length / ARC_CHAR_WIDTH);
      let text = label(g);
      if (maxChars < 2) {
        return;
      }
      if (text.length > maxChars) {
        text = text.slice(0, maxChars - 1) + '\u2026';
      }
      const mid = (a0 + a1) / 2;
      const flip = mid > Math.PI / 2 && mid < (3 * Math.PI) / 2;
      const point = (a: number) => [r * Math.sin(a), -r * Math.cos(a)];
      const [sx, sy] = point(flip ? a1 : a0);
      const [ex, ey] = point(flip ? a0 : a1);
      const large = a1 - a0 > Math.PI ? 1 : 0;
      const id = `${uid}-${i}`;
      const sel = d3.select(this);
      sel
        .append('path')
        .attr('id', id)
        .attr('class', `${CLASS_NAME}-arcGuide`)
        .attr('d', `M${sx},${sy}A${r},${r} 0 ${large} ${flip ? 0 : 1} ${ex},${ey}`);
      sel
        .append('text')
        .attr('dominant-baseline', 'central')
        .append('textPath')
        .attr('href', `#${id}`)
        .attr('startOffset', '50%')
        .attr('text-anchor', 'middle')
        .text(text);
    });
  }

  private _mimeType: string;
}

namespace Private {
  export let nextId = 0;

  export function add(map: Map<HNode, Set<HNode>>, key: HNode, value: HNode) {
    let set = map.get(key);
    if (!set) {
      set = new Set();
      map.set(key, set);
    }
    set.add(value);
  }
}

export const edgeBundleRendererFactory: IRenderMime.IRendererFactory = {
  safe: true,
  mimeTypes: [EDGE_BUNDLE_MIME_TYPE],
  createRenderer: options => new EdgeBundleRenderer(options)
};

export const edgeBundleExtension: IRenderMime.IExtension = {
  id: 'mam-graph:edgebundle',
  description: 'Renders hierarchical edge bundles with d3.',
  rendererFactory: edgeBundleRendererFactory,
  rank: 100,
  dataType: 'json',
  fileTypes: [
    {
      name: 'edgebundle',
      displayName: 'Edge Bundle',
      mimeTypes: [EDGE_BUNDLE_MIME_TYPE],
      extensions: ['.edgebundle.json'],
      fileFormat: 'text'
    }
  ],
  documentWidgetFactoryOptions: {
    name: 'Edge Bundle Viewer',
    primaryFileType: 'edgebundle',
    fileTypes: ['edgebundle'],
    defaultFor: ['edgebundle']
  }
};
