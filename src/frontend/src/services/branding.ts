export interface Branding {
  app_name: string;
  logo_url: string | null;
  favicon_url: string;
}

export type BrandingAsset = "logo" | "favicon";

async function read(response: Response): Promise<Branding> {
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(
      typeof body?.detail === "string"
        ? body.detail
        : `Could not update app branding (${response.status}).`,
    );
  }
  return response.json() as Promise<Branding>;
}

export async function fetchBranding(): Promise<Branding> {
  return read(await fetch("/api/branding", { credentials: "include" }));
}

export async function saveBrandingName(appName: string): Promise<Branding> {
  return read(
    await fetch("/api/branding", {
      method: "PUT",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ app_name: appName }),
    }),
  );
}

export async function uploadBrandingAsset(
  kind: BrandingAsset,
  file: File,
): Promise<Branding> {
  const body = new FormData();
  body.append("file", file);
  return read(
    await fetch(`/api/branding/assets/${kind}`, {
      method: "POST",
      credentials: "include",
      body,
    }),
  );
}

export async function removeBrandingAsset(
  kind: BrandingAsset,
): Promise<Branding> {
  return read(
    await fetch(`/api/branding/assets/${kind}`, {
      method: "DELETE",
      credentials: "include",
    }),
  );
}
