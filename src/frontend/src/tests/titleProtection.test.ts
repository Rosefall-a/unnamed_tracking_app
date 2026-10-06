import { afterEach, describe, expect, it, vi } from "vitest";
import { nextTick, ref } from "vue";
import { useTitleProtection } from "../utils/titleProtection";
import { displayTitle } from "../utils/displayTitle";
import { updateGame, type NewGameInput } from "../services/games";
import { updateMovie, type MovieInput } from "../services/movies";
import { updateTVShow, type TVShowInput } from "../services/tvShows";
import { updateAnime, type AnimeInput } from "../services/anime";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("title protection controls", () => {
  it("shows existing protection while omitting an unchanged override", () => {
    const state = useTitleProtection(
      () => ({ title: "Original", lockedFields: ["title"] }),
      () => "Original",
    );
    expect(state.titleProtected.value).toBe(true);
    expect(state.titleLockOverride.value).toBeUndefined();
  });

  it("reflects automatic locking on edits and allows an explicit atomic unlock", () => {
    const title = ref("Original");
    const saved = ref({ title: "Original", lockedFields: [] });
    const state = useTitleProtection(
      () => saved.value,
      () => title.value,
    );
    expect(state.titleProtected.value).toBe(false);
    title.value = "Manual title";
    expect(state.titleProtected.value).toBe(true);
    expect(state.titleLockOverride.value).toBeUndefined();
    state.titleProtected.value = false;
    expect(state.titleLockOverride.value).toBe(false);
    expect(state.titleProtected.value).toBe(false);
  });

  it("can protect an unchanged title and resets when another record is opened", async () => {
    const saved = ref({ title: "Original", lockedFields: [] as string[] });
    const state = useTitleProtection(
      () => saved.value,
      () => saved.value.title,
    );
    state.titleProtected.value = true;
    expect(state.titleLockOverride.value).toBe(true);
    saved.value = { title: "Next", lockedFields: [] };
    await nextTick();
    expect(state.titleLockOverride.value).toBeUndefined();
    expect(state.titleProtected.value).toBe(false);
  });

  it("shows a protected anime's custom title instead of provider spellings", () => {
    expect(
      displayTitle({
        title: "Custom",
        titleEnglish: "Provider",
        titleRomaji: "Provider",
        titleNative: null,
        lockedFields: ["title"],
      }),
    ).toBe("Custom");
  });
});

const updates = [
  (lock: boolean | undefined) =>
    updateGame("entity", {
      title: "Manual",
      status: "backlog",
      titleLock: lock,
      ownership: {},
    } as NewGameInput),
  (lock: boolean | undefined) =>
    updateMovie("entity", { title: "Manual", titleLock: lock } as MovieInput),
  (lock: boolean | undefined) =>
    updateTVShow("entity", { title: "Manual", titleLock: lock } as TVShowInput),
  (lock: boolean | undefined) =>
    updateAnime("entity", { title: "Manual", titleLock: lock } as AnimeInput),
];

describe.each(updates)("title protection API transport", (update) => {
  it.each([undefined, true, false])(
    "preserves the explicit override %s and surfaces backend denials",
    async (lock) => {
      const fetchMock = vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            detail: "Interactive application session required.",
          }),
          { status: 403 },
        ),
      );
      vi.stubGlobal("fetch", fetchMock);
      await expect(update(lock)).rejects.toThrow();
      const options = fetchMock.mock.calls[0]![1];
      const body = JSON.parse(options.body);
      expect(body.title).toBe("Manual");
      if (lock === undefined) expect(body).not.toHaveProperty("title_lock");
      else expect(body.title_lock).toBe(lock);
      expect(options.credentials).toBe("include");
      expect(options.method).toBe("PATCH");
    },
  );
});
