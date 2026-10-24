#!/usr/bin/env python3
"""Extract numeric features from a private recording on THIS machine (owner's device or box).

    extract_private_features.py KIND PATH --opt-in [--store DIR] [--site on-box|on-device]
        KIND: heart | voice | music | audio   (16-bit PCM WAV, up to 4 MiB / 30 s)
    extract_private_features.py KIND --json FILE --opt-in ...
        KIND: heart (rr_ms, rest_bpm) | light (values) | eeg_muse (bands, contact)   (device-exported numbers)

Prints and stores ONLY the features and their sha256. The path, the samples and the bytes are never printed,
logged or stored, and the store refuses to live inside a git work tree. Nothing is uploaded.
"""
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from beastbox.private_features import FeatureStore, extract_numeric, extract_wav  # noqa: E402


def main(argv):
    if len(argv) < 2 or "--opt-in" not in argv:
        sys.exit(__doc__)
    opt = lambda k, d=None: argv[argv.index(k) + 1] if k in argv else d
    kind, site = argv[0], opt("--site", "on-box")
    if "--json" in argv:
        payload = json.loads(Path(opt("--json")).read_text())
        src = extract_numeric(kind, payload, opt_in=True, site=site)
    else:
        src = extract_wav(kind, argv[1], opt_in=True, site=site)
    FeatureStore(opt("--store")).put(kind, src)
    print(json.dumps({"source": kind, "features": src["features"], "feature_sha256": src["provenance"]["feature_sha256"],
                      "raw_retained": False}, indent=1, sort_keys=True))


if __name__ == "__main__":
    main(sys.argv[1:])
