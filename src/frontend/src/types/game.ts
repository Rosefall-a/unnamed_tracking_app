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
  unlockedAt: string | null
}

export interface GamePlatform {
  platform: string
  playtimeMinutes: number
  completionPercent: number | null
  lastPlayedAt: string | null
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
  series: string | null
  // ISO timestamp — when this game was added to the tracker, not its real-world release date
  dateAdded: string | null
  tags: string[]
  platforms: GamePlatform[]
}