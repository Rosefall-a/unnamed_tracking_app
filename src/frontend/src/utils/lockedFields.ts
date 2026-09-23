// Human-readable labels for the backend field names tracked in a media
// entry's lockedFields, used when telling an admin which fields "Apply
// metadata" skipped because they'd already been manually edited.
const FIELD_LABELS: Record<string, string> = {
  title: "Title",
  description: "Description",
  release_date: "Release date",
  first_air_date: "First air date",
  runtime_minutes: "Runtime",
  episode_runtime_minutes: "Episode runtime",
  director: "Director",
  writer: "Writer",
  creators: "Creators",
  studios: "Studios",
  genres: "Genres",
  poster_url: "Poster",
  backdrop_url: "Backdrop",
  tmdb_score: "TMDB score",
  anilist_score: "AniList score",
  mal_score: "MAL score",
};

export function lockedFieldLabels(fields: string[]): string[] {
  return fields.map((field) => FIELD_LABELS[field] ?? field);
}
