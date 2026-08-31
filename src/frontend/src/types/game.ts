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
  // real placeholder image for the detail page's hero + blurred backdrop.
  // temporary — will point at real IGDB artwork once that sync exists
  coverImageUrl: string
  status: GameStatus
  ratingOverall: number | null
  achievementPercent: number
  achievements: Achievement[]
  description: string | null
  developer: string | null
  publisher: string | null
  series: string | null
  dateAdded: string | null
  tags: string[]
  // capability/technical tags (Achievements, Co-op, Multiplayer...) — different from `tags`,
  // which are genre/style descriptors
  features: string[]
  platforms: GamePlatform[]
}