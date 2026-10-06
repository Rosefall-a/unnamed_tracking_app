// Reorder mode for a grid of tiles: drag one over another, or nudge it with
// the arrows, and the order is saved as you go. The page says how to read and
// change its current order and how to store it.
import { ref } from "vue";

export function useReorderGrid<T>(options: {
  getItems: () => T[];
  setItems: (next: T[]) => void;
  persist: () => void | Promise<void>;
  // called when reorder mode turns on (to switch the sort to "manual")
  onEnter?: () => void;
}) {
  const reorderMode = ref(false);
  const dragIndex = ref<number | null>(null);

  function toggleReorder() {
    reorderMode.value = !reorderMode.value;
    if (reorderMode.value) options.onEnter?.();
  }
  function moveItem(from: number, to: number) {
    const items = [...options.getItems()];
    if (to < 0 || to >= items.length || from === to) return;
    const [moved] = items.splice(from, 1);
    items.splice(to, 0, moved);
    options.setItems(items);
  }
  function onDragStart(index: number, event: DragEvent) {
    dragIndex.value = index;
    if (event.dataTransfer) event.dataTransfer.effectAllowed = "move";
  }
  function onDragOver(index: number) {
    if (dragIndex.value === null || dragIndex.value === index) return;
    moveItem(dragIndex.value, index);
    dragIndex.value = index;
  }
  async function onDragEnd() {
    const dragged = dragIndex.value !== null;
    dragIndex.value = null;
    if (dragged) await options.persist();
  }
  async function nudge(index: number, delta: number) {
    moveItem(index, index + delta);
    await options.persist();
  }

  return {
    reorderMode,
    dragIndex,
    toggleReorder,
    onDragStart,
    onDragOver,
    onDragEnd,
    nudge,
  };
}
