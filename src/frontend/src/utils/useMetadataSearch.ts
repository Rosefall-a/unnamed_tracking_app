// The "search a metadata provider and prefill the form" state that the Movie,
// TV and Anime forms share: the query, the results, and the messages around
// them. Each form still decides which of its own fields a result fills in.
import { ref } from "vue";
import { lockedFieldLabels } from "./lockedFields";

export function useMetadataSearch<
  R extends { title: string; provider: string; providerId?: string },
>(options: {
  search: (query: string) => Promise<{
    results: R[];
    providerErrors: string[];
    providers?: string[];
  }>;
  // the full results for one title, read when a result is picked (the list
  // itself is a quick search with little more than names)
  details?: (title: string) => Promise<{ results: R[] }>;
  // "movie", "show" or "anime", for the messages
  noun: string;
  // when the search finds no provider at all, where to add a key
  // ("TMDB or OMDb"); leave out for a provider that needs no key
  keyHint?: string;
}) {
  const query = ref("");
  const results = ref<R[]>([]);
  const searching = ref(false);
  const message = ref<string | null>(null);
  const warnings = ref<string[]>([]);

  async function run() {
    if (query.value.trim().length < 2) {
      message.value = "Enter at least two characters to search.";
      return;
    }
    searching.value = true;
    message.value = null;
    warnings.value = [];
    try {
      const response = await options.search(query.value.trim());
      results.value = response.results;
      warnings.value = response.providerErrors;
      if (options.keyHint && response.providers && !response.providers.length) {
        message.value = `No metadata providers configured. Add a ${options.keyHint} API key in Settings > Metadata > Metadata/API to enable ${options.noun} search.`;
      } else if (!results.value.length) {
        message.value = `No ${options.noun === "show" ? "shows" : options.noun === "movie" ? "movies" : options.noun} found.`;
      }
    } catch (e) {
      message.value =
        e instanceof Error ? e.message : "Metadata search failed.";
    } finally {
      searching.value = false;
    }
  }

  // the picked result with its details filled in, or as it was if they could
  // not be read
  async function resolve(result: R): Promise<R> {
    if (!options.details) return result;
    message.value = "Reading the details…";
    try {
      const { results: full } = await options.details(result.title);
      return (
        full.find(
          (r) =>
            r.provider === result.provider && r.providerId === result.providerId,
        ) ??
        full.find((r) => r.title.toLowerCase() === result.title.toLowerCase()) ??
        result
      );
    } catch {
      return result;
    }
  }

  // after a result has been applied to the form
  function applied(result: R, lockedFields: string[], note = "") {
    results.value = [];
    query.value = result.title;
    message.value = lockedFields.length
      ? `Prefilled from ${result.provider}${note}. Skipped ${lockedFields.length} field(s) you've already edited: ${lockedFieldLabels(lockedFields).join(", ")}. Review the fields before saving.`
      : `Prefilled from ${result.provider}${note}. Review the fields before saving.`;
  }

  return {
    query,
    results,
    searching,
    message,
    warnings,
    run,
    resolve,
    applied,
  };
}
