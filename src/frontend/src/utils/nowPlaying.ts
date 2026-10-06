// Only one track plays at a time: starting one stops whichever was playing.
let current: HTMLAudioElement | null = null;

export function startPlaying(audio: HTMLAudioElement): void {
  if (current && current !== audio) current.pause();
  current = audio;
}

export function stoppedPlaying(audio: HTMLAudioElement): void {
  if (current === audio) current = null;
}
