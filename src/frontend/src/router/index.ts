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
import PasswordReset from "../views/PasswordReset.vue";
import Setup from "../views/Setup.vue";
import { currentUser, authChecked, checkAuth } from "../state/auth";
import Settings from "../views/Settings.vue";
import { saveLibraryScroll } from "../state/libraryScroll";
import { appearanceLoaded, loadAppearanceSettings } from "../state/appearance";
import { waitForServer } from "../state/serverStartup";
import { oidcLoginStatus } from "../services/oidc";

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
    {
      path: "/login/oidcstart/:provider",
      name: "oidc-start-provider",
      component: OidcStart,
    },
    { path: "/login/oidcstart", name: "oidc-start", component: OidcStart },
    { path: "/login/:provider", name: "oidc-provider-start", component: OidcStart },
    { path: "/reset-password", name: "password-reset", component: PasswordReset },
    { path: "/setup", name: "setup", component: Setup },
    { path: "/profile", redirect: "/settings?section=profile" },
    { path: "/settings", name: "settings", component: Settings },
    {
      path: "/games/:gameId/achievements/:achievementId",
      name: "achievement-detail",
      component: AchievementDetail,
    },
  ],
});

let setupState: "unknown" | "required" | "complete" = "unknown";

router.beforeEach(async (to, from) => {
  if (from.path === "/games") saveLibraryScroll(window.scrollY);
  if (to.path === "/settings" && !to.query.section && from.path === "/") {
    return { path: "/settings", query: { section: "sources" } };
  }

  // The legacy /login/oidcstart URL starts the configured default provider.
  // For the new named-provider configuration, make "SSO" the actual default
  // when the admin has selected it: use the first enabled provider that has
  // autostart enabled. Query-string returns from OIDC must not trigger it
  // again, otherwise the successful callback would immediately restart SSO.
  if (
    to.path === "/login" &&
    to.query.oidc !== "success" &&
    typeof to.query.oidc_error !== "string"
  ) {
    try {
      const status = await oidcLoginStatus();
      if (status.default_login_method === "sso") {
        const provider = status.providers.find((item) => item.autostart_enabled);
        if (provider) {
          return { path: `/login/oidcstart/${encodeURIComponent(provider.slug)}` };
        }
      }
    } catch {
      // If OIDC status cannot be loaded, keep the normal login page usable.
    }
  }

  if (
    to.path === "/reset-password" ||
    to.path.startsWith("/login/oidcstart") ||
    to.path.startsWith("/login/")
  ) {
    return;
  }
  if (setupState === "unknown") setupState = (await waitForServer()) ? "required" : "complete";
  if (setupState === "required") {
    if (to.path !== "/setup") return { path: "/setup" };
    return;
  }
  if (to.path === "/setup") return "/";
  if (!authChecked.value) await checkAuth();
  if (to.path !== "/login" && !to.path.startsWith("/login/") && !currentUser.value) {
    return "/login";
  }
  if (to.path === "/login" && currentUser.value) return "/";
  if (currentUser.value && !appearanceLoaded.value) await loadAppearanceSettings();
});

export default router;
