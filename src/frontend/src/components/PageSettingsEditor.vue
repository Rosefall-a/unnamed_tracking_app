<script setup lang="ts">
// Edits what a game page shows. Used twice: in Settings for the defaults every
// game starts from, and in a game's Edit dialog for that game's overrides.
// In the dialog every row can also say "Default", which clears the override and
// follows Settings again, and a row shows what the default currently is.
import { computed } from "vue";
import SegmentedControl from "./settings/SegmentedControl.vue";
import SettingsCard from "./settings/SettingsCard.vue";
import SettingsRow from "./settings/SettingsRow.vue";
import SettingsSwitch from "./settings/SettingsSwitch.vue";
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
  // "cards" is the Settings look: two cards, switches that say what is shown
  layout?: "plain" | "cards";
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

// In Settings each switch says what is shown, so on means visible, rather
// than the "Hide the ..." wording the dialog uses next to Show and Hide.
const SHOW_LABELS: Record<HideFlag, { label: string; hint?: string }> = {
  hide_rating: {
    label: "Score button",
    hint: "The stars in the header and the score in Stats",
  },
  hide_collections: { label: "Collections button" },
  hide_favorite: { label: "Favorite heart" },
  hide_credits: { label: "Developer and publisher" },
  hide_date_badge: { label: "Date badge" },
  hide_platform_badge: { label: "Platform badge" },
  hide_history: {
    label: "History timeline",
    hint: "Stats keeps its numbers either way",
  },
};

const achievementsGone = computed(() => {
  const mode = tabValue("Achievements");
  const effective = mode === "default" ? base.value.tabs.Achievements : mode;
  return effective === "hide";
});
</script>

<template>
  <template v-if="layout === 'cards'">
    <SettingsCard>
      <template #actions>
        <h3>Tabs</h3>
        <label class="opens-on">
          <span class="st-muted">Opens on</span>
          <select
            class="st-select"
            :value="openValue"
            @change="setOpen(($event.target as HTMLSelectElement).value)"
          >
            <option v-for="o in openOptions" :key="o.value" :value="o.value">
              {{ o.label }}
            </option>
          </select>
        </label>
      </template>
      <p class="st-desc">
        Auto shows a tab once the game has something in it. Any game can
        override this in its Edit dialog.
      </p>
      <SettingsRow
        v-for="tab in OPTIONAL_TABS"
        :key="tab"
        :label="tab"
        :hint="TAB_HINTS[tab]"
      >
        <SegmentedControl
          :model-value="tabValue(tab)"
          :options="tabOptions"
          @update:model-value="setTab(tab, $event)"
        />
      </SettingsRow>
      <p v-if="achievementsGone" class="st-note">
        With Achievements hidden, the achievement badge, the achievement stats
        and the timeline entries for them, and tying files and notes to
        achievements, are hidden too.
      </p>
    </SettingsCard>
    <SettingsCard
      title="Header and details"
      description="Each switch shows the thing when it is on."
    >
      <SettingsRow
        v-for="flag in HIDE_FLAGS"
        :key="flag"
        :label="SHOW_LABELS[flag].label"
        :hint="SHOW_LABELS[flag].hint"
      >
        <SettingsSwitch
          :model-value="flagValue(flag) !== 'hide'"
          :label="SHOW_LABELS[flag].label"
          @update:model-value="setFlag(flag, $event ? 'show' : 'hide')"
        />
      </SettingsRow>
    </SettingsCard>
  </template>
  <div v-else class="pse">
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
.opens-on {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}
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
  color: var(--ui-accent);
}
.pse-hint {
  margin: 0 0 12px;
  font-size: 0.8rem;
  line-height: 1.55;
  color: var(--ui-dim-2);
}
.pse-note {
  margin: 12px 0 0;
  padding: 10px 12px;
  font-size: 0.8rem;
  line-height: 1.5;
  color: var(--ui-accent);
  background: color-mix(in srgb, var(--ui-accent) 8%, transparent);
  border: 1px solid color-mix(in srgb, var(--ui-accent) 25%, transparent);
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
  border-bottom: 1px solid var(--ui-surface-2);
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
  color: var(--ui-text);
}
.pse-name span {
  font-size: 0.78rem;
  color: var(--ui-dim-2);
}
.pse-name small,
.pse-default {
  font-size: 0.74rem;
  color: var(--ui-faint-2);
}
@media (max-width: 640px) {
  .pse-row {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }
}
</style>
