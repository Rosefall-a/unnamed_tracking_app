import { ref, onUnmounted, type Ref } from "vue";
import type { Game } from "../types/game";
import {
  createArchive,
  addArchiveVersion,
  fetchWorldMaps,
  renderWorldMap,
  type WorldMapEntry,
} from "../services/gameArchives";
import {
  startTask,
  updateTask,
  completeTask,
  errorTask,
  setTaskRetry,
} from "../state/taskProgress";
import { usePrompt } from "../state/dialog";
export function useGameWorldMaps(
  game: Ref<Game | null>,
  saveUploading: Ref<Set<string>>,
  prompt: ReturnType<typeof usePrompt>,
  filesError: Ref<string | null>,
) {
  // --- World Map (BlueMap render of a world_save archive) --------------------
  // a game (e.g. a modpack) can have several worlds, one card, many worlds,
  // each named, versioned, rendered, and viewed independently
  const worldMaps = ref<WorldMapEntry[]>([]);
  const worldMapsLoaded = ref(false);
  const worldMapStarting = ref<Set<string>>(new Set());
  const activeMapArchiveId = ref<string | null>(null);
  let worldMapPollTimer: ReturnType<typeof setInterval> | null = null;

  function stopWorldMapPolling() {
    if (worldMapPollTimer) {
      clearInterval(worldMapPollTimer);
      worldMapPollTimer = null;
    }
  }

  async function refreshWorldMaps() {
    if (!game.value) return;
    try {
      worldMaps.value = await fetchWorldMaps(game.value.id);
      worldMapsLoaded.value = true;
      const anyRendering = worldMaps.value.some(
        (w) => w.status === "rendering",
      );
      if (anyRendering && !worldMapPollTimer) {
        // no push mechanism for a background render, poll every few
        // seconds only while at least one world is actually in flight
        worldMapPollTimer = setInterval(refreshWorldMaps, 4000);
      } else if (!anyRendering) {
        stopWorldMapPolling();
      }
    } catch {
      // list just doesn't update this tick, not worth surfacing an error
      // for a polling request
    }
  }

  async function onNewWorldSelected(files: File[]) {
    const file = files[0];
    if (!file || !game.value) return;
    const gameId = game.value.id;
    const name = await prompt({
      title: "Name this world",
      message: "World name",
      defaultValue: file.name.replace(/\.[^.]+$/, ""),
      confirmLabel: "Upload",
    });
    if (!name || !name.trim()) return;
    const trimmedName = name.trim();
    const taskId = startTask(`Uploading "${trimmedName}"`, 100);

    const attempt = async () => {
      saveUploading.value = new Set(saveUploading.value).add("");
      try {
        await createArchive(
          gameId,
          "world_save",
          trimmedName,
          file,
          (f, speedLabel) =>
            updateTask(taskId, Math.round(f * 100), undefined, speedLabel),
        );
        completeTask(taskId, "Saved");
        await refreshWorldMaps();
      } catch (err) {
        errorTask(taskId, err instanceof Error ? err.message : "Upload failed");
        setTaskRetry(taskId, () => void attempt());
      } finally {
        const next = new Set(saveUploading.value);
        next.delete("");
        saveUploading.value = next;
      }
    };
    await attempt();
  }

  async function onAddWorldVersion(archive: WorldMapEntry, files: File[]) {
    const file = files[0];
    if (!file || !game.value) return;
    const gameId = game.value.id;
    const taskId = startTask(`Uploading new version of "${archive.name}"`, 100);

    const attempt = async () => {
      saveUploading.value = new Set(saveUploading.value).add(archive.id);
      try {
        await addArchiveVersion(gameId, archive.id, file, (f, speedLabel) =>
          updateTask(taskId, Math.round(f * 100), undefined, speedLabel),
        );
        completeTask(taskId, "Saved: render again to update the map");
        await refreshWorldMaps();
      } catch (err) {
        errorTask(taskId, err instanceof Error ? err.message : "Upload failed");
        setTaskRetry(taskId, () => void attempt());
      } finally {
        const next = new Set(saveUploading.value);
        next.delete(archive.id);
        saveUploading.value = next;
      }
    };
    await attempt();
  }

  async function startWorldMapRender(archiveId: string) {
    if (!game.value) return;
    worldMapStarting.value = new Set(worldMapStarting.value).add(archiveId);
    filesError.value = null;
    try {
      await renderWorldMap(game.value.id, archiveId);
      await refreshWorldMaps();
    } catch (err) {
      filesError.value =
        err instanceof Error ? err.message : "Failed to start render";
    } finally {
      const next = new Set(worldMapStarting.value);
      next.delete(archiveId);
      worldMapStarting.value = next;
    }
  }

  function viewWorldMap(archiveId: string) {
    activeMapArchiveId.value = archiveId;
  }

  onUnmounted(stopWorldMapPolling);

  return {
    worldMaps,
    worldMapsLoaded,
    worldMapStarting,
    activeMapArchiveId,
    stopWorldMapPolling,
    refreshWorldMaps,
    onNewWorldSelected,
    onAddWorldVersion,
    startWorldMapRender,
    viewWorldMap,
  };
}
