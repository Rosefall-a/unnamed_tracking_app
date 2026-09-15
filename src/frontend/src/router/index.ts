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
    { path: "/login", name: "login", component: Login },
    { path: "/login/local", name: "login-local", component: Login },
    { path: "/login/oidcstart", name: "oidc-start", component: OidcStart },
    { path: "/login/oidcstart/:provider", name: "oidc-start-legacy", redirect: "/login" },
    { path: "/login/:provider", name: "oidc-provider-start", component: OidcProviderStart },
    { path: "/reset-password", name: "password-reset", component: PasswordReset },
    { path: "/setup", name: "setup", component: Setup },
    { path: "/profile", redirect: "/settings?section=profile" },
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

  // Setup has exactly one route and is never authenticated. The only gate is
  // the public server setup-status endpoint. This prevents /api/auth/me (and
  // its expected 401 on a fresh installation) from participating in setup.
  if (to.path === "/setup") {
    const state = await refreshSetupState();
    return state === "required" ? undefined : "/login";
  }

  // Login and password reset are public too. Do not call /api/auth/me merely
  // to render them; a fresh installation legitimately has no session yet.
  if (to.path === "/login" || to.path.startsWith("/login/") || to.path === "/reset-password") {
    return;
  }

  if (setupState === "unknown") setupState = (await waitForServer()) ? "required" : "complete";
  if (setupState === "required") return { path: "/setup" };
  if (!authChecked.value) await checkAuth();
  if (!currentUser.value) return "/login";
  if (!appearanceLoaded.value) await loadAppearanceSettings();
});

export default router;
