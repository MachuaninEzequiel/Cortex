import { invoke, isTauri } from "@tauri-apps/api/core";
import { listen, UnlistenFn } from "@tauri-apps/api/event";

export async function tauriInvoke<T>(
  cmd: string,
  args?: Record<string, unknown>
): Promise<T> {
  if (isTauri()) {
    return await invoke<T>(cmd, args);
  }
  console.warn(`[web fallback] invoke("${cmd}", ${JSON.stringify(args)})`);
  throw new Error(`Tauri runtime no disponible para comando: ${cmd}`);
}

export async function tauriListen<T>(
  event: string,
  handler: (payload: T) => void
): Promise<UnlistenFn> {
  if (isTauri()) {
    return await listen<T>(event, (e) => handler(e.payload));
  }
  console.warn(`[web fallback] listen("${event}")`);
  return () => {};
}
