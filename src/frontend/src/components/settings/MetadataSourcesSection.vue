<script setup lang="ts">
import PasswordInput from "../PasswordInput.vue";
import { useMetadataSources } from "../../composables/useMetadataSources";
const {
  SHORT_DESC,
  VISUALS,
  expanded,
  toggleExpanded,
  steamgriddbApiKey,
  saving,
  saveError,
  saveSuccess,
  saveSteamgriddbKey,
  isAdmin,
  igdbClientId,
  igdbClientSecret,
  igdbConfigured,
  igdbSaving,
  igdbError,
  tmdbApiKey,
  tmdbConfigured,
  tmdbSaving,
  tmdbError,
  omdbApiKey,
  omdbConfigured,
  omdbSaving,
  omdbError,
  keyPlaceholder,
  tvdbApiKey,
  tvdbConfigured,
  tvdbSaving,
  tvdbError,
  saveIgdbCredentials,
  clearIgdbCredentials,
  saveTmdbKey,
  clearTmdbKey,
  saveOmdbKey,
  clearOmdbKey,
  saveTvdbKey,
  clearTvdbKey,
  psnStatus,
  psnLoading,
  npssoToken,
  psnConnecting,
  psnError,
  showDisconnectConfirm,
  handleConnectPsn,
  confirmDisconnectPsn,
  PROVIDER_CARDS,
  credentialStatus,
  fieldValues,
  cardSaving,
  cardError,
  cardInfo,
  credentialsLoading,
  passwordPlaceholder,
  statusLabel,
  statusClass,
  saveCard,
  clearCard,
  librarySyncing,
  handleSyncLibrary,
  formatLastSynced,
  hltbEnabled,
  hltbLoading,
  hltbSaving,
  hltbError,
  toggleHltb,
} = useMetadataSources();
</script>

<template>
  <section class="settings-section">
    <h2>Metadata/API</h2>
    <p class="section-hint">
      Providers used to search for and fill in game metadata and art, plus
      achievement/account connections. Click a tile's key icon to configure it:
      hover a name for details.
    </p>
    <p class="section-hint">
      Keys saved here are yours alone. An administrator can also set server-wide
      keys under Settings &rsaquo; Server Integrations; those are used for
      anyone without their own, shown here as "Using server key". A key of your
      own always takes precedence for your account.
    </p>

    <h3 class="group-heading">Metadata</h3>

    <div class="source-grid">
      <!-- SteamGridDB -->
      <div class="source-tile">
        <div
          class="tile-icon"
          :style="{
            background: VISUALS.SteamGridDB.bg,
            color: VISUALS.SteamGridDB.fg,
          }"
        >
          {{ VISUALS.SteamGridDB.mark }}
        </div>
        <div class="tile-body">
          <span
            class="tile-name"
            title="Cover art and hero banners. Your own key, used instead of the server's for your account."
            >SteamGridDB</span
          >
          <span
            class="tile-status"
            :class="
              steamgriddbApiKey
                ? 'connected'
                : credentialStatus.SteamGridDB?.server_configured
                  ? 'saved'
                  : 'disconnected'
            "
          >
            {{
              steamgriddbApiKey
                ? "Configured"
                : credentialStatus.SteamGridDB?.server_configured
                  ? "Using server key"
                  : "Not configured"
            }}
          </span>
        </div>
        <p class="tile-desc">{{ SHORT_DESC.SteamGridDB }}</p>
        <div class="tile-actions">
          <button
            type="button"
            class="icon-btn"
            :class="{ active: expanded.SteamGridDB }"
            title="Configure"
            @click="toggleExpanded('SteamGridDB')"
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
              <path
                d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"
              />
            </svg>
          </button>
          <a
            class="icon-btn"
            href="https://www.steamgriddb.com/profile/preferences/api"
            target="_blank"
            rel="noopener noreferrer"
            title="Get a free key"
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
              <circle cx="12" cy="12" r="10" />
              <path
                d="M2 12h20M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"
              />
            </svg>
          </a>
        </div>
        <form
          v-if="expanded.SteamGridDB"
          class="tile-form"
          @submit.prevent="saveSteamgriddbKey"
        >
          <label class="field">
            <span>API Key</span>
            <PasswordInput
              v-model="steamgriddbApiKey"
              placeholder="Paste your SteamGridDB API key"
            />
          </label>
          <div v-if="saveError" class="form-error">{{ saveError }}</div>
          <div v-if="saveSuccess" class="form-success">Settings saved.</div>
          <button type="submit" class="primary-button" :disabled="saving">
            {{ saving ? "Saving…" : "Save" }}
          </button>
        </form>
      </div>

      <!-- IGDB: deployment-wide, admin-only credentials -->
      <div class="source-tile">
        <div
          class="tile-icon"
          :style="{ background: VISUALS.IGDB.bg, color: VISUALS.IGDB.fg }"
        >
          {{ VISUALS.IGDB.mark }}
        </div>
        <div class="tile-body">
          <span class="tile-name" :title="PROVIDER_CARDS.IGDB.description"
            >IGDB</span
          >
          <span
            v-if="!credentialsLoading"
            class="tile-status"
            :class="statusClass('IGDB')"
            >{{ statusLabel("IGDB") }}</span
          >
        </div>
        <p class="tile-desc">{{ SHORT_DESC.IGDB }}</p>
        <div class="tile-actions">
          <button
            v-if="isAdmin"
            type="button"
            class="icon-btn"
            :class="{ active: expanded.IGDB }"
            title="Configure (admin only)"
            @click="toggleExpanded('IGDB')"
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
              <path
                d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"
              />
            </svg>
          </button>
        </div>
        <p v-if="!isAdmin" class="tile-desc admin-note">
          Configured deployment-wide by your server administrator.
        </p>
        <form
          v-if="isAdmin && expanded.IGDB"
          class="tile-form"
          @submit.prevent="saveIgdbCredentials"
        >
          <p class="tile-desc admin-note">
            Applies to every user on this server, not just you. Register a free
            app at
            <a
              href="https://dev.twitch.tv/console/apps"
              target="_blank"
              rel="noopener noreferrer"
              >dev.twitch.tv/console/apps</a
            >.
          </p>
          <label class="field">
            <span>Client ID</span>
            <input
              v-model="igdbClientId"
              type="text"
              autocomplete="off"
              placeholder="Paste your Twitch Client ID"
            />
          </label>
          <label class="field">
            <span>Client Secret</span>
            <PasswordInput
              v-model="igdbClientSecret"
              :placeholder="
                keyPlaceholder(
                  'igdb_client_secret',
                  igdbConfigured,
                  'Paste your Twitch Client Secret',
                )
              "
            />
          </label>
          <div v-if="igdbError" class="form-error">{{ igdbError }}</div>
          <div class="card-actions">
            <button type="submit" class="primary-button" :disabled="igdbSaving">
              {{ igdbSaving ? "Saving…" : "Save" }}
            </button>
            <button
              v-if="igdbConfigured"
              type="button"
              class="secondary-button"
              @click="clearIgdbCredentials"
            >
              Disconnect
            </button>
          </div>
        </form>
      </div>

      <!-- TMDB: deployment-wide, admin-only credentials -->
      <div class="source-tile">
        <div
          class="tile-icon"
          :style="{ background: VISUALS.TMDB.bg, color: VISUALS.TMDB.fg }"
        >
          {{ VISUALS.TMDB.mark }}
        </div>
        <div class="tile-body">
          <span class="tile-name" :title="PROVIDER_CARDS.TMDB.description"
            >TMDB</span
          >
          <span
            v-if="!credentialsLoading"
            class="tile-status"
            :class="statusClass('TMDB')"
            >{{ statusLabel("TMDB") }}</span
          >
        </div>
        <p class="tile-desc">{{ SHORT_DESC.TMDB }}</p>
        <div class="tile-actions">
          <button
            v-if="isAdmin"
            type="button"
            class="icon-btn"
            :class="{ active: expanded.TMDB }"
            title="Configure (admin only)"
            @click="toggleExpanded('TMDB')"
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
              <path
                d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"
              />
            </svg>
          </button>
        </div>
        <p v-if="!isAdmin" class="tile-desc admin-note">
          Configured deployment-wide by your server administrator.
        </p>
        <form
          v-if="isAdmin && expanded.TMDB"
          class="tile-form"
          @submit.prevent="saveTmdbKey"
        >
          <p class="tile-desc admin-note">
            Applies to every user on this server, not just you. Register a free
            key at
            <a
              href="https://www.themoviedb.org/settings/api"
              target="_blank"
              rel="noopener noreferrer"
              >themoviedb.org/settings/api</a
            >.
          </p>
          <label class="field">
            <span>API Key</span>
            <PasswordInput
              v-model="tmdbApiKey"
              :placeholder="
                keyPlaceholder(
                  'tmdb_api_key',
                  tmdbConfigured,
                  'Paste your TMDB API key',
                )
              "
            />
          </label>
          <div v-if="tmdbError" class="form-error">{{ tmdbError }}</div>
          <div class="card-actions">
            <button type="submit" class="primary-button" :disabled="tmdbSaving">
              {{ tmdbSaving ? "Saving…" : "Save" }}
            </button>
            <button
              v-if="tmdbConfigured"
              type="button"
              class="secondary-button"
              @click="clearTmdbKey"
            >
              Disconnect
            </button>
          </div>
        </form>
      </div>

      <!-- OMDb: deployment-wide, admin-only credentials -->
      <div class="source-tile">
        <div
          class="tile-icon"
          :style="{ background: VISUALS.OMDb.bg, color: VISUALS.OMDb.fg }"
        >
          {{ VISUALS.OMDb.mark }}
        </div>
        <div class="tile-body">
          <span class="tile-name" :title="PROVIDER_CARDS.OMDb.description"
            >OMDb</span
          >
          <span
            v-if="!credentialsLoading"
            class="tile-status"
            :class="statusClass('OMDb')"
            >{{ statusLabel("OMDb") }}</span
          >
        </div>
        <p class="tile-desc">{{ SHORT_DESC.OMDb }}</p>
        <div class="tile-actions">
          <button
            v-if="isAdmin"
            type="button"
            class="icon-btn"
            :class="{ active: expanded.OMDb }"
            title="Configure (admin only)"
            @click="toggleExpanded('OMDb')"
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
              <path
                d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"
              />
            </svg>
          </button>
        </div>
        <p v-if="!isAdmin" class="tile-desc admin-note">
          Configured deployment-wide by your server administrator.
        </p>
        <form
          v-if="isAdmin && expanded.OMDb"
          class="tile-form"
          @submit.prevent="saveOmdbKey"
        >
          <p class="tile-desc admin-note">
            Applies to every user on this server, not just you. Register a free
            key at
            <a
              href="https://www.omdbapi.com/apikey.aspx"
              target="_blank"
              rel="noopener noreferrer"
              >omdbapi.com/apikey.aspx</a
            >.
          </p>
          <label class="field">
            <span>API Key</span>
            <PasswordInput
              v-model="omdbApiKey"
              :placeholder="
                keyPlaceholder(
                  'omdb_api_key',
                  omdbConfigured,
                  'Paste your OMDb API key',
                )
              "
            />
          </label>
          <div v-if="omdbError" class="form-error">{{ omdbError }}</div>
          <div class="card-actions">
            <button type="submit" class="primary-button" :disabled="omdbSaving">
              {{ omdbSaving ? "Saving…" : "Save" }}
            </button>
            <button
              v-if="omdbConfigured"
              type="button"
              class="secondary-button"
              @click="clearOmdbKey"
            >
              Disconnect
            </button>
          </div>
        </form>
      </div>

      <!-- TVDB: deployment-wide, admin-only credentials -->
      <div class="source-tile">
        <div
          class="tile-icon"
          :style="{ background: VISUALS.TVDB.bg, color: VISUALS.TVDB.fg }"
        >
          {{ VISUALS.TVDB.mark }}
        </div>
        <div class="tile-body">
          <span class="tile-name" :title="PROVIDER_CARDS.TVDB.description"
            >TheTVDB</span
          >
          <span
            v-if="!credentialsLoading"
            class="tile-status"
            :class="statusClass('TVDB')"
            >{{ statusLabel("TVDB") }}</span
          >
        </div>
        <p class="tile-desc">{{ SHORT_DESC.TVDB }}</p>
        <div class="tile-actions">
          <button
            v-if="isAdmin"
            type="button"
            class="icon-btn"
            :class="{ active: expanded.TVDB }"
            title="Configure (admin only)"
            @click="toggleExpanded('TVDB')"
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
              <path
                d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"
              />
            </svg>
          </button>
        </div>
        <p v-if="!isAdmin" class="tile-desc admin-note">
          Configured deployment-wide by your server administrator.
        </p>
        <form
          v-if="isAdmin && expanded.TVDB"
          class="tile-form"
          @submit.prevent="saveTvdbKey"
        >
          <p class="tile-desc admin-note">
            Applies to every user on this server, not just you. Register a free
            key at
            <a
              href="https://thetvdb.com/api-information"
              target="_blank"
              rel="noopener noreferrer"
              >thetvdb.com/api-information</a
            >.
          </p>
          <label class="field">
            <span>API Key</span>
            <PasswordInput
              v-model="tvdbApiKey"
              :placeholder="
                keyPlaceholder(
                  'tvdb_api_key',
                  tvdbConfigured,
                  'Paste your TVDB API key',
                )
              "
            />
          </label>
          <div v-if="tvdbError" class="form-error">{{ tvdbError }}</div>
          <div class="card-actions">
            <button type="submit" class="primary-button" :disabled="tvdbSaving">
              {{ tvdbSaving ? "Saving…" : "Save" }}
            </button>
            <button
              v-if="tvdbConfigured"
              type="button"
              class="secondary-button"
              @click="clearTvdbKey"
            >
              Disconnect
            </button>
          </div>
        </form>
      </div>

      <!-- generic wired-provider tiles -->
      <div
        v-for="key in ['GiantBomb', 'ScreenScraper']"
        :key="key"
        class="source-tile"
      >
        <div
          class="tile-icon"
          :style="{ background: VISUALS[key].bg, color: VISUALS[key].fg }"
        >
          {{ VISUALS[key].mark }}
        </div>
        <div class="tile-body">
          <span class="tile-name" :title="PROVIDER_CARDS[key].description">{{
            PROVIDER_CARDS[key].label
          }}</span>
          <span
            v-if="!credentialsLoading"
            class="tile-status"
            :class="statusClass(key)"
            >{{ statusLabel(key) }}</span
          >
        </div>
        <p class="tile-desc">{{ SHORT_DESC[key] }}</p>
        <div class="tile-actions">
          <button
            v-if="PROVIDER_CARDS[key].fields.length"
            type="button"
            class="icon-btn"
            :class="{ active: expanded[key] }"
            title="Configure"
            @click="toggleExpanded(key)"
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
              <path
                d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"
              />
            </svg>
          </button>
          <a
            v-if="PROVIDER_CARDS[key].linkUrl"
            class="icon-btn"
            :href="PROVIDER_CARDS[key].linkUrl"
            target="_blank"
            rel="noopener noreferrer"
            title="Get a free key"
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
              <circle cx="12" cy="12" r="10" />
              <path
                d="M2 12h20M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"
              />
            </svg>
          </a>
        </div>
        <form
          v-if="expanded[key] && PROVIDER_CARDS[key].fields.length"
          class="tile-form"
          @submit.prevent="saveCard(PROVIDER_CARDS[key])"
        >
          <label
            v-for="field in PROVIDER_CARDS[key].fields"
            :key="field.key"
            class="field"
          >
            <span>{{ field.label }}</span>
            <PasswordInput
              v-if="field.type === 'password'"
              v-model="fieldValues[key][field.key]"
              :placeholder="passwordPlaceholder(key, field.key, field.label)"
            />
            <input
              v-else
              v-model="fieldValues[key][field.key]"
              type="text"
              autocomplete="off"
              :placeholder="`Paste your ${field.label.toLowerCase()}`"
            />
          </label>
          <div v-if="cardError[key]" class="form-error">
            {{ cardError[key] }}
          </div>
          <div class="card-actions">
            <button
              type="submit"
              class="primary-button"
              :disabled="cardSaving[key]"
            >
              {{ cardSaving[key] ? "Saving…" : "Save" }}
            </button>
            <button
              v-if="statusClass(key) !== 'disconnected'"
              type="button"
              class="secondary-button"
              @click="clearCard(PROVIDER_CARDS[key])"
            >
              Disconnect
            </button>
          </div>
        </form>
      </div>

      <!-- GOG -->
      <div class="source-tile">
        <div
          class="tile-icon"
          :style="{ background: VISUALS.GOG.bg, color: VISUALS.GOG.fg }"
        >
          {{ VISUALS.GOG.mark }}
        </div>
        <div class="tile-body">
          <span class="tile-name" :title="PROVIDER_CARDS.GOG.description"
            >GOG</span
          >
          <span
            v-if="!credentialsLoading"
            class="tile-status"
            :class="statusClass('GOG')"
            >{{ statusLabel("GOG") }}</span
          >
        </div>
        <p class="tile-desc">{{ SHORT_DESC.GOG }}</p>
        <div class="tile-actions">
          <button
            type="button"
            class="icon-btn"
            :class="{ active: expanded.GOG }"
            title="Configure"
            @click="toggleExpanded('GOG')"
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
              <path
                d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"
              />
            </svg>
          </button>
        </div>
        <form
          v-if="expanded.GOG"
          class="tile-form"
          @submit.prevent="saveCard(PROVIDER_CARDS.GOG)"
        >
          <label
            v-for="field in PROVIDER_CARDS.GOG.fields"
            :key="field.key"
            class="field"
          >
            <span>{{ field.label }}</span>
            <PasswordInput
              v-model="fieldValues.GOG[field.key]"
              :placeholder="passwordPlaceholder('GOG', field.key, field.label)"
            />
          </label>
          <div v-if="cardError.GOG" class="form-error">{{ cardError.GOG }}</div>
          <div class="card-actions">
            <button
              type="submit"
              class="primary-button"
              :disabled="cardSaving.GOG"
            >
              {{ cardSaving.GOG ? "Saving…" : "Save" }}
            </button>
            <button
              v-if="statusClass('GOG') !== 'disconnected'"
              type="button"
              class="secondary-button"
              @click="clearCard(PROVIDER_CARDS.GOG)"
            >
              Disconnect
            </button>
          </div>
        </form>
      </div>

      <!-- LaunchBox: unavailable -->
      <div
        class="source-tile unavailable"
        title="Local Windows app with an offline XML export, not a cloud API this server can call."
      >
        <div
          class="tile-icon"
          :style="{
            background: VISUALS.LaunchBox.bg,
            color: VISUALS.LaunchBox.fg,
          }"
        >
          {{ VISUALS.LaunchBox.mark }}
        </div>
        <div class="tile-body">
          <span class="tile-name">LaunchBox</span>
          <span class="tile-status disconnected">Not available</span>
        </div>
        <p class="tile-desc">{{ SHORT_DESC.LaunchBox }}</p>
        <div class="tile-actions"></div>
      </div>
    </div>

    <h3 class="group-heading">Achievements &amp; Accounts</h3>

    <div class="source-grid">
      <!-- Steam -->
      <div class="source-tile">
        <div
          class="tile-icon"
          :style="{ background: VISUALS.Steam.bg, color: VISUALS.Steam.fg }"
        >
          {{ VISUALS.Steam.mark }}
        </div>
        <div class="tile-body">
          <span
            class="tile-name"
            title="Metadata search needs no account. Importing your library and achievements needs a Web API key + your profile."
            >Steam</span
          >
          <span
            v-if="credentialStatus.Steam?.display_name"
            class="tile-profile"
          >
            <img
              v-if="credentialStatus.Steam.avatar_url"
              :src="credentialStatus.Steam.avatar_url"
              class="tile-avatar"
              alt=""
            />
            {{ credentialStatus.Steam.display_name }}
          </span>
          <span
            v-else-if="!credentialsLoading"
            class="tile-status"
            :class="statusClass('Steam')"
            >{{ statusLabel("Steam") }}</span
          >
        </div>
        <p class="tile-desc">
          {{ formatLastSynced(credentialStatus.Steam) ?? SHORT_DESC.Steam }}
        </p>
        <div class="tile-actions">
          <button
            type="button"
            class="icon-btn"
            :class="{ active: expanded.Steam }"
            title="Connect account to import your library"
            @click="toggleExpanded('Steam')"
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
              <path
                d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"
              />
            </svg>
          </button>
        </div>
        <button
          v-if="statusClass('Steam') !== 'disconnected'"
          type="button"
          class="import-button"
          :disabled="librarySyncing.steam"
          @click="handleSyncLibrary('steam')"
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
            <path d="M23 4v6h-6M1 20v-6h6" />
            <path
              d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"
            />
          </svg>
          {{ librarySyncing.steam ? "Importing…" : "Import Library" }}
        </button>
        <form
          v-if="expanded.Steam"
          class="tile-form"
          @submit.prevent="saveCard(PROVIDER_CARDS.Steam)"
        >
          <p class="tile-hint">
            Both fields are required to import your library: your profile ID
            (after steamcommunity.com/id/, not the full link) and a Web API key.
            Your profile's game details must be set to Public.
          </p>
          <label
            v-for="field in PROVIDER_CARDS.Steam.fields"
            :key="field.key"
            class="field"
          >
            <span>{{ field.label }}</span>
            <PasswordInput
              v-if="field.type === 'password'"
              v-model="fieldValues.Steam[field.key]"
              :placeholder="
                passwordPlaceholder('Steam', field.key, field.label)
              "
            />
            <input
              v-else
              v-model="fieldValues.Steam[field.key]"
              type="text"
              autocomplete="off"
              :placeholder="`Paste your ${field.label.toLowerCase()}`"
            />
          </label>
          <div v-if="cardError.Steam" class="form-error">
            {{ cardError.Steam }}
          </div>
          <div v-if="cardInfo.Steam" class="form-success">
            {{ cardInfo.Steam }}
          </div>
          <div class="card-actions">
            <button
              type="submit"
              class="primary-button"
              :disabled="cardSaving.Steam"
            >
              {{ cardSaving.Steam ? "Connecting…" : "Connect" }}
            </button>
            <button
              v-if="statusClass('Steam') !== 'disconnected'"
              type="button"
              class="secondary-button"
              @click="clearCard(PROVIDER_CARDS.Steam)"
            >
              Disconnect
            </button>
          </div>
        </form>
      </div>

      <!-- RetroAchievements -->
      <div class="source-tile">
        <div
          class="tile-icon"
          :style="{
            background: VISUALS.RetroAchievements.bg,
            color: VISUALS.RetroAchievements.fg,
          }"
        >
          {{ VISUALS.RetroAchievements.mark }}
        </div>
        <div class="tile-body">
          <span
            class="tile-name"
            :title="PROVIDER_CARDS.RetroAchievements.description"
            >RetroAchievements</span
          >
          <span
            v-if="credentialStatus.RetroAchievements?.display_name"
            class="tile-profile"
          >
            <img
              v-if="credentialStatus.RetroAchievements.avatar_url"
              :src="credentialStatus.RetroAchievements.avatar_url"
              class="tile-avatar"
              alt=""
            />
            {{ credentialStatus.RetroAchievements.display_name }}
          </span>
          <span
            v-else-if="!credentialsLoading"
            class="tile-status"
            :class="statusClass('RetroAchievements')"
          >
            {{ statusLabel("RetroAchievements") }}
          </span>
        </div>
        <p class="tile-desc">{{ SHORT_DESC.RetroAchievements }}</p>
        <div class="tile-actions">
          <button
            type="button"
            class="icon-btn"
            :class="{ active: expanded.RetroAchievements }"
            title="Configure"
            @click="toggleExpanded('RetroAchievements')"
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
              <path
                d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"
              />
            </svg>
          </button>
          <a
            class="icon-btn"
            :href="PROVIDER_CARDS.RetroAchievements.linkUrl"
            target="_blank"
            rel="noopener noreferrer"
            title="Get a free key"
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
              <circle cx="12" cy="12" r="10" />
              <path
                d="M2 12h20M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"
              />
            </svg>
          </a>
        </div>
        <button
          v-if="statusClass('RetroAchievements') !== 'disconnected'"
          type="button"
          class="import-button"
          :disabled="librarySyncing.retroachievements"
          @click="handleSyncLibrary('retroachievements')"
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
            <path d="M23 4v6h-6M1 20v-6h6" />
            <path
              d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"
            />
          </svg>
          {{
            librarySyncing.retroachievements ? "Importing…" : "Import Library"
          }}
        </button>
        <form
          v-if="expanded.RetroAchievements"
          class="tile-form"
          @submit.prevent="saveCard(PROVIDER_CARDS.RetroAchievements)"
        >
          <label
            v-for="field in PROVIDER_CARDS.RetroAchievements.fields"
            :key="field.key"
            class="field"
          >
            <span>{{ field.label }}</span>
            <PasswordInput
              v-if="field.type === 'password'"
              v-model="fieldValues.RetroAchievements[field.key]"
              :placeholder="
                passwordPlaceholder('RetroAchievements', field.key, field.label)
              "
            />
            <input
              v-else
              v-model="fieldValues.RetroAchievements[field.key]"
              type="text"
              autocomplete="off"
              :placeholder="`Paste your ${field.label.toLowerCase()}`"
            />
          </label>
          <div v-if="cardError.RetroAchievements" class="form-error">
            {{ cardError.RetroAchievements }}
          </div>
          <div class="card-actions">
            <button
              type="submit"
              class="primary-button"
              :disabled="cardSaving.RetroAchievements"
            >
              {{ cardSaving.RetroAchievements ? "Saving…" : "Save" }}
            </button>
            <button
              v-if="statusClass('RetroAchievements') !== 'disconnected'"
              type="button"
              class="secondary-button"
              @click="clearCard(PROVIDER_CARDS.RetroAchievements)"
            >
              Disconnect
            </button>
          </div>
        </form>
      </div>

      <!-- PlayStation -->
      <div class="source-tile">
        <div
          class="tile-icon"
          :style="{
            background: VISUALS.PlayStation.bg,
            color: VISUALS.PlayStation.fg,
          }"
        >
          {{ VISUALS.PlayStation.mark }}
        </div>
        <div class="tile-body">
          <span
            class="tile-name"
            title="Unofficial npsso token flow. Also powers PSN Store data."
            >PlayStation</span
          >
          <span
            v-if="psnStatus.connected && psnStatus.display_name"
            class="tile-profile"
          >
            <img
              v-if="psnStatus.avatar_url"
              :src="psnStatus.avatar_url"
              class="tile-avatar"
              alt=""
            />
            {{ psnStatus.display_name }}
          </span>
          <span
            v-else-if="!psnLoading"
            class="tile-status"
            :class="psnStatus.connected ? 'connected' : 'disconnected'"
          >
            {{ psnStatus.connected ? "Connected" : "Not connected" }}
          </span>
        </div>
        <p class="tile-desc">{{ SHORT_DESC.PlayStation }}</p>
        <div class="tile-actions">
          <button
            type="button"
            class="icon-btn"
            :class="{ active: expanded.PlayStation }"
            title="Configure"
            @click="toggleExpanded('PlayStation')"
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
              <path
                d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"
              />
            </svg>
          </button>
          <a
            class="icon-btn"
            href="https://www.playstation.com"
            target="_blank"
            rel="noopener noreferrer"
            title="playstation.com"
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
              <circle cx="12" cy="12" r="10" />
              <path
                d="M2 12h20M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"
              />
            </svg>
          </a>
        </div>
        <button
          v-if="psnStatus.connected"
          type="button"
          class="import-button"
          :disabled="librarySyncing.psn"
          @click="handleSyncLibrary('psn')"
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
            <path d="M23 4v6h-6M1 20v-6h6" />
            <path
              d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"
            />
          </svg>
          {{ librarySyncing.psn ? "Importing…" : "Import Library" }}
        </button>
        <div v-if="expanded.PlayStation" class="tile-form">
          <template v-if="!psnLoading">
            <template v-if="!psnStatus.connected">
              <label class="field">
                <span>npsso token</span>
                <PasswordInput
                  v-model="npssoToken"
                  placeholder="Paste your npsso token"
                />
              </label>
              <div v-if="psnError" class="form-error">{{ psnError }}</div>
              <button
                type="button"
                class="primary-button"
                :disabled="psnConnecting"
                @click="handleConnectPsn"
              >
                {{ psnConnecting ? "Connecting…" : "Connect" }}
              </button>
            </template>
            <template v-else>
              <p class="tile-hint">
                Connected: reconnect with a fresh token to re-check it.
              </p>
              <div v-if="psnError" class="form-error">{{ psnError }}</div>
              <button
                type="button"
                class="secondary-button"
                @click="showDisconnectConfirm = true"
              >
                Disconnect
              </button>
            </template>
          </template>
        </div>
      </div>

      <!-- Xbox -->
      <div class="source-tile">
        <div
          class="tile-icon"
          :style="{ background: VISUALS.Xbox.bg, color: VISUALS.Xbox.fg }"
        >
          {{ VISUALS.Xbox.mark }}
        </div>
        <div class="tile-body">
          <span class="tile-name" :title="PROVIDER_CARDS.Xbox.description"
            >Xbox</span
          >
          <span
            v-if="!credentialsLoading"
            class="tile-status"
            :class="statusClass('Xbox')"
            >{{ statusLabel("Xbox") }}</span
          >
        </div>
        <p class="tile-desc">{{ SHORT_DESC.Xbox }}</p>
        <div class="tile-actions">
          <button
            type="button"
            class="icon-btn"
            :class="{ active: expanded.Xbox }"
            title="Configure"
            @click="toggleExpanded('Xbox')"
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
              <path
                d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"
              />
            </svg>
          </button>
        </div>
        <form
          v-if="expanded.Xbox"
          class="tile-form"
          @submit.prevent="saveCard(PROVIDER_CARDS.Xbox)"
        >
          <label
            v-for="field in PROVIDER_CARDS.Xbox.fields"
            :key="field.key"
            class="field"
          >
            <span>{{ field.label }}</span>
            <PasswordInput
              v-if="field.type === 'password'"
              v-model="fieldValues.Xbox[field.key]"
              :placeholder="passwordPlaceholder('Xbox', field.key, field.label)"
            />
            <input
              v-else
              v-model="fieldValues.Xbox[field.key]"
              type="text"
              autocomplete="off"
              :placeholder="`Paste your ${field.label.toLowerCase()}`"
            />
          </label>
          <div v-if="cardError.Xbox" class="form-error">
            {{ cardError.Xbox }}
          </div>
          <div class="card-actions">
            <button
              type="submit"
              class="primary-button"
              :disabled="cardSaving.Xbox"
            >
              {{ cardSaving.Xbox ? "Saving…" : "Save" }}
            </button>
            <button
              v-if="statusClass('Xbox') !== 'disconnected'"
              type="button"
              class="secondary-button"
              @click="clearCard(PROVIDER_CARDS.Xbox)"
            >
              Disconnect
            </button>
          </div>
        </form>
      </div>

      <!-- HowLongToBeat -->
      <div
        class="source-tile"
        title="No key needed. HLTB's anti-bot protection can make this fail silently: that's not a bug in your setup."
      >
        <div
          class="tile-icon"
          :style="{
            background: VISUALS.HowLongToBeat.bg,
            color: VISUALS.HowLongToBeat.fg,
          }"
        >
          {{ VISUALS.HowLongToBeat.mark }}
        </div>
        <div class="tile-body">
          <span class="tile-name">HowLongToBeat</span>
          <span
            v-if="!hltbLoading"
            class="tile-status"
            :class="hltbEnabled ? 'connected' : 'disconnected'"
          >
            {{ hltbEnabled ? "Enabled" : "Disabled" }}
          </span>
        </div>
        <p class="tile-desc">{{ hltbError ?? SHORT_DESC.HowLongToBeat }}</p>
        <div class="tile-actions">
          <button
            type="button"
            class="mini-switch"
            :class="{ on: hltbEnabled }"
            role="switch"
            :aria-checked="hltbEnabled"
            :disabled="hltbLoading || hltbSaving"
            title="Enable HowLongToBeat"
            @click="toggleHltb(!hltbEnabled)"
          >
            <span class="mini-switch-knob"></span>
          </button>
        </div>
      </div>
    </div>

    <div
      v-if="showDisconnectConfirm"
      class="confirm-backdrop"
      @click.self="showDisconnectConfirm = false"
    >
      <div class="confirm-dialog">
        <h3>Disconnect PlayStation account?</h3>
        <p>You'll need to paste your npsso token again to reconnect.</p>
        <div class="confirm-actions">
          <button
            type="button"
            class="secondary-button"
            @click="showDisconnectConfirm = false"
          >
            Cancel
          </button>
          <button
            type="button"
            class="danger-button"
            @click="confirmDisconnectPsn"
          >
            Disconnect
          </button>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped src="../../styles/pages/metadata-sources.css" />
