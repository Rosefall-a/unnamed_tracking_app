import { createRouter, createWebHistory } from 'vue-router'
import HomeHub from '../views/HomeHub.vue'
import GameLibrary from '../views/GameLibrary.vue'
import Collections from '../views/Collections.vue'
import CollectionDetail from '../views/CollectionDetail.vue'
import GameDetail from '../views/GameDetail.vue'
import AchievementDetail from '../views/AchievementDetail.vue'
import Login from '../views/Login.vue'
import { currentUser, authChecked, checkAuth } from '../state/auth'
import Settings from '../views/Settings.vue'

const router = createRouter({
  history: createWebHistory(),
  scrollBehavior(_to, _from, savedPosition) {
    if (savedPosition) return savedPosition
    return { top: 0 }
  },
  routes: [
    { path: '/', name: 'home', component: HomeHub },
    { path: '/games', name: 'library', component: GameLibrary },
    { path: '/collections', name: 'collections', component: Collections },
    { path: '/collections/:name', name: 'collection-detail', component: CollectionDetail },
    { path: '/games/:id', name: 'game-detail', component: GameDetail },
    { path: '/login', name: 'login', component: Login },
    // Profile lives inside Settings now (its own side-nav section)
    { path: '/profile', redirect: '/settings' },
    { path: '/settings', name: 'settings', component: Settings },
    {
      path: '/games/:gameId/achievements/:achievementId',
      name: 'achievement-detail',
      component: AchievementDetail,
    },
  ],
})

router.beforeEach(async (to) => {
  if (!authChecked.value) {
    await checkAuth()
  }
  if (to.path !== '/login' && !currentUser.value) {
    return '/login'
  }
  if (to.path === '/login' && currentUser.value) {
    return '/'
  }
})

export default router