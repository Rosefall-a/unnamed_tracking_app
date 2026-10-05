<script setup lang="ts">
import UploadDropzone from "../UploadDropzone.vue";
import ViewUploadSidebar from "../ViewUploadSidebar.vue";
import { useGameDetailContext } from "../../composables/gameDetailContext";
const {
  game,
  worldMapViewUrl,
  worldMapThumbnailUrl,
  panelMode,
  onDropError,
  modpackFiles,
  filesError,
  uploadingFiles,
  onGameFilesSelected,
  removeGameFile,
  modpackTrash,
  showModpackTrash,
  restoreFileItem,
  formatFileSize,
  saveUploading,
  onRenameArchive,
  onDeleteArchive,
  worldTrash,
  showWorldTrash,
  daysUntil,
  onRestoreArchive,
  worldMaps,
  worldMapsLoaded,
  worldMapStarting,
  activeMapArchiveId,
  onNewWorldSelected,
  onAddWorldVersion,
  startWorldMapRender,
  viewWorldMap,
  displayFileName,
} = useGameDetailContext();
</script>
<template>
  <section v-if="game" class="world-map-panel">
    <h2>World Map</h2>
    <div class="panel-body">
      <ViewUploadSidebar v-model="panelMode" />
      <div class="panel-content">
        <template v-if="panelMode === 'upload'">
          <div class="world-map-uploads">
            <div class="world-map-upload-col">
              <h3>New World</h3>
              <UploadDropzone
                accept="*/*"
                :uploading="saveUploading.has('')"
                title="Drop a world save .zip here"
                hint="Zip the world folder (the one containing level.dat): you'll be asked to name it"
                @files-selected="onNewWorldSelected"
                @drop-error="onDropError"
              />
            </div>

            <div class="world-map-upload-col">
              <h3>Modpack</h3>
              <UploadDropzone
                accept="*/*"
                :uploading="uploadingFiles"
                title="Drop your modpack .zip here"
                hint="Optional: kept alongside for reference, not tied to a specific world"
                @files-selected="onGameFilesSelected($event, 'modpack')"
                @drop-error="onDropError"
              />
              <ul v-if="modpackFiles.length" class="file-list">
                <li
                  v-for="file in modpackFiles"
                  :key="file.filename"
                  class="file-row"
                >
                  <a
                    :href="file.url"
                    class="file-name"
                    target="_blank"
                    rel="noopener noreferrer"
                    >{{ displayFileName(file.filename) }}</a
                  >
                  <span class="file-size">{{ formatFileSize(file.size) }}</span>
                  <button
                    type="button"
                    class="tile-remove-inline"
                    title="Delete"
                    @click="removeGameFile('modpack', file)"
                  >
                    ✕
                  </button>
                </li>
              </ul>
              <div v-if="modpackTrash.length" class="trash-section">
                <button
                  type="button"
                  class="trash-toggle"
                  @click="showModpackTrash = !showModpackTrash"
                >
                  {{ showModpackTrash ? "▾" : "▸" }} Recently deleted ({{
                    modpackTrash.length
                  }})
                </button>
                <ul v-if="showModpackTrash" class="trash-list">
                  <li
                    v-for="file in modpackTrash"
                    :key="file.filename"
                    class="trash-row"
                  >
                    <span class="trash-name">{{
                      displayFileName(file.filename)
                    }}</span>
                    <span class="trash-meta"
                      >purges in {{ daysUntil(file.purge_at) }}d</span
                    >
                    <button
                      type="button"
                      class="secondary-button small"
                      @click="restoreFileItem('modpack', file)"
                    >
                      Restore
                    </button>
                  </li>
                </ul>
              </div>
            </div>
          </div>
          <div v-if="filesError" class="form-error">{{ filesError }}</div>
        </template>

        <template v-else>
          <div v-if="worldMaps.length" class="world-map-grid">
            <div
              v-for="world in worldMaps"
              :key="world.id"
              class="world-map-card"
              :class="{ rendering: world.status === 'rendering' }"
            >
              <div
                class="world-map-thumb"
                @click="
                  world.has_thumbnail ? viewWorldMap(world.id) : undefined
                "
              >
                <img
                  v-if="world.has_thumbnail"
                  :src="worldMapThumbnailUrl(game.id, world.id)"
                  alt=""
                />
                <div v-else class="world-map-thumb-placeholder">
                  <svg
                    viewBox="0 0 24 24"
                    width="28"
                    height="28"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="1.5"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                  >
                    <path d="M3 6l6-3 6 3 6-3v15l-6 3-6-3-6 3z" />
                    <path d="M9 3v15M15 6v15" />
                  </svg>
                </div>
                <div
                  v-if="world.status === 'rendering'"
                  class="world-map-progress"
                >
                  <div class="world-map-progress-fill"></div>
                </div>
              </div>
              <div class="world-map-card-body">
                <div class="archive-card-header">
                  <span class="archive-name">{{ world.name }}</span>
                  <div class="archive-card-actions">
                    <button
                      type="button"
                      class="icon-button"
                      title="Rename"
                      @click="onRenameArchive(world, true)"
                    >
                      ✎
                    </button>
                    <button
                      type="button"
                      class="icon-button"
                      title="Delete"
                      @click="onDeleteArchive(world, true)"
                    >
                      ✕
                    </button>
                  </div>
                </div>
                <span class="world-map-status" :class="world.status">{{
                  world.detail || world.status
                }}</span>
                <div class="world-map-card-actions">
                  <button
                    type="button"
                    class="secondary-button small"
                    :disabled="
                      worldMapStarting.has(world.id) ||
                      world.status === 'rendering'
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
                  <label class="secondary-button small upload-label">
                    {{
                      saveUploading.has(world.id) ? "Uploading…" : "New version"
                    }}
                    <input
                      type="file"
                      class="hidden-input"
                      :disabled="saveUploading.has(world.id)"
                      @change="
                        onAddWorldVersion(
                          world,
                          Array.from(
                            ($event.target as HTMLInputElement).files ?? [],
                          ),
                        )
                      "
                    />
                  </label>
                </div>
              </div>
            </div>
          </div>
          <p v-else-if="worldMapsLoaded" class="empty-row">
            No worlds yet: switch to Upload to add a world save.
          </p>

          <div v-if="worldTrash.length" class="trash-section">
            <button
              type="button"
              class="trash-toggle"
              @click="showWorldTrash = !showWorldTrash"
            >
              {{ showWorldTrash ? "▾" : "▸" }} Recently deleted ({{
                worldTrash.length
              }})
            </button>
            <ul v-if="showWorldTrash" class="trash-list">
              <li v-for="world in worldTrash" :key="world.id" class="trash-row">
                <span class="trash-name">{{ world.name }}</span>
                <span class="trash-meta"
                  >purges in {{ daysUntil(world.purge_at) }}d</span
                >
                <button
                  type="button"
                  class="secondary-button small"
                  @click="onRestoreArchive(world, true)"
                >
                  Restore
                </button>
              </li>
            </ul>
          </div>

          <iframe
            v-if="activeMapArchiveId"
            :src="worldMapViewUrl(game.id, activeMapArchiveId)"
            class="world-map-frame"
            title="World map"
          ></iframe>
        </template>
      </div>
    </div>
  </section>
</template>
