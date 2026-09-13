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
import Inbox from "../views/Inbox.vue";
import Bounties from "../views/Bounties.vue";
import AchievementDetail from "../views/AchievementDetail.vue";
import Login from "../views/Login.vue";
import OidcStart from "../views/OidcStart.vue";
import Setup from "../views/Setup.vue";
import { currentUser, authChecked, checkAuth } from "../state/auth";
import Settings from "../views/Settings.vue";
import { saveLibraryScroll } from "../state/libraryScroll";
import { appearanceLoaded, loadAppearanceSettings } from "../state/appearance";
import { fetchSetupStatus } from "../services/setup";

const router = createRouter({ history: createWebHistory(), scrollBehavior(to, _from, savedPosition) {
  if (to.path === "/games") return false;
  if (savedPosition) return savedPosition;
  return { top: 0 };
}, routes: [
  { path: "/", name: "home", component: HomeHub }, { path: "/games", name: "library", component: GameLibrary },
  { path: "/collections", name: "collections", component: Collections }, { path: "/collections/:name", name: "collection-detail", component: CollectionDetail },
  { path: "/inbox", name: "inbox", component: Inbox }, { path: "/bounties", name: "bounties", component: Bounties },
  { path: "/games/:id", name: "game-detail", component: GameDetail }, { path: "/cards", name: "card-collection", component: CardCollection },
  { path: "/cards/:cardId", name: "card-detail", component: CardDetail }, { path: "/sets", name: "set-list", component: SetList },
  { path: "/sets/:id", name: "set-detail", component: SetDetail }, { path: "/login", name: "login", component: Login },
  { path: "/login/oidcstart", name: "oidc-start", component: OidcStart },
  { path: "/setup", name: "setup", component: Setup }, { path: "/profile", redirect: "/settings" }, { path: "/settings", name: "settings", component: Settings },
  { path: "/games/:gameId/achievements/:achievementId", name: "achievement-detail", component: AchievementDetail },
] });

let setupState: "unknown" | "required" | "complete" | "error" = "unknown";

router.beforeEach(async (to, from) => {
  if (from.path === "/games") saveLibraryScroll(window.scrollY);

  if (setupState === "unknown" || setupState === "error") {
    try {
      setupState = (await fetchSetupStatus()).setup_required ? "required" : "complete";
    } catch {
      setupState = "error";
    }
  }

  if (setupState === "required" && to.path !== "/setup") {
    try {
      setupState = (await fetchSetupStatus()).setup_required ? "required" : "complete";
    } catch {
      setupState = "error";
    }
  }

  if (setupState === "required" || setupState === "error") {
    if (to.path !== "/setup") return { path: "/setup", query: setupState === "error" ? { backend_error: "1" } : undefined };
    return;
  }
  if (to.path === "/setup") return "/";

  // This public route deliberately bypasses the normal auth redirect so a
  // bookmark or reverse-proxy login entrypoint can start OIDC immediately.
  if (to.path === "/login/oidcstart") return;

  if (!authChecked.value) await checkAuth();
  if (to.path !== "/login" && !currentUser.value) return "/login";
  if (to.path === "/login" && currentUser.value) return "/";
  if (currentUser.value && !appearanceLoaded.value) await loadAppearanceSettings();
});

export default router;
