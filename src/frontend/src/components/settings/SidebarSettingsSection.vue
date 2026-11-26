<script setup lang="ts">
// Look and feel, Sidebar and navigation: how the sidebar looks, when it
// shows, what is in it, and the titles pinned to it.
import { computed, onMounted, ref } from "vue";
import SettingsCard from "./SettingsCard.vue";
import SettingsRow from "./SettingsRow.vue";
import SettingsSwitch from "./SettingsSwitch.vue";
import SegmentedControl from "./SegmentedControl.vue";
import { sidebarMode, type SidebarMode } from "../../state/sidebarMode";
import {
  JUMP_COUNTS,
  mediaOpensOn,
  movePin,
  sidebarJumpCount,
  sidebarPins,
  sidebarShowCounts,
  sidebarShowJump,
  sidebarShowSearch,
  sidebarStyle,
  togglePin,
  type MediaOpensOn,
  type SidebarStyle,
} from "../../state/sidebarPrefs";
import { allTitles, ensure, KIND_NOUN } from "../../home/data";
import { usesShowMode } from "../../state/navData";

const STYLES: { value: SidebarStyle; label: string; sub: string }[] = [
  {
    value: "classic",
    label: "Clean list",
    sub: "Like Linear: every section open, one line per title",
  },
  {
    value: "library",
    label: "Your library",
    sub: "Like Spotify: one list of pins and recents, filtered by kind",
  },
  {
    value: "railpanel",
    label: "Rail and panel",
    sub: "Like Discord: icons always there, a panel for where you are",
  },
  {
    value: "minimal",
    label: "Minimal",
    sub: "Like Arc: big rows; Jump back in and Pinned open beside it",
  },
  {
    value: "peek",
    label: "Peek",
    sub: "Hidden until your mouse touches the left edge",
  },
  {
    value: "topbar",
    label: "Top bar",
    sub: "Like Plex: no sidebar, everything across the top",
  },
  {
    value: "guide",
    label: "Guide button",
    sub: "Like the Xbox Guide: one button opens a big panel",
  },
  {
    value: "dock",
    label: "Dock",
    sub: "Like macOS: a small floating bar at the bottom",
  },
];
const MODE_OPTIONS = [
  { value: "pinned", label: "Always" },
  { value: "overlay", label: "Menu button" },
  { value: "rail", label: "Icons until hover" },
];
const MEDIA_OPTIONS = [
  { value: "anime", label: "Anime" },
  { value: "movies", label: "Movies" },
  { value: "tv", label: "TV" },
  { value: "last", label: "Last used" },
];
const COUNT_OPTIONS = JUMP_COUNTS.map((n) => ({
  value: String(n),
  label: String(n),
}));

onMounted(() => {
  for (const key of ["games", "movies", "tv", "anime"] as const)
    void ensure(key);
});

// pick something to pin by typing part of its name
const query = ref("");
const matches = computed(() => {
  const q = query.value.trim().toLowerCase();
  if (q.length < 2) return [];
  return allTitles.value
    .filter((t) => t.title.toLowerCase().includes(q))
    .slice(0, 8);
});
function pin(t: (typeof allTitles.value)[number]) {
  togglePin({
    key: t.key,
    title: t.title,
    art: t.art,
    to: t.to,
    kind: KIND_NOUN[t.kind],
  });
  query.value = "";
}
</script>

<template>
  <SettingsCard title="Sidebar">
    <SettingsRow label="Style" stack>
      <div class="styles">
        <button
          v-for="st in STYLES"
          :key="st.value"
          type="button"
          class="style"
          :class="{ on: sidebarStyle === st.value }"
          :aria-pressed="sidebarStyle === st.value"
          @click="sidebarStyle = st.value"
        >
          <strong>{{ st.label }}</strong>
          <span>{{ st.sub }}</span>
        </button>
      </div>
    </SettingsRow>
    <SettingsRow
      label="When it shows"
      :hint="
        usesShowMode(sidebarStyle)
          ? 'Always open, behind the menu button, or a strip of icons that widens on hover'
          : 'Not used by this style'
      "
    >
      <SegmentedControl
        :class="{ off: !usesShowMode(sidebarStyle) }"
        :model-value="sidebarMode"
        :options="MODE_OPTIONS"
        @update:model-value="sidebarMode = $event as SidebarMode"
      />
    </SettingsRow>
    <SettingsRow
      label="Jump back in"
      hint="What you last played or watched, at the top"
    >
      <span class="pair">
        <SegmentedControl
          :model-value="String(sidebarJumpCount)"
          :options="COUNT_OPTIONS"
          @update:model-value="sidebarJumpCount = Number($event)"
        />
        <SettingsSwitch v-model="sidebarShowJump" label="Jump back in" />
      </span>
    </SettingsRow>
    <SettingsRow
      label="Counts next to each library"
      hint="Plain grey numbers, like Games 249"
    >
      <SettingsSwitch v-model="sidebarShowCounts" label="Counts" />
    </SettingsRow>
    <SettingsRow
      label="Search bar in the sidebar"
      hint="Opens the same search as Ctrl + K"
    >
      <SettingsSwitch v-model="sidebarShowSearch" label="Search bar" />
    </SettingsRow>
    <SettingsRow
      label="Media opens on"
      hint="Media and its count follow this. The arrow next to it still lists every library."
    >
      <SegmentedControl
        :model-value="mediaOpensOn"
        :options="MEDIA_OPTIONS"
        @update:model-value="mediaOpensOn = $event as MediaOpensOn"
      />
    </SettingsRow>
  </SettingsCard>

  <SettingsCard
    title="Pinned"
    description="Always at hand in the sidebar. Saved to your account."
  >
    <div v-for="(p, i) in sidebarPins" :key="p.key" class="st-list-row pin-row">
      <img v-if="p.art" :src="p.art" alt="" class="pin-cv" />
      <span v-else class="pin-cv blank"></span>
      <div class="st-lbl">
        <strong>{{ p.title }}</strong>
        <span>{{ p.kind }}</span>
      </div>
      <span class="st-btns">
        <button
          type="button"
          class="st-btn"
          :disabled="i === 0"
          aria-label="Move up"
          @click="movePin(p.key, -1)"
        >
          ↑
        </button>
        <button
          type="button"
          class="st-btn"
          :disabled="i === sidebarPins.length - 1"
          aria-label="Move down"
          @click="movePin(p.key, 1)"
        >
          ↓
        </button>
        <button type="button" class="st-btn" @click="togglePin(p)">
          Unpin
        </button>
      </span>
    </div>
    <p v-if="!sidebarPins.length" class="st-muted">Nothing pinned yet.</p>
    <label class="st-flabel" for="pin-search">Pin a game, show or film</label>
    <input
      id="pin-search"
      v-model="query"
      class="st-field"
      type="search"
      placeholder="Type part of a name"
      autocomplete="off"
    />
    <div v-if="matches.length" class="matches">
      <button
        v-for="t in matches"
        :key="t.key"
        type="button"
        class="match"
        @click="pin(t)"
      >
        <img v-if="t.art" :src="t.art" alt="" />
        <span class="match-title">{{ t.title }}</span>
        <span class="st-muted">{{ KIND_NOUN[t.kind] }}</span>
      </button>
    </div>
  </SettingsCard>
</template>

<style scoped>
.styles {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 8px;
  width: 100%;
}
.style {
  display: flex;
  flex-direction: column;
  gap: 3px;
  text-align: left;
  padding: 10px 12px;
  border: 1px solid #2b2b2b;
  border-radius: 9px;
  background: #141414;
  color: var(--ui-text-soft);
  font: inherit;
  cursor: pointer;
}
.style strong {
  font-size: 13px;
}
.style span {
  font-size: 12px;
  color: #8a8a8a;
}
.style.on {
  border-color: var(--ui-accent);
  background: color-mix(in srgb, var(--ui-accent) 8%, transparent);
  color: var(--ui-accent-bright);
}
.off {
  opacity: 0.4;
  pointer-events: none;
}
.pair {
  display: inline-flex;
  align-items: center;
  gap: 12px;
}
.pin-cv {
  width: 28px;
  height: 42px;
  object-fit: cover;
  border-radius: 4px;
  flex: 0 0 auto;
}
.pin-cv.blank {
  background: #262626;
}
.matches {
  display: flex;
  flex-direction: column;
  margin-top: 6px;
  border: 1px solid #2b2b2b;
  border-radius: 8px;
  overflow: hidden;
}
.match {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 10px;
  border: 0;
  background: #141414;
  color: var(--ui-text-soft);
  font: inherit;
  text-align: left;
  cursor: pointer;
}
.match + .match {
  border-top: 1px solid #242424;
}
.match:hover {
  background: #1f1f1f;
}
.match img {
  width: 20px;
  height: 30px;
  object-fit: cover;
  border-radius: 3px;
}
.match-title {
  flex: 1;
  min-width: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
