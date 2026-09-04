export type GameStatus =
  | 'wishlist'
  | 'backlog'
  | 'playing'
  | 'on hold'
  | 'beaten'
  | 'played'
  | 'dropped'
  | 'mastered'

export type AchievementTier = 'bronze' | 'silver' | 'gold'

// where a game's achievement tracking comes from — 'retroachievements' means
// synced via retroachievements.org, common for emulated/retro platforms
export type AchievementsProvider = 'native' | 'retroachievements' | null

export interface Achievement {
  id: string
  name: string
  description?: string | null
  unlockedAt: string | null
  hidden?: boolean
  rarityPercent?: number | null
  tierOverride?: AchievementTier | null
  progressCurrent?: number | null
  progressTarget?: number | null
  notes?: string | null
  media?: string[]
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
  bannerImageUrl: string
  status: GameStatus
  ratingOverall: number | null
  ratingStory: number | null
  ratingGameplay: number | null
  ratingSound: number | null
  achievementPercent: number
  achievements: Achievement[]
  description: string | null
  developer: string | null
  publisher: string | null
  series: string | null
  dateAdded: string | null
  folderLocation: string | null
  releaseDate: string | null
  source: string | null
  ageRating: string | null
  timeToBeatHours: number | null
  region: string | null
  language: string | null
  achievementsProvider: AchievementsProvider
  links: GameLink[]
  ownership: GameOwnership
  favorite: boolean
  collections: string[]
  tags: string[]
  // capability/technical tags (Achievements, Co-op, Multiplayer...) — different from `tags`,
  // which are genre/style descriptors
  features: string[]
  platforms: GamePlatform[]
}

export interface GameLink {
  label: string
  url: string
}

export interface GameOwnership {
  format: 'digital' | 'physical' | null
  purchaseDate: string | null
  price: number | null
  priceCurrency: string | null
  condition: string | null
}