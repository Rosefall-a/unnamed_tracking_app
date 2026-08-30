import type { Game } from '../types/game'

export const mockGames: Game[] = [
  {
    id: '1',
    title: 'Elden Ring',
    coverColor: '#5b3a29',
    status: 'playing',
    ratingOverall: 9.4,
    achievementPercent: 60,
    achievements: [
      { id: 'a1', name: 'Defeat Margit', unlocked: true },
      { id: 'a2', name: 'Reach Caelid', unlocked: true },
      { id: 'a3', name: 'Defeat Godrick', unlocked: true },
      { id: 'a4', name: 'Defeat Malenia', unlocked: false },
      { id: 'a5', name: '100% Completion', unlocked: false },
    ],
  },
  {
    id: '2',
    title: 'Hades',
    coverColor: '#7a1f2b',
    status: 'mastered',
    ratingOverall: 9.1,
    achievementPercent: 100,
    achievements: [
      { id: 'b1', name: 'Escape the Underworld', unlocked: true },
      { id: 'b2', name: 'Max Bond with Megaera', unlocked: true },
      { id: 'b3', name: 'Clear Heat 32', unlocked: true },
      { id: 'b4', name: 'Complete the Codex', unlocked: true },
    ],
  },
  {
    id: '3',
    title: 'Hollow Knight',
    coverColor: '#22303c',
    status: 'backlog',
    ratingOverall: null,
    achievementPercent: 0,
    achievements: [
      { id: 'c1', name: 'Reach Dirtmouth', unlocked: false },
      { id: 'c2', name: 'Defeat False Knight', unlocked: false },
      { id: 'c3', name: 'Find the Mothwing Cloak', unlocked: false },
    ],
  },
]