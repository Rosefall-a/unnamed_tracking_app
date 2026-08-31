import { createRouter, createWebHistory } from 'vue-router'
import GameLibrary from '../views/GameLibrary.vue'
import GameDetail from '../views/GameDetail.vue'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: GameLibrary,
  },
  {
    path: '/game/:id',
    name: 'GameDetail',
    component: GameDetail,
    props: true,
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('../views/NotFound.vue'),
  },
]

export const router = createRouter({
  history: createWebHistory(),
  routes,
})