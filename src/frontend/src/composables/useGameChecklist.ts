import { computed, ref } from "vue";
import {
  listChecklist,
  createChecklistItem,
  updateChecklistItem,
  deleteChecklistItem,
  reorderChecklist,
} from "../services/gameProfiles";
import type { ChecklistItem } from "../services/gameProfiles";
import type { Game } from "../types/game";
import { usePrompt } from "../state/dialog";
import type { Ref } from "vue";

export function useGameChecklist(
  game: Ref<Game | null>,
  activeProfileId: Ref<string | null>,
  prompt: ReturnType<typeof usePrompt>,
) {
  // --- Checklist (per-game, or per-profile when one account is selected) -----
  const checklistItems = ref<ChecklistItem[]>([]);
  const checklistLoading = ref(false);
  const checklistError = ref<string | null>(null);
  const newChecklistText = ref("");
  const editingItemId = ref<string | null>(null);
  const editingText = ref("");

  const checklistProgress = computed(() => {
    const real = checklistItems.value.filter((i) => !i.is_header);
    return { done: real.filter((i) => i.done).length, total: real.length };
  });

  // groups the flat, already-ordered list into sections at each header row,
  // a header just being another row in the same sort order, not a separate
  // table, keeps "move an item above/below a header" a plain reorder
  interface ChecklistSection {
    header: ChecklistItem | null;
    items: ChecklistItem[];
  }
  const checklistSections = computed<ChecklistSection[]>(() => {
    const sections: ChecklistSection[] = [{ header: null, items: [] }];
    for (const item of checklistItems.value) {
      if (item.is_header) {
        sections.push({ header: item, items: [] });
      } else {
        sections[sections.length - 1].items.push(item);
      }
    }
    return sections.filter((s) => s.header !== null || s.items.length > 0);
  });

  // collapsed section state, per game, remembered across visits
  const collapsedSections = ref<Set<string>>(new Set());
  function collapsedStorageKey(gameId: string) {
    return `checklist-collapsed-${gameId}`;
  }
  function loadCollapsedSections() {
    if (!game.value) return;
    try {
      const raw = localStorage.getItem(collapsedStorageKey(game.value.id));
      collapsedSections.value = new Set(
        raw ? (JSON.parse(raw) as string[]) : [],
      );
    } catch {
      collapsedSections.value = new Set();
    }
  }
  function saveCollapsedSections() {
    if (!game.value) return;
    try {
      localStorage.setItem(
        collapsedStorageKey(game.value.id),
        JSON.stringify([...collapsedSections.value]),
      );
    } catch {
      // best-effort, a checklist with no persisted collapse state just
      // starts fully expanded next time, not worth failing over
    }
  }
  function toggleSectionCollapsed(headerId: string) {
    if (collapsedSections.value.has(headerId))
      collapsedSections.value.delete(headerId);
    else collapsedSections.value.add(headerId);
    collapsedSections.value = new Set(collapsedSections.value);
    saveCollapsedSections();
  }
  function sectionProgress(section: ChecklistSection) {
    return {
      done: section.items.filter((i) => i.done).length,
      total: section.items.length,
    };
  }

  async function loadChecklist() {
    if (!game.value) return;
    checklistLoading.value = true;
    checklistError.value = null;
    loadCollapsedSections();
    try {
      checklistItems.value = await listChecklist(
        game.value.id,
        activeProfileId.value,
      );
    } catch (err) {
      checklistError.value =
        err instanceof Error ? err.message : "Failed to load checklist";
    } finally {
      checklistLoading.value = false;
    }
  }

  async function addChecklistItem() {
    if (!game.value) return;
    const text = newChecklistText.value.trim();
    if (!text) return;
    try {
      const created = await createChecklistItem(
        game.value.id,
        text,
        activeProfileId.value,
      );
      checklistItems.value = [...checklistItems.value, created];
      newChecklistText.value = "";
    } catch (err) {
      checklistError.value =
        err instanceof Error ? err.message : "Failed to add item";
    }
  }

  async function addChecklistSection() {
    if (!game.value) return;
    const name = await prompt({
      title: "New section",
      message: 'Section name (e.g. "Quest cape reqs")',
      confirmLabel: "Add",
    });
    const text = name?.trim();
    if (!text) return;
    createChecklistItem(game.value.id, text, activeProfileId.value, true)
      .then((created) => {
        checklistItems.value = [...checklistItems.value, created];
      })
      .catch((err) => {
        checklistError.value =
          err instanceof Error ? err.message : "Failed to add section";
      });
  }

  async function toggleChecklistItem(item: ChecklistItem) {
    if (!game.value) return;
    const next = !item.done;
    item.done = next;
    try {
      await updateChecklistItem(game.value.id, item.id, { done: next });
    } catch (err) {
      item.done = !next;
      checklistError.value =
        err instanceof Error ? err.message : "Failed to update item";
    }
  }

  function startEditItem(item: ChecklistItem) {
    editingItemId.value = item.id;
    editingText.value = item.text;
  }

  async function commitEditItem(item: ChecklistItem) {
    if (!game.value) return;
    const text = editingText.value.trim();
    editingItemId.value = null;
    if (!text || text === item.text) return;
    item.text = text;
    try {
      await updateChecklistItem(game.value.id, item.id, { text });
    } catch (err) {
      checklistError.value =
        err instanceof Error ? err.message : "Failed to rename item";
    }
  }

  function cancelEditItem() {
    editingItemId.value = null;
  }

  async function moveChecklistItem(item: ChecklistItem, direction: -1 | 1) {
    if (!game.value) return;
    const list = checklistItems.value;
    const index = list.indexOf(item);
    const targetIndex = index + direction;
    if (index === -1 || targetIndex < 0 || targetIndex >= list.length) return;
    const reordered = [...list];
    [reordered[index], reordered[targetIndex]] = [
      reordered[targetIndex],
      reordered[index],
    ];
    checklistItems.value = reordered;
    try {
      await reorderChecklist(
        game.value.id,
        activeProfileId.value,
        reordered.map((i) => i.id),
      );
    } catch (err) {
      checklistError.value =
        err instanceof Error ? err.message : "Failed to reorder checklist";
      await loadChecklist();
    }
  }

  async function removeChecklistItem(item: ChecklistItem) {
    if (!game.value) return;
    try {
      await deleteChecklistItem(game.value.id, item.id);
      checklistItems.value = checklistItems.value.filter(
        (i) => i.id !== item.id,
      );
    } catch (err) {
      checklistError.value =
        err instanceof Error ? err.message : "Failed to delete item";
    }
  }

  return {
    checklistItems,
    checklistLoading,
    checklistError,
    newChecklistText,
    editingItemId,
    editingText,
    checklistProgress,
    checklistSections,
    collapsedSections,
    collapsedStorageKey,
    loadCollapsedSections,
    saveCollapsedSections,
    toggleSectionCollapsed,
    sectionProgress,
    loadChecklist,
    addChecklistItem,
    addChecklistSection,
    toggleChecklistItem,
    startEditItem,
    commitEditItem,
    cancelEditItem,
    moveChecklistItem,
    removeChecklistItem,
  };
}
