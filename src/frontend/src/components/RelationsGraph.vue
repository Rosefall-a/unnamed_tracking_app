<script setup lang="ts">
// A pannable, zoomable node graph — ported from the "Media Detail
// Redesign" mockup's vanilla-JS graph controller. Used two ways: a show's
// Seasons tab (chain nodes = seasons, connected by SEQUEL edges, no node
// is "current" — every click opens that season) and a season's own
// Relations tab (branch nodes = related entries hanging off one anchor,
// nothing chained). Both cases are just different combinations of the
// same chainNodes/branchNodes props, so one component covers both.
import { ref, computed, reactive } from "vue";

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
  side: "up" | "down";
}

const props = defineProps<{
  chainNodes: ChainNode[];
  branchNodes: BranchNode[];
}>();

const emit = defineEmits<{
  (e: "chain-click", id: string): void;
  (e: "branch-click", id: string): void;
}>();

const NODE_W = 172;
const NODE_H = 70;
const STEP_X = 230;
const MID_Y = 170;
const BRANCH_UP_Y = 30;
const BRANCH_DOWN_Y = 310;

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

const branchCounts = computed(() => {
  const counts: { up: number; down: number } = { up: 0, down: 0 };
  return props.branchNodes.map((n) => {
    const anchor = chainPositions.value[n.anchorIndex];
    const cy =
      n.side === "up" ? BRANCH_UP_Y + NODE_H / 2 : BRANCH_DOWN_Y + NODE_H / 2;
    const branchIndex = counts[n.side]++;
    const cx = (anchor?.cx ?? 0) + 90 + branchIndex * 210;
    return { node: n, cx, cy, anchor };
  });
});

interface Edge {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  label: string;
  length: number;
  angle: number;
}

const edges = computed<Edge[]>(() => {
  const list: Edge[] = [];
  const chain = chainPositions.value;
  for (let i = 1; i < chain.length; i++) {
    const prev = chain[i - 1];
    const cur = chain[i];
    const a = edgePoint(prev.cx, prev.cy, NODE_W, NODE_H, cur.cx - prev.cx, 0);
    const b = edgePoint(cur.cx, cur.cy, NODE_W, NODE_H, prev.cx - cur.cx, 0);
    const dx = b.x - a.x;
    const dy = b.y - a.y;
    list.push({
      x1: a.x,
      y1: a.y,
      x2: b.x,
      y2: b.y,
      label: "SEQUEL",
      length: Math.sqrt(dx * dx + dy * dy),
      angle: (Math.atan2(dy, dx) * 180) / Math.PI,
    });
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
    const dx = b.x - a.x;
    const dy = b.y - a.y;
    list.push({
      x1: a.x,
      y1: a.y,
      x2: b.x,
      y2: b.y,
      label: node.label,
      length: Math.sqrt(dx * dx + dy * dy),
      angle: (Math.atan2(dy, dx) * 180) / Math.PI,
    });
  });
  return list;
});

// ---- pan / zoom / drag ----
const pan = reactive({ x: 40, y: 0 });
const zoom = ref(1);
const dragging = ref(false);
const expanded = ref(false);
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
function fit() {
  pan.x = 40;
  pan.y = 0;
  zoom.value = 1;
}
function toggleExpand() {
  expanded.value = !expanded.value;
}

defineExpose({ fit });
</script>

<template>
  <div
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
      <div
        v-for="edge in edges"
        :key="`${edge.x1}-${edge.y1}-${edge.x2}-${edge.y2}`"
        class="graph-edge-line"
        :style="{
          left: edge.x1 + 'px',
          top: edge.y1 + 'px',
          width: edge.length + 'px',
          transform: `rotate(${edge.angle}deg)`,
        }"
      ></div>
      <div
        v-for="edge in edges"
        :key="`label-${edge.x1}-${edge.y1}-${edge.x2}-${edge.y2}`"
        class="graph-edge-label"
        :style="{
          left: (edge.x1 + edge.x2) / 2 - 30 + 'px',
          top: (edge.y1 + edge.y2) / 2 - 9 + 'px',
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
  height: 380px;
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
  width: 172px;
  min-height: 70px;
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
.graph-edge-line {
  position: absolute;
  height: 0;
  border-top: 1px dashed #2b2b2b;
  transform-origin: 0 0;
  pointer-events: none;
}
.graph-edge-label {
  position: absolute;
  font-size: 0.6rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-weight: 700;
  color: #666;
  background: #1a1a1a;
  border: 1px solid #202020;
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
