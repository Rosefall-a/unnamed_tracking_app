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
  if (error instanceof TypeError) return true;
  if (!(error instanceof Error)) return false;
  return /fetch|network|failed to check setup/i.test(error.message)
    || /failed to check setup:\s*5\d\d/i.test(error.message);
}

/**
 * The backend deliberately may not answer until database startup and
 * migrations have completed. Keep the public shell alive and retry rather
 * than treating that normal startup interval as an authentication failure.
 *
 * These are descriptive phases, not measured migration progress.
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
