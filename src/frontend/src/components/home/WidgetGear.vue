<script setup lang="ts">
// The gear in a widget's heading: opens every option the widget has in a panel
// right next to it, so nothing needs the page's edit mode. Changes apply and are
// saved as you make them.
import { computed, inject, onBeforeUnmount, ref } from "vue";
import SettingsFields from "./SettingsFields.vue";
import { WIDGET_CONTEXT } from "../../home/context";

const ctx = inject(WIDGET_CONTEXT, null);
const c = computed(() => ctx?.value ?? null);

const open = ref(false);
const gear = ref<HTMLElement | null>(null);
const place = ref<Record<string, string>>({});

function toggle() {
  if (open.value) return close();
  const r = gear.value?.getBoundingClientRect();
  if (r) {
    const width = Math.min(360, window.innerWidth - 24);
    const left = Math.max(
      12,
      Math.min(r.right - width, window.innerWidth - width - 12),
    );
    const top = r.bottom + 6;
    place.value = {
      top: `${top}px`,
      left: `${left}px`,
      width: `${width}px`,
      maxHeight: `${Math.max(240, window.innerHeight - top - 16)}px`,
    };
  }
  open.value = true;
  window.setTimeout(() => {
    document.addEventListener("pointerdown", outside, true);
    document.addEventListener("keydown", onKey, true);
  });
}
function close() {
  open.value = false;
  document.removeEventListener("pointerdown", outside, true);
  document.removeEventListener("keydown", onKey, true);
}
function outside(e: PointerEvent) {
  const target = e.target as HTMLElement;
  if (gear.value?.contains(target) || target.closest?.(".more-panel")) return;
  close();
}
function onKey(e: KeyboardEvent) {
  if (e.key === "Escape") close();
}
onBeforeUnmount(close);

function onChange(settings: Record<string, unknown>, variant: string | null) {
  const cur = ctx?.value;
  if (!cur) return;
  if (variant !== cur.variant && variant !== null) cur.setVariant(variant);
  else cur.update(settings);
}
</script>

<template>
  <template v-if="c && (c.def.cog || c.def.variants.length > 1)">
    <button
      ref="gear"
      type="button"
      class="gear"
      :class="{ on: open, always: c.def.type === 'random' }"
      aria-label="More options"
      title="More options"
      @click="toggle"
    >
      &#9881;
    </button>
    <Teleport to="body">
      <div
        v-if="open"
        class="more-panel"
        :style="place"
        role="dialog"
        :aria-label="`${c.def.name} options`"
      >
        <header>
          <strong>{{ c.def.name }}</strong>
          <button type="button" class="done" @click="close">Done</button>
        </header>
        <div class="scroll">
          <SettingsFields
            :def="c.def"
            :settings="c.settings"
            :variant="c.variant"
            @change="onChange"
          />
        </div>
      </div>
    </Teleport>
  </template>
</template>

<style scoped>
.gear {
  width: 26px;
  height: 26px;
  border: 0;
  border-radius: 7px;
  background: transparent;
  color: var(--ui-faint);
  font-size: 1rem;
  cursor: pointer;
  /* out of the way until you point at the widget */
  opacity: 0;
  transition: opacity 0.15s;
}
:global(.wf:hover) .gear,
.gear.always,
.gear:focus-visible,
.gear.on {
  opacity: 1;
}
@media (hover: none) {
  .gear {
    opacity: 1;
  }
}
.gear:hover,
.gear.on {
  background: var(--ui-surface-2);
  color: var(--ui-text);
}
.more-panel {
  position: fixed;
  z-index: var(--ui-z-popover);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-card);
  background: var(--ui-popover);
  color: var(--ui-text);
  box-shadow: 0 18px 48px
    color-mix(in srgb, var(--ui-scrim-base) 55%, transparent);
}
.more-panel header {
  flex: none;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid var(--ui-border-soft);
}
.done {
  padding: 5px 12px;
  border: 0;
  border-radius: 7px;
  background: var(--ui-accent);
  color: var(--ui-on-accent);
  font: inherit;
  font-size: 0.8rem;
  font-weight: 700;
  cursor: pointer;
}
.scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 16px;
  scrollbar-width: thin;
}
</style>
