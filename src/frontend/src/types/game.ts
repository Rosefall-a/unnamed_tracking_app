export interface Achievement {
  id: string
  name: string
  unlockedAt: string | null
}

export interface PlatformInfo {
  platform: string
  playtimeMinutes: number
  completionPercent: number | null
  lastPlayedAt: string | null
}

export interface Game {
  id: string
  title: string
  status: string
  coverImageUrl?: string
  ratingOverall: number | null
  description?: string
  series?: string
  developer?: string
  publisher?: string
  dateAdded?: string
  platforms: PlatformInfo[]
  features: string[]
  tags: string[]
  achievementPercent: number
  achievements: Achievement[]
}