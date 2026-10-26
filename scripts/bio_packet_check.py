#!/usr/bin/env python3
"""GitHub Actions: look for the latest numbers-only heartbeat packet the owner's phone saved, re-validate it with the SAME strict gate
the IBM workflow uses, and report ONLY validity, sha12, age and bpm/sqi. Never prints the storage secret, never starts IBM, never invents a pulse.
Uses AZURE_STORAGE_CONTAINER_SAS_URL (or AZURE_STORAGE_CONNECTION_STRING). Exit 0 either way (the answer is in the outputs); exit 1 only on a bug."""
import json, os, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bio_packet_fetch as bf  # noqa: E402


def result(max_age_s=None, env_vars=None):
    e = env_vars if env_vars is not None else os.environ
    cs, sas = e.get("AZURE_STORAGE_CONNECTION_STRING", ""), e.get("AZURE_STORAGE_CONTAINER_SAS_URL", "")
    try:
        if cs:
            env = bf.fetch(cs, e.get("AZURE_STORAGE_CONTAINER") or None)
        elif sas:
            env = bf.fetch_sas(sas)
        else:
            raise SystemExit("no storage secret is available to this run")
        p, age = bf.check(env, max_age_s if max_age_s is not None else 6 * 3600)
    except SystemExit as x:
        return {"valid": False, "reason": str(x.code)}
    return {"valid": True, "sha12": p["packet_sha256"][:12], "age_s": int(age), "bpm": p["pulse"]["bpm"], "sqi": p["pulse"]["sqi"],
            "beats": p["pulse"]["beats"], "duration_s": p["pulse"]["duration_s"], "packet": p}


def main():
    r = result(int(os.environ.get("MAX_AGE_S") or 6 * 3600))
    if r["valid"]:
        line = f"valid=yes sha12={r['sha12']} age_s={r['age_s']} bpm={r['bpm']} sqi={r['sqi']} beats={r['beats']} duration_s={r['duration_s']} (numbers only, MEASURED on the phone)"
    else:
        line = f"valid=no -> no valid pulse ({r['reason']}). IBM was not started."
    print(line)
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a") as f:
            f.write(f"valid={'yes' if r['valid'] else 'no'}\n")
            if r["valid"]:
                f.write(f"sha12={r['sha12']}\nage_s={r['age_s']}\n")
                f.write("packet_json=" + json.dumps(r["packet"], sort_keys=True, separators=(",", ":")) + "\n")
    summ = os.environ.get("GITHUB_STEP_SUMMARY")
    if summ:
        with open(summ, "a") as f:
            f.write("### Saved heartbeat packet check\n\n")
            if r["valid"]:
                f.write(f"- **Valid pulse: yes**\n- sha12: `{r['sha12']}`\n- age: {r['age_s']} s\n- bpm: {r['bpm']} (quality {r['sqi']}, {r['beats']} beats, {r['duration_s']} s)\n- Label: heartbeat MEASURED on the phone (numbers only)\n")
            else:
                f.write(f"- **Valid pulse: no**. no valid pulse ({r['reason']})\n")
            f.write("- IBM was not started by this check.\n")


if __name__ == "__main__":
    main()
