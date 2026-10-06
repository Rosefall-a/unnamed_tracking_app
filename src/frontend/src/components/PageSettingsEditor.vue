<script setup lang="ts">
// Edits what a game page shows. Used twice: in Settings for the defaults every
// game starts from, and in a game's Edit dialog for that game's overrides.
// In the dialog every row can also say "Default", which clears the override and
// follows Settings again, and a row shows what the default currently is.
import { computed } from "vue";
import SegmentedControl from "./settings/SegmentedControl.vue";
import {
  FLAG_LABELS,
  HIDE_FLAGS,
  OPTIONAL_TABS,
  TAB_HINTS,
  resolvePage,
} from "../utils/gamePage";
import type {
  HideFlag,
  OptionalTab,
  PageOverrides,
  PageSettings,
  TabMode,
} from "../utils/gamePage";

const props = defineProps<{
  // the defaults themselves (Settings) or one game's overrides (Edit dialog)
  modelValue: PageSettings | PageOverrides;
  // set in the Edit dialog: the defaults the overrides sit on top of
  defaults?: PageSettings | null;
}>();
const emit = defineEmits<{
  "update:modelValue": [value: PageSettings | PageOverrides];
}>();

const overriding = computed(() => props.defaults !== undefined);
const base = computed(() => resolvePage(props.defaults ?? null, null));
const MODE_LABEL: Record<TabMode, string> = {
  show: "shown",
  hide: "hidden",
  auto: "shown once it has something",
};

function tabValue(tab: OptionalTab): string {
  return (
    (props.modelValue.tabs as Record<string, TabMode> | undefined)?.[tab] ??
    (overriding.value ? "default" : "show")
  );
}
function setTab(tab: OptionalTab, value: string) {
  const tabs: Record<string, TabMode> = {
    ...((props.modelValue.tabs as Record<string, TabMode> | undefined) ?? {}),
  };
  if (value === "default") delete tabs[tab];
  else tabs[tab] = value as TabMode;
  const next = { ...props.modelValue, tabs } as PageSettings | PageOverrides;
  if (overriding.value && !Object.keys(tabs).length) delete next.tabs;
  emit("update:modelValue", next);
}
const tabOptions = computed(() => {
  const own = [
    { value: "show", label: "Show" },
    { value: "auto", label: "Auto" },
    { value: "hide", label: "Hide" },
  ];
  return overriding.value
    ? [{ value: "default", label: "Default" }, ...own]
    : own;
});

const openOptions = computed(() => [
  ...(overriding.value ? [{ value: "default", label: "Default" }] : []),
  { value: "Overview", label: "Overview" },
  ...OPTIONAL_TABS.map((t) => ({ value: t, label: t })),
]);
const openValue = computed(
  () =>
    (props.modelValue.default_tab as string | undefined) ??
    (overriding.value ? "default" : "Overview"),
);
function setOpen(value: string) {
  const next = { ...props.modelValue } as Record<string, unknown>;
  if (value === "default") delete next.default_tab;
  else next.default_tab = value;
  emit("update:modelValue", next as PageSettings | PageOverrides);
}

function flagValue(flag: HideFlag): string {
  const v = (props.modelValue as Record<string, unknown>)[flag];
  if (overriding.value)
    return v === undefined ? "default" : v ? "hide" : "show";
  return v ? "hide" : "show";
}
function setFlag(flag: HideFlag, value: string) {
  const next = { ...props.modelValue } as Record<string, unknown>;
  if (value === "default") delete next[flag];
  else next[flag] = value === "hide";
  emit("update:modelValue", next as PageSettings | PageOverrides);
}
const flagOptions = computed(() => [
  ...(overriding.value ? [{ value: "default", label: "Default" }] : []),
  { value: "show", label: "Show" },
  { value: "hide", label: "Hide" },
]);

const achievementsGone = computed(() => {
  const mode = tabValue("Achievements");
  const effective = mode === "default" ? base.value.tabs.Achievements : mode;
  return effective === "hide";
});
</script>

<template>
  <div class="pse">
    <section class="pse-block">
      <h3>Tabs</h3>
      <p class="pse-hint">
        <strong>Show</strong> always. <strong>Hide</strong> never.
        <strong>Auto</strong> only once the game has something in it; until then
        it waits behind the + at the end of the tab bar.
      </p>
      <ul class="pse-rows">
        <li v-for="tab in OPTIONAL_TABS" :key="tab" class="pse-row">
          <div class="pse-name">
            <strong>{{ tab }}</strong>
            <span>{{ TAB_HINTS[tab] }}</span>
            <small v-if="overriding && tabValue(tab) === 'default'">
              Default: {{ MODE_LABEL[base.tabs[tab]] }}
            </small>
          </div>
          <SegmentedControl
            :model-value="tabValue(tab)"
            :options="tabOptions"
            @update:model-value="setTab(tab, $event)"
          />
        </li>
      </ul>
      <p v-if="achievementsGone" class="pse-note">
        With Achievements hidden, the achievement badge, the achievement stats
        and the timeline entries for them, and tying files and notes to
        achievements, are hidden too.
      </p>
    </section>

    <section class="pse-block">
      <h3>Opens on</h3>
      <SegmentedControl
        :model-value="openValue"
        :options="openOptions"
        @update:model-value="setOpen"
      />
      <small v-if="overriding && openValue === 'default'" class="pse-default">
        Default: {{ base.default_tab }}
      </small>
    </section>

    <section class="pse-block">
      <h3>Buttons and details</h3>
      <ul class="pse-rows">
        <li v-for="flag in HIDE_FLAGS" :key="flag" class="pse-row">
          <div class="pse-name">
            <strong>{{ FLAG_LABELS[flag].label }}</strong>
            <span>{{ FLAG_LABELS[flag].hint }}</span>
            <small v-if="overriding && flagValue(flag) === 'default'">
              Default: {{ base[flag] ? "hidden" : "shown" }}
            </small>
          </div>
          <SegmentedControl
            :model-value="flagValue(flag)"
            :options="flagOptions"
            @update:model-value="setFlag(flag, $event)"
          />
        </li>
      </ul>
    </section>
  </div>
</template>

<style scoped>
.pse {
  display: flex;
  flex-direction: column;
  gap: 26px;
}
.pse-block h3 {
  margin: 0 0 8px;
  font-size: 0.72rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #d68a34;
}
.pse-hint {
  margin: 0 0 12px;
  font-size: 0.8rem;
  line-height: 1.55;
  color: #888;
}
.pse-note {
  margin: 12px 0 0;
  padding: 10px 12px;
  font-size: 0.8rem;
  line-height: 1.5;
  color: #d68a34;
  background: rgba(214, 138, 52, 0.08);
  border: 1px solid rgba(214, 138, 52, 0.25);
  border-radius: 10px;
}
.pse-rows {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
}
.pse-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 11px 0;
  border-bottom: 1px solid #222;
}
.pse-row:last-child {
  border-bottom: none;
}
.pse-name {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}
.pse-name strong {
  font-size: 0.88rem;
  color: #f0f0f0;
}
.pse-name span {
  font-size: 0.78rem;
  color: #888;
}
.pse-name small,
.pse-default {
  font-size: 0.74rem;
  color: #777;
}
@media (max-width: 640px) {
  .pse-row {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }
}
</style>
