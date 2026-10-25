#!/usr/bin/env python3
"""Box-side: fetch the latest numbers-only bio packet the phone saved to the owner's PRIVATE storage, re-validate it, and print the
exact (secret-free) `gh workflow run` command. Never prints the storage secret. Never dispatches. Never invents a pulse.

    AZURE_STORAGE_CONNECTION_STRING=... [AZURE_STORAGE_CONTAINER=name] python scripts/bio_packet_fetch.py --out /tmp/bio_packet.json [--max-age-s 21600]

Exit 0 only for a packet that passes the SAME strict checks the workflow uses (schema, ranges, sqi>=0.6, hash) and is recent.
Exit 2 = nothing saved / invalid / too old -> say "no valid pulse" and do not run IBM."""
import argparse, base64, hashlib, hmac, json, os, sys, time, urllib.request, urllib.error, urllib.parse
from email.utils import formatdate
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bio_connection_packet as bp  # noqa: E402

VERSION = "2021-08-06"
BLOB = "owner/bio-packets/latest.json"
WORKFLOW = "real-ibm-bio-connection.yml"


def parse_cs(cs):
    kv = dict(p.split("=", 1) for p in cs.split(";") if "=" in p)
    acct, key = kv.get("AccountName"), kv.get("AccountKey")
    if not acct or not key:
        raise SystemExit("storage connection string missing AccountName/AccountKey")
    ep = (kv.get("BlobEndpoint") or f"{kv.get('DefaultEndpointsProtocol', 'https')}://{acct}.blob.{kv.get('EndpointSuffix', 'core.windows.net')}").rstrip("/")
    return acct, key, ep


def request(acct, key, url, now=None):
    u = urllib.parse.urlsplit(url)
    hdr = {"x-ms-date": formatdate(now or time.time(), usegmt=True), "x-ms-version": VERSION}
    canon_h = "".join(f"{k}:{v}\n" for k, v in sorted(hdr.items()))
    q = urllib.parse.parse_qs(u.query, keep_blank_values=True)
    canon_r = f"/{acct}{u.path}" + "".join(f"\n{k.lower()}:{','.join(sorted(v))}" for k, v in sorted(q.items()))
    sts = "\n".join(["GET", "", "", "", "", "", "", "", "", "", "", "", canon_h + canon_r])
    sig = base64.b64encode(hmac.new(base64.b64decode(key), sts.encode(), hashlib.sha256).digest()).decode()
    req = urllib.request.Request(url, headers={**hdr, "Authorization": f"SharedKey {acct}:{sig}"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:  # noqa: S310 (https storage endpoint from the owner's own config)
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, b""


def containers(acct, key, ep):
    st, body = request(acct, key, ep + "/?comp=list")
    if st != 200:
        return []
    import re
    return re.findall(r"<Name>([^<]+)</Name>", body.decode("utf-8", "replace"))


def fetch(cs, container=None):
    acct, key, ep = parse_cs(cs)
    names = [container] if container else (containers(acct, key, ep) or ["beast-cosmos"])
    for c in names:
        st, body = request(acct, key, f"{ep}/{c}/{BLOB}")
        if st == 200:
            return json.loads(body)
    return None


def check(env, max_age_s, now=None):
    """Return (packet, age_s) or raise SystemExit(2) with a plain reason. Same strict gate as the workflow."""
    if not env or "packet" not in env:
        raise SystemExit("no saved packet: no valid pulse")
    p = env["packet"]
    errs = bp.validate(p)
    if errs:
        raise SystemExit("saved packet is not valid: " + "; ".join(errs[:3]))
    body = {k: v for k, v in p.items() if k != "packet_sha256"}
    if bp.sha(bp.canonical(body)) != p["packet_sha256"]:
        raise SystemExit("saved packet hash mismatch")
    age = (now or time.time()) - float(env.get("saved_at_ms", 0)) / 1000.0
    if age > max_age_s:
        raise SystemExit(f"saved packet is {int(age)} s old (limit {max_age_s}): no recent valid pulse")
    return p, age


def dispatch_command(p, path):
    return (f"gh workflow run {WORKFLOW} -R NavisWORLD/The-beast-box- --ref main -f packet_sha12={p['packet_sha256'][:12]} "
            f"-f \"packet_json=$(cat {path})\"")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-age-s", type=int, default=6 * 3600)
    a = ap.parse_args(argv)
    cs = os.environ.get("AZURE_STORAGE_CONNECTION_STRING", "")
    if not cs:
        raise SystemExit("AZURE_STORAGE_CONNECTION_STRING is not set")
    env = fetch(cs, os.environ.get("AZURE_STORAGE_CONTAINER") or None)
    p, age = check(env, a.max_age_s)
    Path(a.out).write_text(json.dumps(p, sort_keys=True, separators=(",", ":")))
    print(f"BIO_PACKET_VALID sha12={p['packet_sha256'][:12]} bpm={p['pulse']['bpm']} sqi={p['pulse']['sqi']} age_s={int(age)} (numbers only)")
    print("DISPATCH_CMD " + dispatch_command(p, a.out))


if __name__ == "__main__":
    main()
