<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  createInitialAdmin,
  fetchSetupConfiguration,
  fetchSetupStatus,
  saveSetupConfiguration,
  type SetupConfiguration,
  type SetupField,
  type SetupSection,
} from "../services/setup";
import { checkAuth } from "../state/auth";

const route = useRoute();
const router = useRouter();

const configuration = ref<SetupConfiguration | null>(null);
const selectedSections = ref<string[]>([]);
const values = ref<Record<string, unknown>>({});
const currentSection = ref("welcome");
const loading = ref(true);
const saving = ref(false);
const error = ref<string | null>(
  route.query.backend_error
    ? "The backend is not ready yet. Reload once it is available."
    : null,
);
const saved = ref(false);

const forced = computed(() => configuration.value?.forced === true);
const sections = computed(() => configuration.value?.sections ?? []);
const current = computed(() =>
  sections.value.find((section) => section.id === currentSection.value),
);
const selected = computed(() =>
  sections.value.filter((section) => selectedSections.value.includes(section.id)),
);
const isLastSelectedSection = computed(() =>
  currentSection.value === selected.value[selected.value.length - 1]?.id,
);
const optionalSections = computed(() =>
  sections.value.filter((section) => !section.required),
);
const requiredSections = computed(() =>
  sections.value.filter((section) => section.required),
);
const isLastSection = computed(() => currentSection.value === selected.value[selected.value.length - 1]?.id);
const allRequiredComplete = computed(() =>
  requiredSections.value.every((section) => {
    if (section.id === "first_admin" && forced.value) return true;
    return sectionIsComplete(section);
  }),
);
const oidcEnabled = computed(() => {
  const value = values.value.OIDC_ENABLED;
  return typeof value === "boolean" ? value : value !== "false";
});

function fieldValue(field: SetupField): unknown {
  if (field.name in values.value) return values.value[field.name];
  return field.value;
}

function setField(field: SetupField, value: unknown) {
  values.value[field.name] = value;
}

function sectionIsComplete(section: SetupSection): boolean {
  if (section.id === "oidc" && !oidcEnabled.value) return true;
  return section.fields
    .filter((field) => field.required)
    .every((field) => field.configured || hasValue(fieldValue(field)));
}

function hasValue(value: unknown): boolean {
  if (typeof value === "boolean") return true;
  return value !== null && value !== undefined && String(value).trim() !== "";
}

function statusLabel(section: SetupSection): string {
  if (section.status === "completed_by_env") return "Completed by .env";
  if (sectionIsComplete(section)) return "Complete";
  if (section.status === "partial") return "Partially configured";
  return "Not configured";
}

function initialize(config: SetupConfiguration) {
  configuration.value = config;
  values.value = {};

  // Required sections are always selected. Optional sections containing
  // deployment-provided values are selected automatically so a half-filled
  // .env file is visible rather than silently ignored.
  selectedSections.value = config.sections
    .filter(
      (section) =>
        section.required ||
        section.status === "partial" ||
        section.status === "configured" ||
        section.status === "completed_by_env",
    )
    .map((section) => section.id);

  for (const section of config.sections) {
    for (const field of section.fields) {
      if (field.secret) {
        // Secrets are intentionally never returned. A configured secret is
        // represented by an empty input plus configured/locked metadata.
        values.value[field.name] = "";
      } else {
        values.value[field.name] = field.value;
      }
    }
  }

  if (!forced.value && selectedSections.value.includes("first_admin")) {
    currentSection.value = "welcome";
  } else {
    currentSection.value =
      selectedSections.value.find((id) => id !== "database") ?? "welcome";
  }
}

onMounted(async () => {
  try {
    const [status, config] = await Promise.all([
      fetchSetupStatus(),
      fetchSetupConfiguration(),
    ]);

    if (!status.setup_required && !status.forced) {
      await checkAuth();
      await router.replace("/");
      return;
    }

    initialize(config);
  } catch (err) {
    error.value =
      err instanceof Error ? err.message : "Unable to load setup configuration.";
  } finally {
    loading.value = false;
  }
});

function toggleOptional(section: SetupSection) {
  if (section.required || section.status === "completed_by_env") return;
  const index = selectedSections.value.indexOf(section.id);
  if (index >= 0) {
    selectedSections.value.splice(index, 1);
    if (currentSection.value === section.id) currentSection.value = "welcome";
  } else {
    selectedSections.value.push(section.id);
    currentSection.value = section.id;
  }
}

function nextSection() {
  const ids = ["welcome", ...selected.value.map((section) => section.id)];
  const index = ids.indexOf(currentSection.value);
  currentSection.value = ids[Math.min(index + 1, ids.length - 1)];
}

function previousSection() {
  const ids = ["welcome", ...selected.value.map((section) => section.id)];
  const index = ids.indexOf(currentSection.value);
  currentSection.value = ids[Math.max(index - 1, 0)];
}

function inputType(field: SetupField): string {
  if (field.type === "secret") return "password";
  if (field.type === "email") return "email";
  if (field.type === "url") return "url";
  if (field.type === "integer") return "number";
  return "text";
}

function fieldRequired(field: SetupField): boolean {
  if (
    current.value?.id === "oidc" &&
    ["OIDC_ISSUER_URL", "OIDC_CLIENT_ID", "OIDC_CLIENT_SECRET"].includes(field.name)
  ) {
    return oidcEnabled.value;
  }
  return field.required;
}

function textFieldValue(field: SetupField | undefined): string {
  const value = field ? fieldValue(field) : undefined;
  return value === null || value === undefined ? "" : String(value);
}

function payloadValues(): Record<string, unknown> {
  const result: Record<string, unknown> = {};

  for (const section of selected.value) {
    for (const field of section.fields) {
      if (field.locked) continue;
      const value = fieldValue(field);

      // Empty secret inputs mean “leave the existing secret alone”.
      if (field.secret && !String(value ?? "").trim()) continue;
      if (value === undefined || value === null) continue;
      result[field.name] = value;
    }
  }

  return result;
}

async function submit() {
  error.value = null;
  saved.value = false;

  for (const section of selected.value) {
    if (section.id === "first_admin" && forced.value) continue;
    if (section.id === "oidc" && !oidcEnabled.value) continue;

    for (const field of section.fields) {
      if (
        fieldRequired(field) &&
        !field.configured &&
        !hasValue(fieldValue(field))
      ) {
        currentSection.value = section.id;
        error.value = `“${field.label}” is required before continuing.`;
        return;
      }
    }
  }

  saving.value = true;
  try {
    const submission = {
      sections: selectedSections.value,
      configuration: payloadValues(),
    };

    if (forced.value) {
      await saveSetupConfiguration(submission);
      saved.value = true;
      configuration.value = await fetchSetupConfiguration();
      return;
    }

    const admin = sections.value.find((section) => section.id === "first_admin");
    const username = textFieldValue(
      admin?.fields.find((field) => field.name === "PRIMARY_USER_USERNAME"),
    );
    const email = textFieldValue(
      admin?.fields.find((field) => field.name === "PRIMARY_USER_EMAIL"),
    );
    const password = textFieldValue(
      admin?.fields.find((field) => field.name === "PRIMARY_USER_PASSWORD"),
    );

    await createInitialAdmin({
      ...submission,
      username,
      email,
      password,
    });
    await checkAuth();
    await router.replace("/");
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Setup failed.";
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <main class="setup-page">
    <section v-if="loading" class="setup-card">
      <div class="brand"><span>🎮</span><h1>Archive setup</h1></div>
      <p class="subtitle">Loading the configuration registry…</p>
    </section>

    <section v-else class="setup-shell">
      <aside class="setup-nav">
        <div class="brand"><span>🎮</span><strong>Archive setup</strong></div>
        <button
          class="nav-item"
          :class="{ active: currentSection === 'welcome' }"
          @click="currentSection = 'welcome'"
        >
          Welcome
        </button>
        <button
          v-for="section in selected"
          :key="section.id"
          class="nav-item"
          :class="{ active: currentSection === section.id }"
          @click="currentSection = section.id"
        >
          <span>{{ section.title }}</span>
          <small>{{ statusLabel(section) }}</small>
        </button>
      </aside>

      <section class="setup-card content">
        <div v-if="currentSection === 'welcome'">
          <div class="brand"><span>👋</span><h1>Welcome to setup</h1></div>
          <p class="subtitle">
            This page is generated from the backend configuration registry.
            Required sections are kept automatically; optional sections can be
            added or removed without changing this Vue component.
          </p>

          <div v-if="forced" class="forced-banner">
            <strong>STARTUP_UI=forced</strong>
            <span>
              Configuration is available after installation. The first
              administrator cannot be recreated from this screen.
            </span>
          </div>

          <div class="section-list">
            <article v-for="section in requiredSections" :key="section.id" class="section-choice required">
              <div>
                <strong>{{ section.title }}</strong>
                <p>{{ section.description }}</p>
              </div>
              <span class="badge">{{ statusLabel(section) }}</span>
            </article>

            <article
              v-for="section in optionalSections"
              :key="section.id"
              class="section-choice"
              :class="{ selected: selectedSections.includes(section.id) }"
            >
              <div>
                <strong>{{ section.title }}</strong>
                <p>{{ section.description }}</p>
              </div>
              <button
                type="button"
                class="secondary small"
                :disabled="section.status === 'completed_by_env'"
                @click="toggleOptional(section)"
              >
                {{
                  section.status === "completed_by_env"
                    ? "Completed by .env"
                    : selectedSections.includes(section.id)
                      ? "Remove"
                      : "Add"
                }}
              </button>
            </article>
          </div>

          <div v-if="error" class="error">{{ error }}</div>
          <button class="primary" :disabled="!allRequiredComplete && forced === false" @click="nextSection">
            Continue
          </button>
        </div>

        <div v-else-if="current" class="section-editor">
          <header>
            <div>
              <h1>{{ current.title }}</h1>
              <p class="subtitle">{{ current.description }}</p>
            </div>
            <span class="badge">{{ statusLabel(current) }}</span>
          </header>

          <div
            v-if="current.id === 'oidc' && !oidcEnabled"
            class="info-banner"
          >
            OIDC is disabled. Provider fields may be saved partially so they
            can be completed later, but they will not be used for login.
          </div>

          <div class="fields">
            <label v-for="field in current.fields" :key="field.name">
              <span>
                {{ field.label }}
                <b v-if="fieldRequired(field)" class="required-mark">*</b>
                <em v-if="field.locked">Managed by .env</em>
              </span>

              <select
                v-if="field.type === 'choice'"
                :value="fieldValue(field) as string"
                :disabled="field.locked"
                @change="setField(field, ($event.target as HTMLSelectElement).value)"
              >
                <option
                  v-for="choice in field.choices"
                  :key="choice.value"
                  :value="choice.value"
                >
                  {{ choice.label }}
                </option>
              </select>

              <input
                v-else-if="field.type === 'boolean'"
                :checked="Boolean(fieldValue(field))"
                type="checkbox"
                :disabled="field.locked"
                @change="setField(field, ($event.target as HTMLInputElement).checked)"
              />

              <input
                v-else
                :value="fieldValue(field) as string | number | undefined"
                :type="inputType(field)"
                :placeholder="field.secret && field.configured ? 'Already configured — leave blank to keep it' : field.placeholder"
                :required="fieldRequired(field) && !field.configured"
                :disabled="field.locked || (field.generated && field.configured)"
                @input="setField(field, ($event.target as HTMLInputElement).value)"
              />

              <small v-if="field.description">{{ field.description }}</small>
              <small v-if="field.hint">{{ field.hint }}</small>
              <small v-if="field.locked" class="env-help">
                This value comes from the deployment environment and cannot be changed here.
              </small>
            </label>
          </div>

          <div v-if="error" class="error">{{ error }}</div>
          <div v-if="saved" class="success">Configuration saved.</div>

          <div class="actions">
            <button class="secondary" @click="previousSection">Back</button>
            <button
              v-if="currentSection !== 'welcome' && !isLastSelectedSection"
              class="secondary"
              @click="nextSection"
            >
              Next
            </button>
            <button
              v-else
              class="primary"
              :disabled="saving"
              @click="submit"
            >
              {{ saving ? "Saving…" : forced ? "Save configuration" : "Finish setup" }}
            </button>
          </div>
        </div>
      </section>
    </section>
  </main>
</template>

<style scoped>
.setup-page{min-height:100vh;background:#121212;color:#ccc;font-family:system-ui,sans-serif;padding:24px 16px;display:flex;justify-content:center;align-items:center}
.setup-shell{width:min(1120px,100%);display:grid;grid-template-columns:260px minmax(0,1fr);gap:16px;align-items:start}
.setup-card,.setup-nav{background:#1a1a1a;border:1px solid #2a2a2a;border-radius:14px}
.setup-card{padding:32px}.setup-card.content{min-height:650px}
.setup-nav{padding:18px;display:flex;flex-direction:column;gap:8px;position:sticky;top:16px}
.brand{display:flex;align-items:center;gap:10px;justify-content:center;color:#fff;margin-bottom:12px}.brand h1{font-size:1.4rem;margin:0}.brand strong{font-size:1rem}
.subtitle{color:#999;font-size:13px;line-height:1.5}
.nav-item{border:1px solid transparent;background:transparent;color:#aaa;text-align:left;padding:10px;border-radius:8px;cursor:pointer;display:flex;justify-content:space-between;gap:8px}.nav-item.active{background:#252525;border-color:#3a3a3a;color:#fff}.nav-item small{color:#777;font-size:10px;text-align:right}
.section-list{display:flex;flex-direction:column;gap:10px;margin:24px 0}
.section-choice{border:1px solid #333;border-radius:10px;padding:14px;display:flex;align-items:center;justify-content:space-between;gap:16px;background:#151515}.section-choice.selected{border-color:#57411f}.section-choice p{margin:5px 0 0;color:#888;font-size:12px;line-height:1.4}.section-choice.required{background:#181818}
.badge{white-space:nowrap;border:1px solid #3a3a3a;border-radius:999px;padding:4px 8px;color:#aaa;font-size:11px}.small{padding:7px 10px!important;font-size:12px}
.forced-banner,.info-banner{display:flex;flex-direction:column;gap:5px;padding:12px;border:1px solid #57411f;background:#211b11;border-radius:8px;color:#d8c39a;font-size:12px;line-height:1.5}
.section-editor header{display:flex;justify-content:space-between;gap:16px;align-items:flex-start}.section-editor h1{margin:0;color:#fff;font-size:1.35rem}
.fields{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px;margin:24px 0}.fields label{display:flex;flex-direction:column;gap:6px;color:#ccc;font-size:13px}.fields label:has(input[type=checkbox]){flex-direction:row;align-items:center}.fields label>span{display:flex;gap:5px;align-items:center}.fields em{font-style:normal;color:#d8c39a;font-size:10px;margin-left:auto}.fields input,.fields select{background:#111;border:1px solid #3a3a3a;border-radius:8px;color:#fff;padding:10px;font:inherit}.fields input[type=checkbox]{width:18px;height:18px;accent-color:#d68a34}.fields input:focus,.fields select:focus{outline:none;border-color:#d68a34}.fields input:disabled,.fields select:disabled{opacity:.55}.fields small{color:#777;font-size:11px;line-height:1.4}.env-help{color:#d8c39a!important}.required-mark{color:#fca5a5}
.actions{display:flex;gap:10px;margin-top:20px}.actions button{flex:1}
button.primary,.setup-card button.primary{background:#d68a34;color:#111;border:0;border-radius:8px;padding:11px 14px;font-weight:700;cursor:pointer}.secondary{background:#252525!important;color:#ddd!important;border:1px solid #3a3a3a!important;border-radius:8px;padding:11px 14px;cursor:pointer}.setup-card button:disabled{opacity:.6;cursor:not-allowed}
.error{color:#fca5a5;background:rgba(220,38,38,.1);border:1px solid rgba(220,38,38,.3);border-radius:8px;padding:9px;font-size:13px}.success{color:#86efac;background:rgba(34,197,94,.08);border:1px solid rgba(34,197,94,.2);border-radius:8px;padding:9px;font-size:13px}
@media(max-width:800px){.setup-page{align-items:flex-start}.setup-shell{grid-template-columns:1fr}.setup-nav{position:static}.fields{grid-template-columns:1fr}.section-choice{align-items:flex-start;flex-direction:column}}
</style>
