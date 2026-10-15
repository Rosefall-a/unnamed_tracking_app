<script setup lang="ts">
// Lays a page's widgets out on the 12 column grid. In edit mode you grab a widget
// anywhere to move it: it follows the pointer, a dashed outline shows where it
// will land, the other widgets slide out of the way, and the page scrolls along
// when you reach its top or bottom edge. Pull its corner or either edge to resize
// it. A click without a drag opens its settings, and the arrow keys move the focused
// widget (with Shift they resize it). On a narrow screen the page stacks into one
// column.
import {
  computed,
  nextTick,
  onBeforeUnmount,
  onUpdated,
  ref,
  watch,
} from "vue";
import WidgetHost from "./WidgetHost.vue";
import { GAP_PX, GRID_COLUMNS, ROW_PX, moveWidget } from "../../home/layout";
import type { HomePage, WidgetInstance } from "../../home/layout";
import { definitionOf } from "../../home/registry";

const props = defineProps<{ page: HomePage; editing: boolean }>();

const emit = defineEmits<{
  "update:widgets": [widgets: WidgetInstance[]];
  settings: [id: string];
  remove: [id: string];
}>();

const gridEl = ref<HTMLElement | null>(null);
const gap = computed(() => GAP_PX[props.page.options.gap]);

// reading order, which is also the order the page stacks in on a phone
const ordered = computed(() =>
  [...props.page.widgets].sort((a, b) => a.y - b.y || a.x - b.x),
);

// ---- sliding into place ----
// Every widget that ends up somewhere else after a change slides there instead of
// jumping: where each one was is noted just before the page updates, and each is
// moved from there to where it is now.
const cellEls = new Map<string, HTMLElement>();
function setCell(id: string, el: unknown) {
  if (el instanceof HTMLElement) cellEls.set(id, el);
  else cellEls.delete(id);
}
const reduceMotion =
  typeof window !== "undefined" &&
  window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
let before = new Map<string, DOMRect>();
watch(
  () => props.page.widgets,
  () => {
    before = new Map();
    cellEls.forEach((el, id) => before.set(id, el.getBoundingClientRect()));
  },
  { flush: "pre" },
);
onUpdated(() => {
  if (!reduceMotion && before.size) {
    cellEls.forEach((el, id) => {
      const was = before.get(id);
      if (!was || id === active.value) return;
      const now = el.getBoundingClientRect();
      const dx = was.left - now.left;
      const dy = was.top - now.top;
      if (Math.abs(dx) < 2 && Math.abs(dy) < 2) return;
      el.animate(
        [{ transform: `translate(${dx}px, ${dy}px)` }, { transform: "none" }],
        { duration: 220, easing: "cubic-bezier(0.2, 0.8, 0.2, 1)" },
      );
    });
  }
  before = new Map();
});

// ---- dragging and resizing ----
type Mode = "move" | "resize" | "resize-w" | "resize-h";
interface Gesture {
  id: string;
  mode: Mode;
  startX: number;
  startY: number;
  startScroll: number;
  from: WidgetInstance;
  strideX: number;
  strideY: number;
  // has the pointer travelled far enough to count as a drag rather than a click
  started: boolean;
}
let gesture: Gesture | null = null;
// The page as it was when the grab began. Every step of a drag is worked out from
// this, not from the last step, so a widget moved out of the way comes back when
// you move off it, and nothing drifts.
let startWidgets: WidgetInstance[] = [];
// A move that would push other widgets aside waits until the pointer settles for a
// moment, so sweeping across the page does not shuffle everything you pass over.
// Until then the outline shows where it would land.
const preview = ref<{ x: number; y: number; w: number; h: number } | null>(
  null,
);
let dwell: number | undefined;
const DWELL_MS = 200;
const active = ref<string | null>(null);
const dragging = ref(false);
// what kind of gesture is under way, for the template (the gesture itself is not reactive)
const gestureMode = ref<Mode | null>(null);
// where the pointer is, in pixels, from where the grab started
const pull = ref({ x: 0, y: 0 });
let fromAt = { x: 0, y: 0 };
let pointer = { x: 0, y: 0 };
let frame = 0;
// set while a resize is being held at the widget's smallest size, to say so
const limited = ref<{ id: string; note: string } | null>(null);

const activeWidget = computed(
  () => props.page.widgets.find((w) => w.id === active.value) ?? null,
);

function begin(e: PointerEvent, w: WidgetInstance, mode: Mode) {
  const grid = gridEl.value;
  if (!grid || !props.editing || e.button !== 0) return;
  const width = grid.getBoundingClientRect().width;
  gesture = {
    id: w.id,
    mode,
    startX: e.clientX,
    startY: e.clientY,
    startScroll: window.scrollY,
    from: { ...w },
    strideX: (width + gap.value) / GRID_COLUMNS,
    strideY: ROW_PX + gap.value,
    started: false,
  };
  fromAt = { x: w.x, y: w.y };
  startWidgets = props.page.widgets.map((item) => ({ ...item }));
  pointer = { x: e.clientX, y: e.clientY };
  active.value = w.id;
  gestureMode.value = mode;
  pull.value = { x: 0, y: 0 };
  (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
}

function onMove(e: PointerEvent) {
  if (!gesture) return;
  pointer = { x: e.clientX, y: e.clientY };
  if (!gesture.started) {
    if (Math.hypot(e.clientX - gesture.startX, e.clientY - gesture.startY) < 5)
      return;
    gesture.started = true;
    dragging.value = true;
    document.body.style.userSelect = "none";
    frame = requestAnimationFrame(scrollAlong);
  }
  apply();
}

// near the top or bottom of the window the page scrolls, faster the closer to the
// edge, even while the pointer is held still
function scrollAlong() {
  if (!gesture) return;
  const edge = 90;
  let speed = 0;
  if (pointer.y < edge) speed = -Math.ceil(((edge - pointer.y) / edge) * 18);
  else if (pointer.y > window.innerHeight - edge)
    speed = Math.ceil(((pointer.y - (window.innerHeight - edge)) / edge) * 18);
  if (speed) {
    const was = window.scrollY;
    window.scrollBy(0, speed);
    if (window.scrollY !== was) apply();
  }
  frame = requestAnimationFrame(scrollAlong);
}

function apply() {
  if (!gesture) return;
  const px = pointer.x - gesture.startX;
  const py =
    pointer.y - gesture.startY + (window.scrollY - gesture.startScroll);
  const dx = Math.round(px / gesture.strideX);
  const dy = Math.round(py / gesture.strideY);
  const f = gesture.from;
  const def = definitionOf(f.type);
  const minW = def?.size.minW ?? 1;
  const minH = def?.size.minH ?? 1;
  if (gesture.mode === "move") {
    pull.value = { x: px, y: py };
    place(gesture.id, { x: f.x + dx, y: f.y + dy, w: f.w, h: f.h });
    return;
  }
  const askedW = gesture.mode === "resize-h" ? f.w : f.w + dx;
  const askedH = gesture.mode === "resize-w" ? f.h : f.h + dy;
  const w = Math.max(minW, Math.min(GRID_COLUMNS - f.x, askedW));
  const h = Math.max(minH, askedH);
  limited.value =
    askedW < minW || askedH < minH
      ? {
          id: f.id,
          note:
            askedW < minW && askedH < minH
              ? `Smallest size is ${minW} wide and ${minH} tall`
              : askedW < minW
                ? `Smallest width is ${minW} columns`
                : `Smallest height is ${minH} rows`,
        }
      : null;
  commit(gesture.id, { x: f.x, y: f.y, w, h }, startWidgets);
}

// letting go of a widget without having dragged it is a click: open its settings
function finish(e: PointerEvent) {
  if (
    gesture &&
    !gesture.started &&
    gesture.mode === "move" &&
    e.type === "pointerup"
  )
    emit("settings", gesture.id);
  end();
}

// would this move leave every other widget where it is on screen right now?
function displaces(
  id: string,
  rect: { x: number; y: number; w: number; h: number },
): boolean {
  const next = moveWidget(startWidgets, id, rect);
  const now = props.page.widgets;
  return next.some((n) => {
    if (n.id === id) return false;
    const o = now.find((w) => w.id === n.id);
    return !o || o.x !== n.x || o.y !== n.y;
  });
}

function place(
  id: string,
  rect: { x: number; y: number; w: number; h: number },
) {
  window.clearTimeout(dwell);
  if (!displaces(id, rect)) {
    preview.value = null;
    commit(id, rect, startWidgets);
    return;
  }
  preview.value = rect;
  dwell = window.setTimeout(() => {
    preview.value = null;
    commit(id, rect, startWidgets);
  }, DWELL_MS);
}

function end() {
  window.clearTimeout(dwell);
  // letting go commits wherever the outline was
  if (gesture && preview.value) commit(gesture.id, preview.value, startWidgets);
  preview.value = null;
  cancelAnimationFrame(frame);
  document.body.style.userSelect = "";
  // the widget glides from where the pointer left it into its place
  const w = activeWidget.value;
  const el = w ? cellEls.get(w.id) : null;
  const offset = w && gesture?.mode === "move" ? follow(w).transform : null;
  gesture = null;
  active.value = null;
  gestureMode.value = null;
  dragging.value = false;
  limited.value = null;
  pull.value = { x: 0, y: 0 };
  if (el && offset && !reduceMotion)
    void nextTick(() =>
      el.animate([{ transform: offset }, { transform: "none" }], {
        duration: 180,
        easing: "cubic-bezier(0.2, 0.8, 0.2, 1)",
      }),
    );
}
onBeforeUnmount(() => {
  cancelAnimationFrame(frame);
  document.body.style.userSelect = "";
});

function commit(
  id: string,
  rect: { x: number; y: number; w: number; h: number },
  from: WidgetInstance[] = props.page.widgets,
) {
  const next = moveWidget(from, id, rect);
  // nothing to do while everything is still where it was
  const now = props.page.widgets;
  if (
    next.length === now.length &&
    next.every((n, i) => {
      const o = now[i];
      return (
        o.id === n.id &&
        o.x === n.x &&
        o.y === n.y &&
        o.w === n.w &&
        o.h === n.h
      );
    })
  )
    return;
  emit("update:widgets", next);
}

// a widget being moved follows the pointer exactly, not the snapped cell
function follow(w: WidgetInstance): Record<string, string> {
  if (active.value !== w.id || !gesture || gesture.mode !== "move") return {};
  const x = pull.value.x - (w.x - fromAt.x) * gesture.strideX;
  const y = pull.value.y - (w.y - fromAt.y) * gesture.strideY;
  return { transform: `translate(${x}px, ${y}px)` };
}

function key(e: KeyboardEvent, w: WidgetInstance) {
  const step: Record<string, [number, number]> = {
    ArrowLeft: [-1, 0],
    ArrowRight: [1, 0],
    ArrowUp: [0, -1],
    ArrowDown: [0, 1],
  };
  const d = step[e.key];
  if (!d) return;
  e.preventDefault();
  const def = definitionOf(w.type);
  if (e.shiftKey)
    commit(w.id, {
      x: w.x,
      y: w.y,
      w: Math.max(
        def?.size.minW ?? 1,
        Math.min(GRID_COLUMNS - w.x, w.w + d[0]),
      ),
      h: Math.max(def?.size.minH ?? 1, w.h + d[1]),
    });
  else commit(w.id, { x: w.x + d[0], y: w.y + d[1], w: w.w, h: w.h });
}
</script>

<template>
  <div
    ref="gridEl"
    class="grid"
    :class="{ editing, dragging }"
    :style="{ '--gap': `${gap}px`, '--row': `${ROW_PX}px` }"
  >
    <!-- where the widget being moved will land -->
    <div
      v-if="dragging && activeWidget && gestureMode === 'move'"
      class="drop"
      aria-hidden="true"
      :style="{
        '--x': (preview ?? activeWidget).x,
        '--y': (preview ?? activeWidget).y,
        '--w': (preview ?? activeWidget).w,
        '--h': (preview ?? activeWidget).h,
      }"
    ></div>
    <div
      v-for="w in ordered"
      :key="w.id"
      :ref="(el) => setCell(w.id, el)"
      class="cell"
      :data-widget="w.id"
      :class="{ active: active === w.id }"
      :style="{ '--x': w.x, '--y': w.y, '--w': w.w, '--h': w.h, ...follow(w) }"
    >
      <div class="content" :inert="editing">
        <WidgetHost
          v-if="definitionOf(w.type)"
          :id="w.id"
          :def="definitionOf(w.type)!"
          :settings="w.settings"
          :variant="w.variant"
          :w="w.w"
          :h="w.h"
        />
        <div v-else class="unknown">
          <strong>This widget is not available</strong>
          <span>It may come from something that was removed.</span>
        </div>
      </div>
      <template v-if="editing">
        <div
          class="hit"
          role="button"
          tabindex="0"
          :aria-label="`Move ${definitionOf(w.type)?.name ?? w.type}. Arrow keys move, Shift and arrows resize.`"
          @pointerdown.prevent="begin($event, w, 'move')"
          @pointermove="onMove"
          @pointerup="finish"
          @pointercancel="finish"
          @keydown="key($event, w)"
        ></div>
        <div class="bar">
          <span class="name">{{ definitionOf(w.type)?.name ?? w.type }}</span>
          <span v-if="limited?.id === w.id" class="limit">{{
            limited.note
          }}</span>
          <span class="tools">
            <button
              v-if="definitionOf(w.type)"
              type="button"
              class="tool"
              aria-label="Widget settings"
              title="Settings"
              @click.stop="emit('settings', w.id)"
            >
              &#9881;
            </button>
            <button
              type="button"
              class="tool"
              aria-label="Remove widget"
              title="Remove"
              @click.stop="emit('remove', w.id)"
            >
              &#10005;
            </button>
          </span>
        </div>
        <div
          class="edge edge-r"
          aria-hidden="true"
          @pointerdown.prevent="begin($event, w, 'resize-w')"
          @pointermove="onMove"
          @pointerup="finish"
          @pointercancel="finish"
        ></div>
        <div
          class="edge edge-b"
          aria-hidden="true"
          @pointerdown.prevent="begin($event, w, 'resize-h')"
          @pointermove="onMove"
          @pointerup="finish"
          @pointercancel="finish"
        ></div>
        <div
          class="grip"
          aria-hidden="true"
          @pointerdown.prevent="begin($event, w, 'resize')"
          @pointermove="onMove"
          @pointerup="finish"
          @pointercancel="finish"
        ></div>
      </template>
    </div>
  </div>
</template>

<style scoped>
.grid {
  position: relative;
  display: grid;
  grid-template-columns: repeat(12, minmax(0, 1fr));
  grid-auto-rows: var(--row);
  gap: var(--gap);
}
.cell {
  position: relative;
  grid-column: calc(var(--x) + 1) / span var(--w);
  grid-row: calc(var(--y) + 1) / span var(--h);
  min-width: 0;
  min-height: 0;
}
.drop {
  grid-column: calc(var(--x) + 1) / span var(--w);
  grid-row: calc(var(--y) + 1) / span var(--h);
  border: 2px dashed var(--ui-accent);
  border-radius: var(--ui-radius-row);
  background: var(--ui-accent-soft);
  pointer-events: none;
}
.content {
  width: 100%;
  height: 100%;
  min-width: 0;
}
.editing .cell {
  outline: 1.5px dashed var(--ui-border-strong);
  outline-offset: 4px;
  border-radius: var(--ui-radius-row);
}
.editing .cell:hover,
.editing .cell.active {
  outline-color: var(--ui-accent-line);
}
.editing .content {
  opacity: 0.5;
  transition: opacity 0.15s;
}
.editing .cell:hover .content {
  opacity: 0.7;
}
.cell.active {
  z-index: 6;
}
.cell.active .content {
  opacity: 0.88;
}
.cell.active::after {
  content: "";
  position: absolute;
  inset: -4px;
  border-radius: var(--ui-radius-row);
  box-shadow: 0 22px 48px
    color-mix(in srgb, var(--ui-scrim-base) 60%, transparent);
  pointer-events: none;
}
.dragging .cell:not(.active) {
  z-index: 1;
}
.hit {
  position: absolute;
  inset: 0;
  z-index: 1;
  cursor: grab;
  touch-action: none;
  user-select: none;
  border-radius: var(--ui-radius-row);
}
.active .hit {
  cursor: grabbing;
}
.hit:focus-visible {
  outline: 2px solid var(--ui-accent);
  outline-offset: 2px;
}
.bar {
  position: absolute;
  inset: 0 0 auto 0;
  z-index: 2;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 6px 4px 10px;
  border-radius: var(--ui-radius-row) var(--ui-radius-row) 0 0;
  background: color-mix(in srgb, var(--ui-bg) 90%, transparent);
  border-bottom: 1px solid var(--ui-border);
  pointer-events: none;
}
.active .bar {
  border-color: var(--ui-accent-line);
}
.name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--ui-text);
  font-size: 0.78rem;
  font-weight: 700;
}
.limit {
  padding: 1px 8px;
  border-radius: 999px;
  background: var(--ui-accent-soft);
  color: var(--ui-accent);
  font-size: 0.7rem;
  font-weight: 700;
  white-space: nowrap;
}
.tools {
  display: flex;
  gap: 2px;
  pointer-events: auto;
}
.tool {
  width: 26px;
  height: 26px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: var(--ui-dim);
  font-size: 0.95rem;
  cursor: pointer;
}
.tool:hover {
  background: var(--ui-surface-2);
  color: var(--ui-text);
}
.edge {
  position: absolute;
  z-index: 3;
  touch-action: none;
}
.edge-r {
  top: 36px;
  right: -8px;
  bottom: 28px;
  width: 16px;
  cursor: ew-resize;
}
.edge-b {
  left: 12px;
  right: 28px;
  bottom: -8px;
  height: 16px;
  cursor: ns-resize;
}
.edge:hover {
  background: var(--ui-accent-soft);
}
.grip {
  position: absolute;
  right: -2px;
  bottom: -2px;
  z-index: 4;
  width: 28px;
  height: 28px;
  cursor: nwse-resize;
  touch-action: none;
  background: linear-gradient(
    135deg,
    transparent 52%,
    var(--ui-accent) 52%,
    var(--ui-accent) 64%,
    transparent 64%,
    transparent 76%,
    var(--ui-accent) 76%,
    var(--ui-accent) 88%,
    transparent 88%
  );
  border-bottom-right-radius: var(--ui-radius-row);
}
/* an empty spacer or a divider is hard to see when nothing else is */
.editing .content :deep(.spacer-box) {
  border: 1px dashed var(--ui-border-strong);
  border-radius: var(--ui-radius-row);
  background: repeating-linear-gradient(
    135deg,
    transparent 0 8px,
    color-mix(in srgb, var(--ui-wash-base) 4%, transparent) 8px 16px
  );
}
.unknown {
  display: grid;
  place-content: center;
  gap: 4px;
  height: 100%;
  border: 1px dashed var(--ui-border);
  border-radius: var(--ui-radius-row);
  color: var(--ui-dim);
  font-size: 0.82rem;
  text-align: center;
}
.unknown strong {
  color: var(--ui-text);
}
@media (max-width: 760px) {
  .grid {
    grid-template-columns: minmax(0, 1fr);
  }
  .cell {
    grid-column: 1;
    grid-row: span var(--h);
  }
}
</style>
