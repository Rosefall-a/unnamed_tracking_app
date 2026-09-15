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
import SetupFirstUser from "../views/SetupFirstUser.vue";
import SetupOidc from "../views/SetupOidc.vue";
import SetupSmtp from "../views/SetupSmtp.vue";
import { currentUser, authChecked, checkAuth } from "../state/auth";
import Settings from "../views/Settings.vue";
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
    { path: "/setup/firstuser", name: "setup-firstuser", component: SetupFirstUser },
    { path: "/setup/oidc", name: "setup-oidc", component: SetupOidc },
    { path: "/setup/smtp", name: "setup-smtp", component: SetupSmtp },
    { path: "/profile", redirect: "/settings?section=profile" },
    { path: "/settings", name: "settings", component: Settings },
    { path: "/games/:gameId/achievements/:achievementId", name: "achievement-detail", component: AchievementDetail },
  ],
});

let setupState: "unknown" | "required" | "complete" = "unknown";

async function refreshSetupState(): Promise<boolean> {
  try {
    const status = await fetchSetupStatus();
    setupState = status.setup_required ? "required" : "complete";
    return status.setup_required;
  } catch {
    // If the backend is still starting, use the startup retry loop rather
    // than treating a temporary failure as setup being complete.
    setupState = (await waitForServer()) ? "required" : "complete";
    return setupState === "required";
  }
}

router.beforeEach(async (to, from) => {
  if (from.path === "/games") saveLibraryScroll(window.scrollY);
  if (to.path === "/settings" && !to.query.section && from.path === "/") {
    return { path: "/settings", query: { section: "sources" } };
  }

  if (to.path === "/login" || to.path.startsWith("/login/") || to.path === "/reset-password") {
    if (setupState === "required" && !currentUser.value) await checkAuth();
    if (setupState === "required" && currentUser.value) setupState = "complete";
    return;
  }

  const isSetupRoute = to.path === "/setup" || to.path.startsWith("/setup/");
  if (isSetupRoute) {
    // Setup is deliberately public: none of the setup pages ever call
    // /api/auth/me or require a session. The only gate is the server's
    // authoritative setup status. This also refreshes the status on every
    // setup navigation so a stale client-side state cannot expose the wizard
    // after the first account has been created.
    const setupRequired = await refreshSetupState();
    if (setupRequired) return;

    // An installation that already has a user must never expose setup pages.
    return "/login";
  }

  if (setupState === "unknown") setupState = (await waitForServer()) ? "required" : "complete";
  if (setupState === "required") return { path: "/setup" };
  if (!authChecked.value) await checkAuth();
  if (!currentUser.value) return "/login";
  if (!appearanceLoaded.value) await loadAppearanceSettings();
});

export default router;
