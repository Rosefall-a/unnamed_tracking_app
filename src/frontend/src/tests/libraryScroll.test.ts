import { beforeEach, expect, it } from "vitest";
import {
  captureLibraryNavigation,
  saveLibraryScroll,
  takeLibraryScroll,
} from "../state/libraryScroll";

beforeEach(() => saveLibraryScroll(0));

it("restores a game-detail return once", () => {
  captureLibraryNavigation("/games/game-id", "/games", 640);
  captureLibraryNavigation("/games", "/games/game-id", 0);
  expect(takeLibraryScroll()).toBe(640);
  expect(takeLibraryScroll()).toBe(0);
});

it("starts a fresh Games visit at the top after visiting another page", () => {
  captureLibraryNavigation("/games/game-id", "/games", 640);
  captureLibraryNavigation("/collections", "/games/game-id", 300);
  captureLibraryNavigation("/games", "/collections", 900);
  expect(takeLibraryScroll()).toBe(0);
});

it("does not remember the scroll position when leaving Games for another section", () => {
  captureLibraryNavigation("/statistics", "/games", 640);
  captureLibraryNavigation("/games", "/statistics", 200);
  expect(takeLibraryScroll()).toBe(0);
});
