import type { Game } from '../types/game'

export interface GameScore {
    sum: number
    max: number
}

export function computeScore(game: Game): GameScore | null {
    const values = [game.ratingOverall, game.ratingStory, game.ratingGameplay, game.ratingSound].filter(
        (v): v is number => v !== null,
    )
    if (values.length === 0) return null
    return { sum: values.reduce((a, b) => a + b, 0), max: values.length * 10 }
}