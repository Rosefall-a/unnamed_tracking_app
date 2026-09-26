export interface YamtrackDifference {
  field: string;
  site: string | null;
  mal: string;
}

export interface YamtrackPreview {
  total: number;
  new_count: number;
  new_titles: string[];
  existing: Array<{
    yamtrack_id: string;
    title: string;
    site_title: string;
    differences: YamtrackDifference[];
  }>;
  identical: number;
  skipped_other: number;
}

export interface YamtrackImportResult {
  created: number;
  updated: number;
  kept: number;
  total_in_file: number;
  skipped_other: number;
  details_filled: number;
  details_not_found: number;
  details_unavailable: boolean;
  details_source: string | null;
  episodes_imported: number;
}

async function postYamtrack(
  path: string,
  file: File,
  extra: Record<string, string> = {},
): Promise<Response> {
  const body = new FormData();
  body.append("file", file);
  for (const [key, value] of Object.entries(extra)) body.append(key, value);
  const response = await fetch(path, {
    method: "POST",
    credentials: "include",
    body,
  });
  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try {
      detail = (await response.json()).detail ?? detail;
    } catch {
      /* keep the status line */
    }
    throw new Error(detail);
  }
  return response;
}

export async function previewYamtrack(file: File): Promise<YamtrackPreview> {
  return await (await postYamtrack("/api/import/yamtrack/preview", file)).json();
}

export async function importYamtrack(
  file: File,
  useYamtrack: string[],
  fetchDetails: boolean,
): Promise<YamtrackImportResult> {
  return await (
    await postYamtrack("/api/import/yamtrack", file, {
      overwrite: JSON.stringify(useYamtrack),
      fetch_details: String(fetchDetails),
    })
  ).json();
}
