// Makes the preview picture for a clip: one frame, shrunk, as a JPEG, and the
// clip's length. It is made once, when a clip is uploaded (from the file the
// browser already has) or, for older clips, the first time it is shown, and
// then saved on the server so it never has to be made again.
import { settleDuration } from "./videoDuration";

export interface ClipFrame {
  blob: Blob;
  duration: number;
}

const MAX_WIDTH = 640;

function seekTo(video: HTMLVideoElement, seconds: number): Promise<void> {
  return new Promise((resolve) => {
    const done = () => {
      video.removeEventListener("seeked", done);
      resolve();
    };
    video.addEventListener("seeked", done);
    video.currentTime = seconds;
    window.setTimeout(done, 4000);
  });
}

// `video` must already have its metadata loaded
export async function captureFrame(
  video: HTMLVideoElement,
): Promise<ClipFrame | null> {
  const duration = await settleDuration(video);
  if (!Number.isFinite(duration) || duration <= 0) return null;
  // a second in, or a tenth of the way for a short clip: past a black first frame
  await seekTo(video, Math.min(1, duration * 0.1));
  const width = video.videoWidth;
  const height = video.videoHeight;
  if (!width || !height) return null;
  const scale = Math.min(1, MAX_WIDTH / width);
  const canvas = document.createElement("canvas");
  canvas.width = Math.round(width * scale);
  canvas.height = Math.round(height * scale);
  const context = canvas.getContext("2d");
  if (!context) return null;
  try {
    context.drawImage(video, 0, 0, canvas.width, canvas.height);
  } catch {
    return null;
  }
  const blob = await new Promise<Blob | null>((resolve) =>
    canvas.toBlob(resolve, "image/jpeg", 0.8),
  );
  return blob ? { blob, duration } : null;
}

// For a clip that is not on screen: a File just chosen for upload, or a url.
export async function frameFromSource(
  source: File | string,
): Promise<ClipFrame | null> {
  const url = typeof source === "string" ? source : URL.createObjectURL(source);
  const video = document.createElement("video");
  video.muted = true;
  video.preload = "metadata";
  video.playsInline = true;
  try {
    await new Promise<void>((resolve, reject) => {
      video.onloadedmetadata = () => resolve();
      video.onerror = () => reject(new Error("unreadable"));
      video.src = url;
      window.setTimeout(() => reject(new Error("timeout")), 15000);
    });
    return await captureFrame(video);
  } catch {
    return null;
  } finally {
    video.removeAttribute("src");
    video.load();
    if (typeof source !== "string") URL.revokeObjectURL(url);
  }
}
