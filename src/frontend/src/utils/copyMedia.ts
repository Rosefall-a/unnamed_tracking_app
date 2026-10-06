// Copy and download helpers for uploaded media. Images go on the clipboard
// as a real image (paste straight into Discord or a doc); everything else
// copies its link, because browsers cannot put a video or audio file on the
// clipboard.

function absolute(url: string): string {
  return new URL(url, window.location.origin).href;
}

export type CopyOutcome = "image" | "link";

async function toPng(blob: Blob): Promise<Blob> {
  if (blob.type === "image/png") return blob;
  const bitmap = await createImageBitmap(blob);
  const canvas = document.createElement("canvas");
  canvas.width = bitmap.width;
  canvas.height = bitmap.height;
  canvas.getContext("2d")?.drawImage(bitmap, 0, 0);
  bitmap.close();
  return new Promise((resolve, reject) =>
    canvas.toBlob(
      (png) => (png ? resolve(png) : reject(new Error("Could not encode."))),
      "image/png",
    ),
  );
}

export async function copyLink(url: string): Promise<void> {
  await navigator.clipboard.writeText(absolute(url));
}

// Falls back to the link when the browser will not accept an image (older
// browsers, or a page that is not on https or localhost).
export async function copyImage(url: string): Promise<CopyOutcome> {
  if (typeof ClipboardItem === "undefined" || !navigator.clipboard?.write) {
    await copyLink(url);
    return "link";
  }
  try {
    const response = await fetch(url, { credentials: "include" });
    if (!response.ok) throw new Error("Download failed.");
    const png = await toPng(await response.blob());
    await navigator.clipboard.write([new ClipboardItem({ "image/png": png })]);
    return "image";
  } catch {
    await copyLink(url);
    return "link";
  }
}

export function downloadMedia(url: string, filename: string): void {
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
}

// The stored name is "<id>_<original>", so strip the id for display and
// for the downloaded file.
export function originalName(filename: string): string {
  const i = filename.indexOf("_");
  return i > 0 ? filename.slice(i + 1) : filename;
}
