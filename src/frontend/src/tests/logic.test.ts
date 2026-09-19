import { describe, it, expect } from "vitest";
import { bucketToReal, statusBucket, statusBucketLabel } from "../utils/mediaStatus";
import { createEntityCache } from "../utils/entityCache";
import { activeDialog, closeDialog, useConfirm, usePrompt } from "../state/dialog";

describe("status buckets", () => {
  it("collapses the eight stored statuses into the five shown ones", () => {
    expect(statusBucket("wishlist")).toBe("plan");
    expect(statusBucket("watchlist")).toBe("plan");
    expect(statusBucket("in progress")).toBe("watching");
    expect(statusBucket("rewatch")).toBe("watching");
    expect(statusBucket("favorite")).toBe("completed");
    expect(statusBucketLabel("backlog")).toBe("On Hold");
  });
  it("writes back one canonical stored status per bucket", () => {
    expect(bucketToReal("completed")).toBe("watched");
    expect(bucketToReal("watching")).toBe("in progress");
  });
});

describe("entity cache", () => {
  it("remembers entities, forgets deleted ones, and knows when the list is complete", () => {
    const cache = createEntityCache<{ id: string; n: number }>();
    expect(cache.listLoaded()).toBe(false);
    cache.put({ id: "a", n: 1 });
    cache.put({ id: "b", n: 2 });
    expect(cache.peek("a")?.n).toBe(1);
    cache.put({ id: "a", n: 3 });
    expect(cache.peek("a")?.n).toBe(3);
    cache.remove("b");
    expect(cache.peek("b")).toBeUndefined();
    expect(cache.all()).toHaveLength(1);
    cache.markListLoaded();
    expect(cache.listLoaded()).toBe(true);
  });
});

describe("in-app dialogs", () => {
  it("resolves confirm with true on accept and false on cancel", async () => {
    const confirm = useConfirm();
    const accepted = confirm({ message: "Sure?" });
    expect(activeDialog.value?.kind).toBe("confirm");
    closeDialog(true);
    expect(await accepted).toBe(true);
    const declined = confirm({ message: "Sure?" });
    closeDialog(false);
    expect(await declined).toBe(false);
    expect(activeDialog.value).toBeNull();
  });
  it("resolves prompt with the text, or null when cancelled", async () => {
    const prompt = usePrompt();
    const named = prompt({ message: "Name?" });
    closeDialog("Favorites");
    expect(await named).toBe("Favorites");
    const cancelled = prompt({ message: "Name?" });
    closeDialog(null);
    expect(await cancelled).toBeNull();
  });
  it("queues a second dialog until the first closes", async () => {
    const confirm = useConfirm();
    const first = confirm({ message: "one" });
    const second = confirm({ message: "two" });
    expect(activeDialog.value?.message).toBe("one");
    closeDialog(true);
    await first;
    expect(activeDialog.value?.message).toBe("two");
    closeDialog(false);
    expect(await second).toBe(false);
  });
});
