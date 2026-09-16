import { ref } from "vue";
import { fetchSetupStatus } from "../services/setup";

export type ServerStartupPhase =
  | "waiting_for_backend"
  | "waiting_for_database"
  | "running_migrations"
  | "starting_api"
  | "ready";

export const serverStartupPhase = ref<ServerStartupPhase>("waiting_for_backend");
export const serverStartupVisible = ref(true);

let startupPromise: Promise<boolean> | null = null;

function phaseForAttempt(attempt: number): ServerStartupPhase {
  if (attempt < 3) return "waiting_for_database";
  if (attempt < 8) return "running_migrations";
  return "starting_api";
}

export function isBackendUnavailable(error: unknown): boolean {
  return error instanceof TypeError ||
    (error instanceof Error && /fetch|network|failed to check setup/i.test(error.message));
}

/**
 * Keep the public shell on a startup screen while the backend container is
 * booting. The backend intentionally does not listen until its migrations are
 * complete, so the UI cannot get a real migration percentage; the phases here
 * describe the expected startup sequence and continue retrying until the API
 * becomes reachable.
 */
export function waitForServer(): Promise<boolean> {
  if (startupPromise) return startupPromise;

  startupPromise = (async () => {
    let attempt = 0;
    while (true) {
      try {
        const status = await fetchSetupStatus();
        serverStartupPhase.value = "ready";
        serverStartupVisible.value = false;
        return status.setup_required;
      } catch (error) {
        if (!isBackendUnavailable(error)) throw error;
        serverStartupPhase.value = phaseForAttempt(attempt);
        attempt += 1;
        await new Promise((resolve) => setTimeout(resolve, Math.min(1000 + attempt * 250, 3000)));
      }
    }
  })().finally(() => {
    startupPromise = null;
  });

  return startupPromise;
}
