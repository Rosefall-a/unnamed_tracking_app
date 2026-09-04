<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import ToggleButton from './ToggleButton.vue'
import { currentUser, checkAuth } from '../../state/auth'
import { updateProfile } from '../../services/auth'
import { fetchPsnStatus, connectPsn, disconnectPsn } from '../../services/psn'
import type { PsnStatus } from '../../services/psn'
import {
  fetchProviderCredentials,
  saveProviderCredentials,
  deleteProviderCredentials,
  fetchScanSettings,
  updateScanSettings,
} from '../../services/settings'
import type { ProviderCredentialStatus } from '../../services/settings'

const steamgriddbApiKey = ref(currentUser.value?.steamgriddb_api_key ?? '')
const currentPassword = ref('')
const saving = ref(false)
const saveError = ref<string | null>(null)
const saveSuccess = ref(false)

async function saveSteamgriddbKey() {
  if (!currentPassword.value) {
    saveError.value = 'Enter your current password to make changes.'
    return
  }

  saving.value = true
  saveError.value = null
  saveSuccess.value = false

  try {
    await updateProfile({
      currentPassword: currentPassword.value,
      steamgriddbApiKey: steamgriddbApiKey.value.trim(),
    })
    await checkAuth()
    currentPassword.value = ''
    saveSuccess.value = true
  } catch (err) {
    saveError.value = err instanceof Error ? err.message : 'Failed to save settings'
  } finally {
    saving.value = false
  }
}

const psnStatus = ref<PsnStatus>({ connected: false, validated_at: null })
const psnLoading = ref(true)
const npssoToken = ref('')
const psnConnecting = ref(false)
const psnError = ref<string | null>(null)
const showDisconnectConfirm = ref(false)

onMounted(async () => {
  try {
    psnStatus.value = await fetchPsnStatus()
  } finally {
    psnLoading.value = false
  }
})

async function handleConnectPsn() {
  if (!npssoToken.value.trim()) {
    psnError.value = 'Paste your npsso token first.'
    return
  }
  psnConnecting.value = true
  psnError.value = null
  try {
    psnStatus.value = await connectPsn(npssoToken.value.trim())
    npssoToken.value = ''
  } catch (err) {
    psnError.value = err instanceof Error ? err.message : 'Failed to connect PlayStation account'
  } finally {
    psnConnecting.value = false
  }
}

async function confirmDisconnectPsn() {
  await disconnectPsn()
  psnStatus.value = { connected: false, validated_at: null }
  showDisconnectConfirm.value = false
}

// --- data-driven providers ---------------------------------------------

interface ProviderFieldConfig {
  key: string
  label: string
  type: 'text' | 'password'
}

interface ProviderCardConfig {
  key: string
  label: string
  description: string
  fields: ProviderFieldConfig[]
  kind: 'wired' | 'deferred'
  linkLabel?: string
  linkUrl?: string
}

const PROVIDER_CARDS: Record<string, ProviderCardConfig> = {
  IGDB: {
    key: 'IGDB',
    label: 'IGDB',
    description:
      'General game metadata and cover art. Uses app-wide developer credentials configured by your server administrator — nothing for you to enter here.',
    fields: [],
    kind: 'wired',
  },
  RetroAchievements: {
    key: 'RetroAchievements',
    label: 'RetroAchievements',
    description: 'Retro/console game metadata and achievement data — powers both roles from one key.',
    fields: [{ key: 'api_key', label: 'API Key', type: 'password' }],
    kind: 'wired',
    linkLabel: 'Get a free key from RetroAchievements',
    linkUrl: 'https://retroachievements.org/controlpanel.php',
  },
  GiantBomb: {
    key: 'GiantBomb',
    label: 'Giant Bomb',
    description: 'General game metadata and cover art.',
    fields: [{ key: 'api_key', label: 'API Key', type: 'password' }],
    kind: 'wired',
    linkLabel: 'Get a free key from Giant Bomb',
    linkUrl: 'https://www.giantbomb.com/api/',
  },
  ScreenScraper: {
    key: 'ScreenScraper',
    label: 'ScreenScraper',
    description:
      'Retro box art and screenshots. Needs your personal screenscraper.fr account on top of the app-wide developer credentials your server administrator configures.',
    fields: [
      { key: 'ssid', label: 'Username', type: 'text' },
      { key: 'sspassword', label: 'Password', type: 'password' },
    ],
    kind: 'wired',
    linkLabel: 'Create a free ScreenScraper account',
    linkUrl: 'https://www.screenscraper.fr/membreinscription.php',
  },
  Xbox: {
    key: 'Xbox',
    label: 'Xbox',
    description:
      "Unofficial — Xbox's real API needs a full sign-in flow this page can't host yet. Saving your Azure app credentials here just gets them ready for that; nothing is pulled from Xbox yet.",
    fields: [
      { key: 'client_id', label: 'Application (client) ID', type: 'text' },
      { key: 'client_secret', label: 'Client secret', type: 'password' },
    ],
    kind: 'deferred',
  },
  GOG: {
    key: 'GOG',
    label: 'GOG',
    description: "Unofficial — GOG has no public API for third-party apps. Library data isn't pulled yet.",
    fields: [{ key: 'refresh_token', label: 'Refresh token', type: 'password' }],
    kind: 'deferred',
  },
}

const credentialStatus = reactive<Record<string, ProviderCredentialStatus>>({})
const fieldValues = reactive<Record<string, Record<string, string>>>({})
const cardSaving = reactive<Record<string, boolean>>({})
const cardError = reactive<Record<string, string | null>>({})
const credentialsLoading = ref(true)

// must be ready before first render — the template binds
// fieldValues[card.key][field.key] immediately, not just after mount
for (const key of Object.keys(PROVIDER_CARDS)) {
  fieldValues[key] = {}
}

onMounted(async () => {
  try {
    const result = await fetchProviderCredentials()
    Object.assign(credentialStatus, result)
  } finally {
    credentialsLoading.value = false
  }
})

function statusLabel(key: string): string {
  const status = credentialStatus[key]?.status
  if (status === 'connected') return 'Connected'
  if (status === 'saved' || status === 'configured') return 'Saved'
  if (status === 'error') return 'Error'
  return 'Not configured'
}
function statusClass(key: string): string {
  const status = credentialStatus[key]?.status
  if (status === 'connected') return 'connected'
  if (status === 'saved' || status === 'configured') return 'saved'
  if (status === 'error') return 'error'
  return 'disconnected'
}

async function saveCard(card: ProviderCardConfig) {
  cardSaving[card.key] = true
  cardError[card.key] = null
  try {
    const result = await saveProviderCredentials(card.key, fieldValues[card.key])
    credentialStatus[card.key] = result
    if (result.status === 'error') {
      cardError[card.key] = result.detail ?? 'Could not verify these credentials.'
    } else {
      fieldValues[card.key] = {}
    }
  } catch (err) {
    cardError[card.key] = err instanceof Error ? err.message : 'Failed to save'
  } finally {
    cardSaving[card.key] = false
  }
}

async function clearCard(card: ProviderCardConfig) {
  try {
    await deleteProviderCredentials(card.key)
    credentialStatus[card.key] = { status: 'not_configured' }
    cardError[card.key] = null
  } catch (err) {
    cardError[card.key] = err instanceof Error ? err.message : 'Failed to disconnect'
  }
}

// HowLongToBeat — a real toggle now, not just informational. "Enabled"
// means "HowLongToBeat" is present in the user's scan provider_order.
const hltbEnabled = ref(false)
const hltbLoading = ref(true)
const hltbSaving = ref(false)

onMounted(async () => {
  try {
    const scan = await fetchScanSettings()
    hltbEnabled.value = scan.provider_order.includes('HowLongToBeat')
  } finally {
    hltbLoading.value = false
  }
})

async function toggleHltb(enabled: boolean) {
  hltbSaving.value = true
  try {
    const scan = await fetchScanSettings()
    const nextOrder = enabled
      ? [...scan.provider_order.filter((p) => p !== 'HowLongToBeat'), 'HowLongToBeat']
      : scan.provider_order.filter((p) => p !== 'HowLongToBeat')
    await updateScanSettings({ provider_order: nextOrder as typeof scan.provider_order })
    hltbEnabled.value = enabled
  } finally {
    hltbSaving.value = false
  }
}
</script>

<template>
  <section class="settings-section">
    <h2>Metadata/API</h2>
    <p class="section-hint">
      Providers used to search for and fill in game metadata and art, plus achievement/account
      connections. RetroAchievements does both, so it appears in both groups below.
    </p>

    <h3 class="group-heading">Metadata</h3>

    <div class="source-card">
      <div class="source-header">
        <span class="source-name">Steam</span>
        <span class="status-badge connected"><span class="status-dot"></span>Connected</span>
      </div>
      <p class="source-hint">No account or key required — uses Steam's public store data.</p>
    </div>

    <div class="source-card">
      <div class="source-header">
        <span class="source-name">SteamGridDB</span>
        <span class="status-badge" :class="steamgriddbApiKey ? 'connected' : 'disconnected'">
          <span class="status-dot"></span>{{ steamgriddbApiKey ? 'Configured' : 'Not configured' }}
        </span>
      </div>
      <p class="source-hint">
        Pulls real cover art (Steam vertical / Galaxy 2.0 style) and hero banners. This key is
        yours alone — it's not shared with other accounts on this server.
        <a href="https://www.steamgriddb.com/profile/preferences/api" target="_blank" rel="noopener noreferrer">
          Get a free key from SteamGridDB
        </a>.
      </p>

      <form @submit.prevent="saveSteamgriddbKey">
        <label class="field">
          <span>API Key</span>
          <input v-model="steamgriddbApiKey" type="text" placeholder="Paste your SteamGridDB API key" autocomplete="off" />
        </label>
        <label class="field">
          <span>Current password (required to save)</span>
          <input v-model="currentPassword" type="password" autocomplete="current-password" required />
        </label>
        <div v-if="saveError" class="form-error">{{ saveError }}</div>
        <div v-if="saveSuccess" class="form-success">Settings saved.</div>
        <button type="submit" class="primary-button" :disabled="saving">
          {{ saving ? 'Saving…' : 'Save' }}
        </button>
      </form>
    </div>

    <div v-for="key in ['IGDB', 'GiantBomb', 'ScreenScraper']" :key="key" class="source-card">
      <div class="source-header">
        <span class="source-name">{{ PROVIDER_CARDS[key].label }}</span>
        <span v-if="!credentialsLoading" class="status-badge" :class="statusClass(key)">
          <span class="status-dot"></span>{{ statusLabel(key) }}
        </span>
      </div>
      <p class="source-hint">
        {{ PROVIDER_CARDS[key].description }}
        <a v-if="PROVIDER_CARDS[key].linkUrl" :href="PROVIDER_CARDS[key].linkUrl" target="_blank" rel="noopener noreferrer">
          {{ PROVIDER_CARDS[key].linkLabel }}
        </a>
      </p>

      <form v-if="PROVIDER_CARDS[key].fields.length" @submit.prevent="saveCard(PROVIDER_CARDS[key])">
        <label v-for="field in PROVIDER_CARDS[key].fields" :key="field.key" class="field">
          <span>{{ field.label }}</span>
          <input
            v-model="fieldValues[key][field.key]"
            :type="field.type"
            autocomplete="off"
            :placeholder="`Paste your ${field.label.toLowerCase()}`"
          />
        </label>
        <div v-if="cardError[key]" class="form-error">{{ cardError[key] }}</div>
        <div class="card-actions">
          <button type="submit" class="primary-button" :disabled="cardSaving[key]">
            {{ cardSaving[key] ? 'Saving…' : 'Save' }}
          </button>
          <button v-if="statusClass(key) !== 'disconnected'" type="button" class="secondary-button" @click="clearCard(PROVIDER_CARDS[key])">
            Disconnect
          </button>
        </div>
      </form>
    </div>

    <div class="source-card">
      <div class="source-header">
        <span class="source-name">{{ PROVIDER_CARDS.GOG.label }}</span>
        <span v-if="!credentialsLoading" class="status-badge" :class="statusClass('GOG')">
          <span class="status-dot"></span>{{ statusLabel('GOG') }}
        </span>
      </div>
      <p class="source-hint">{{ PROVIDER_CARDS.GOG.description }}</p>
      <form @submit.prevent="saveCard(PROVIDER_CARDS.GOG)">
        <label v-for="field in PROVIDER_CARDS.GOG.fields" :key="field.key" class="field">
          <span>{{ field.label }}</span>
          <input v-model="fieldValues.GOG[field.key]" :type="field.type" autocomplete="off" :placeholder="`Paste your ${field.label.toLowerCase()}`" />
        </label>
        <div v-if="cardError.GOG" class="form-error">{{ cardError.GOG }}</div>
        <div class="card-actions">
          <button type="submit" class="primary-button" :disabled="cardSaving.GOG">
            {{ cardSaving.GOG ? 'Saving…' : 'Save' }}
          </button>
          <button v-if="statusClass('GOG') !== 'disconnected'" type="button" class="secondary-button" @click="clearCard(PROVIDER_CARDS.GOG)">
            Disconnect
          </button>
        </div>
      </form>
    </div>

    <div class="source-card unavailable">
      <div class="source-header">
        <span class="source-name">LaunchBox</span>
        <span class="status-badge disconnected"><span class="status-dot"></span>Not available</span>
      </div>
      <p class="source-hint">
        LaunchBox stores its library in a local XML export on Windows, not a cloud API this
        self-hosted server can call. Use LaunchBox's own export/import tools to move data
        between the two instead.
      </p>
    </div>

    <h3 class="group-heading">Achievements &amp; Accounts</h3>

    <div class="source-card">
      <div class="source-header">
        <span class="source-name">{{ PROVIDER_CARDS.RetroAchievements.label }}</span>
        <span v-if="!credentialsLoading" class="status-badge" :class="statusClass('RetroAchievements')">
          <span class="status-dot"></span>{{ statusLabel('RetroAchievements') }}
        </span>
      </div>
      <p class="source-hint">
        {{ PROVIDER_CARDS.RetroAchievements.description }}
        <a :href="PROVIDER_CARDS.RetroAchievements.linkUrl" target="_blank" rel="noopener noreferrer">
          {{ PROVIDER_CARDS.RetroAchievements.linkLabel }}
        </a>
      </p>
      <form @submit.prevent="saveCard(PROVIDER_CARDS.RetroAchievements)">
        <label v-for="field in PROVIDER_CARDS.RetroAchievements.fields" :key="field.key" class="field">
          <span>{{ field.label }}</span>
          <input
            v-model="fieldValues.RetroAchievements[field.key]"
            :type="field.type"
            autocomplete="off"
            :placeholder="`Paste your ${field.label.toLowerCase()}`"
          />
        </label>
        <div v-if="cardError.RetroAchievements" class="form-error">{{ cardError.RetroAchievements }}</div>
        <div class="card-actions">
          <button type="submit" class="primary-button" :disabled="cardSaving.RetroAchievements">
            {{ cardSaving.RetroAchievements ? 'Saving…' : 'Save' }}
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

    <div class="source-card">
      <div class="source-header">
        <span class="source-name">PlayStation</span>
        <span v-if="!psnLoading" class="status-badge" :class="psnStatus.connected ? 'connected' : 'disconnected'">
          <span class="status-dot"></span>{{ psnStatus.connected ? 'Connected' : 'Not connected' }}
        </span>
      </div>
      <p class="source-hint">
        Unofficial — there's no official public PSN API, so this uses the same
        reverse-engineered "npsso" token flow as Playnite's PlayStation plugin. It can break
        without notice if Sony changes how it works. Also powers PSN Store data — one
        connection covers both. Log into
        <a href="https://www.playstation.com" target="_blank" rel="noopener noreferrer">playstation.com</a>,
        then copy your <code>npsso</code> cookie value here.
      </p>

      <template v-if="!psnLoading">
        <template v-if="!psnStatus.connected">
          <label class="field">
            <span>npsso token</span>
            <input v-model="npssoToken" type="password" placeholder="Paste your npsso token" autocomplete="off" />
          </label>
          <div v-if="psnError" class="form-error">{{ psnError }}</div>
          <button type="button" class="primary-button" :disabled="psnConnecting" @click="handleConnectPsn">
            {{ psnConnecting ? 'Connecting…' : 'Connect' }}
          </button>
        </template>
        <template v-else>
          <p class="section-hint">
            Connected — the token itself is never shown again. To check it still works,
            reconnect with a fresh token.
          </p>
          <button type="button" class="secondary-button" @click="showDisconnectConfirm = true">Disconnect</button>
        </template>
      </template>
    </div>

    <div class="source-card">
      <div class="source-header">
        <span class="source-name">{{ PROVIDER_CARDS.Xbox.label }}</span>
        <span v-if="!credentialsLoading" class="status-badge" :class="statusClass('Xbox')">
          <span class="status-dot"></span>{{ statusLabel('Xbox') }}
        </span>
      </div>
      <p class="source-hint">{{ PROVIDER_CARDS.Xbox.description }}</p>
      <form @submit.prevent="saveCard(PROVIDER_CARDS.Xbox)">
        <label v-for="field in PROVIDER_CARDS.Xbox.fields" :key="field.key" class="field">
          <span>{{ field.label }}</span>
          <input v-model="fieldValues.Xbox[field.key]" :type="field.type" autocomplete="off" :placeholder="`Paste your ${field.label.toLowerCase()}`" />
        </label>
        <div v-if="cardError.Xbox" class="form-error">{{ cardError.Xbox }}</div>
        <div class="card-actions">
          <button type="submit" class="primary-button" :disabled="cardSaving.Xbox">
            {{ cardSaving.Xbox ? 'Saving…' : 'Save' }}
          </button>
          <button v-if="statusClass('Xbox') !== 'disconnected'" type="button" class="secondary-button" @click="clearCard(PROVIDER_CARDS.Xbox)">
            Disconnect
          </button>
        </div>
      </form>
    </div>

    <div class="source-card">
      <div class="source-header">
        <span class="source-name">HowLongToBeat</span>
        <span v-if="!hltbLoading" class="status-badge" :class="hltbEnabled ? 'connected' : 'disconnected'">
          <span class="status-dot"></span>{{ hltbEnabled ? 'Enabled' : 'Disabled' }}
        </span>
      </div>
      <p class="source-hint">
        Unofficial — no API key needed. Pulls "time to beat" onto games when enabled. Note: HLTB's
        current anti-bot protection can make this fail silently on some searches — if it never
        seems to fill in, that's why, not a bug in your setup.
      </p>
      <ToggleButton :model-value="hltbEnabled" label="Enable HowLongToBeat" :disabled="hltbLoading || hltbSaving" @update:model-value="toggleHltb">
        {{ hltbEnabled ? 'Enabled' : 'Disabled' }} — include in metadata searches
      </ToggleButton>
    </div>

    <div v-if="showDisconnectConfirm" class="confirm-backdrop" @click.self="showDisconnectConfirm = false">
      <div class="confirm-dialog">
        <h3>Disconnect PlayStation account?</h3>
        <p>You'll need to paste your npsso token again to reconnect.</p>
        <div class="confirm-actions">
          <button type="button" class="secondary-button" @click="showDisconnectConfirm = false">Cancel</button>
          <button type="button" class="danger-button" @click="confirmDisconnectPsn">Disconnect</button>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.settings-section h2 {
  margin: 0 0 8px;
  padding-left: 12px;
  border-left: 3px solid #d68a34;
  font-size: 1rem;
  color: #fff;
}
.section-hint {
  color: #999;
  font-size: 0.82rem;
  line-height: 1.6;
  margin: 0 0 16px;
}
.section-hint a {
  color: #d68a34;
  text-decoration: none;
  font-weight: 600;
}
.section-hint a:hover {
  text-decoration: underline;
}
.group-heading {
  color: #999;
  font-size: 0.76rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin: 24px 0 12px;
}
.group-heading:first-of-type {
  margin-top: 4px;
}
.source-card {
  background: #111;
  border: 1px solid #2a2a2a;
  border-radius: 10px;
  padding: 16px;
  margin-bottom: 14px;
  transition: transform 0.15s ease, border-color 0.15s ease;
}
.source-card:hover {
  transform: translateY(-1px);
  border-color: #3a3a3a;
}
.source-card.unavailable {
  opacity: 0.65;
}
.source-card.unavailable:hover {
  transform: none;
}
.source-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}
.source-name {
  color: #fff;
  font-weight: 600;
}
.source-hint {
  color: #999;
  font-size: 0.8rem;
  line-height: 1.6;
  margin: 0 0 12px;
}
.source-hint code {
  background: rgba(255, 255, 255, 0.08);
  padding: 1px 5px;
  border-radius: 4px;
  color: #ccc;
}
.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  font-weight: 700;
  padding: 3px 10px;
  border-radius: 999px;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  flex-shrink: 0;
}
.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
  flex-shrink: 0;
}
.status-badge.connected {
  color: #86efac;
  background: rgba(34, 197, 94, 0.14);
}
.status-badge.saved {
  color: #999;
  background: rgba(255, 255, 255, 0.1);
}
.status-badge.error {
  color: #fca5a5;
  background: rgba(220, 38, 38, 0.14);
}
.status-badge.disconnected {
  color: #999;
  background: rgba(255, 255, 255, 0.06);
}
form {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 0.85rem;
  color: #ccc;
}
.field input {
  background: #1a1a1a;
  border: 1px solid #3a3a3a;
  border-radius: 8px;
  color: #fff;
  padding: 10px 12px;
  font: inherit;
}
.field input:focus {
  outline: none;
  border-color: #d68a34;
}
.card-actions {
  display: flex;
  gap: 10px;
}
.form-error {
  color: #fca5a5;
  font-size: 13px;
  background: rgba(220, 38, 38, 0.1);
  border: 1px solid rgba(220, 38, 38, 0.3);
  border-radius: 8px;
  padding: 8px 10px;
}
.form-success {
  color: #86efac;
  font-size: 13px;
  background: rgba(34, 197, 94, 0.1);
  border: 1px solid rgba(34, 197, 94, 0.3);
  border-radius: 8px;
  padding: 8px 10px;
}
.primary-button {
  background: #d68a34;
  color: #111;
  border: none;
  border-radius: 8px;
  padding: 11px;
  font-weight: 600;
  cursor: pointer;
}
.primary-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.secondary-button {
  background: rgba(255, 255, 255, 0.08);
  color: #fff;
  border: none;
  border-radius: 8px;
  padding: 10px 18px;
  font-weight: 600;
  cursor: pointer;
}
.secondary-button:hover {
  background: rgba(255, 255, 255, 0.14);
}
.confirm-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.65);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 60;
}
.confirm-dialog {
  background: #1a1a1a;
  border: 1px solid #2a2a2a;
  border-radius: 12px;
  padding: 22px;
  max-width: 360px;
  box-shadow: 0 24px 64px rgba(0, 0, 0, 0.6);
}
.confirm-dialog h3 {
  margin: 0 0 8px;
  color: #fff;
}
.confirm-dialog p {
  margin: 0 0 18px;
  color: #999;
  font-size: 0.85rem;
}
.confirm-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
.danger-button {
  background: rgba(220, 38, 38, 0.18);
  color: #fca5a5;
  border: none;
  border-radius: 8px;
  padding: 10px 18px;
  font-weight: 600;
  cursor: pointer;
}
</style>
