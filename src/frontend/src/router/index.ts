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
import Setup from "../views/Setup.vue";
import { currentUser, authChecked, checkAuth } from "../state/auth";
import Settings from "../views/Settings.vue";
import { saveLibraryScroll } from "../state/libraryScroll";
import { appearanceLoaded, loadAppearanceSettings } from "../state/appearance";
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
    { path: "/setup", name: "setup", component: Setup },
    { path: "/profile", redirect: "/settings" },
    { path: "/settings", name: "settings", component: Settings },
    { path: "/games/:gameId/achievements/:achievementId", name: "achievement-detail", component: AchievementDetail },
  ],
});

let setupChecked = false;
let setupRequired = false;

router.beforeEach(async (to, from) => {
  if (from.path === "/games") saveLibraryScroll(window.scrollY);

  if (!setupChecked) {
    try {
      setupRequired = (await fetchSetupStatus()).setup_required;
    } catch {
      setupRequired = false;
    }
    setupChecked = true;
  }

  if (setupRequired) {
    if (to.path !== "/setup") return "/setup";
    return;
  }
  if (to.path === "/setup") return "/";

  if (!authChecked.value) await checkAuth();
  if (to.path !== "/login" && !currentUser.value) return "/login";
  if (to.path === "/login" && currentUser.value) return "/";
  if (currentUser.value && !appearanceLoaded.value) await loadAppearanceSettings();
});

export default router;
