/** Where the one mounted Lost Cosmos screen is allowed to show. */

export const MINI_PATHS = ["/", "/try", "/beast-cage", "/beast-cage/talk", "/beast-cage/guest", "/beast-cage/play"];
export const FULL_PATH = "/beast-cage/go";

export function modeFor(path) {
  const value = String(path || "/").replace(/\/+$/, "") || "/";
  if (value.startsWith("/workspace")) return "parked";
  if (value === FULL_PATH) return "full";
  if (MINI_PATHS.includes(value)) return "mini";
  return "parked";
}
