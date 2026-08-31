import type { Game } from '../types/game'

export const MOCK_GAMES: Game[] = [
  {
    id: '1',
    title: 'Cyberpunk 2077',
    status: 'Completed',
    coverImageUrl: 'https://via.placeholder.com/1200x600',
    ratingOverall: 4.5,
    description: 'An open-world, action-adventure story set in Night City.',
    series: 'Cyberpunk',
    developer: 'CD Projekt Red',
    publisher: 'CD Projekt',
    dateAdded: '2025-01-15T00:00:00Z',
    platforms: [
      {
        platform: 'PC (Steam)',
        playtimeMinutes: 5400,
        completionPercent: 100,
        lastPlayedAt: '2026-02-10T12:00:00Z',
      },
    ],
    features: ['Single-player', 'Ray Tracing', 'Cloud Saves'],
    tags: ['RPG', 'Sci-Fi', 'Open World'],
    achievementPercent: 85,
    achievements: [
      { id: 'a1', name: 'The Fool', unlockedAt: '2025-01-16T10:00:00Z' },
      { id: 'a2', name: 'The World', unlockedAt: '2026-02-10T12:00:00Z' },
      { id: 'a3', name: 'Superhero Landing', unlockedAt: null },
    ],
  },
]