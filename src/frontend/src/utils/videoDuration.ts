// Some recordings (browser or OBS WebM files, for example) carry no length,
// so the player reports Infinity or a guess that grows as it buffers. Seeking
// far past the end makes the browser read the file and settle on the real
// length. Call this from `loadedmetadata`; it puts the playhead back after.
export function settleDuration(video: HTMLVideoElement): Promise<number> {
  return new Promise((resolve) => {
    if (Number.isFinite(video.duration) && video.duration > 0) {
      resolve(video.duration);
      return;
    }
    const done = () => {
      video.removeEventListener("durationchange", onChange);
      if (Number.isFinite(video.duration)) {
        video.currentTime = 0;
        resolve(video.duration);
      }
    };
    const onChange = () => {
      if (Number.isFinite(video.duration)) done();
    };
    video.addEventListener("durationchange", onChange);
    video.currentTime = 1e101;
    window.setTimeout(() => resolve(video.duration), 4000);
  });
}

export function formatDuration(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds < 0) return "";
  const total = Math.round(seconds);
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  return h
    ? `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`
    : `${m}:${String(s).padStart(2, "0")}`;
}
