<script setup lang="ts">
// See what each library is missing and fill it in without a reimport. Looking
// changes nothing, and a run only ever adds what is blank.
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import {
  fixOneGame,
  gamesWithProblem,
  repairStatus,
  restoreOldFiles,
  scanLibraries,
  scanOldFiles,
  startRepair,
} from "../../services/gameRepair";
import type {
  OldFiles,
  RepairGame,
  RepairPerson,
  RepairResult,
  RepairRun,
} from "../../services/gameRepair";

const POLL_MS = 2000;

// in the order they are shown; the ones marked report-only are never changed
const PROBLEMS: { id: string; label: string; reportOnly?: boolean }[] = [
  { id: "placeholder_name", label: 'Named "Steam app"' },
  { id: "no_key_art", label: "No cover" },
  { id: "no_banner", label: "No banner" },
  { id: "no_logo", label: "No logo" },
  { id: "no_icon", label: "No icon" },
  { id: "no_description", label: "No description" },
  { id: "no_developer", label: "No developer" },
  { id: "no_publisher", label: "No publisher" },
  { id: "no_release_date", label: "No release date" },
  { id: "no_tags", label: "No genres" },
  { id: "no_features", label: "No features" },
  { id: "no_times", label: "No play time" },
  { id: "placeholder_folder", label: 'Folder named "Steam-app"' },
  { id: "no_info_file", label: "No game.json" },
  { id: "missing_media", label: "File gone", reportOnly: true },
];

const people = ref<RepairPerson[] | null>(null);
const run = ref<RepairRun | null>(null);
const force = ref(false);
const error = ref<string | null>(null);
const opened = ref<{
  person: RepairPerson;
  problem: string;
  games: RepairGame[] | null;
} | null>(null);
const fixing = ref<string | null>(null);
const fixed = ref<Record<string, string>>({});
let timer: ReturnType<typeof setTimeout> | null = null;

const running = computed(() => run.value?.running ?? false);
// what the progress line counts: games, or pictures when saving them for offline
const unit = ref("games");

function offlineTotal(person: RepairPerson): number {
  return Object.values(person.offline_missing ?? {}).reduce((a, b) => a + b, 0);
}
function offlineSummary(person: RepairPerson): string {
  const m = person.offline_missing ?? {};
  const parts: string[] = [];
  const posters = (m.movie ?? 0) + (m.tv ?? 0) + (m.anime ?? 0);
  if (posters)
    parts.push(
      `${posters} ${posters === 1 ? "poster or backdrop" : "posters and backdrops"}`,
    );
  if (m.icon)
    parts.push(`${m.icon} achievement ${m.icon === 1 ? "icon" : "icons"}`);
  if (m.still)
    parts.push(`${m.still} episode ${m.still === 1 ? "still" : "stills"}`);
  if (m.page)
    parts.push(
      `${m.page} ${m.page === 1 ? "picture or clip" : "pictures and clips"} from game descriptions`,
    );
  return parts.join(", ");
}

function shown(person: RepairPerson) {
  return PROBLEMS.filter((p) => person.problems[p.id]);
}
function labelOf(problem: string): string {
  return PROBLEMS.find((p) => p.id === problem)?.label ?? problem;
}
function isReportOnly(problem: string): boolean {
  return PROBLEMS.some((p) => p.id === problem && p.reportOnly);
}
function message(err: unknown, fallback: string): string {
  return err instanceof Error ? err.message : fallback;
}

async function scan() {
  try {
    people.value = await scanLibraries();
    error.value = null;
  } catch (err) {
    error.value = message(err, "Could not read the libraries.");
  }
}

async function poll() {
  try {
    const wasRunning = running.value;
    run.value = await repairStatus();
    if (run.value.running) timer = setTimeout(() => void poll(), POLL_MS);
    else if (wasRunning) await scan();
  } catch (err) {
    error.value = message(err, "Could not read the progress.");
  }
}

async function start(userId: string | null, covers = false, pictures = false) {
  error.value = null;
  opened.value = null;
  unit.value = pictures ? "pictures" : "games";
  try {
    run.value = await startRepair(userId, force.value, covers, pictures);
    void poll();
  } catch (err) {
    error.value = message(err, "Could not start the repair.");
  }
}

async function open(person: RepairPerson, problem: string) {
  if (opened.value?.person === person && opened.value.problem === problem) {
    opened.value = null;
    return;
  }
  opened.value = { person, problem, games: null };
  fixed.value = {};
  try {
    const games = await gamesWithProblem(person.user_id, problem);
    if (opened.value?.problem === problem) opened.value.games = games;
  } catch (err) {
    error.value = message(err, "Could not list those games.");
    opened.value = null;
  }
}

function describe(r: Partial<RepairResult>): string {
  const parts: string[] = [];
  const add = (count: number | undefined, words: string) => {
    if (count) parts.push(`${count} ${words}`);
  };
  add(r.names, "named");
  add(r.details, "with details added");
  add(r.art, "images added");
  add(r.dates, "finish dates corrected");
  add(
    r.covers,
    r.covers === 1 ? "poor cover replaced" : "poor covers replaced",
  );
  add(r.times, "play times added");
  add(r.pictures, "pictures saved for offline");
  add(r.folders, "folders renamed");
  add(r.failed, "failed");
  if (r.hltb_error)
    parts.push("HowLongToBeat did not answer, those games are tried again");
  return parts.join(", ") || "Nothing new was found";
}

async function fixGame(game: RepairGame) {
  fixing.value = game.id;
  try {
    fixed.value = {
      ...fixed.value,
      [game.id]: describe(await fixOneGame(game.id)),
    };
  } catch (err) {
    fixed.value = {
      ...fixed.value,
      [game.id]: message(err, "Could not fix this game."),
    };
  } finally {
    fixing.value = null;
  }
}

// files stuck in the old shared data folder
const oldFor = ref<string | null>(null);
const oldFiles = ref<OldFiles | null>(null);
const oldBusy = ref(false);
const oldMessage = ref<string | null>(null);
function oldSummary(files: Record<string, number>): string {
  return Object.entries(files)
    .map(([kind, count]) => `${count} ${kind}`)
    .join(", ");
}
async function checkOldFiles(person: RepairPerson) {
  oldFor.value = person.user_id;
  oldFiles.value = null;
  oldMessage.value = null;
  try {
    oldFiles.value = await scanOldFiles(person.user_id);
  } catch (err) {
    oldMessage.value = message(err, "Could not read the old folder.");
  }
}
async function bringBackOldFiles(person: RepairPerson) {
  oldBusy.value = true;
  oldMessage.value = null;
  try {
    const done = await restoreOldFiles(person.user_id);
    oldFiles.value = await scanOldFiles(person.user_id);
    oldMessage.value = `Copied ${done.copied} files${done.failed ? `, ${done.failed} could not be copied` : ""}. The originals are still in the old folder.`;
  } catch (err) {
    oldMessage.value = message(err, "Could not copy the files.");
  } finally {
    oldBusy.value = false;
  }
}

onMounted(() => {
  void scan();
  void poll();
});
onBeforeUnmount(() => {
  if (timer) clearTimeout(timer);
});
</script>

<template>
  <section class="settings-section">
    <h2>Repair</h2>
    <p class="section-hint">
      Finds what games are missing and fills it in without a reimport. It only
      adds: anything already there, edited or locked is left alone. A game that
      has been checked is not asked about again for 30 days.
    </p>

    <div v-if="error" class="form-error">{{ error }}</div>

    <div class="tile">
      <div class="controls">
        <button
          class="secondary-button"
          :disabled="running"
          type="button"
          @click="start(null)"
        >
          Fix everyone
        </button>
        <button
          class="secondary-button"
          :disabled="running"
          type="button"
          @click="scan"
        >
          Check again
        </button>
        <label class="inline">
          <input v-model="force" type="checkbox" :disabled="running" />
          Include games checked in the last 30 days
        </label>
      </div>
      <p v-if="running && run" class="last-run" aria-live="polite">
        Working on {{ run.who }}: {{ run.done }} of {{ run.total }} {{ unit }}
      </p>
      <p v-else-if="run?.error" class="form-error">{{ run.error }}</p>
      <p v-else-if="run?.finished_at" class="last-run" aria-live="polite">
        Last run: {{ run.result.checked ?? 0 }} checked.
        {{ describe(run.result) }}.
      </p>
    </div>

    <p v-if="people === null && !error" class="tile-desc">
      Reading the libraries...
    </p>
    <p v-else-if="people && !people.length" class="tile-desc">
      No libraries have any games yet.
    </p>

    <div v-for="person in people ?? []" :key="person.user_id" class="tile">
      <div class="tile-head">
        <h3>{{ person.username }}</h3>
        <div class="tile-actions">
          <button
            class="secondary-button small"
            :disabled="running"
            title="Swaps covers that are only Steam's small old copy or the image it generates for a real cover. A cover that was chosen or uploaded is left alone."
            type="button"
            @click="start(person.user_id, true)"
          >
            Replace poor Steam covers
          </button>
          <button
            class="secondary-button small"
            :disabled="running"
            type="button"
            @click="start(person.user_id)"
          >
            Fix this library
          </button>
        </div>
      </div>
      <p class="tile-desc">
        {{ person.games }} games, {{ person.to_fix }} ready to be filled
        in<template v-if="person.to_fix_forced > person.to_fix">
          ({{ person.to_fix_forced - person.to_fix }} more waiting for their 30
          days)</template
        >.
      </p>
      <div v-if="shown(person).length" class="chips">
        <button
          v-for="p in shown(person)"
          :key="p.id"
          class="chip"
          :class="{
            on: opened?.person === person && opened.problem === p.id,
            report: p.reportOnly,
          }"
          type="button"
          @click="open(person, p.id)"
        >
          {{ p.label }} <strong>{{ person.problems[p.id] }}</strong>
        </button>
      </div>
      <p v-else class="tile-desc">Nothing is missing.</p>

      <div v-if="person.offline_missing" class="offline">
        <p v-if="!offlineTotal(person)" class="tile-desc">
          Every picture is saved here, so this library can be viewed offline.
        </p>
        <template v-else>
          <p class="tile-desc">
            {{ offlineSummary(person) }}
            {{ offlineTotal(person) === 1 ? "is" : "are" }} only online and will
            not show without internet.
          </p>
          <button
            class="secondary-button small"
            :disabled="running"
            type="button"
            @click="start(person.user_id, false, true)"
          >
            Save for offline
          </button>
        </template>
      </div>

      <div class="old-files">
        <button
          class="text-button"
          type="button"
          @click="checkOldFiles(person)"
        >
          Check the old data folder
        </button>
        <template v-if="oldFor === person.user_id">
          <p v-if="oldMessage" class="tile-desc">{{ oldMessage }}</p>
          <template v-if="oldFiles">
            <p v-if="!oldFiles.folders.length" class="tile-desc">
              Nothing here is only in the old folder.
            </p>
            <template v-else>
              <p class="tile-desc">
                These are only in the old /data/games folder, so the app does
                not show them. Bringing them back copies them and leaves the
                originals.
              </p>
              <ul class="old-list">
                <li v-for="f in oldFiles.folders" :key="f.folder">
                  <strong>{{ f.title }}</strong>
                  <template v-if="f.in_trash"> (in the trash)</template>:
                  {{ oldSummary(f.files) }}
                </li>
              </ul>
              <button
                class="secondary-button small"
                type="button"
                :disabled="oldBusy"
                @click="bringBackOldFiles(person)"
              >
                {{ oldBusy ? "Copying..." : "Bring these back" }}
              </button>
            </template>
            <p v-if="oldFiles.no_game.length" class="tile-desc">
              Left alone, no matching game: {{ oldFiles.no_game.join(", ") }}.
            </p>
            <p v-if="oldFiles.map_folders" class="tile-desc">
              Saved world maps are not copied, because the app no longer has
              that feature.
            </p>
          </template>
        </template>
      </div>

      <div v-if="opened?.person === person" class="game-list">
        <p v-if="opened.games === null" class="tile-desc">Listing games...</p>
        <template v-else>
          <p class="tile-desc">
            {{ labelOf(opened.problem) }}: {{ opened.games.length }}
            {{ opened.games.length === 1 ? "game" : "games" }}
          </p>
          <ul>
            <li v-for="game in opened.games" :key="game.id" class="game-row">
              <RouterLink class="game-title" :to="`/games/${game.id}`">
                {{ game.title }}
              </RouterLink>
              <span class="game-meta">{{
                game.source || "Added by hand"
              }}</span>
              <span v-if="fixed[game.id]" class="game-meta">
                {{ fixed[game.id] }}
              </span>
              <button
                v-if="!isReportOnly(opened.problem)"
                class="secondary-button small"
                :disabled="fixing !== null || running"
                type="button"
                @click="fixGame(game)"
              >
                {{ fixing === game.id ? "Working..." : "Fix" }}
              </button>
            </li>
          </ul>
        </template>
      </div>
    </div>
  </section>
</template>

<style scoped>
.settings-section h2 {
  margin: 0 0 8px;
  padding-left: 12px;
  border-left: 3px solid var(--ui-accent);
  font-size: 1rem;
  color: var(--ui-heading);
}
.section-hint {
  color: var(--ui-dim-3);
  font-size: 0.82rem;
  line-height: 1.6;
  margin: 0 0 20px;
}
.tile {
  background: var(--ui-bg-2);
  border: 1px solid var(--ui-border);
  border-radius: 10px;
  padding: 18px 20px;
  margin-bottom: 16px;
}
.tile-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 6px;
}
.tile-head h3 {
  margin: 0;
  font-size: 0.9rem;
  color: var(--ui-heading);
}
.tile-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: flex-end;
}
.tile-desc {
  color: var(--ui-dim-3);
  font-size: 0.8rem;
  line-height: 1.5;
  margin: 0 0 12px;
}
.last-run {
  color: var(--ui-faint-2);
  font-size: 0.76rem;
  margin: 0;
}
.form-error {
  color: var(--ui-danger-bright);
  font-size: 0.8rem;
  margin: 10px 0 12px;
}
.controls {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
  margin-bottom: 10px;
}
.inline {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.82rem;
  color: var(--ui-text-strong);
}
.secondary-button {
  background: var(--ui-surface);
  border: 1px solid var(--ui-border);
  color: var(--ui-text-soft);
  border-radius: 8px;
  padding: 9px 16px;
  font-weight: 600;
  font-size: 0.82rem;
  cursor: pointer;
  white-space: nowrap;
}
.secondary-button:disabled {
  opacity: 0.6;
  cursor: default;
}
.small {
  padding: 5px 12px;
  font-size: 0.76rem;
}
.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.chip {
  background: var(--ui-surface);
  border: 1px solid var(--ui-border);
  border-radius: 999px;
  color: var(--ui-text-soft);
  cursor: pointer;
  font-size: 0.76rem;
  padding: 4px 12px;
}
.chip strong {
  color: var(--ui-text-strong);
  margin-left: 4px;
}
.chip.on {
  border-color: var(--ui-accent);
}
.chip.report strong {
  color: var(--ui-danger-bright);
}
.old-files,
.offline {
  margin-top: 12px;
}
.offline .tile-desc,
.old-files .tile-desc {
  margin: 8px 0;
}
.old-list {
  color: var(--ui-text-soft);
  font-size: 0.8rem;
  margin: 8px 0 10px;
  padding-left: 18px;
}
.text-button {
  background: none;
  border: 0;
  color: var(--ui-dim-3);
  cursor: pointer;
  font-size: 0.78rem;
  padding: 0;
  text-decoration: underline;
}
.game-list {
  margin-top: 14px;
}
.game-list ul {
  list-style: none;
  margin: 0;
  max-height: 360px;
  overflow-y: auto;
  padding: 0;
}
.game-row {
  align-items: center;
  border-top: 1px solid var(--ui-border);
  display: flex;
  flex-wrap: wrap;
  font-size: 0.8rem;
  gap: 6px 12px;
  padding: 6px 0;
}
.game-title {
  color: var(--ui-text-strong);
  flex: 1;
  min-width: 140px;
  overflow-wrap: anywhere;
}
.game-meta {
  color: var(--ui-dim-3);
  font-size: 0.76rem;
}
</style>
