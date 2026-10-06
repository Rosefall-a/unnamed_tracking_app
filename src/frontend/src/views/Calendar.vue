<script setup lang="ts">
import UiModal from "../components/UiModal.vue";
import AppTopBar from "../components/AppTopBar.vue";
import SegmentedTabs from "../components/SegmentedTabs.vue";
import { useCalendar } from "../composables/useCalendar";
const {
  blurOnLeave,
  tab,
  calView,
  TAB_OPTIONS,
  VIEW_OPTIONS,
  loadManualLibrary,
  filters,
  prefs,
  showGamesFilter,
  AIRING_STATUS_CHIPS,
  toggleAiringStatus,
  calLoading,
  calError,
  viewYear,
  viewMonth,
  isCurrentMonth,
  CAL_MAX_DAYS,
  canGoPrev,
  canGoNext,
  jumpMonthValue,
  jumpToMonth,
  historyEntries,
  historyLoading,
  historyError,
  refreshing,
  refreshAll,
  MONTH_NAMES,
  WEEKDAY_LABELS,
  gridCells,
  prevMonth,
  nextMonth,
  weekDays,
  weekLabel,
  isCurrentWeek,
  canWeekNext,
  canWeekPrev,
  shiftWeek,
  goToday,
  chipsFor,
  itemTooltip,
  activate,
  agendaGroups,
  longDayLabel,
  drawerKey,
  drawerItems,
  openDrawer,
  closeDrawer,
  LAYER_LABEL,
  showEventForm,
  eventId,
  eventTitle,
  eventDate,
  eventTime,
  eventNote,
  eventLink,
  eventLinkSearch,
  eventError,
  eventSaving,
  openEventForm,
  closeEventForm,
  eventLinkResults,
  pickEventLink,
  saveEvent,
  removeEvent,
  openLinkedTitle,
  showFeed,
  feedUrl,
  feedError,
  feedCopied,
  feedBusy,
  openFeed,
  copyFeed,
  regenerateFeed,
  historySearch,
  historyType,
  historyWindowDays,
  historyDayLabel,
  describeActivity,
  HISTORY_ICONS,
  groupedHistory,
  hasOlderHistory,
  openHistoryEntry,
  editingId,
  editDate,
  editCount,
  editDetail,
  editEventType,
  editMediaSearch,
  editMediaPicked,
  editChangingMedia,
  editError,
  startEdit,
  cancelEdit,
  editSearchResults,
  pickEditMedia,
  saveEdit,
  removeHistoryEntry,
  showManualForm,
  manualSearch,
  manualPicked,
  manualEventType,
  manualDate,
  manualCount,
  manualDetail,
  manualError,
  manualSaving,
  EVENT_TYPE_LABELS,
  openManualForm,
  closeManualForm,
  addEventForDrawerDay,
  logForDrawerDay,
  manualSearchResults,
  pickManualMedia,
  submitManualEntry,
} = useCalendar();
</script>

<template>
  <main class="ui-page">
    <AppTopBar>
      <SegmentedTabs
        :options="TAB_OPTIONS"
        :model-value="tab"
        aria-label="Calendar sections"
        @update:model-value="tab = $event as 'calendar' | 'history'"
      />
      <template #actions>
        <button
          v-if="tab === 'calendar'"
          type="button"
          class="ui-btn ui-btn-secondary"
          @click="openFeed"
        >
          Subscribe
        </button>
        <button
          v-if="tab === 'calendar'"
          type="button"
          class="ui-btn ui-btn-primary"
          @click="openEventForm()"
        >
          + Add Entry
        </button>
        <button
          type="button"
          class="ui-btn"
          :class="tab === 'calendar' ? 'ui-btn-secondary' : 'ui-btn-primary'"
          @click="openManualForm()"
        >
          + Log Watched
        </button>
      </template>
    </AppTopBar>

    <div class="ui-content medium">
      <div class="ui-head">
        <h1>Calendar</h1>
      </div>
      <template v-if="tab === 'calendar'">
        <div class="month-bar">
          <div v-if="calView === 'month'" class="month-nav">
            <button
              type="button"
              class="nav-btn"
              :disabled="!canGoPrev"
              @click="prevMonth"
            >
              ‹
            </button>
            <label class="month-label month-picker" title="Jump to a month">
              {{ MONTH_NAMES[viewMonth] }} {{ viewYear }}
              <input
                type="month"
                :value="jumpMonthValue"
                @change="jumpToMonth"
              />
            </label>
            <button
              type="button"
              class="nav-btn"
              :disabled="!canGoNext"
              @click="nextMonth"
            >
              ›
            </button>
          </div>
          <div v-else-if="calView === 'week'" class="month-nav">
            <button
              type="button"
              class="nav-btn"
              :disabled="!canWeekPrev"
              aria-label="Previous week"
              @click="shiftWeek(-1)"
            >
              ‹
            </button>
            <span class="month-label">{{ weekLabel }}</span>
            <button
              type="button"
              class="nav-btn"
              :disabled="!canWeekNext"
              aria-label="Next week"
              @click="shiftWeek(1)"
            >
              ›
            </button>
          </div>
          <div v-else class="month-nav">
            <span class="month-label agenda-label"
              >Next {{ CAL_MAX_DAYS }} days</span
            >
          </div>
          <div class="month-bar-actions">
            <SegmentedTabs
              :options="VIEW_OPTIONS"
              :model-value="calView"
              aria-label="Calendar view"
              @update:model-value="
                calView = $event as 'month' | 'week' | 'agenda'
              "
            />
            <button
              type="button"
              class="refresh-btn"
              :class="{ spinning: refreshing }"
              title="Refresh"
              :disabled="refreshing"
              @click="refreshAll"
            >
              <svg
                viewBox="0 0 24 24"
                width="14"
                height="14"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
              >
                <path d="M21 12a9 9 0 1 1-2.64-6.36" />
                <polyline points="21 4 21 10 15 10" />
              </svg>
            </button>
            <button
              type="button"
              class="ui-btn ui-btn-sm ui-btn-secondary"
              :class="{ 'is-hidden': calView === 'agenda' }"
              :aria-hidden="calView === 'agenda'"
              :tabindex="calView === 'agenda' ? -1 : undefined"
              :disabled="
                calView === 'agenda' ||
                (calView === 'month' ? isCurrentMonth : isCurrentWeek)
              "
              title="Jump to today (T)"
              @click="goToday"
            >
              Today
            </button>
          </div>
        </div>

        <div class="filter-row">
          <div class="filter-group">
            <button
              type="button"
              class="ui-chip"
              :class="{ on: filters.movie }"
              @click="filters.movie = !filters.movie"
            >
              Movies
            </button>
            <button
              type="button"
              class="ui-chip"
              :class="{ on: filters.tv }"
              @click="filters.tv = !filters.tv"
            >
              TV
            </button>
            <button
              type="button"
              class="ui-chip"
              :class="{ on: filters.anime }"
              @click="filters.anime = !filters.anime"
            >
              Anime
            </button>
            <button
              v-if="showGamesFilter"
              type="button"
              class="ui-chip"
              :class="{ on: filters.game }"
              @click="filters.game = !filters.game"
            >
              Games
            </button>
          </div>
          <div class="filter-group">
            <button
              type="button"
              class="ui-chip layer-episode"
              :class="{ on: filters.episode }"
              @click="filters.episode = !filters.episode"
            >
              <span class="swatch"></span>Airing
            </button>
            <button
              type="button"
              class="ui-chip layer-release"
              :class="{ on: filters.release }"
              @click="filters.release = !filters.release"
            >
              <span class="swatch"></span>Releases
            </button>
            <button
              type="button"
              class="ui-chip layer-watched"
              :class="{ on: filters.watched }"
              @click="filters.watched = !filters.watched"
            >
              <span class="swatch"></span>Watched
            </button>
            <button
              type="button"
              class="ui-chip layer-event"
              :class="{ on: filters.event }"
              title="Entries you added yourself"
              @click="filters.event = !filters.event"
            >
              <span class="swatch"></span>My entries
            </button>
            <button
              v-if="prefs.calendar_show_estimated"
              type="button"
              class="ui-chip layer-estimated"
              :class="{ on: filters.estimated }"
              title="Episodes projected from the weekly airing pattern, not confirmed dates"
              @click="filters.estimated = !filters.estimated"
            >
              <span class="swatch"></span>Estimated
            </button>
          </div>
          <div class="filter-group" role="group" aria-label="Airing shows">
            <span class="filter-caption">Airing shows</span>
            <button
              v-for="chip in AIRING_STATUS_CHIPS"
              :key="chip.key"
              type="button"
              class="ui-chip"
              :class="{ on: prefs.calendar_airing_statuses.includes(chip.key) }"
              :title="`Show airing episodes for titles on ${chip.label}`"
              @click="toggleAiringStatus(chip.key)"
            >
              {{ chip.label }}
            </button>
          </div>
        </div>

        <p v-if="calError" class="ui-state error">{{ calError }}</p>

        <template v-if="calView === 'month'">
          <div class="weekday-row">
            <span v-for="w in WEEKDAY_LABELS" :key="w">{{ w }}</span>
          </div>
          <div class="month-grid" :class="{ loading: calLoading }">
            <button
              v-for="cell in gridCells"
              :key="cell.key"
              type="button"
              class="day-cell"
              :class="{
                'out-of-month': !cell.inMonth,
                today: cell.isToday,
                past: cell.isPast,
              }"
              @click="openDrawer(cell)"
            >
              <span class="day-number">{{ cell.day }}</span>
              <span class="day-chips">
                <span
                  v-for="i in chipsFor(cell).shown"
                  :key="i.key"
                  class="chip"
                  :class="[`layer-${i.layer}`, { projected: i.projected }]"
                  :title="itemTooltip(i)"
                >
                  <img
                    v-if="i.posterUrl"
                    :src="i.posterUrl"
                    alt=""
                    loading="lazy"
                  />
                  <span v-else class="chip-fallback">{{
                    i.title.slice(0, 1)
                  }}</span>
                  <span v-if="i.badge" class="chip-badge">{{ i.badge }}</span>
                </span>
                <span v-if="chipsFor(cell).more" class="chip chip-more"
                  >+{{ chipsFor(cell).more }}</span
                >
              </span>
            </button>
          </div>
        </template>

        <template v-else-if="calView === 'week'">
          <div class="week-grid" :class="{ loading: calLoading }">
            <section
              v-for="d in weekDays"
              :key="d.key"
              class="week-day"
              :class="{ today: d.isToday, past: d.isPast }"
            >
              <header class="week-day-head">
                <span>{{ d.label }}</span>
                <button
                  type="button"
                  class="week-add"
                  title="Add an entry on this day"
                  @click="openEventForm(d.key)"
                >
                  +
                </button>
              </header>
              <p v-if="!d.items.length" class="week-empty">Nothing</p>
              <button
                v-for="i in d.items"
                :key="i.key"
                type="button"
                class="agenda-row"
                :class="[`layer-${i.layer}`, { projected: i.projected }]"
                :title="i.title"
                @click="activate(i)"
              >
                <span class="agenda-thumb">
                  <img
                    v-if="i.posterUrl"
                    :src="i.posterUrl"
                    alt=""
                    loading="lazy"
                  />
                </span>
                <span class="agenda-main">
                  <span class="agenda-title">{{ i.title }}</span>
                  <span class="agenda-detail">{{ i.detail }}</span>
                </span>
              </button>
            </section>
          </div>
        </template>

        <template v-else>
          <p v-if="!agendaGroups.length && !calLoading" class="ui-state">
            Nothing scheduled in the next {{ CAL_MAX_DAYS }} days with these
            filters.
          </p>
          <div v-else class="agenda">
            <div v-for="g in agendaGroups" :key="g.key" class="agenda-day">
              <div class="day-heading">{{ longDayLabel(g.key) }}</div>
              <button
                v-for="i in g.items"
                :key="i.key"
                type="button"
                class="agenda-row"
                :class="[`layer-${i.layer}`, { projected: i.projected }]"
                :title="i.title"
                @click="activate(i)"
              >
                <span class="agenda-thumb">
                  <img
                    v-if="i.posterUrl"
                    :src="i.posterUrl"
                    alt=""
                    loading="lazy"
                  />
                </span>
                <span class="agenda-main">
                  <span class="agenda-title">{{ i.title }}</span>
                  <span class="agenda-detail">{{ i.detail }}</span>
                </span>
                <span class="agenda-tag">{{ LAYER_LABEL[i.layer] }}</span>
              </button>
            </div>
          </div>
        </template>
      </template>

      <template v-else>
        <div class="history-filters">
          <input
            v-model="historySearch"
            type="text"
            class="ui-field history-search"
            placeholder="Search history…"
          />
          <select v-model="historyType" class="ui-field history-type">
            <option value="all">Everything</option>
            <option
              v-for="(label, key) in EVENT_TYPE_LABELS"
              :key="key"
              :value="key"
            >
              {{ label }}
            </option>
          </select>
        </div>
        <p v-if="historyLoading" class="ui-state">Loading…</p>
        <p v-else-if="historyError" class="ui-state error">
          {{ historyError }}
        </p>
        <p
          v-else-if="!groupedHistory.length && historyEntries.length"
          class="ui-state"
        >
          Nothing matches the search and filters.
        </p>
        <p v-else-if="!groupedHistory.length" class="ui-state">
          Nothing logged yet. Checking off episodes or changing a status will
          show up here.
        </p>
        <div v-else class="days">
          <div
            v-for="[key, dayEntries] in groupedHistory"
            :key="key"
            class="day-group"
          >
            <div class="day-heading">{{ historyDayLabel(key) }}</div>
            <template v-for="entry in dayEntries" :key="entry.id">
              <div v-if="editingId === entry.id" class="entry-edit-row">
                <div class="entry-edit-title-row">
                  <template v-if="editChangingMedia">
                    <div class="entry-edit-title-search">
                      <input
                        v-model="editMediaSearch"
                        type="text"
                        placeholder="Search your library…"
                        class="entry-edit-detail"
                        @input="editMediaPicked = null"
                      />
                      <div
                        v-if="editSearchResults.length"
                        class="modal-search-results"
                      >
                        <button
                          v-for="m in editSearchResults"
                          :key="`${m.mediaType}-${m.mediaId}`"
                          type="button"
                          class="modal-search-result"
                          @click="pickEditMedia(m)"
                        >
                          {{ m.title }}
                          <span class="modal-search-kind">{{
                            m.mediaType
                          }}</span>
                        </button>
                      </div>
                    </div>
                  </template>
                  <template v-else>
                    <span class="entry-edit-title">{{
                      editMediaPicked?.title
                    }}</span>
                    <button
                      type="button"
                      class="entry-change-title-btn"
                      @click="
                        editChangingMedia = true;
                        loadManualLibrary();
                      "
                    >
                      Change title
                    </button>
                  </template>
                </div>
                <div class="entry-edit-fields">
                  <select v-model="editEventType" class="entry-edit-type">
                    <option
                      v-for="(label, key) in EVENT_TYPE_LABELS"
                      :key="key"
                      :value="key"
                    >
                      {{ label }}
                    </option>
                  </select>
                  <input
                    v-model="editDate"
                    type="date"
                    class="entry-edit-date"
                  />
                  <input
                    v-model.number="editCount"
                    type="number"
                    min="1"
                    class="entry-edit-count"
                  />
                  <input
                    v-model="editDetail"
                    type="text"
                    placeholder="Note (optional)"
                    class="entry-edit-detail"
                  />
                </div>
                <p v-if="editError" class="ui-error-box">{{ editError }}</p>
                <div class="entry-edit-actions">
                  <button
                    type="button"
                    class="entry-save-btn"
                    @click="saveEdit(entry)"
                  >
                    Save
                  </button>
                  <button
                    type="button"
                    class="entry-cancel-btn"
                    @click="cancelEdit"
                  >
                    Cancel
                  </button>
                </div>
              </div>
              <div
                v-else
                class="entry-row"
                :class="entry.eventType"
                @click="openHistoryEntry(entry)"
                @mouseleave="blurOnLeave"
              >
                <span class="entry-icon">{{
                  HISTORY_ICONS[entry.eventType]
                }}</span>
                <span class="entry-text">{{ describeActivity(entry) }}</span>
                <span class="entry-actions">
                  <button
                    type="button"
                    class="entry-action-btn"
                    title="Edit"
                    @click.stop="startEdit(entry)"
                  >
                    ✎
                  </button>
                  <button
                    type="button"
                    class="entry-action-btn"
                    title="Delete"
                    @click.stop="removeHistoryEntry(entry)"
                  >
                    ×
                  </button>
                </span>
              </div>
            </template>
          </div>
          <button
            v-if="hasOlderHistory"
            type="button"
            class="secondary-button older-btn"
            @click="historyWindowDays += 90"
          >
            Show Older
          </button>
        </div>
      </template>
    </div>

    <Teleport to="body">
      <div v-if="drawerKey" class="drawer-backdrop" @click.self="closeDrawer">
        <aside class="drawer" role="dialog" aria-label="Day details">
          <div class="drawer-head">
            <h3>{{ longDayLabel(drawerKey) }}</h3>
            <button
              type="button"
              class="drawer-close"
              title="Close"
              @click="closeDrawer"
            >
              ×
            </button>
          </div>
          <p v-if="!drawerItems.length" class="drawer-empty">
            Nothing on this day with the current filters.
          </p>
          <div v-else class="drawer-list">
            <button
              v-for="i in drawerItems"
              :key="i.key"
              type="button"
              class="agenda-row"
              :class="[`layer-${i.layer}`, { projected: i.projected }]"
              @click="activate(i)"
            >
              <span class="agenda-thumb">
                <img
                  v-if="i.posterUrl"
                  :src="i.posterUrl"
                  alt=""
                  loading="lazy"
                />
              </span>
              <span class="agenda-main">
                <span class="agenda-title">{{ i.title }}</span>
                <span class="agenda-detail">{{ i.detail }}</span>
              </span>
              <span class="agenda-tag">{{ LAYER_LABEL[i.layer] }}</span>
            </button>
          </div>
          <div class="drawer-foot">
            <button
              type="button"
              class="ui-btn ui-btn-primary"
              @click="addEventForDrawerDay"
            >
              Add an entry
            </button>
            <button
              type="button"
              class="ui-btn ui-btn-secondary"
              @click="logForDrawerDay"
            >
              Log something watched
            </button>
          </div>
        </aside>
      </div>
    </Teleport>

    <UiModal
      v-if="showFeed"
      title="Subscribe in your calendar app"
      @close="showFeed = false"
    >
      <p class="modal-hint">
        Paste this link into Google Calendar (Other calendars, From URL), Apple
        Calendar or Outlook and every airing episode and release shows up there,
        kept up to date. Anyone with the link can see your schedule, so treat it
        like a password. The app has to be reachable from the internet for
        Google Calendar to fetch it.
      </p>
      <input
        class="ui-field"
        type="text"
        readonly
        aria-label="Calendar subscription link"
        :value="feedUrl"
        placeholder="Loading…"
        @focus="($event.target as HTMLInputElement).select()"
      />
      <p v-if="feedError" class="ui-error-box feed-error">{{ feedError }}</p>
      <div class="ui-modal-actions">
        <button
          type="button"
          class="ui-btn ui-btn-secondary"
          :disabled="feedBusy"
          @click="regenerateFeed"
        >
          New link
        </button>
        <button
          type="button"
          class="ui-btn ui-btn-primary"
          :disabled="!feedUrl"
          @click="copyFeed"
        >
          {{ feedCopied ? "Copied" : "Copy link" }}
        </button>
      </div>
    </UiModal>

    <UiModal
      v-if="showEventForm"
      :title="eventId ? 'Edit entry' : 'Add a calendar entry'"
      size="wide"
      :dismissible="!eventSaving"
      @close="closeEventForm"
    >
      <p class="modal-hint">
        For anything the sources do not list: a premiere date, a watch party, a
        reminder. It only appears here and in your calendar feed.
      </p>
      <label class="modal-field">
        <span>Title</span>
        <input
          v-model="eventTitle"
          type="text"
          class="ui-field"
          maxlength="200"
          placeholder="e.g. Dune Part 3 premiere"
        />
      </label>
      <div class="modal-field-row">
        <label class="modal-field">
          <span>Date</span>
          <input v-model="eventDate" type="date" class="ui-field" />
        </label>
        <label class="modal-field">
          <span>Time (optional)</span>
          <input v-model="eventTime" type="time" class="ui-field" />
        </label>
      </div>
      <label class="modal-field">
        <span>Related title (optional)</span>
        <input
          v-model="eventLinkSearch"
          type="text"
          class="ui-field"
          placeholder="Search your library…"
          @input="eventLink = null"
        />
        <div v-if="eventLinkResults.length" class="modal-search-results">
          <button
            v-for="m in eventLinkResults"
            :key="`${m.mediaType}-${m.mediaId}`"
            type="button"
            class="modal-search-result"
            @click="pickEventLink(m)"
          >
            {{ m.title }}
            <span class="modal-search-kind">{{ m.mediaType }}</span>
          </button>
        </div>
      </label>
      <label class="modal-field">
        <span>Note (optional)</span>
        <input
          v-model="eventNote"
          type="text"
          class="ui-field"
          maxlength="2000"
        />
      </label>
      <p v-if="eventError" class="ui-error-box">{{ eventError }}</p>
      <div class="ui-modal-actions">
        <button
          v-if="eventId"
          type="button"
          class="ui-btn ui-btn-danger"
          @click="removeEvent"
        >
          Delete
        </button>
        <button
          v-if="eventLink"
          type="button"
          class="ui-btn ui-btn-secondary"
          @click="openLinkedTitle"
        >
          Open title
        </button>
        <button
          type="button"
          class="ui-btn ui-btn-secondary"
          @click="closeEventForm"
        >
          Cancel
        </button>
        <button
          type="button"
          class="ui-btn ui-btn-primary"
          :disabled="eventSaving"
          @click="saveEvent"
        >
          {{ eventSaving ? "Saving…" : "Save" }}
        </button>
      </div>
    </UiModal>

    <UiModal
      v-if="showManualForm"
      title="Log a history entry"
      size="wide"
      :dismissible="!manualSaving"
      @close="closeManualForm"
    >
      <p class="modal-hint">
        For anything the app didn't catch automatically: watch history from
        before you added this title, or an import.
      </p>

      <label class="modal-field">
        <span>Title</span>
        <input
          v-model="manualSearch"
          type="text"
          placeholder="Search your library…"
          class="ui-field"
          @input="manualPicked = null"
        />
        <div
          v-if="manualSearchResults.length && !manualPicked"
          class="modal-search-results"
        >
          <button
            v-for="m in manualSearchResults"
            :key="`${m.mediaType}-${m.mediaId}`"
            type="button"
            class="modal-search-result"
            @click="pickManualMedia(m)"
          >
            {{ m.title }}
            <span class="modal-search-kind">{{ m.mediaType }}</span>
          </button>
        </div>
      </label>

      <label class="modal-field">
        <span>What happened</span>
        <select v-model="manualEventType" class="ui-field">
          <option
            v-for="(label, key) in EVENT_TYPE_LABELS"
            :key="key"
            :value="key"
          >
            {{ label }}
          </option>
        </select>
      </label>

      <div class="modal-field-row">
        <label class="modal-field">
          <span>Date</span>
          <input v-model="manualDate" type="date" class="ui-field" />
        </label>
        <label
          v-if="manualEventType === 'episodes_watched'"
          class="modal-field"
        >
          <span>Episodes</span>
          <input
            v-model.number="manualCount"
            type="number"
            min="1"
            class="ui-field"
          />
        </label>
      </div>

      <label class="modal-field">
        <span>Note (optional)</span>
        <input
          v-model="manualDetail"
          type="text"
          class="ui-field"
          placeholder="e.g. rewatched with friends"
        />
      </label>

      <p v-if="manualError" class="ui-error-box">{{ manualError }}</p>

      <div class="ui-modal-actions">
        <button
          type="button"
          class="ui-btn ui-btn-secondary"
          @click="closeManualForm"
        >
          Cancel
        </button>
        <button
          type="button"
          class="ui-btn ui-btn-primary"
          :disabled="manualSaving"
          @click="submitManualEntry"
        >
          {{ manualSaving ? "Logging…" : "Log entry" }}
        </button>
      </div>
    </UiModal>
  </main>
</template>

<style scoped src="../styles/pages/calendar.css" />

.month-picker input { font-family: inherit; }
