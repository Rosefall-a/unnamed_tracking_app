import { expect, it } from "vitest";
import {
  notificationDestination,
  notificationPresentation,
} from "../utils/notificationPresentation";

it("groups plugin notifications without requiring a media page", () => {
  expect(notificationPresentation("plugin")).toEqual({
    label: "Plugin",
    tone: "violet",
    group: "plugins",
  });
  expect(
    notificationDestination({ mediaType: "plugin", mediaId: "publisher-uuid" }),
  ).toBeNull();
});

it.each(["legacy-event", "constructor", "__proto__"])(
  "renders unfamiliar notification kind %s safely",
  (kind) => {
    expect(notificationPresentation(kind)).toEqual({
      label: "Notification",
      tone: "blue",
      group: null,
    });
  },
);

it("preserves known media groups and actual title routes", () => {
  expect(notificationPresentation("episode_aired").group).toBe("episodes");
  expect(notificationPresentation("season_started").group).toBe("seasons");
  expect(notificationPresentation("movie_released").group).toBe("releases");
  for (const [mediaType, root] of [
    ["movie", "movies"],
    ["tv", "tv"],
    ["anime", "anime"],
  ]) {
    expect(notificationDestination({ mediaType, mediaId: "title-uuid" })).toBe(
      `/${root}/title-uuid`,
    );
  }
  expect(
    notificationDestination({ mediaType: "movie", mediaId: "" }),
  ).toBeNull();
  expect(
    notificationDestination({
      mediaType: "constructor",
      mediaId: "title-uuid",
    }),
  ).toBeNull();
});
