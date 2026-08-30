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
  unlocked: boolean
}

export interface Game {
  id: string
  title: string
  coverColor: string
  status: GameStatus
  ratingOverall: number | null
  achievementPercent: number
  achievements: Achievement[]
}