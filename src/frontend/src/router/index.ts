import { createRouter, createWebHistory } from 'vue-router'
import HomeHub from '../views/HomeHub.vue'
import GameLibrary from '../views/GameLibrary.vue'
import GameDetail from '../views/GameDetail.vue'
import AchievementDetail from '../views/AchievementDetail.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'home', component: HomeHub },
    { path: '/games', name: 'library', component: GameLibrary },
    { path: '/games/:id', name: 'game-detail', component: GameDetail },
    {
      path: '/games/:gameId/achievements/:achievementId',
      name: 'achievement-detail',
      component: AchievementDetail,
    },
  ],
})

export default router