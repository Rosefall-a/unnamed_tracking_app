<script setup lang="ts">
// A pannable, zoomable node graph — ported from the "Media Detail
// Redesign" mockup's vanilla-JS graph controller. Used two ways: a show's
// Seasons tab (chain nodes = seasons, connected by SEQUEL edges, no node
// is "current" — every click opens that season) and a season's own
// Relations tab (branch nodes = related entries hanging off one anchor,
// nothing chained). Both cases are just different combinations of the
// same chainNodes/branchNodes props, so one component covers both.
import { ref, computed, reactive, watch } from "vue";

export interface ChainNode {
  id: string;
  title: string;
  type: string;
  sub: string;
  current?: boolean;
}

export interface BranchNode {
  id: string;
  title: string;
  type: string;
  sub: string;
  label: string;
  anchorIndex: number;
  // When set, this node is positioned relative to another BranchNode's
  // id instead of a chain position — e.g. two related titles that are
  // themselves a sequel pair, not each independently tied to the show.
  parentBranchId?: string;
}

const props = defineProps<{
  chainNodes: ChainNode[];
  branchNodes: BranchNode[];
}>();

const emit = defineEmits<{
  (e: "chain-click", id: string): void;
  (e: "branch-click", id: string): void;
}>();

const NODE_W = 200;
const NODE_H = 74;
const STEP_X = 270;
const MID_Y = 190;
const BRANCH_SPACING = NODE_W + 70;
const ROW_H = 130;

// Roughly groups a top-level branch's whole subtree by format so the
// graph reads top-to-bottom as specials/shorts, then the main
// series-like entries, then source manga/novels — rather than whatever
// order the source API happened to list relations in.
function branchBand(type: string): number {
  const t = type.toLowerCase();
  if (t.includes("manga") || t.includes("novel") || t.includes("doujin") || t.includes("one shot")) {
    return 2; // bottom: source material
  }
  if (t === "special" || t === "ova" || t === "ona" || t === "music") {
    return 0; // top: shorts/specials
  }
  return 1; // middle: tv, tv short, movie
}

function edgePoint(
  cx: number,
  cy: number,
  w: number,
  h: number,
  dx: number,
  dy: number,
) {
  if (dx === 0 && dy === 0) return { x: cx, y: cy };
  const sx = dx === 0 ? Infinity : w / 2 / Math.abs(dx);
  const sy = dy === 0 ? Infinity : h / 2 / Math.abs(dy);
  const scale = Math.min(sx, sy);
  return { x: cx + dx * scale, y: cy + dy * scale };
}

const chainPositions = computed(() =>
  props.chainNodes.map((n, i) => ({
    node: n,
    cx: i * STEP_X + NODE_W / 2,
    cy: MID_Y + NODE_H / 2,
  })),
);

// A real left-to-right tree per chain anchor: every direct branch gets
// its own vertical slot (a leaf takes the next open one, a parent with
// children centers over them), and a branch's nested children
// (parentBranchId set — e.g. two related titles that are themselves a
// sequel pair) sit one column further right at their parent's row.
//
// Slots split into an upper and lower stack rather than one row
// centered on the anchor's own Y — TV/movie entries (the "main
// series") fill from the center outward on both sides, specials push
// out beyond them on top, manga/novels beyond them on the bottom — and
// critically, neither stack ever uses the row the chain itself sits
// on (both start one full row away from center). A chain can run deep
// (a long-running show easily has 5+ entries), and a branch sharing
// the chain's own Y would land exactly on top of the next entry
// whenever its horizontal depth happens to reach that far — starting
// one row off guarantees real separation from the chain regardless of
// how wide a branch subtree gets.
const branchCounts = computed(() => {
  type Positioned = { node: BranchNode; cx: number; cy: number; anchor: { cx: number; cy: number } | undefined };
  const childrenOf = new Map<string, BranchNode[]>();
  for (const n of props.branchNodes) {
    if (!n.parentBranchId) continue;
    const list = childrenOf.get(n.parentBranchId);
    if (list) list.push(n);
    else childrenOf.set(n.parentBranchId, [n]);
  }
  const rootsByAnchor = new Map<number, BranchNode[]>();
  for (const n of props.branchNodes) {
    if (n.parentBranchId) continue;
    const list = rootsByAnchor.get(n.anchorIndex);
    if (list) list.push(n);
    else rootsByAnchor.set(n.anchorIndex, [n]);
  }

  const result: Positioned[] = [];
  const posById = new Map<string, { cx: number; cy: number }>();

  for (const [anchorIndex, roots] of rootsByAnchor) {
    const anchor = chainPositions.value[anchorIndex];
    const byBand = [0, 1, 2].map((band) => roots.filter((n) => branchBand(n.type) === band));
    const [specials, mainSeries, manga] = byBand;
    const mainUpper: BranchNode[] = [];
    const mainLower: BranchNode[] = [];
    mainSeries.forEach((n, i) => (i % 2 === 0 ? mainUpper : mainLower).push(n));
    // main series closest to center on both sides, specials pushed
    // further out above, manga/novels pushed further out below
    const upperRoots = [...mainUpper, ...specials];
    const lowerRoots = [...mainLower, ...manga];

    const slotOf = new Map<string, number>();
    const depthOf = new Map<string, number>();

    function assignSlot(node: BranchNode, depth: number, dir: 1 | -1, counter: { n: number }): number {
      depthOf.set(node.id, depth);
      const kids = childrenOf.get(node.id) ?? [];
      if (!kids.length) {
        counter.n += 1;
        const slot = counter.n * dir;
        slotOf.set(node.id, slot);
        return slot;
      }
      const kidSlots = kids.map((k) => assignSlot(k, depth + 1, dir, counter));
      const avg = kidSlots.reduce((a, b) => a + b, 0) / kidSlots.length;
      slotOf.set(node.id, avg);
      return avg;
    }
    const upCounter = { n: 0 };
    for (const root of upperRoots) assignSlot(root, 1, -1, upCounter);
    const downCounter = { n: 0 };
    for (const root of lowerRoots) assignSlot(root, 1, 1, downCounter);

    function place(node: BranchNode) {
      const depth = depthOf.get(node.id) ?? 1;
      const slot = slotOf.get(node.id) ?? 1;
      const cx = (anchor?.cx ?? 0) + depth * BRANCH_SPACING;
      const cy = (anchor?.cy ?? 0) + slot * ROW_H;
      const parentPos = node.parentBranchId ? posById.get(node.parentBranchId) : undefined;
      result.push({ node, cx, cy, anchor: parentPos ?? anchor });
      posById.set(node.id, { cx, cy });
      for (const kid of childrenOf.get(node.id) ?? []) place(kid);
    }
    for (const root of roots) place(root);
  }
  return result;
});

interface Edge {
  path: string;
  labelX: number;
  labelY: number;
  label: string;
}

// A smooth S-curve (cubic bezier) between two node edges, control points
// pulled horizontally toward each other — reads as a real connection
// between two specific nodes even when they're several rows apart
// vertically, unlike a straight line crossing through unrelated nodes.
function bezier(x1: number, y1: number, x2: number, y2: number) {
  const pull = Math.max(Math.abs(x2 - x1) * 0.5, 40);
  const c1x = x1 + pull;
  const c2x = x2 - pull;
  const path = `M ${x1} ${y1} C ${c1x} ${y1}, ${c2x} ${y2}, ${x2} ${y2}`;
  // point at t=0.5 on the cubic bezier, for the label
  const labelX = 0.125 * x1 + 0.375 * c1x + 0.375 * c2x + 0.125 * x2;
  const labelY = 0.125 * y1 + 0.375 * y1 + 0.375 * y2 + 0.125 * y2;
  return { path, labelX, labelY };
}

const edges = computed<Edge[]>(() => {
  const list: Edge[] = [];
  const chain = chainPositions.value;
  for (let i = 1; i < chain.length; i++) {
    const prev = chain[i - 1];
    const cur = chain[i];
    const a = edgePoint(prev.cx, prev.cy, NODE_W, NODE_H, cur.cx - prev.cx, 0);
    const b = edgePoint(cur.cx, cur.cy, NODE_W, NODE_H, prev.cx - cur.cx, 0);
    const { path, labelX, labelY } = bezier(a.x, a.y, b.x, b.y);
    list.push({ path, labelX, labelY, label: "SEQUEL" });
  }
  branchCounts.value.forEach(({ node, cx, cy, anchor }) => {
    if (!anchor) return;
    const a = edgePoint(
      anchor.cx,
      anchor.cy,
      NODE_W,
      NODE_H,
      cx - anchor.cx,
      cy - anchor.cy,
    );
    const b = edgePoint(cx, cy, NODE_W, NODE_H, anchor.cx - cx, anchor.cy - cy);
    const { path, labelX, labelY } = bezier(a.x, a.y, b.x, b.y);
    list.push({ path, labelX, labelY, label: node.label });
  });
  return list;
});

// ---- pan / zoom / drag ----
const pan = reactive({ x: 40, y: 0 });
const zoom = ref(1);
const dragging = ref(false);
const expanded = ref(false);
const canvasEl = ref<HTMLElement | null>(null);
let dragStart: { x: number; y: number } | null = null;

const worldStyle = computed(() => ({
  transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom.value})`,
}));

function onMouseDown(e: MouseEvent) {
  const target = e.target as HTMLElement;
  if (target.closest(".graph-node") || target.closest(".graph-toolbar")) return;
  e.preventDefault();
  dragging.value = true;
  dragStart = { x: e.clientX - pan.x, y: e.clientY - pan.y };
}
function onMouseMove(e: MouseEvent) {
  if (!dragging.value || !dragStart) return;
  pan.x = e.clientX - dragStart.x;
  pan.y = e.clientY - dragStart.y;
}
function onMouseUp() {
  dragging.value = false;
}
function onWheel(e: WheelEvent) {
  e.preventDefault();
  zoomBy(e.deltaY < 0 ? 0.1 : -0.1);
}
function zoomBy(delta: number) {
  zoom.value = Math.max(0.5, Math.min(1.8, zoom.value + delta));
}
// Fits the whole graph (chain + branches) into view instead of just
// resetting to a fixed pan/zoom — a wide multi-season chain otherwise
// spills past the canvas edge with no indication there's more to see.
function fit() {
  const positions = [
    ...chainPositions.value.map((p) => ({ cx: p.cx, cy: p.cy })),
    ...branchCounts.value.map((p) => ({ cx: p.cx, cy: p.cy })),
  ];
  if (!positions.length || !canvasEl.value) {
    pan.x = 40;
    pan.y = 0;
    zoom.value = 1;
    return;
  }
  const minX = Math.min(...positions.map((p) => p.cx)) - NODE_W / 2;
  const maxX = Math.max(...positions.map((p) => p.cx)) + NODE_W / 2;
  const minY = Math.min(...positions.map((p) => p.cy)) - NODE_H / 2;
  const maxY = Math.max(...positions.map((p) => p.cy)) + NODE_H / 2;
  const contentW = Math.max(maxX - minX, 1);
  const contentH = Math.max(maxY - minY, 1);
  const padding = 32;
  const canvasW = canvasEl.value.clientWidth;
  const canvasH = canvasEl.value.clientHeight;
  const scale = Math.max(
    0.4,
    Math.min(1.4, (canvasW - padding * 2) / contentW, (canvasH - padding * 2) / contentH),
  );
  zoom.value = scale;
  pan.x = (canvasW - contentW * scale) / 2 - minX * scale;
  pan.y = (canvasH - contentH * scale) / 2 - minY * scale;
}
function toggleExpand() {
  expanded.value = !expanded.value;
  requestAnimationFrame(fit);
}

watch(
  () => [props.chainNodes, props.branchNodes],
  () => requestAnimationFrame(fit),
  { immediate: true },
);

defineExpose({ fit });
</script>

<template>
  <div
    ref="canvasEl"
    class="graph-canvas"
    :class="{ dragging, expanded }"
    @mousedown="onMouseDown"
    @mousemove="onMouseMove"
    @mouseup="onMouseUp"
    @mouseleave="onMouseUp"
    @wheel="onWheel"
  >
    <div class="graph-hint">drag to pan · scroll or +/− to zoom</div>
    <div class="graph-world" :style="worldStyle">
      <svg class="graph-edges">
        <path
          v-for="(edge, i) in edges"
          :key="`path-${i}`"
          :d="edge.path"
          class="graph-edge-path"
        />
      </svg>
      <div
        v-for="(edge, i) in edges"
        :key="`label-${i}`"
        class="graph-edge-label"
        :style="{
          left: edge.labelX - 34 + 'px',
          top: edge.labelY - 9 + 'px',
        }"
      >
        {{ edge.label }}
      </div>
      <div
        v-for="{ node, cx, cy } in chainPositions"
        :key="node.id"
        class="graph-node"
        :class="{ current: node.current }"
        :style="{ left: cx - NODE_W / 2 + 'px', top: cy - NODE_H / 2 + 'px' }"
        @click="emit('chain-click', node.id)"
      >
        <div class="graph-node-title">{{ node.title }}</div>
        <div class="graph-node-meta">
          <span class="graph-node-type">{{ node.type }}</span>
          <span class="graph-node-sub">{{ node.sub }}</span>
        </div>
      </div>
      <div
        v-for="{ node, cx, cy } in branchCounts"
        :key="node.id"
        class="graph-node"
        :style="{ left: cx - NODE_W / 2 + 'px', top: cy - NODE_H / 2 + 'px' }"
        @click="emit('branch-click', node.id)"
      >
        <div class="graph-node-title">{{ node.title }}</div>
        <div class="graph-node-meta">
          <span class="graph-node-type">{{ node.type }}</span>
          <span class="graph-node-sub">{{ node.sub }}</span>
        </div>
      </div>
    </div>
    <div class="graph-toolbar">
      <button type="button" title="Zoom in" @click="zoomBy(0.15)">+</button>
      <button type="button" title="Zoom out" @click="zoomBy(-0.15)">−</button>
      <button type="button" title="Fit" @click="fit">⤢</button>
      <button type="button" title="Expand" @click="toggleExpand">⛶</button>
    </div>
  </div>
</template>

<style scoped>
.graph-canvas {
  position: relative;
  height: 440px;
  background:
    radial-gradient(circle, rgba(255, 255, 255, 0.09) 1px, transparent 1.2px) 0
      0 / 22px 22px,
    #1a1a1a;
  border: 1px solid #202020;
  border-radius: 12px;
  overflow: hidden;
  cursor: grab;
  transition: height 0.2s ease;
  user-select: none;
  -webkit-user-select: none;
}
.graph-canvas.dragging {
  cursor: grabbing;
}
.graph-canvas.expanded {
  height: 620px;
}
.graph-world {
  position: absolute;
  top: 0;
  left: 0;
  transform-origin: 0 0;
  will-change: transform;
}
.graph-node {
  position: absolute;
  width: 200px;
  min-height: 74px;
  background: #222222;
  border: 1px solid #2b2b2b;
  border-radius: 8px;
  padding: 10px 12px;
  cursor: pointer;
  user-select: none;
}
.graph-node.current {
  border-color: #d68a34;
  background: rgba(214, 138, 52, 0.16);
  box-shadow: 0 0 0 1px rgba(214, 138, 52, 0.4);
}
.graph-node-title {
  font-size: 0.84rem;
  font-weight: 700;
  margin-bottom: 6px;
  line-height: 1.25;
  color: #f2f2f2;
}
.graph-node-meta {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  align-items: center;
}
.graph-node-type {
  font-size: 0.6rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #666;
  background: #0d0d0d;
  border: 1px solid #2b2b2b;
  padding: 1px 6px;
  border-radius: 4px;
}
.graph-node-sub {
  font-size: 0.68rem;
  color: #666;
}
.graph-node.current .graph-node-type {
  color: #d68a34;
  border-color: rgba(214, 138, 52, 0.4);
}
.graph-edges {
  position: absolute;
  top: 0;
  left: 0;
  width: 1px;
  height: 1px;
  overflow: visible;
  pointer-events: none;
}
.graph-edge-path {
  fill: none;
  stroke: rgba(214, 138, 52, 0.45);
  stroke-width: 1.5;
  stroke-dasharray: 4 4;
}
.graph-edge-label {
  position: absolute;
  font-size: 0.62rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-weight: 700;
  color: #d68a34;
  background: #1a1a1a;
  border: 1px solid rgba(214, 138, 52, 0.35);
  padding: 2px 7px;
  border-radius: 5px;
  white-space: nowrap;
  pointer-events: none;
}
.graph-toolbar {
  position: absolute;
  bottom: 10px;
  left: 10px;
  z-index: 5;
  display: flex;
  gap: 4px;
}
.graph-toolbar button {
  width: 28px;
  height: 28px;
  background: rgba(20, 20, 20, 0.85);
  border: 1px solid #2b2b2b;
  border-radius: 6px;
  color: #9c9c9c;
  cursor: pointer;
  font-size: 0.85rem;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: inherit;
}
.graph-toolbar button:hover {
  color: #d68a34;
  border-color: rgba(214, 138, 52, 0.4);
}
.graph-hint {
  position: absolute;
  top: 10px;
  right: 12px;
  font-size: 0.68rem;
  color: #666;
  background: rgba(20, 20, 20, 0.7);
  padding: 3px 9px;
  border-radius: 999px;
  z-index: 5;
}
</style>
