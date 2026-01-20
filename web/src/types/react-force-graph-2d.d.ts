declare module 'react-force-graph-2d' {
  import { Component, RefObject, ForwardRefExoticComponent, RefAttributes } from 'react';

  export interface NodeObject {
    id?: string | number;
    x?: number;
    y?: number;
    vx?: number;
    vy?: number;
    fx?: number;
    fy?: number;
    [key: string]: any;
  }

  export interface LinkObject {
    source?: string | number | NodeObject;
    target?: string | number | NodeObject;
    [key: string]: any;
  }

  export interface GraphData {
    nodes: NodeObject[];
    links: LinkObject[];
  }

  export interface ForceGraphMethods {
    d3Force: (forceName: string) => any;
    d3ReheatSimulation: () => void;
    emitParticle: (link: LinkObject) => void;
    pauseAnimation: () => void;
    resumeAnimation: () => void;
    centerAt: (x?: number, y?: number, ms?: number) => void;
    zoom: (k?: number, ms?: number) => void;
    zoomToFit: (ms?: number, px?: number, nodeFilter?: (node: NodeObject) => boolean) => void;
    getGraphBbox: (nodeFilter?: (node: NodeObject) => boolean) => { x: [number, number]; y: [number, number] };
    screen2GraphCoords: (x: number, y: number) => { x: number; y: number };
    graph2ScreenCoords: (x: number, y: number) => { x: number; y: number };
  }

  export interface ForceGraph2DProps {
    ref?: any;
    graphData?: GraphData;
    width?: number;
    height?: number;
    backgroundColor?: string;
    nodeRelSize?: number;
    nodeId?: string;
    nodeLabel?: string | ((node: NodeObject) => string);
    nodeVal?: number | string | ((node: NodeObject) => number);
    nodeVisibility?: boolean | string | ((node: NodeObject) => boolean);
    nodeColor?: string | ((node: NodeObject) => string);
    nodeAutoColorBy?: string | ((node: NodeObject) => string | null);
    nodeCanvasObject?: (node: NodeObject, ctx: CanvasRenderingContext2D, globalScale: number) => void;
    nodeCanvasObjectMode?: string | ((node: NodeObject) => string);
    nodePointerAreaPaint?: (node: NodeObject, color: string, ctx: CanvasRenderingContext2D, globalScale: number) => void;
    linkSource?: string;
    linkTarget?: string;
    linkLabel?: string | ((link: LinkObject) => string);
    linkVisibility?: boolean | string | ((link: LinkObject) => boolean);
    linkColor?: string | ((link: LinkObject) => string);
    linkAutoColorBy?: string | ((link: LinkObject) => string | null);
    linkLineDash?: number[] | string | ((link: LinkObject) => number[] | null);
    linkWidth?: number | string | ((link: LinkObject) => number);
    linkCurvature?: number | string | ((link: LinkObject) => number);
    linkCanvasObject?: (link: LinkObject, ctx: CanvasRenderingContext2D, globalScale: number) => void;
    linkCanvasObjectMode?: string | ((link: LinkObject) => string);
    linkDirectionalArrowLength?: number | string | ((link: LinkObject) => number);
    linkDirectionalArrowColor?: string | ((link: LinkObject) => string);
    linkDirectionalArrowRelPos?: number | string | ((link: LinkObject) => number);
    linkDirectionalParticles?: number | string | ((link: LinkObject) => number);
    linkDirectionalParticleSpeed?: number | string | ((link: LinkObject) => number);
    linkDirectionalParticleWidth?: number | string | ((link: LinkObject) => number);
    linkDirectionalParticleColor?: string | ((link: LinkObject) => string);
    linkPointerAreaPaint?: (link: LinkObject, color: string, ctx: CanvasRenderingContext2D, globalScale: number) => void;
    dagMode?: 'td' | 'bu' | 'lr' | 'rl' | 'radialout' | 'radialin' | null;
    dagLevelDistance?: number | null;
    dagNodeFilter?: (node: NodeObject) => boolean;
    onDagError?: (loopNodeIds: (string | number)[]) => void;
    d3AlphaMin?: number;
    d3AlphaDecay?: number;
    d3VelocityDecay?: number;
    warmupTicks?: number;
    cooldownTicks?: number;
    cooldownTime?: number;
    onEngineTick?: () => void;
    onEngineStop?: () => void;
    onNodeClick?: (node: NodeObject, event: MouseEvent) => void;
    onNodeRightClick?: (node: NodeObject, event: MouseEvent) => void;
    onNodeHover?: (node: NodeObject | null, previousNode: NodeObject | null) => void;
    onNodeDrag?: (node: NodeObject, translate: { x: number; y: number }) => void;
    onNodeDragEnd?: (node: NodeObject, translate: { x: number; y: number }) => void;
    onLinkClick?: (link: LinkObject, event: MouseEvent) => void;
    onLinkRightClick?: (link: LinkObject, event: MouseEvent) => void;
    onLinkHover?: (link: LinkObject | null, previousLink: LinkObject | null) => void;
    onBackgroundClick?: (event: MouseEvent) => void;
    onBackgroundRightClick?: (event: MouseEvent) => void;
    onZoom?: (transform: { k: number; x: number; y: number }) => void;
    onZoomEnd?: (transform: { k: number; x: number; y: number }) => void;
    enableNodeDrag?: boolean;
    enableZoomInteraction?: boolean;
    enablePanInteraction?: boolean;
    enablePointerInteraction?: boolean;
    autoPauseRedraw?: boolean;
    minZoom?: number;
    maxZoom?: number;
  }

  export default class ForceGraph2D extends Component<ForceGraph2DProps> {
    d3Force: ForceGraphMethods['d3Force'];
    d3ReheatSimulation: ForceGraphMethods['d3ReheatSimulation'];
    emitParticle: ForceGraphMethods['emitParticle'];
    pauseAnimation: ForceGraphMethods['pauseAnimation'];
    resumeAnimation: ForceGraphMethods['resumeAnimation'];
    centerAt: ForceGraphMethods['centerAt'];
    zoom: ForceGraphMethods['zoom'];
    zoomToFit: ForceGraphMethods['zoomToFit'];
    getGraphBbox: ForceGraphMethods['getGraphBbox'];
    screen2GraphCoords: ForceGraphMethods['screen2GraphCoords'];
    graph2ScreenCoords: ForceGraphMethods['graph2ScreenCoords'];
  }
}
