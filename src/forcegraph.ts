import { IRenderMime } from '@jupyterlab/rendermime-interfaces';
import { Widget } from '@lumino/widgets';
import * as d3 from 'd3';

import { parseData, wheelZoomFilter } from './utils';

/**
 * The MIME type rendered by this extension.
 */
export const FORCE_GRAPH_MIME_TYPE = 'application/vnd.mam.forcegraph+json';

const CLASS_NAME = 'jp-ForceGraph';

export interface IGraphNode extends d3.SimulationNodeDatum {
  id: string | number;
  label?: string;
  group?: string | number;
  size?: number;
  color?: string;
  [key: string]: unknown;
}

export interface IGraphLink extends d3.SimulationLinkDatum<IGraphNode> {
  value?: number;
  color?: string;
  [key: string]: unknown;
}

export interface IGraphOptions {
  height?: number;
  charge?: number;
  linkDistance?: number;
  nodeRadius?: number;
  showLabels?: boolean;
  directed?: boolean;
  zoom?: boolean;
}

export interface IGraphData {
  nodes: IGraphNode[];
  links: IGraphLink[];
  options?: IGraphOptions;
}

const DEFAULTS: Required<IGraphOptions> = {
  height: 500,
  charge: -120,
  linkDistance: 40,
  nodeRadius: 6,
  showLabels: false,
  directed: false,
  zoom: true
};

/**
 * A widget that renders a force-directed graph with d3.
 */
class ForceGraphRenderer extends Widget implements IRenderMime.IRenderer {
  constructor(options: IRenderMime.IRendererOptions) {
    super();
    this._mimeType = options.mimeType;
    this.addClass(CLASS_NAME);
  }

  renderModel(model: IRenderMime.IMimeModel): Promise<void> {
    this._teardown();
    try {
      this._draw(parseData<IGraphData>(model.data[this._mimeType]));
    } catch (err) {
      this.node.textContent = `Unable to render force graph: ${err}`;
    }
    return Promise.resolve();
  }

  protected onResize(): void {
    this._recenter();
  }

  protected onAfterShow(): void {
    this._recenter();
  }

  dispose(): void {
    this._teardown();
    super.dispose();
  }

  private _teardown(): void {
    this._simulation?.stop();
    this._simulation = null;
    this._resizeObserver?.disconnect();
    this._resizeObserver = null;
    this.node.textContent = '';
  }

  private _width(): number {
    return this.node.clientWidth || 800;
  }

  private _recenter(): void {
    if (!this._simulation || !this._svg) {
      return;
    }
    const width = this._width();
    if (width === this._lastWidth) {
      return;
    }
    this._lastWidth = width;
    this._svg.attr('viewBox', [0, 0, width, this._height].join(' '));
    this._simulation
      .force('center', d3.forceCenter(width / 2, this._height / 2))
      .alpha(0.3)
      .restart();
  }

  private _draw(data: IGraphData): void {
    if (!data || !Array.isArray(data.nodes) || !Array.isArray(data.links)) {
      throw new Error('expected an object with "nodes" and "links" arrays');
    }
    const opts = { ...DEFAULTS, ...(data.options ?? {}) };
    // Copy so the simulation does not mutate the model data.
    const nodes: IGraphNode[] = data.nodes.map(d => ({ ...d }));
    const links: IGraphLink[] = data.links.map(d => ({ ...d }));

    const width = this._width();
    const height = (this._height = opts.height);
    this._lastWidth = width;

    const color = d3.scaleOrdinal<string>(d3.schemeTableau10);
    const radius = (d: IGraphNode) => d.size ?? opts.nodeRadius;
    const linkWidth = (d: IGraphLink) => Math.sqrt(d.value ?? 1);

    const svg = d3
      .select(this.node)
      .append('svg')
      .attr('viewBox', [0, 0, width, height].join(' '))
      .attr('height', height)
      .attr('class', `${CLASS_NAME}-svg`);
    this._svg = svg;

    const uid = `fg-${Private.nextId++}`;
    if (opts.directed) {
      svg
        .append('defs')
        .append('marker')
        .attr('id', `${uid}-arrow`)
        .attr('viewBox', '0 -5 10 10')
        .attr('refX', 10)
        .attr('markerWidth', 6)
        .attr('markerHeight', 6)
        .attr('orient', 'auto')
        .append('path')
        .attr('class', `${CLASS_NAME}-arrow`)
        .attr('d', 'M0,-5L10,0L0,5');
    }

    const root = svg.append('g');

    const link = root
      .append('g')
      .attr('class', `${CLASS_NAME}-links`)
      .selectAll<SVGLineElement, IGraphLink>('line')
      .data(links)
      .join('line')
      .attr('stroke-width', linkWidth)
      .style('stroke', d => d.color ?? null)
      .attr('marker-end', opts.directed ? `url(#${uid}-arrow)` : null);

    const node = root
      .append('g')
      .attr('class', `${CLASS_NAME}-nodes`)
      .selectAll<SVGCircleElement, IGraphNode>('circle')
      .data(nodes)
      .join('circle')
      .attr('r', radius)
      .attr('fill', d => d.color ?? color(String(d.group ?? '')));

    node.append('title').text(d => d.label ?? String(d.id));

    const label = root
      .append('g')
      .attr('class', `${CLASS_NAME}-labels`)
      .selectAll<SVGTextElement, IGraphNode>('text')
      .data(opts.showLabels ? nodes : [])
      .join('text')
      .attr('dx', d => radius(d) + 2)
      .attr('dy', '0.35em')
      .text(d => d.label ?? String(d.id));

    const simulation = d3
      .forceSimulation<IGraphNode>(nodes)
      .force(
        'link',
        d3
          .forceLink<IGraphNode, IGraphLink>(links)
          .id(d => d.id as string)
          .distance(opts.linkDistance)
      )
      .force('charge', d3.forceManyBody().strength(opts.charge))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('x', d3.forceX(width / 2).strength(0.05))
      .force('y', d3.forceY(height / 2).strength(0.05));
    this._simulation = simulation;

    simulation.on('tick', () => {
      link
        .attr('x1', d => (d.source as IGraphNode).x!)
        .attr('y1', d => (d.source as IGraphNode).y!)
        .attr('x2', d => Private.endX(d, opts.directed, radius))
        .attr('y2', d => Private.endY(d, opts.directed, radius));
      node.attr('cx', d => d.x!).attr('cy', d => d.y!);
      label.attr('x', d => d.x!).attr('y', d => d.y!);
    });

    node.call(
      d3
        .drag<SVGCircleElement, IGraphNode>()
        .on('start', (event, d) => {
          if (!event.active) {
            simulation.alphaTarget(0.3).restart();
          }
          d.fx = d.x;
          d.fy = d.y;
        })
        .on('drag', (event, d) => {
          d.fx = event.x;
          d.fy = event.y;
        })
        .on('end', (event, d) => {
          if (!event.active) {
            simulation.alphaTarget(0);
          }
          d.fx = null;
          d.fy = null;
        })
    );

    if (opts.zoom) {
      svg.call(
        d3
          .zoom<SVGSVGElement, unknown>()
          .scaleExtent([0.1, 10])
          .filter(wheelZoomFilter)
          .on('zoom', event => root.attr('transform', event.transform))
      );
    }

    this._resizeObserver = new ResizeObserver(() => this._recenter());
    this._resizeObserver.observe(this.node);
  }

  private _mimeType: string;
  private _height = DEFAULTS.height;
  private _lastWidth = 0;
  private _svg: d3.Selection<SVGSVGElement, unknown, null, undefined> | null =
    null;
  private _simulation: d3.Simulation<IGraphNode, IGraphLink> | null = null;
  private _resizeObserver: ResizeObserver | null = null;
}

namespace Private {
  export let nextId = 0;

  /**
   * Shorten directed links so the arrowhead touches the target's edge.
   */
  function shorten(
    d: IGraphLink,
    directed: boolean,
    radius: (n: IGraphNode) => number
  ): [number, number] {
    const s = d.source as IGraphNode;
    const t = d.target as IGraphNode;
    if (!directed) {
      return [t.x!, t.y!];
    }
    const dx = t.x! - s.x!;
    const dy = t.y! - s.y!;
    const len = Math.hypot(dx, dy) || 1;
    const r = radius(t);
    return [t.x! - (dx / len) * r, t.y! - (dy / len) * r];
  }

  export function endX(
    d: IGraphLink,
    directed: boolean,
    radius: (n: IGraphNode) => number
  ): number {
    return shorten(d, directed, radius)[0];
  }

  export function endY(
    d: IGraphLink,
    directed: boolean,
    radius: (n: IGraphNode) => number
  ): number {
    return shorten(d, directed, radius)[1];
  }
}

export const forceGraphRendererFactory: IRenderMime.IRendererFactory = {
  safe: true,
  mimeTypes: [FORCE_GRAPH_MIME_TYPE],
  createRenderer: options => new ForceGraphRenderer(options)
};

export const forceGraphExtension: IRenderMime.IExtension = {
  id: 'mam-graph:plugin',
  description: 'Renders force-directed graphs with d3.',
  rendererFactory: forceGraphRendererFactory,
  rank: 100,
  dataType: 'json',
  fileTypes: [
    {
      name: 'forcegraph',
      displayName: 'Force Graph',
      mimeTypes: [FORCE_GRAPH_MIME_TYPE],
      extensions: ['.forcegraph.json', '.fgraph'],
      fileFormat: 'text'
    }
  ],
  documentWidgetFactoryOptions: {
    name: 'Force Graph Viewer',
    primaryFileType: 'forcegraph',
    fileTypes: ['forcegraph'],
    defaultFor: ['forcegraph']
  }
};