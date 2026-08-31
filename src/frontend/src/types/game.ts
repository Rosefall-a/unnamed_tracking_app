export type GameStatus =
  | 'wishlist'
  | 'backlog'
  | 'playing'
  | 'paused'
  | 'completed'
  | 'mastered'
  | 'dropped'

export interface Achievement {
  id: string
  name: string
  // full ISO timestamp (date + time), e.g. "2026-06-02T19:14:03" — null means still locked
  unlockedAt: string | null
}

export interface Game {
  id: string
  title: string
  coverColor: string
  status: GameStatus
  ratingOverall: number | null
  achievementPercent: number
  achievements: Achievement[]
  description: string | null
  developer: string | null
  publisher: string | null
  tags: string[]
  playtimeMinutes: number
  // full ISO timestamp, e.g. "2026-08-28T20:15:47" — null means never played
  lastPlayedAt: string | null
}