/** Canonical JSON and Python-style rounding used by the tested QBEAST1 writer. */

export function pyRound(value, digits = 0) {
  const sign = value < 0 ? -1 : 1;
  const p = 10 ** digits;
  const y = Math.abs(value) * p;
  const fl = Math.floor(y);
  const frac = y - fl;
  let n;
  if (Math.abs(frac - 0.5) < 1e-8) n = (fl % 2 === 0) ? fl : fl + 1;
  else n = frac > 0.5 ? fl + 1 : fl;
  const rounded = sign * n / p;
  return digits === 0 ? rounded : Number(rounded.toFixed(digits));
}

export function canonicalJson(value) {
  if (value === null) return "null";
  if (typeof value === "boolean") return value ? "true" : "false";
  if (typeof value === "string") return JSON.stringify(value);
  if (typeof value === "number") {
    if (!Number.isFinite(value)) throw new Error("Invalid number");
    return JSON.stringify(value);
  }
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(",")}]`;
  const keys = Object.keys(value).sort();
  return `{${keys.map((key) => `${JSON.stringify(key)}:${canonicalJson(value[key])}`).join(",")}}`;
}
