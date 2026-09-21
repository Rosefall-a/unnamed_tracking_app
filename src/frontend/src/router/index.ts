import { createRouter, createWebHistory } from "vue-router";
import HomeHub from "../views/HomeHub.vue";
import GameLibrary from "../views/GameLibrary.vue";
import Collections from "../views/Collections.vue";
import CollectionDetail from "../views/CollectionDetail.vue";
import GameDetail from "../views/GameDetail.vue";
import CardCollection from "../views/CardCollection.vue";
import CardDetail from "../views/CardDetail.vue";
import SetList from "../views/SetList.vue";
import SetDetail from "../views/SetDetail.vue";
import MovieLibrary from "../views/MovieLibrary.vue";
import MovieDetail from "../views/MovieDetail.vue";
import TVShowLibrary from "../views/TVShowLibrary.vue";
import TVShowDetail from "../views/TVShowDetail.vue";
import AnimeLibrary from "../views/AnimeLibrary.vue";
import AnimeDetail from "../views/AnimeDetail.vue";
import Calendar from "../views/Calendar.vue";
import Statistics from "../views/Statistics.vue";
import Notifications from "../views/Notifications.vue";
import MediaLists from "../views/MediaLists.vue";
import MediaListDetail from "../views/MediaListDetail.vue";
import Inbox from "../views/Inbox.vue";
import Bounties from "../views/Bounties.vue";
import AchievementDetail from "../views/AchievementDetail.vue";
import InviteAccept from "../views/InviteAccept.vue";
import Login from "../views/Login.vue";
import OidcStart from "../views/OidcStart.vue";
import OidcProviderStart from "../views/OidcProviderStart.vue";
import PasswordReset from "../views/PasswordReset.vue";
import Setup from "../views/Setup.vue";
import Settings from "../views/Settings.vue";
import { currentUser, authChecked, checkAuth } from "../state/auth";
import { saveLibraryScroll } from "../state/libraryScroll";
import { appearanceLoaded, loadAppearanceSettings } from "../state/appearance";
import { waitForServer } from "../state/serverStartup";
import { fetchSetupStatus } from "../services/setup";

const router = createRouter({
  history: createWebHistory(),
  scrollBehavior(to, _from, savedPosition) {
    if (to.path === "/games") return false;
    if (savedPosition) return savedPosition;
    return { top: 0 };
  },
  routes: [
    { path: "/", name: "home", component: HomeHub },
    { path: "/games", name: "library", component: GameLibrary },
    { path: "/collections", name: "collections", component: Collections },
    { path: "/collections/:name", name: "collection-detail", component: CollectionDetail },
    { path: "/inbox", name: "inbox", component: Inbox },
    { path: "/bounties", name: "bounties", component: Bounties },
    { path: "/games/:id", name: "game-detail", component: GameDetail },
    { path: "/cards", name: "card-collection", component: CardCollection },
    { path: "/cards/:cardId", name: "card-detail", component: CardDetail },
    { path: "/sets", name: "set-list", component: SetList },
    { path: "/sets/:id", name: "set-detail", component: SetDetail },
    { path: "/movies", name: "movie-library", component: MovieLibrary },
    { path: "/movies/:id", name: "movie-detail", component: MovieDetail },
    { path: "/tv", name: "tv-show-library", component: TVShowLibrary },
    { path: "/tv/:id", name: "tv-show-detail", component: TVShowDetail },
    { path: "/anime", name: "anime-library", component: AnimeLibrary },
    { path: "/anime/:id", name: "anime-detail", component: AnimeDetail },
    { path: "/calendar", name: "calendar", component: Calendar },
    { path: "/statistics", name: "statistics", component: Statistics },
    { path: "/notifications", name: "notifications", component: Notifications },
    { path: "/lists", name: "media-lists", component: MediaLists },
    { path: "/lists/:id", name: "media-list-detail", component: MediaListDetail },
    { path: "/history", redirect: "/calendar" },
    { path: "/login", name: "login", component: Login },
    { path: "/login/local", name: "login-local", component: Login },
    { path: "/login/oidcstart", name: "oidc-start", component: OidcStart },
    { path: "/login/oidcstart/:provider", name: "oidc-start-legacy", redirect: "/login" },
    { path: "/login/:provider", name: "oidc-provider-start", component: OidcProviderStart },
    { path: "/reset-password", name: "password-reset", component: PasswordReset },
    { path: "/invite", name: "invite-accept", component: InviteAccept },
    { path: "/setup", name: "setup", component: Setup },
    { path: "/profile", redirect: "/settings" },
    { path: "/settings", name: "settings", component: Settings },
    { path: "/games/:gameId/achievements/:achievementId", name: "achievement-detail", component: AchievementDetail },
  ],
});

let setupState: "unknown" | "required" | "complete" = "unknown";

async function refreshSetupState(): Promise<"required" | "complete"> {
  try {
    const status = await fetchSetupStatus();
    setupState = status.setup_required ? "required" : "complete";
    return setupState;
  } catch {
    setupState = (await waitForServer()) ? "required" : "complete";
    return setupState;
  }
}

router.beforeEach(async (to, from) => {
  if (from.path === "/games") saveLibraryScroll(window.scrollY);
  if (to.path === "/settings" && !to.query.section && from.path === "/") {
    return { path: "/settings", query: { section: "sources" } };
  }

  if (to.path === "/setup") {
    const state = await refreshSetupState();
    if (state === "required") return undefined;
    if (!authChecked.value) await checkAuth();
    return currentUser.value ? "/" : "/login";
  }

  if (
    to.path === "/login" ||
    to.path.startsWith("/login/") ||
    to.path === "/reset-password" ||
    to.path === "/invite"
  ) {
    return;
  }

  if (setupState === "unknown") await refreshSetupState();
  if (setupState === "required") return { path: "/setup" };
  if (!authChecked.value) await checkAuth();
  if (!currentUser.value) return "/login";
  if (!appearanceLoaded.value) await loadAppearanceSettings();
});

export default router;
