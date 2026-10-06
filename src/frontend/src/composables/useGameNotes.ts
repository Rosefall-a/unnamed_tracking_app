import { computed, ref, type Ref } from "vue";
import type { Game } from "../types/game";
import {
  createGameNote,
  deleteGameNote,
  fetchGameNote,
  renameGameNote,
  listGameNotes,
  saveGameNote,
} from "../services/games";
import { marked } from "marked";
import DOMPurify from "dompurify";
export function useGameNotes(game: Ref<Game | null>) {
  const noteNames = ref<string[]>([]);
  const noteMode = ref<"list" | "view" | "editor">("list");
  const viewingNoteName = ref<string | null>(null);
  const viewingNoteContent = ref("");
  const editingNoteName = ref<string | null>(null);
  const draftName = ref("");
  const draftContent = ref("");
  const noteLoading = ref(false);
  const noteSaving = ref(false);
  const noteError = ref<string | null>(null);

  const hasDraft = computed(
    () =>
      editingNoteName.value === null &&
      (draftName.value.trim() !== "" || draftContent.value.trim() !== ""),
  );

  const renderedNoteHtml = computed(() =>
    DOMPurify.sanitize(marked.parse(viewingNoteContent.value || "") as string),
  );

  function startNewNote() {
    if (!hasDraft.value) {
      draftName.value = "";
      draftContent.value = "";
    }
    editingNoteName.value = null;
    noteMode.value = "editor";
  }

  async function viewNote(noteName: string) {
    if (!game.value) return;
    viewingNoteName.value = noteName;
    noteLoading.value = true;
    noteError.value = null;
    try {
      viewingNoteContent.value = await fetchGameNote(game.value.id, noteName);
      noteMode.value = "view";
    } catch (err) {
      noteError.value =
        err instanceof Error ? err.message : "Failed to load note";
    } finally {
      noteLoading.value = false;
    }
  }

  function editFromView() {
    if (!viewingNoteName.value) return;
    editingNoteName.value = viewingNoteName.value;
    draftName.value = viewingNoteName.value;
    draftContent.value = viewingNoteContent.value;
    noteMode.value = "editor";
  }

  function backToList() {
    noteMode.value = "list";
    viewingNoteName.value = null;
  }

  async function saveDraft() {
    if (!game.value) return;
    const newName = draftName.value.trim();
    if (!newName) {
      noteError.value = "Enter a note name first.";
      return;
    }

    noteSaving.value = true;
    noteError.value = null;

    try {
      if (editingNoteName.value) {
        const originalName = editingNoteName.value;
        await saveGameNote(game.value.id, originalName, draftContent.value);
        if (originalName !== newName) {
          await renameGameNote(game.value.id, originalName, newName);
        }
      } else {
        await createGameNote(game.value.id, newName, draftContent.value);
      }
      editingNoteName.value = null;
      draftName.value = "";
      draftContent.value = "";
      noteMode.value = "list";
      await loadNotes();
    } catch (err) {
      noteError.value =
        err instanceof Error ? err.message : "Failed to save note";
    } finally {
      noteSaving.value = false;
    }
  }

  async function deleteNote(noteName: string) {
    if (!game.value) return;

    noteSaving.value = true;
    noteError.value = null;

    try {
      await deleteGameNote(game.value.id, noteName);
      if (
        viewingNoteName.value === noteName ||
        editingNoteName.value === noteName
      ) {
        noteMode.value = "list";
        viewingNoteName.value = null;
        editingNoteName.value = null;
      }
      await loadNotes();
    } catch (err) {
      noteError.value =
        err instanceof Error ? err.message : "Failed to delete note";
    } finally {
      noteSaving.value = false;
    }
  }

  async function loadNotes() {
    if (!game.value) {
      noteNames.value = [];
      return;
    }
    noteLoading.value = true;
    noteError.value = null;
    try {
      noteNames.value = await listGameNotes(game.value.id);
    } catch (err) {
      noteError.value =
        err instanceof Error ? err.message : "Failed to load notes";
    } finally {
      noteLoading.value = false;
    }
  }
  return {
    noteNames,
    noteMode,
    viewingNoteName,
    editingNoteName,
    draftName,
    draftContent,
    noteLoading,
    noteSaving,
    noteError,
    hasDraft,
    renderedNoteHtml,
    startNewNote,
    viewNote,
    editFromView,
    backToList,
    saveDraft,
    deleteNote,
    loadNotes,
  };
}
