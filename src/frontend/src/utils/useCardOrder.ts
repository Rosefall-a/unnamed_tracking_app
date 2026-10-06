// "My order" for a grid of cards where pinned ones always come first: which
// cards can move, moving one a step, and dragging one onto another. Shared by
// the Collections and Lists pages, which differ only in how a new order is
// stored (`apply`).
import { computed, ref } from "vue";
import type { Ref } from "vue";

export function useCardOrder<T extends { pinned: boolean }>(options: {
  items: Ref<T[]>;
  keyOf: (item: T) => string;
  // how two cards compare within a group when nothing else decides
  inMyOrder: (a: T, b: T) => number;
  // store the new order (every card, pinned ones first)
  apply: (ordered: T[]) => void | Promise<void>;
}) {
  const { items, keyOf, inMyOrder, apply } = options;

  const myOrder = computed(() =>
    [...items.value].sort(
      (a, b) => Number(b.pinned) - Number(a.pinned) || inMyOrder(a, b),
    ),
  );

  // pinned cards and the rest are ordered separately
  function groupOf(key: string): T[] {
    const pinned = items.value.find((i) => keyOf(i) === key)?.pinned ?? false;
    return myOrder.value.filter((i) => i.pinned === pinned);
  }
  function canMove(key: string, direction: -1 | 1): boolean {
    const at = groupOf(key).findIndex((i) => keyOf(i) === key);
    return at + direction >= 0 && at + direction < groupOf(key).length;
  }
  // the whole order with one group (pinned or not) replaced by `replacement`
  function withGroup(replacement: T[], pinned: boolean): T[] {
    const pinnedGroup = pinned
      ? replacement
      : myOrder.value.filter((i) => i.pinned);
    const rest = pinned ? myOrder.value.filter((i) => !i.pinned) : replacement;
    return [...pinnedGroup, ...rest];
  }
  async function move(key: string, direction: -1 | 1) {
    const group = groupOf(key);
    const at = group.findIndex((i) => keyOf(i) === key);
    const to = at + direction;
    if (at < 0 || to < 0 || to >= group.length) return;
    const swapped = [...group];
    [swapped[at], swapped[to]] = [swapped[to], swapped[at]];
    await apply(withGroup(swapped, group[0].pinned));
  }

  // dragging a card onto another one of the same group puts it in that place;
  // pinned and other cards stay apart
  const dragKey = ref<string | null>(null);
  const dropOn = ref<string | null>(null);
  function endDrag() {
    dragKey.value = dropOn.value = null;
  }
  function drop(targetKey: string) {
    const from = dragKey.value;
    endDrag();
    if (!from || from === targetKey) return;
    const group = groupOf(from);
    if (!group.some((i) => keyOf(i) === targetKey)) return;
    const moving = group.find((i) => keyOf(i) === from);
    if (!moving) return;
    const rest = group.filter((i) => keyOf(i) !== from);
    rest.splice(
      group.findIndex((i) => keyOf(i) === targetKey),
      0,
      moving,
    );
    void apply(withGroup(rest, moving.pinned));
  }
  function isDropTarget(key: string): boolean {
    return dropOn.value === key && dragKey.value !== key;
  }

  return {
    myOrder,
    canMove,
    move,
    dragKey,
    dropOn,
    drop,
    endDrag,
    isDropTarget,
  };
}

// The "All / Manual / Smart" counts both pages show above their grid.
export function kindOptions(total: number, smart: number) {
  return [
    { value: "all", label: "All", count: total },
    { value: "manual", label: "Manual", count: total - smart },
    { value: "smart", label: "Smart", count: smart },
  ];
}
