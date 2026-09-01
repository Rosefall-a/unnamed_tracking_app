export type GameStatus =
  | 'wishlist'
  | 'backlog'
  | 'playing'
  | 'on hold'
  | 'beaten'
  | 'played'
  | 'dropped'
  | 'mastered'

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
  links: GameLink[]
  ownership: GameOwnership
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
  condition: string | null
}