<script setup lang="ts">
import type { TrashedGameFile } from "../../services/media";
import {
  worldMapViewUrl,
  worldMapThumbnailUrl,
} from "../../services/gameArchives";
import GameMediaPanel from "../GameMediaPanel.vue";
import GameArchivesPanel from "../GameArchivesPanel.vue";
import ArchiveCard from "../ArchiveCard.vue";
import { useGameDetailContext } from "../../composables/gameDetailContext";
const {
  game,
  modpackFiles,
  filesLoaded,
  filesError,
  uploadingFiles,
  onGameFilesSelected,
  saveGameFile,
  bulkSaveFiles,
  removeGameFile,
  modpackTrash,
  restoreFileItem,
  saveUploading,
  openArchiveEdit,
  bulkDeleteArchives,
  onDeleteArchive,
  worldTrash,
  onRestoreArchive,
  worldMaps,
  worldMapsLoaded,
  worldMapStarting,
  activeMapArchiveId,
  onNewWorldSelected,
  onAddWorldVersion,
  startWorldMapRender,
  viewWorldMap,
} = useGameDetailContext();
</script>
<template>
  <section v-if="game" class="world-map-panel">
    <GameArchivesPanel
      scoped
      title="Worlds"
      plural="worlds"
      singular="world"
      hint="Zip the world folder (the one containing level.dat), then drop it here. You'll be asked to name it."
      :archives="worldMaps"
      :trash="worldTrash"
      :loaded="worldMapsLoaded"
      :uploading="saveUploading.has('')"
      :error="filesError"
      @files="onNewWorldSelected"
      @bulk-delete="bulkDeleteArchives($event, true)"
      @restore="onRestoreArchive($event, true)"
      @problem="filesError = $event"
    >
      <template #card="{ archive: world, selecting, selected, toggle }">
        <ArchiveCard
          :archive="world"
          kind="world"
          :selecting="selecting"
          :selected="selected"
          :uploading="saveUploading.has(world.id)"
          :thumbnail-url="
            world.has_thumbnail ? worldMapThumbnailUrl(game.id, world.id) : null
          "
          :rendering="world.status === 'rendering'"
          @toggle="toggle"
          @open="viewWorldMap($event.id)"
          @edit="openArchiveEdit($event, true)"
          @delete="onDeleteArchive($event, true)"
          @add-version="onAddWorldVersion"
        >
          <span class="world-map-status" :class="world.status">{{
            world.detail || world.status
          }}</span>
          <div class="world-map-card-actions">
            <button
              type="button"
              class="secondary-button small"
              :disabled="
                worldMapStarting.has(world.id) || world.status === 'rendering'
              "
              @click="startWorldMapRender(world.id)"
            >
              {{
                world.status === "rendering"
                  ? "Rendering…"
                  : world.has_thumbnail
                    ? "Re-render"
                    : "Render Map"
              }}
            </button>
            <button
              v-if="world.has_thumbnail"
              type="button"
              class="primary-button small"
              @click="viewWorldMap(world.id)"
            >
              View Map
            </button>
          </div>
        </ArchiveCard>
      </template>
      <template #after>
        <iframe
          v-if="activeMapArchiveId"
          :src="worldMapViewUrl(game.id, activeMapArchiveId)"
          class="world-map-frame"
          title="World map"
        ></iframe>
      </template>
    </GameArchivesPanel>

    <div class="modpack-block">
      <GameMediaPanel
        scoped
        kind="modpack"
        :items="modpackFiles"
        :trash="modpackTrash"
        :loading="filesLoaded.modpack === null"
        :uploading="uploadingFiles"
        :error="null"
        @files="onGameFilesSelected($event, 'modpack')"
        @delete="removeGameFile('modpack', $event)"
        @save="(item, patch) => saveGameFile('modpack', item, patch)"
        @bulk-save="bulkSaveFiles('modpack', $event)"
        @bulk-delete="
          (items) => items.forEach((f) => removeGameFile('modpack', f))
        "
        @restore="restoreFileItem('modpack', $event as TrashedGameFile)"
        @problem="filesError = $event"
      />
    </div>
  </section>
</template>
