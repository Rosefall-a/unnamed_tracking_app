// AniList files an anime under a format: TV, Movie, OVA, ONA, Special, Music. A
// film (or an OVA) has no seasons to speak of, so it is called what it is rather
// than "1 season".

// "Movie", "OVA" and so on; null for a TV series or when the format is not known
export function animeFormatLabel(
  format: string | null | undefined,
): string | null {
  const f = (format ?? "").trim();
  if (!f || /^tv(_short)?$/i.test(f)) return null;
  if (/^tv short$/i.test(f)) return null;
  // OVA and ONA stay capitals; the rest read as words
  return /^(ova|ona)$/i.test(f)
    ? f.toUpperCase()
    : f.charAt(0).toUpperCase() + f.slice(1).toLowerCase().replace(/_/g, " ");
}

export function isAnimeMovie(format: string | null | undefined): boolean {
  return /^movie$/i.test((format ?? "").trim());
}
