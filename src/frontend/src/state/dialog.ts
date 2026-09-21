// In-app replacements for window.confirm and window.prompt, so every
// question the app asks looks like the rest of the app (and works inside
// the desktop shell, where the browser's own boxes look foreign). Both
// return a promise, so call sites read the same as before:
//   const confirm = useConfirm();
//   if (!(await confirm({ message: "Delete it?", confirmLabel: "Delete", danger: true }))) return;
import { ref } from "vue";

export interface DialogRequest {
  kind: "confirm" | "prompt";
  message: string;
  title?: string;
  confirmLabel: string;
  cancelLabel: string;
  danger: boolean;
  dismissible: boolean;
  defaultValue: string;
  placeholder: string;
  resolve: (value: boolean | string | null) => void;
}

// one dialog at a time: a second request waits for the first to close
export const activeDialog = ref<DialogRequest | null>(null);
const queue: DialogRequest[] = [];

function show(request: DialogRequest) {
  if (activeDialog.value) queue.push(request);
  else activeDialog.value = request;
}

export function closeDialog(value: boolean | string | null) {
  const current = activeDialog.value;
  activeDialog.value = queue.shift() ?? null;
  current?.resolve(value);
}

export interface ConfirmOptions {
  message: string;
  title?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  danger?: boolean;
  dismissible?: boolean;
}

export function useConfirm(): (options: ConfirmOptions) => Promise<boolean> {
  return (o) =>
    new Promise<boolean>((resolve) =>
      show({
        kind: "confirm",
        message: o.message,
        title: o.title,
        confirmLabel: o.confirmLabel ?? "Confirm",
        cancelLabel: o.cancelLabel ?? "Cancel",
        danger: o.danger ?? false,
        dismissible: o.dismissible ?? true,
        defaultValue: "",
        placeholder: "",
        resolve: (v) => resolve(v === true),
      }),
    );
}

export interface PromptOptions {
  message: string;
  title?: string;
  defaultValue?: string;
  placeholder?: string;
  confirmLabel?: string;
}

/** Resolves to the entered text, or null if the dialog was cancelled. */
export function usePrompt(): (
  options: PromptOptions,
) => Promise<string | null> {
  return (o) =>
    new Promise<string | null>((resolve) =>
      show({
        kind: "prompt",
        message: o.message,
        title: o.title,
        confirmLabel: o.confirmLabel ?? "OK",
        cancelLabel: "Cancel",
        danger: false,
        dismissible: true,
        defaultValue: o.defaultValue ?? "",
        placeholder: o.placeholder ?? "",
        resolve: (v) => resolve(typeof v === "string" ? v : null),
      }),
    );
}
