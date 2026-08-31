import { createRouter, createWebHistory } from 'vue-router'
import GameLibrary from '../views/GameLibrary.vue'
import GameDetail from '../views/GameDetail.vue'

const router = createRouter({
  // createWebHistory (not createWebHashHistory) gives real URLs like
  // /games/1 instead of /#/games/1 — needs the dev server to be
  // configured to serve index.html for unknown paths, which Vite already does
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'library', component: GameLibrary },
    { path: '/games/:id', name: 'game-detail', component: GameDetail },
  ],
})

export default router