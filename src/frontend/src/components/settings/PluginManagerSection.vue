<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import {
  managerEntries,
  catalogueVersions,
  pluginChannel,
  type ManagerView,
} from "../../services/pluginManagerViews";
import { refreshPluginExtensions } from "../../state/pluginExtensions";
import UiModal from "../UiModal.vue";
import PluginInstallConsentDialog from "../plugins/PluginInstallConsentDialog.vue";
import PluginSettingsDialog from "../plugins/PluginSettingsDialog.vue";
import PluginIsolationWarning from "../plugins/PluginIsolationWarning.vue";
import PluginGatewayWarning from "../plugins/PluginGatewayWarning.vue";
import PluginPackageDropZone from "../plugins/PluginPackageDropZone.vue";
import PluginVersionConfirmationDialog from "../plugins/PluginVersionConfirmationDialog.vue";
import {
  deletePlugin,
  deletePluginCatalogue,
  disablePlugin,
  enablePlugin,
  createPluginCatalogue,
  fetchPluginCatalogFromSource,
  fetchPluginCatalogues,
  fetchPluginLogs,
  fetchPlugins,
  fetchPluginDetails,
  checkPluginUpdates,
  installPlugin,
  installPluginFromUrl,
  previewPluginInstall,
  previewPluginInstallUrl,
  previewPluginUpdate,
  previewPluginUpdateUrl,
  retryPlugin,
  updatePluginCatalogue,
  updatePlugin,
  updatePluginFromUrl,
  type PluginCatalogue,
  type PluginInstallConfirmation,
  type PluginInstallPreview,
  type PluginSourceMetadata,
  type PluginCatalogEntry,
  type PluginDiagnostics,
  type PluginSummary,
  type PluginUpdateCheck,
  fetchRuntimeCapabilities,
  fetchManagerSettings,
  saveManagerSettings,
  setPluginAutomaticUpdates,
  packageOperation,
  previewStagedUpdate,
  type RuntimeCapabilities,
  type ManagerSettings,
} from "../../services/plugins";
import {
  approvePluginPermission,
  denyPluginPermission,
  fetchPluginPermissionGrants,
  fetchPluginPermissionRequests,
  revokePluginPermission,
  type PluginPermissionGrant,
  type PluginPermissionRequest,
} from "../../services/pluginPermissions";
import {
  fetchPluginUi,
  type PluginUiDocument,
  type UiAction,
  type UiValues,
} from "../../services/pluginUi";

const plugins = ref<PluginSummary[]>([]);
const catalog = ref<PluginCatalogEntry[]>([]);
const loading = ref(true);
const cataloguesLoading = ref(false);
const error = ref("");
const operationError = ref("");
const pendingVersionInstall = ref<PluginInstallConfirmation | null>(null);
const action = ref("");
const selectedFile = ref<File | null>(null);
const installFile = ref<File | null>(null);
const installUrl = ref<string | null>(null);
const remoteUrl = ref("");
const installPreview = ref<PluginInstallPreview | null>(null);
const reviewView = ref<"overview" | "access">("access");
const previewing = ref(false);
const installing = ref(false);
const installMessage = ref("");
const selected = ref<PluginSummary | null>(null);
const pluginUi = ref<PluginUiDocument | null>(null);
const pluginDiagnostics = ref<PluginDiagnostics | null>(null);
const pluginGrants = ref<PluginPermissionGrant[]>([]);
const pluginRequests = ref<PluginPermissionRequest[]>([]);
const popupLoading = ref(false);
let popupGeneration = 0;
const installOpen = ref(false);
const catalogues = ref<PluginCatalogue[]>([]);
const catalogueErrors = ref<string[]>([]);
const newCatalogEndpoint = ref("");
const installSource = ref<Partial<PluginSourceMetadata>>({ type: "upload" });
const updateTarget = ref<PluginSummary | null>(null);
const updateFile = ref<File | null>(null);
const updateUrl = ref<string | null>(null);
const replacement = ref(false);
const updateSource = ref<Partial<PluginSourceMetadata>>({});
watch(error, (value) => {
  if (
    value &&
    !selected.value &&
    !installOpen.value &&
    !installPreview.value &&
    !duplicate.value
  )
    operationError.value = value;
});
const availableUpdates = ref<Record<string, PluginUpdateCheck>>({});
const checkingUpdates = ref(false);
const view = ref<ManagerView>("Installed");
const search = ref("");
const tag = ref("");
const channel = ref("");
const selectedVersions = ref<Record<string, string>>({});
const runtime = ref<RuntimeCapabilities | null>(null);
const managerSettings = ref<ManagerSettings>({
  automatic_updates: false,
  retained_versions: 1,
});
const isolationWarning = ref<InstanceType<
  typeof PluginIsolationWarning
> | null>(null);
let pendingIsolationInstall: PluginInstallConfirmation | null = null;
const needsIsolationApproval = computed(
  () =>
    runtime.value?.available !== false &&
    runtime.value?.bubblewrap_available === false &&
    !runtime.value?.reduced_isolation_allowed,
);

async function approveReducedIsolation() {
  managerSettingsBusy.value = true;
  managerSettingsError.value = "";
  try {
    managerSettings.value = await saveManagerSettings({
      reduced_isolation_acknowledged: true,
    });
    await load();
    isolationWarning.value?.close();
    const confirmation = pendingIsolationInstall;
    pendingIsolationInstall = null;
    if (confirmation) await confirmInstall(confirmation);
  } catch (err) {
    managerSettingsError.value =
      err instanceof Error
        ? err.message
        : "Reduced isolation approval could not be saved.";
  } finally {
    managerSettingsBusy.value = false;
  }
}

async function withdrawReducedIsolation() {
  managerSettingsBusy.value = true;
  managerSettingsError.value = "";
  try {
    managerSettings.value = await saveManagerSettings({
      reduced_isolation_acknowledged: false,
    });
    await load();
    await refreshPluginExtensions();
  } catch (err) {
    managerSettingsError.value =
      err instanceof Error
        ? err.message
        : "Reduced isolation approval could not be withdrawn.";
  } finally {
    managerSettingsBusy.value = false;
  }
}
const managerSettingsLoaded = ref(false);
const managerSettingsBusy = ref(false);
const managerSettingsMessage = ref("");
const managerSettingsError = ref("");
const retainedVersionsValid = computed(
  () =>
    Number.isInteger(managerSettings.value.retained_versions) &&
    managerSettings.value.retained_versions >= 1 &&
    managerSettings.value.retained_versions <= 100,
);
const stagedTarget = ref<string | null>(null);
const grantTarget = ref<string | null>(null);
const duplicate = ref<PluginSummary | null>(null);
const entries = computed(() =>
  managerEntries(
    plugins.value,
    catalog.value,
    view.value,
    search.value,
    tag.value,
    channel.value,
  ),
);
const tags = computed(() =>
  [
    ...new Set(
      [...plugins.value, ...catalog.value].flatMap((item) => item.tags ?? []),
    ),
  ].sort(),
);
const installedEntries = computed(() =>
  entries.value.filter((item): item is PluginSummary => "status" in item),
);
const catalogueEntries = computed(() =>
  entries.value.filter(
    (item): item is PluginCatalogEntry => !("status" in item),
  ),
);
const catalogueGroups = computed(() =>
  [
    { id: "official", label: "Official plugins" },
    { id: "demo", label: "Example plugins" },
    { id: "community", label: "Community and unverified plugins" },
  ]
    .map((group) => ({
      ...group,
      entries: catalogueEntries.value.filter(
        (entry) => pluginChannel(entry) === group.id,
      ),
    }))
    .filter((group) => group.entries.length),
);

async function saveGlobalSettings() {
  if (!retainedVersionsValid.value || managerSettingsBusy.value) return;
  managerSettingsBusy.value = true;
  managerSettingsMessage.value = "";
  managerSettingsError.value = "";
  try {
    const saved = await saveManagerSettings(managerSettings.value);
    managerSettings.value = saved;
    managerSettingsMessage.value = saved.history_pruning_deferred
      ? "Plugin Manager settings saved. Existing package history could not be trimmed while the runtime is unavailable. Future package operations use the saved limit."
      : "Plugin Manager settings saved.";
  } catch (err) {
    managerSettingsError.value =
      err instanceof Error ? err.message : "Settings could not be saved.";
  } finally {
    managerSettingsBusy.value = false;
  }
}

async function loadManagerSettings() {
  managerSettingsError.value = "";
  try {
    managerSettings.value = await fetchManagerSettings();
    managerSettingsLoaded.value = true;
  } catch (err) {
    managerSettingsError.value =
      err instanceof Error
        ? err.message
        : "Plugin Manager settings could not be loaded.";
  }
}

async function lifecycleOperation(operation: string, purge = false) {
  const plugin = selected.value;
  if (!plugin) return;
  if (operation === "uninstall") {
    await removePlugin(plugin);
    return;
  }
  if (
    purge &&
    !window.confirm(
      `Permanently purge all ${plugin.name} data, configuration, credentials and permissions?`,
    )
  )
    return;
  await run(plugin.plugin_id, async (id) => {
    if (operation.startsWith("rollback/")) {
      await packageOperation(id, "rollback", {
        history_id: operation.split("/")[1],
        allow_untrusted: plugin.trust?.status !== "trusted",
      });
    } else {
      await packageOperation(id, operation, {
        purge,
        confirmed: purge,
        allow_untrusted: plugin.trust?.status !== "trusted",
      });
    }
  });
}

async function autoUpdateSelected(mode: string) {
  if (selected.value)
    await run(selected.value.plugin_id, async (id) => {
      await setPluginAutomaticUpdates(id, mode);
    });
}

async function deleteHistory(id: string) {
  if (
    !selected.value ||
    !window.confirm("Delete this retained package? Plugin data is preserved.")
  )
    return;
  await run(selected.value.plugin_id, async (pluginId) => {
    const response = await fetch(
      `/api/plugins/${encodeURIComponent(pluginId)}/history/${encodeURIComponent(id)}`,
      { method: "DELETE", credentials: "include" },
    );
    if (!response.ok) throw new Error("Retained package could not be deleted.");
  });
}

async function reviewGrant(key: string) {
  if (!selected.value) return;
  const response = await fetch(
    `/api/plugins/${encodeURIComponent(selected.value.plugin_id)}/permissions/preview`,
    { method: "POST", credentials: "include" },
  );
  if (!response.ok) {
    error.value = "Permission preview is unavailable.";
    return;
  }
  const preview = (await response.json()) as PluginInstallPreview;
  grantTarget.value = selected.value.plugin_id;
  installPreview.value = {
    ...preview,
    operation: "update",
    requires_version_confirmation: false,
    permissions: preview.permissions
      .filter((item) => item.key === key)
      .map((item) => ({ ...item, new: true })),
  };
}

async function chooseDuplicate(choice: "update" | "reinstall" | "replace") {
  const plugin = duplicate.value;
  if (!plugin) return;
  if (choice === "reinstall") {
    duplicate.value = null;
    cancelInstall();
    selected.value = plugin;
    await lifecycleOperation("reinstall");
    return;
  }
  previewing.value = true;
  error.value = "";
  try {
    replacement.value = choice === "replace";
    updateTarget.value = plugin;
    updateFile.value = installFile.value;
    updateUrl.value = installUrl.value;
    updateSource.value = installSource.value;
    installPreview.value = updateFile.value
      ? await previewPluginUpdate(
          plugin.plugin_id,
          updateFile.value,
          replacement.value ? "replace" : "update",
        )
      : await previewPluginUpdateUrl(
          plugin.plugin_id,
          updateUrl.value!,
          installSource.value,
          replacement.value ? "replace" : "update",
        );
    duplicate.value = null;
  } catch (failure) {
    updateTarget.value = null;
    error.value =
      failure instanceof Error
        ? failure.message
        : "Plugin update preview failed.";
  } finally {
    previewing.value = false;
  }
}

async function addCatalogEndpoint() {
  const url = newCatalogEndpoint.value.trim();
  if (!/^https?:\/\//i.test(url)) return;
  await createPluginCatalogue({
    name: new URL(url).hostname,
    url,
    enabled: true,
    priority: 100,
  });
  newCatalogEndpoint.value = "";
  await loadCatalogues();
}

async function removeCatalogEndpoint(catalogue: PluginCatalogue) {
  if (catalogue.id === "official") return;
  await deletePluginCatalogue(catalogue.id);
  await loadCatalogues();
}

async function toggleCatalogEndpoint(
  catalogue: PluginCatalogue,
  enabled: boolean,
) {
  await updatePluginCatalogue(catalogue.id, { enabled });
  await loadCatalogues();
}

async function loadCatalogues() {
  if (cataloguesLoading.value) return;
  cataloguesLoading.value = true;
  catalogueErrors.value = [];
  try {
    catalogues.value = await fetchPluginCatalogues();
    const enabled = catalogues.value.filter((catalogue) => catalogue.enabled);
    const results = await Promise.all(
      enabled.map(async (catalogue) => ({
        catalogue,
        entries: await fetchPluginCatalogFromSource(catalogue.url).catch(
          (error: unknown) => {
            catalogueErrors.value.push(
              `${catalogue.name}: ${error instanceof Error ? error.message : "Catalogue could not be loaded"}`,
            );
            return [];
          },
        ),
      })),
    );
    const seen = new Set<string>();
    catalog.value = results
      .flatMap((result) =>
        result.entries.map((entry) => ({
          ...entry,
          catalogue_url: result.catalogue.url,
        })),
      )
      .filter((entry) => {
        if (seen.has(entry.plugin_id)) return false;
        seen.add(entry.plugin_id);
        return true;
      });
  } catch (err) {
    catalogueErrors.value.push(
      err instanceof Error ? err.message : "Catalogues are unavailable.",
    );
  } finally {
    cataloguesLoading.value = false;
  }
}

function discoverPlugins() {
  view.value = "Discover";
  search.value = "";
  tag.value = "";
  void loadCatalogues();
}

function openInstaller() {
  if (installing.value || previewing.value) return;
  installOpen.value = true;
}

function closeInstaller() {
  if (installing.value) return;
  installOpen.value = false;
  newCatalogEndpoint.value = "";
}

async function load() {
  loading.value = true;
  error.value = "";
  void fetchRuntimeCapabilities()
    .then((value) => (runtime.value = value))
    .catch(() => (runtime.value = null));
  try {
    plugins.value = await fetchPlugins();
    availableUpdates.value = Object.fromEntries(
      plugins.value
        .filter((item) => item.available_update?.update_available)
        .map((item) => [item.plugin_id, item.available_update!]),
    );
    // Installed inventory is usable while remote catalogue enrichment loads.
    void loadCatalogues();
    if (selected.value) {
      selected.value =
        plugins.value.find(
          (item) => item.plugin_id === selected.value?.plugin_id,
        ) ?? null;
    }
  } catch (err) {
    error.value =
      err instanceof Error ? err.message : "Plugin manager is unavailable.";
  } finally {
    loading.value = false;
  }
}

async function run(id: string, operation: (id: string) => Promise<void>) {
  action.value = id;
  error.value = "";
  try {
    await operation(id);
    await load();
    await refreshPluginExtensions();
    if (selected.value?.plugin_id === id) await refreshPlugin();
  } catch (err) {
    const failure =
      err instanceof Error ? err.message : "Plugin action failed.";
    // Refresh failed status and logs without clearing the operation's explanation.
    await load();
    if (selected.value?.plugin_id === id) await refreshPlugin();
    error.value = failure;
  } finally {
    action.value = "";
  }
}

function selectFile(event: Event) {
  selectedFile.value = (event.target as HTMLInputElement).files?.[0] ?? null;
  installMessage.value = "";
}

async function reviewDroppedPackage(file: File) {
  if (installing.value || previewing.value) return;
  selectedFile.value = file;
  await previewSelected();
  if (duplicate.value) await chooseDuplicate("update");
}

async function previewSelected() {
  if (!selectedFile.value || installing.value || previewing.value) return;
  previewing.value = true;
  error.value = "";
  installMessage.value = "";
  try {
    installUrl.value = null;
    installSource.value = { type: "upload" };
    installFile.value = selectedFile.value;
    reviewView.value = "access";
    installPreview.value = await previewPluginInstall(selectedFile.value);
    installOpen.value = false;
    duplicate.value =
      plugins.value.find(
        (item) => item.plugin_id === installPreview.value?.plugin_id,
      ) ?? null;
  } catch (err) {
    installFile.value = null;
    installPreview.value = null;
    error.value = err instanceof Error ? err.message : "Plugin preview failed.";
  } finally {
    previewing.value = false;
  }
}

async function previewRemoteUrl(
  url = remoteUrl.value,
  source: Partial<PluginSourceMetadata> = { type: "url" },
  initialView: "overview" | "access" = "access",
) {
  if (installing.value || previewing.value) return;
  const normalized = url.trim();
  if (!normalized) return;
  previewing.value = true;
  error.value = "";
  installMessage.value = "";
  try {
    installFile.value = null;
    reviewView.value = initialView;
    installUrl.value = normalized;
    installSource.value = source;
    installPreview.value = await previewPluginInstallUrl(normalized, source);
    installOpen.value = false;
    duplicate.value =
      plugins.value.find(
        (item) => item.plugin_id === installPreview.value?.plugin_id,
      ) ?? null;
  } catch (err) {
    installUrl.value = null;
    installPreview.value = null;
    error.value =
      err instanceof Error ? err.message : "Plugin URL preview failed.";
  } finally {
    previewing.value = false;
  }
}

async function previewCatalogEntry(
  entry: PluginCatalogEntry,
  initialView: "overview" | "access" = "access",
) {
  error.value = "";
  const release =
    catalogueVersions(entry).find(
      (item) => item.version === selectedVersions.value[entry.plugin_id],
    ) ?? entry;
  await previewRemoteUrl(
    release.url,
    {
      type: "catalogue",
      catalogue_url: entry.catalogue_url,
      release_notes: release.release_notes,
      changelog_url: entry.changelog_url,
    },
    initialView,
  );
  if (installPreview.value) {
    installPreview.value.readme ??= entry.readme;
    installPreview.value.icon ??= entry.icon;
  }
}

function cancelInstall() {
  if (installing.value) return;
  installFile.value = null;
  installUrl.value = null;
  installPreview.value = null;
  updateTarget.value = null;
  updateFile.value = null;
  updateUrl.value = null;
  updateSource.value = {};
  stagedTarget.value = null;
  grantTarget.value = null;
  duplicate.value = null;
  pendingVersionInstall.value = null;
  replacement.value = false;
  reviewView.value = "access";
}

async function confirmInstall(confirmation: PluginInstallConfirmation) {
  if (!installPreview.value) return;
  const denyingStage =
    stagedTarget.value &&
    installPreview.value.new_permission_keys?.length &&
    !confirmation.approvedPermissions.length;
  if (
    !grantTarget.value &&
    !denyingStage &&
    installPreview.value.requires_version_confirmation &&
    !confirmation.versionChangeConfirmed
  ) {
    pendingVersionInstall.value = confirmation;
    return;
  }
  confirmation = {
    ...confirmation,
    expectedDigest: installPreview.value.digest,
    expectedInstalledVersion: installPreview.value.installed_version,
  };
  if (needsIsolationApproval.value) {
    pendingIsolationInstall = confirmation;
    isolationWarning.value?.review();
    return;
  }
  installing.value = true;
  error.value = "";
  try {
    if (grantTarget.value || stagedTarget.value) {
      const id = grantTarget.value ?? stagedTarget.value!;
      const result = await packageOperation(
        id,
        grantTarget.value ? "permissions/grant" : "update/staged",
        {
          approved_permissions: confirmation.approvedPermissions,
          expected_digest: installPreview.value.digest,
          permissions_reviewed: Boolean(stagedTarget.value),
          version_change_confirmed:
            confirmation.versionChangeConfirmed ?? false,
          expected_installed_version: confirmation.expectedInstalledVersion,
          confirmed: Boolean(
            stagedTarget.value &&
            installPreview.value.new_permission_keys?.length &&
            !confirmation.approvedPermissions.length,
          ),
          admin_password: confirmation.adminPassword,
          confirm_dangerous: confirmation.confirmDangerous,
          allow_untrusted: installPreview.value.trust_status !== "trusted",
        },
      );
      installMessage.value = grantTarget.value
        ? "Selected permissions explicitly granted."
        : result.status === "denied"
          ? "Staged update denied. The current package remains active."
          : result.status === "awaiting_permissions"
            ? "Update remains staged for approval. The current package remains active."
            : result.status === "rolled_back"
              ? `Update failed verification; v${result.version} restored. See diagnostics.`
              : `Update activated: v${result.version}.`;
      grantTarget.value = null;
      stagedTarget.value = null;
    } else if (updateTarget.value && (updateFile.value || updateUrl.value)) {
      const result = updateFile.value
        ? await updatePlugin(
            updateTarget.value.plugin_id,
            updateFile.value,
            confirmation,
            installPreview.value.trust_status !== "trusted",
            replacement.value ? "replace" : "update",
          )
        : await updatePluginFromUrl(
            updateTarget.value.plugin_id,
            updateUrl.value!,
            confirmation,
            installPreview.value.digest,
            installPreview.value.trust_status !== "trusted",
            updateSource.value,
            replacement.value ? "replace" : "update",
          );
      installMessage.value =
        result.status === "awaiting_permissions"
          ? `${updateTarget.value.name}: update staged for permission approval. The current version remains active.`
          : result.status === "rolled_back"
            ? `${updateTarget.value.name}: update failed verification; v${result.version} was restored. See runtime diagnostics.`
            : `Updated ${updateTarget.value.name} to v${result.version}; ${result.permissions_requested} new permission(s) reviewed.`;
    } else if (installUrl.value) {
      const result = await installPluginFromUrl(
        installUrl.value,
        confirmation,
        installPreview.value.digest,
        installPreview.value.trust_status !== "trusted",
        installSource.value,
      );
      installMessage.value =
        `Installed ${result.name} v${result.version}; ` +
        `${result.permissions_granted} permission(s) granted and ${result.permissions_denied} denied.`;
    } else if (installFile.value) {
      const result = await installPlugin(
        installFile.value,
        confirmation,
        installPreview.value.trust_status !== "trusted",
      );
      installMessage.value =
        `Installed ${result.name} v${result.version}; ` +
        `${result.permissions_granted} permission(s) granted and ${result.permissions_denied} denied.`;
    }
    selectedFile.value = null;
    installFile.value = null;
    installUrl.value = null;
    remoteUrl.value = "";
    installPreview.value = null;
    updateTarget.value = null;
    updateFile.value = null;
    updateUrl.value = null;
    updateSource.value = {};
    await load();
    await refreshPluginExtensions();
  } catch (err) {
    error.value =
      err instanceof Error ? err.message : "Plugin installation failed.";
  } finally {
    installing.value = false;
  }
}

async function openPlugin(plugin: PluginSummary) {
  const generation = ++popupGeneration;
  selected.value = plugin;
  popupLoading.value = true;
  error.value = "";
  try {
    const [ui, logs, grants, requests, details] = await Promise.all([
      fetchPluginUi(plugin.plugin_id).catch(() => null),
      fetchPluginLogs(plugin.plugin_id).catch(() => null),
      fetchPluginPermissionGrants(),
      fetchPluginPermissionRequests(),
      fetchPluginDetails(plugin.plugin_id).catch((err: unknown) => ({
        readme: null,
        documentation_error:
          err instanceof Error
            ? err.message
            : "Unable to load installed documentation.",
      })),
    ]);
    if (
      generation !== popupGeneration ||
      selected.value?.plugin_id !== plugin.plugin_id
    )
      return;
    selected.value = { ...plugin, ...details };
    pluginUi.value = ui;
    pluginDiagnostics.value = logs;
    pluginGrants.value = grants.filter(
      (grant) => grant.plugin_id === plugin.plugin_id,
    );
    pluginRequests.value = requests.filter(
      (request) =>
        request.plugin_id === plugin.plugin_id && request.status === "pending",
    );
  } catch (err) {
    error.value =
      err instanceof Error ? err.message : "Failed to open plugin settings.";
  } finally {
    if (generation === popupGeneration) popupLoading.value = false;
  }
}

function closePlugin() {
  popupGeneration++;
  selected.value = null;
  pluginUi.value = null;
  pluginDiagnostics.value = null;
  pluginGrants.value = [];
  pluginRequests.value = [];
}

async function refreshPlugin() {
  if (selected.value) await openPlugin(selected.value);
}

async function runSelected(operation: (id: string) => Promise<void>) {
  if (!selected.value) return;
  await run(selected.value.plugin_id, operation);
}

async function revokeGrant(grantId: string) {
  if (!selected.value) return;
  action.value = selected.value.plugin_id;
  try {
    await revokePluginPermission(grantId);
    await refreshPlugin();
    await refreshPluginExtensions();
  } catch (err) {
    error.value =
      err instanceof Error ? err.message : "Permission revocation failed.";
  } finally {
    action.value = "";
  }
}

async function resolveRequest(requestId: string, approved: boolean) {
  if (!selected.value) return;
  action.value = selected.value.plugin_id;
  try {
    await (approved
      ? approvePluginPermission(requestId)
      : denyPluginPermission(requestId));
    await refreshPlugin();
  } catch (err) {
    error.value =
      err instanceof Error ? err.message : "Permission review failed.";
  } finally {
    action.value = "";
  }
}

async function savePlugin(values: UiValues) {
  if (!selected.value) return;
  const response = await fetch(
    `/api/plugins/${encodeURIComponent(selected.value.plugin_id)}/settings`,
    {
      method: "PUT",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(values),
    },
  );
  if (!response.ok) throw new Error("Plugin settings could not be saved.");
}

async function runPluginAction(item: UiAction, values: UiValues) {
  if (!selected.value) return;
  const response = await fetch(
    `/api/plugins/${encodeURIComponent(selected.value.plugin_id)}/actions/${encodeURIComponent(item.id)}`,
    {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ values }),
    },
  );
  if (!response.ok) throw new Error("Plugin action could not be completed.");
  await refreshPlugin();
}

async function updateSelected(plugin: PluginSummary, event: Event) {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file) return;
  await reviewUpdatePackage(plugin, file);
  input.value = "";
}

async function reviewUpdatePackage(plugin: PluginSummary, file: File) {
  if (installing.value || previewing.value) return;
  previewing.value = true;
  error.value = "";
  try {
    replacement.value = false;
    updateTarget.value = plugin;
    updateFile.value = file;
    updateUrl.value = null;
    updateSource.value = {};
    installFile.value = file;
    installUrl.value = null;
    installPreview.value = await previewPluginUpdate(plugin.plugin_id, file);
    selected.value = null;
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Plugin update failed.";
  } finally {
    previewing.value = false;
  }
}

async function reviewAvailableUpdate(plugin: PluginSummary) {
  if (plugin.staged_update) {
    stagedTarget.value = plugin.plugin_id;
    installPreview.value = await previewStagedUpdate(plugin.plugin_id);
    return;
  }
  const update = availableUpdates.value[plugin.plugin_id];
  if (!update?.url) return;
  previewing.value = true;
  error.value = "";
  try {
    const source = {
      ...(update.source ?? {}),
      release_notes: update.release_notes,
      changelog_url: update.changelog_url,
    };
    updateTarget.value = plugin;
    updateFile.value = null;
    updateUrl.value = update.url;
    updateSource.value = source;
    installFile.value = null;
    installUrl.value = null;
    installPreview.value = await previewPluginUpdateUrl(
      plugin.plugin_id,
      update.url,
      source,
    );
  } catch (err) {
    error.value =
      err instanceof Error ? err.message : "Plugin update preview failed.";
  } finally {
    previewing.value = false;
  }
}

async function refreshUpdates() {
  checkingUpdates.value = true;
  error.value = "";
  try {
    const result = await checkPluginUpdates();
    plugins.value = plugins.value.map((plugin) => ({
      ...plugin,
      available_update: result.updates.find(
        (update) => update.plugin_id === plugin.plugin_id,
      ),
    }));
    availableUpdates.value = Object.fromEntries(
      result.updates
        .filter((update) => update.update_available)
        .map((update) => [update.plugin_id, update]),
    );
    installMessage.value = result.available
      ? `${result.available} plugin update(s) available. Notifications were added for administrators.`
      : "All update-capable plugins are current.";
  } catch (err) {
    error.value =
      err instanceof Error ? err.message : "Plugin update check failed.";
  } finally {
    checkingUpdates.value = false;
  }
}

async function removePlugin(plugin: PluginSummary) {
  if (!window.confirm(`Delete ${plugin.name} and its stored plugin data?`))
    return;
  action.value = plugin.plugin_id;
  error.value = "";
  try {
    await deletePlugin(plugin.plugin_id);
    if (selected.value?.plugin_id === plugin.plugin_id) closePlugin();
    await load();
    await refreshPluginExtensions();
  } catch (err) {
    error.value =
      err instanceof Error ? err.message : "Plugin deletion failed.";
  } finally {
    action.value = "";
  }
}

onMounted(() => {
  void load();
  void loadManagerSettings();
});
</script>

<template>
  <section class="plugin-manager">
    <h2>Plugins</h2>
    <p class="muted">
      Browse plugins, review access, and manage installed releases and
      persistent data.
    </p>
    <PluginIsolationWarning
      v-if="runtime"
      ref="isolationWarning"
      :runtime="runtime"
      :busy="managerSettingsBusy"
      :error="managerSettingsError"
      @approve="approveReducedIsolation"
      @cancel="pendingIsolationInstall = null"
    />
    <PluginGatewayWarning v-if="runtime" :runtime="runtime" />
    <details
      v-if="runtime"
      class="manager-settings"
      :open="
        runtime.version_health === 'incompatible' ||
        runtime.gateway_configured === false
      "
    >
      <summary>Plugin platform versions & health</summary>
      <dl>
        <div>
          <dt>Version health</dt>
          <dd>{{ runtime.version_health ?? "Not reported" }}</dd>
        </div>
        <div>
          <dt>UI/API contract</dt>
          <dd>
            Host {{ runtime.host_api_contract_version ?? "Not reported" }} ·
            Runtime {{ runtime.api_contract_version ?? "Not reported" }}
          </dd>
        </div>
        <div>
          <dt>Plugin SDK compatibility version</dt>
          <dd>
            Host {{ runtime.host_sdk_version ?? "Not reported" }} · Runtime
            {{ runtime.sdk_version ?? "Not reported" }}
          </dd>
        </div>
        <div>
          <dt>Application compatibility version</dt>
          <dd>
            Host {{ runtime.host_application_version ?? "Not reported" }} ·
            Runtime {{ runtime.application_version ?? "Not reported" }}
          </dd>
        </div>
        <div>
          <dt>Gateway protocol</dt>
          <dd>
            {{ runtime.api_version ?? "Not reported" }} ·
            {{ runtime.plugin_transport ?? "Not reported" }}
          </dd>
        </div>
        <div>
          <dt>Gateway configuration</dt>
          <dd>
            {{
              runtime.gateway_configured === true
                ? "Configured"
                : runtime.gateway_configured === false
                  ? "Needs repair"
                  : "Not reported"
            }}
            <template v-if="runtime.gateway_configured">
              ·
              {{
                runtime.gateway_configuration_source === "host"
                  ? "App service"
                  : "Runtime service"
              }}
            </template>
          </dd>
        </div>
      </dl>
      <p class="muted">
        Compatibility versions are the targets checked against plugin manifests.
        Package release numbers and the gateway protocol are separate. Update
        host and runtime together when these targets differ.
      </p>
      <p v-if="runtime.version_error" class="error" role="alert">
        {{ runtime.version_error }}
      </p>
      <p v-if="runtime.version_health === 'unavailable'" class="error">
        Version checks are unavailable until the plugin runtime reconnects.
      </p>
    </details>
    <details class="manager-settings">
      <summary>Plugin Manager settings</summary>
      <p class="muted">
        Control catalogue updates and retained package history for this server.
      </p>
      <p v-if="managerSettingsError" role="alert" class="error">
        {{ managerSettingsError }}
      </p>
      <p v-if="managerSettingsMessage" role="status" class="success">
        {{ managerSettingsMessage }}
      </p>
      <fieldset :disabled="!managerSettingsLoaded || managerSettingsBusy">
        <div
          v-if="managerSettings.reduced_isolation_acknowledged"
          class="manager-setting"
        >
          <span
            ><strong>Reduced isolation acknowledged</strong
            ><small
              >Approval applies to this server. Withdrawing it stops plugins
              when Bubblewrap is unavailable, unless the deployment override is
              enabled.</small
            ></span
          >
          <button type="button" @click="withdrawReducedIsolation">
            Withdraw approval
          </button>
        </div>
        <label class="manager-setting"
          ><input v-model="managerSettings.automatic_updates" type="checkbox" />
          <span
            ><strong>Automatic catalogue updates</strong
            ><small
              >Allow eligible catalogue releases to update automatically. New
              permissions still require approval.</small
            ></span
          ></label
        >
        <label class="manager-setting"
          ><span
            ><strong>Old package versions to retain</strong
            ><small
              >Keep 1–100 package versions for rollback. Plugin data is stored
              separately.</small
            ></span
          >
          <input
            v-model.number="managerSettings.retained_versions"
            type="number"
            min="1"
            max="100"
            aria-label="Old package versions to retain"
        /></label>
        <p v-if="!retainedVersionsValid" role="alert" class="error">
          Enter a whole number from 1 to 100.
        </p>
        <button
          type="button"
          class="primary"
          :disabled="!retainedVersionsValid"
          @click="saveGlobalSettings"
        >
          {{ managerSettingsBusy ? "Saving…" : "Save manager settings" }}
        </button>
      </fieldset>
      <button
        v-if="!managerSettingsLoaded"
        type="button"
        @click="loadManagerSettings"
      >
        Retry loading settings
      </button>
    </details>
    <nav class="manager-tabs" aria-label="Plugin views">
      <button
        v-for="item in [
          'Installed',
          'Updates Available',
          'Discover',
        ] as ManagerView[]"
        :key="item"
        :aria-pressed="view === item"
        @click="view = item"
      >
        {{ item }}
      </button>
    </nav>
    <div class="manager-filters">
      <input
        v-model="search"
        type="search"
        placeholder="Filter plugins"
        aria-label="Filter plugins"
      /><select v-model="tag" aria-label="Filter by tag">
        <option value="">All tags</option>
        <option v-for="item in tags" :key="item">{{ item }}</option>
      </select>
      <select v-model="channel" aria-label="Filter by plugin source">
        <option value="">All sources</option>
        <option value="official">Official</option>
        <option value="demo">Examples</option>
        <option value="community">Community / unverified</option>
      </select>
    </div>
    <p v-for="error in catalogueErrors" :key="error" role="alert" class="muted">
      {{ error }}
    </p>
    <PluginPackageDropZone
      class="installer-launcher"
      :busy="installing || previewing"
      @package="reviewDroppedPackage"
    >
      <button
        type="button"
        class="primary install-launcher"
        v-if="view !== 'Discover'"
        :disabled="installing || previewing"
        @click="discoverPlugins"
      >
        Install a plugin
      </button>
      <button
        type="button"
        :disabled="installing || previewing"
        @click="openInstaller"
      >
        Install package or URL
      </button>
      <button type="button" :disabled="checkingUpdates" @click="refreshUpdates">
        {{ checkingUpdates ? "Checking…" : "Check for updates" }}
      </button>
      <p class="muted">
        Discover a plugin and review its access before installing. Use Updates
        Available to review updates; click an installed plugin for
        configuration, permissions and retained versions.
      </p>
      <p v-if="installMessage" class="success">{{ installMessage }}</p>
    </PluginPackageDropZone>
    <details v-if="view === 'Discover'" class="catalogue discovery-sources">
      <summary>Manage catalogues</summary>
      <section>
        <div class="catalogue-header">
          <div>
            <strong>Plugin catalogues</strong>
            <p class="muted">
              The official catalogue is enabled by default. Catalogue provenance
              never replaces package signature verification.
            </p>
          </div>
        </div>
        <div
          v-for="catalogueSource in catalogues"
          :key="catalogueSource.id"
          class="endpoint-row"
        >
          <label
            ><input
              type="checkbox"
              :checked="catalogueSource.enabled"
              @change="
                toggleCatalogEndpoint(
                  catalogueSource,
                  ($event.target as HTMLInputElement).checked,
                )
              "
            />
            {{ catalogueSource.name }} · priority
            {{ catalogueSource.priority }}</label
          >
          <span class="muted">{{ catalogueSource.url }}</span>
          <span v-if="catalogueSource.last_error" class="error">{{
            catalogueSource.last_error
          }}</span>
          <button
            v-if="catalogueSource.id !== 'official'"
            type="button"
            class="danger"
            @click="removeCatalogEndpoint(catalogueSource)"
          >
            Remove
          </button>
        </div>
        <div class="endpoint-add">
          <input
            v-model="newCatalogEndpoint"
            type="url"
            placeholder="https://example.com/list.json"
            aria-label="New catalogue URL"
            @keyup.enter="addCatalogEndpoint"
          /><button
            type="button"
            :disabled="!newCatalogEndpoint.trim()"
            @click="addCatalogEndpoint"
          >
            Add catalogue
          </button>
        </div>
      </section>
    </details>
    <p v-if="view === 'Discover'" class="muted discovery-note">
      Official plugins and examples are listed separately. Source categories use
      the trusted publisher registry; package signatures, compatibility and
      permissions are checked during review.
    </p>
    <UiModal
      v-if="installOpen"
      title="Install package or URL"
      size="wide"
      description="Review a local package or a public package URL before installing."
      :dismissible="!installing"
      @close="closeInstaller"
    >
      <section class="installer-dialog installer-browser">
        <p v-if="error" class="error" role="alert">{{ error }}</p>
        <div class="installer-methods">
          <details class="install-method" open>
            <summary>Upload package</summary>
            <div>
              <p class="muted">
                Choose a plugin package to review its publisher and requested
                access.
              </p>
              <input
                id="plugin-package"
                aria-label="Plugin package"
                type="file"
                accept="*/*"
                @change="selectFile"
              />
              <button
                type="button"
                :disabled="!selectedFile || previewing || installing"
                @click="previewSelected"
              >
                {{ previewing ? "Inspecting…" : "Review package" }}
              </button>
            </div>
          </details>
          <details class="install-method">
            <summary>Install from URL</summary>
            <div>
              <p class="muted">Enter the public URL of a plugin package.</p>
              <div class="url-row">
                <input
                  v-model="remoteUrl"
                  type="url"
                  placeholder="https://example.com/plugin.utp"
                  aria-label="Plugin package URL"
                  @keyup.enter="previewRemoteUrl()"
                /><button
                  type="button"
                  :disabled="!remoteUrl.trim() || previewing || installing"
                  @click="previewRemoteUrl()"
                >
                  Review URL
                </button>
              </div>
            </div>
          </details>
        </div>
      </section>
    </UiModal>
    <p v-if="loading">Loading plugins…</p>
    <p v-if="cataloguesLoading" class="muted">Refreshing catalogues…</p>
    <p v-if="!loading && !entries.length" class="muted">
      {{
        view === "Installed" && !plugins.length
          ? "No plugins installed yet. Choose Install a plugin to browse the catalogue, or install a package you already have."
          : "No plugins match these filters."
      }}
    </p>
    <div v-if="!loading && entries.length" class="list">
      <template v-for="group in catalogueGroups" :key="group.id">
        <h3 class="catalogue-group-heading">{{ group.label }}</h3>
        <article
          v-for="entry in group.entries"
          :key="entry.plugin_id"
          class="plugin"
        >
          <img
            v-if="entry.icon"
            :src="entry.icon"
            alt=""
            width="48"
            height="48"
          />
          <h3>
            <button
              class="plugin-title"
              :disabled="previewing || installing"
              @click="previewCatalogEntry(entry, 'overview')"
            >
              {{ entry.name }}<span aria-hidden="true"> →</span>
            </button>
          </h3>
          <span class="source-category">{{
            pluginChannel(entry) === "official"
              ? "Official"
              : pluginChannel(entry) === "demo"
                ? "Example"
                : "Community / unverified"
          }}</span>
          <p
            v-if="
              plugins.some((plugin) => plugin.plugin_id === entry.plugin_id)
            "
            class="muted"
          >
            Already installed · select a release to review an update or
            replacement
          </p>
          <p>{{ entry.description }}</p>
          <p>
            {{ entry.publisher ?? "Publisher information not supplied" }} · v{{
              entry.version
            }}
            · {{ entry.compatibility ?? "Compatibility checked during review" }}
          </p>
          <p>{{ entry.tags?.join(" · ") }}</p>
          <label class="release-picker"
            >Release
            <select
              :value="selectedVersions[entry.plugin_id] ?? entry.version"
              :aria-label="`Release for ${entry.name}`"
              @change="
                selectedVersions[entry.plugin_id] = (
                  $event.target as HTMLSelectElement
                ).value
              "
            >
              <option
                v-for="release in catalogueVersions(entry)"
                :key="release.version"
                :value="release.version"
              >
                v{{ release.version
                }}{{
                  release.version === entry.version
                    ? " · Latest"
                    : " · Pins automatic updates"
                }}
              </option>
            </select>
          </label>
          <button
            :disabled="previewing || installing"
            @click="previewCatalogEntry(entry)"
          >
            Review {{ selectedVersions[entry.plugin_id] ?? entry.version }}
          </button>
        </article>
      </template>
      <PluginPackageDropZone
        v-for="plugin in installedEntries"
        :key="plugin.plugin_id"
        class="plugin"
        tag="article"
        :busy="previewing || installing || action === plugin.plugin_id"
        :label="`Update package for ${plugin.name}`"
        :show-hint="false"
        @package="reviewUpdatePackage(plugin, $event)"
      >
        <header>
          <div>
            <img
              v-if="plugin.icon"
              :src="plugin.icon"
              alt=""
              width="48"
              height="48"
            />
            <h3>
              <button class="plugin-title" @click="openPlugin(plugin)">
                {{ plugin.name }}<span aria-hidden="true"> →</span>
              </button>
            </h3>
            <span>{{ plugin.plugin_id }} · v{{ plugin.version }}</span>
          </div>
          <strong>{{ plugin.status }}</strong>
        </header>
        <p>
          {{
            plugin.compatible
              ? "Compatible with the current host."
              : `Incompatible: ${plugin.compatibility_reason}`
          }}
        </p>
        <p v-if="plugin.staged_update" class="muted">
          Staged v{{
            plugin.staged_update.available_version ??
            plugin.staged_update.version
          }}
          · {{ plugin.staged_update.status.replaceAll("_", " ") }} · Installed
          release remains v{{ plugin.version }}
        </p>
        <p v-if="plugin.version_pin" class="muted">
          Pinned to v{{ plugin.version_pin }} · automatic updates disabled
        </p>
        <dl>
          <div>
            <dt>Publisher trust</dt>
            <dd>
              {{
                plugin.trust?.status === "trusted"
                  ? plugin.trust?.publisher_channel === "official"
                    ? "Official · verified"
                    : plugin.trust?.publisher_channel === "demo"
                      ? "Demo/example · verified"
                      : "Community · verified"
                  : (plugin.trust?.status ?? "Unverified")
              }}
            </dd>
          </div>
          <div>
            <dt>Health</dt>
            <dd>{{ plugin.health }}</dd>
          </div>
          <div>
            <dt>Permissions</dt>
            <dd>{{ plugin.permissions.length }}</dd>
          </div>
          <div>
            <dt>Enabled</dt>
            <dd>{{ plugin.enabled ? "Yes" : "No" }}</dd>
          </div>
        </dl>
        <div class="actions">
          <button
            type="button"
            :disabled="action === plugin.plugin_id"
            @click="openPlugin(plugin)"
          >
            Settings & access
          </button>
          <label class="file-button"
            >Upload update<input
              type="file"
              accept="*/*"
              :disabled="action === plugin.plugin_id"
              @change="updateSelected(plugin, $event)"
          /></label>
          <button
            v-if="
              availableUpdates[plugin.plugin_id]?.update_available ||
              plugin.staged_update
            "
            type="button"
            :disabled="previewing"
            @click="reviewAvailableUpdate(plugin)"
          >
            Review v{{
              availableUpdates[plugin.plugin_id]?.available_version ??
              plugin.staged_update?.available_version ??
              plugin.staged_update?.version
            }}
            update
          </button>
          <button
            type="button"
            class="danger"
            :disabled="action === plugin.plugin_id"
            @click="removePlugin(plugin)"
          >
            Uninstall
          </button>
        </div>
      </PluginPackageDropZone>
    </div>

    <PluginInstallConsentDialog
      v-if="installPreview && !duplicate"
      :preview="installPreview"
      :busy="installing"
      :initial-view="reviewView"
      :error="error"
      @cancel="cancelInstall"
      @confirm="confirmInstall"
    />
    <UiModal
      v-if="duplicate"
      :title="`${duplicate.name} is already installed`"
      :dismissible="!previewing"
      @close="cancelInstall"
    >
      <section class="installer-dialog">
        <p v-if="error" class="error" role="alert">{{ error }}</p>
        <p>
          Installed v{{ duplicate.version }}; selected v{{
            installPreview?.version
          }}. Choose the operation explicitly.
        </p>
        <button :disabled="previewing" @click="chooseDuplicate('update')">
          Review update</button
        ><button :disabled="previewing" @click="chooseDuplicate('reinstall')">
          Reinstall installed release, retaining data</button
        ><button :disabled="previewing" @click="chooseDuplicate('replace')">
          Replace package</button
        ><button :disabled="previewing" @click="cancelInstall">Cancel</button>
      </section>
    </UiModal>
    <PluginSettingsDialog
      v-if="selected"
      :plugin="selected"
      :document="pluginUi"
      :grants="pluginGrants"
      :requests="pluginRequests"
      :diagnostics="pluginDiagnostics"
      :loading="popupLoading"
      :busy="action === selected.plugin_id || previewing || installing"
      :error="error"
      @close="closePlugin"
      @save="savePlugin"
      @action="runPluginAction"
      @enable="runSelected(enablePlugin)"
      @disable="runSelected(disablePlugin)"
      @retry="runSelected(retryPlugin)"
      @revoke="revokeGrant"
      @approve="resolveRequest($event, true)"
      @deny="resolveRequest($event, false)"
      @refresh="refreshPlugin"
      @update="reviewAvailableUpdate(selected)"
      @update-package="reviewUpdatePackage(selected, $event)"
      @operation="lifecycleOperation"
      @auto-update="autoUpdateSelected"
      @grant="reviewGrant"
      @delete-history="deleteHistory"
    />
    <PluginVersionConfirmationDialog
      v-if="pendingVersionInstall && installPreview"
      :installed="installPreview.installed_version ?? ''"
      :candidate="installPreview.version"
      :downgrade="installPreview.version_change === 'downgrade'"
      @cancel="pendingVersionInstall = null"
      @confirm="
        () => {
          const confirmation = pendingVersionInstall;
          pendingVersionInstall = null;
          if (confirmation)
            confirmInstall({ ...confirmation, versionChangeConfirmed: true });
        }
      "
    />
    <UiModal
      v-if="operationError"
      title="Plugin operation failed"
      @close="
        operationError = '';
        error = '';
      "
    >
      <p class="error" role="alert">{{ operationError }}</p>
      <template #footer
        ><button
          type="button"
          class="ui-btn ui-btn-primary"
          @click="
            operationError = '';
            error = '';
          "
        >
          Close
        </button></template
      >
    </UiModal>
  </section>
</template>

<style scoped src="../../styles/settings/plugin-manager.css"></style>
