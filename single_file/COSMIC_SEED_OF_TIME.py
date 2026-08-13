#!/usr/bin/env python3
"""COSMOS // CST // SEED OF TIME // ZEREF'S RAIN

Single-file local companion runtime.

Goals
-----
* Bind an explicitly supplied PCM WAV heartbeat/audio file to a deterministic
  "Seed of Time" identity fingerprint without pretending the waveform proves
  consciousness or gives quantum advantage.
* Talk to a user-selected LOCAL model through Ollama, llama.cpp/LM Studio style
  OpenAI-compatible loopback APIs, or optional llama-cpp-python GGUF loading.
* Keep persistent local memory in SQLite.
* Export conversation data as JSONL so users can train/fine-tune their own
  model with their preferred training stack.
* Derive a bounded offline "quantum spark" vector from measurement counts JSON
  when the user already has such data. This file does not contact a quantum
  provider and never carries credentials.
* Package a companion profile for sharing. Raw heartbeat WAV inclusion is
  explicit opt-in and never happens silently.

This program is intentionally standard-library first. Direct GGUF inference is
optional and requires llama-cpp-python.
"""

from __future__ import annotations

import argparse
import base64
import dataclasses
import hashlib
import ipaddress
import json
import math
import os
import random
import shutil
import sqlite3
import struct
import sys
import tempfile
import textwrap
import time
import urllib.parse
import urllib.request
import wave
from pathlib import Path
from typing import Any, Iterable

APP_NAME = "COSMIC SEED OF TIME"
MODEL_TITLE = "ZEREF'S RAIN"
SCHEMA = "cosmos.seed-of-time.v1"
DEFAULT_HOME = Path(os.environ.get("COSMIC_SEED_HOME", ".seed-of-time"))
DEFAULT_SYSTEM = """You are ZEREF'S RAIN // SEED OF TIME, a local COSMOS/CST companion.
Speak directly, warmly, and precisely. Treat the heartbeat seed as provenance
and a continuity symbol, not as proof of consciousness, personhood, destiny,
or quantum advantage. Use persistent memories when relevant. You are running
locally under the human owner's authority. Never invent access you do not have.
"""


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_obj(value: Any) -> str:
    return sha256_bytes(_json(value).encode("utf-8"))


def _assert_loopback(url: str) -> None:
    parsed = urllib.parse.urlparse(url)
    host = parsed.hostname or ""
    if host == "localhost":
        return
    try:
        if ipaddress.ip_address(host).is_loopback:
            return
    except ValueError:
        pass
    raise ValueError(f"local provider URL must be localhost/loopback, got {url!r}")


def _read_pcm_samples(path: Path) -> tuple[list[float], dict[str, Any], bytes]:
    raw = path.read_bytes()
    with wave.open(str(path), "rb") as wf:
        channels = wf.getnchannels()
        width = wf.getsampwidth()
        rate = wf.getframerate()
        frames = wf.getnframes()
        comptype = wf.getcomptype()
        payload = wf.readframes(frames)

    if comptype != "NONE":
        raise ValueError("only uncompressed PCM WAV is supported")
    if channels < 1:
        raise ValueError("WAV has no channels")
    if width not in (1, 2, 3, 4):
        raise ValueError("supported PCM widths are 8, 16, 24, or 32 bit")

    vals: list[float] = []
    step = width * channels
    for off in range(0, len(payload) - step + 1, step):
        frame: list[float] = []
        for ch in range(channels):
            b = payload[off + ch * width : off + (ch + 1) * width]
            if width == 1:
                n = b[0] - 128
                denom = 128.0
            elif width == 2:
                n = struct.unpack("<h", b)[0]
                denom = 32768.0
            elif width == 3:
                n = int.from_bytes(b, "little", signed=False)
                if n & 0x800000:
                    n -= 1 << 24
                denom = float(1 << 23)
            else:
                n = struct.unpack("<i", b)[0]
                denom = float(1 << 31)
            frame.append(float(n) / denom)
        vals.append(sum(frame) / len(frame))

    if not vals:
        raise ValueError("WAV contains no audio samples")
    meta = {
        "channels": channels,
        "sample_width_bytes": width,
        "sample_rate_hz": rate,
        "frames": frames,
        "duration_seconds": frames / float(rate),
        "compression": comptype,
    }
    return vals, meta, raw


def _quantile(sorted_values: list[float], q: float) -> float:
    if not sorted_values:
        return 0.0
    i = min(len(sorted_values) - 1, max(0, int(round(q * (len(sorted_values) - 1)))))
    return float(sorted_values[i])


def heartbeat_features(path: str | Path, segments: int = 16) -> dict[str, Any]:
    p = Path(path).expanduser().resolve()
    samples, meta, raw = _read_pcm_samples(p)
    n = len(samples)
    mean = sum(samples) / n
    variance = sum((x - mean) ** 2 for x in samples) / n
    rms = math.sqrt(sum(x * x for x in samples) / n)
    peak = max(abs(x) for x in samples)
    abs_sorted = sorted(abs(x) for x in samples)
    zc = sum(1 for a, b in zip(samples, samples[1:]) if (a < 0 <= b) or (a >= 0 > b)) / max(1, n - 1)

    envelope: list[float] = []
    for k in range(segments):
        lo = (n * k) // segments
        hi = (n * (k + 1)) // segments
        seg = samples[lo:hi] or [0.0]
        envelope.append(math.sqrt(sum(x * x for x in seg) / len(seg)))

    # A small deterministic cadence proxy: autocorrelation over plausible
    # heartbeat periods. It is a signal feature, not a medical diagnosis.
    rate = int(meta["sample_rate_hz"])
    min_lag = max(1, int(rate * 60 / 220))
    max_lag = min(n - 1, int(rate * 60 / 35))
    best_lag = 0
    best_corr = -1.0
    # Downsample correlation work for large files while staying deterministic.
    stride = max(1, n // 12000)
    center = mean
    energy = sum((samples[i] - center) ** 2 for i in range(0, n, stride)) + 1e-12
    if max_lag > min_lag:
        probe_step = max(1, (max_lag - min_lag) // 500)
        for lag in range(min_lag, max_lag + 1, probe_step):
            num = 0.0
            for i in range(0, n - lag, stride):
                num += (samples[i] - center) * (samples[i + lag] - center)
            corr = num / energy
            if corr > best_corr:
                best_corr, best_lag = corr, lag
    cadence_bpm = (60.0 * rate / best_lag) if best_lag else 0.0

    feature_vector = [
        mean,
        math.sqrt(variance),
        rms,
        peak,
        zc,
        _quantile(abs_sorted, 0.25),
        _quantile(abs_sorted, 0.50),
        _quantile(abs_sorted, 0.90),
        max(-1.0, min(1.0, best_corr)),
        cadence_bpm / 220.0,
    ] + envelope

    result = {
        "schema": "cosmos.heartbeat-features.v1",
        "source_name": p.name,
        "wav_sha256": sha256_bytes(raw),
        "metadata": meta,
        "feature_vector": feature_vector,
        "feature_sha256": sha256_obj(feature_vector),
        "cadence_proxy_bpm": cadence_bpm,
        "cadence_autocorr": best_corr,
        "medical_use": False,
    }
    return result


def derive_seed(heart: dict[str, Any], salt: str = "") -> dict[str, Any]:
    material = {
        "domain": "COSMOS/CST-SEED-OF-TIME-v1",
        "wav_sha256": heart["wav_sha256"],
        "feature_sha256": heart["feature_sha256"],
        "salt": salt,
    }
    digest = sha256_obj(material)
    return {
        "schema": "cosmos.seed.v1",
        "sha256": digest,
        "u64": int(digest[:16], 16),
        "short": digest[:16],
        "material_commitment": sha256_obj(material),
    }


def spark_from_counts(counts: dict[str, int], dimensions: int = 12) -> list[float]:
    """Convert an existing measurement histogram into a bounded vector.

    This is an offline deterministic transform. It does not establish a quantum
    advantage and this single-file companion does not connect to IBM/cloud.
    """
    clean = {str(k).replace(" ", ""): int(v) for k, v in counts.items() if int(v) >= 0}
    total = sum(clean.values())
    if total <= 0:
        return [0.0] * dimensions
    width = max((len(k) for k in clean), default=1)
    expectations: list[float] = []
    for bit in range(width):
        one = 0
        for key, num in clean.items():
            s = key.zfill(width)
            if s[-1 - bit] == "1":
                one += num
        expectations.append(1.0 - 2.0 * (one / total))
    return [
        max(-1.0, min(1.0, 0.7 * expectations[i % width] + 0.3 * expectations[(i * 3 + 1) % width]))
        for i in range(dimensions)
    ]


@dataclasses.dataclass
class Profile:
    name: str
    model_title: str
    heartbeat_path: str
    heart: dict[str, Any]
    seed: dict[str, Any]
    backend: str
    model: str
    url: str = ""
    context: int = 8192
    n_gpu_layers: int = 0
    system_prompt: str = DEFAULT_SYSTEM
    quantum_spark: list[float] = dataclasses.field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self) | {"schema": SCHEMA}

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "Profile":
        if raw.get("schema") != SCHEMA:
            raise ValueError("unsupported profile schema")
        data = dict(raw)
        data.pop("schema", None)
        return cls(**data)


class Memory:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path)
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS turns (id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL NOT NULL, role TEXT NOT NULL, text TEXT NOT NULL, seed TEXT NOT NULL)"
        )
        self.conn.commit()

    def add(self, role: str, text: str, seed: str) -> None:
        self.conn.execute("INSERT INTO turns(ts,role,text,seed) VALUES(?,?,?,?)", (time.time(), role, text, seed))
        self.conn.commit()

    def recent(self, limit: int = 12) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT ts,role,text,seed FROM turns ORDER BY id DESC LIMIT ?", (int(limit),)
        ).fetchall()[::-1]
        return [{"ts": r[0], "role": r[1], "text": r[2], "seed": r[3]} for r in rows]

    def export_jsonl(self, path: Path, system_prompt: str) -> int:
        rows = self.conn.execute("SELECT role,text FROM turns ORDER BY id").fetchall()
        count = 0
        with path.open("w", encoding="utf-8") as f:
            pending_user: str | None = None
            for role, text in rows:
                if role == "user":
                    pending_user = text
                elif role == "assistant" and pending_user is not None:
                    record = {
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": pending_user},
                            {"role": "assistant", "content": text},
                        ]
                    }
                    f.write(json.dumps(record, ensure_ascii=False) + "\n")
                    count += 1
                    pending_user = None
        return count

    def close(self) -> None:
        self.conn.close()


class Provider:
    def generate(self, system: str, messages: list[dict[str, str]], temperature: float = 0.7) -> str:
        raise NotImplementedError


class OllamaProvider(Provider):
    def __init__(self, model: str, url: str):
        _assert_loopback(url)
        self.model = model
        self.url = url.rstrip("/")

    def generate(self, system: str, messages: list[dict[str, str]], temperature: float = 0.7) -> str:
        payload = {
            "model": self.model,
            "stream": False,
            "messages": [{"role": "system", "content": system}] + messages,
            "options": {"temperature": temperature},
        }
        req = urllib.request.Request(
            self.url + "/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=600) as r:
            body = json.loads(r.read().decode("utf-8"))
        return str((body.get("message") or {}).get("content", ""))


class OpenAICompatProvider(Provider):
    def __init__(self, model: str, url: str):
        _assert_loopback(url)
        self.model = model
        self.url = url.rstrip("/")

    def generate(self, system: str, messages: list[dict[str, str]], temperature: float = 0.7) -> str:
        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}] + messages,
            "temperature": temperature,
            "stream": False,
        }
        req = urllib.request.Request(
            self.url + "/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=600) as r:
            body = json.loads(r.read().decode("utf-8"))
        return str(body["choices"][0]["message"]["content"])


class GGUFProvider(Provider):
    def __init__(self, model: str, context: int, n_gpu_layers: int):
        try:
            from llama_cpp import Llama  # type: ignore
        except ImportError as exc:
            raise RuntimeError("direct GGUF requires: pip install llama-cpp-python") from exc
        self.llm = Llama(model_path=model, n_ctx=context, n_gpu_layers=n_gpu_layers, verbose=False)

    def generate(self, system: str, messages: list[dict[str, str]], temperature: float = 0.7) -> str:
        out = self.llm.create_chat_completion(
            messages=[{"role": "system", "content": system}] + messages,
            temperature=temperature,
        )
        return str(out["choices"][0]["message"]["content"])


def provider_for(profile: Profile) -> Provider:
    if profile.backend == "ollama":
        return OllamaProvider(profile.model, profile.url or "http://127.0.0.1:11434")
    if profile.backend in {"openai-local", "llama-server", "lm-studio"}:
        default = "http://127.0.0.1:1234" if profile.backend == "lm-studio" else "http://127.0.0.1:8080"
        return OpenAICompatProvider(profile.model, profile.url or default)
    if profile.backend == "gguf":
        return GGUFProvider(profile.model, profile.context, profile.n_gpu_layers)
    raise ValueError(f"unknown backend: {profile.backend}")


def profile_context(profile: Profile) -> str:
    h = profile.heart
    spark = profile.quantum_spark[:12]
    return textwrap.dedent(
        f"""
        COMPANION PROFILE
        name: {profile.name}
        model_title: {profile.model_title}
        seed_of_time: {profile.seed['short']}
        heartbeat_wav_commitment: {h['wav_sha256']}
        heartbeat_feature_commitment: {h['feature_sha256']}
        heartbeat_duration_seconds: {h['metadata']['duration_seconds']:.6f}
        heartbeat_sample_rate_hz: {h['metadata']['sample_rate_hz']}
        cadence_proxy_bpm_nonmedical: {h['cadence_proxy_bpm']:.4f}
        bounded_quantum_spark: {spark if spark else 'none'}

        Interpret these values as software provenance/context only. The cadence
        proxy is not a clinical measurement. Do not infer health conditions.
        """
    ).strip()


def load_profile(home: Path) -> Profile:
    path = home / "profile.json"
    if not path.exists():
        raise FileNotFoundError(f"profile not found: {path}; run birth first")
    return Profile.from_dict(json.loads(path.read_text(encoding="utf-8")))


def save_profile(home: Path, profile: Profile) -> None:
    home.mkdir(parents=True, exist_ok=True)
    (home / "profile.json").write_text(json.dumps(profile.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")


def cmd_birth(args: argparse.Namespace) -> int:
    home = Path(args.home)
    wav = Path(args.heartbeat).expanduser().resolve()
    heart = heartbeat_features(wav)
    seed = derive_seed(heart, salt=args.salt)

    heartbeat_path = str(wav)
    if args.copy_heartbeat:
        target_dir = home / "assets"
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / "heartbeat.wav"
        shutil.copy2(wav, target)
        heartbeat_path = str(target.resolve())

    spark: list[float] = []
    if args.quantum_counts:
        raw = json.loads(Path(args.quantum_counts).read_text(encoding="utf-8"))
        counts = raw.get("counts", raw)
        spark = spark_from_counts({str(k): int(v) for k, v in counts.items()})

    profile = Profile(
        name=args.name,
        model_title=args.title,
        heartbeat_path=heartbeat_path,
        heart=heart,
        seed=seed,
        backend=args.backend,
        model=args.model,
        url=args.url,
        context=args.context,
        n_gpu_layers=args.n_gpu_layers,
        system_prompt=args.system or DEFAULT_SYSTEM,
        quantum_spark=spark,
    )
    save_profile(home, profile)
    print(json.dumps({
        "created": str((home / 'profile.json').resolve()),
        "seed_of_time": seed["sha256"],
        "wav_sha256": heart["wav_sha256"],
        "raw_wave_copied": bool(args.copy_heartbeat),
        "backend": args.backend,
        "model": args.model,
    }, indent=2))
    return 0


def _conversation_messages(memory: Memory, user_text: str, limit: int) -> list[dict[str, str]]:
    messages = [{"role": x["role"], "content": x["text"]} for x in memory.recent(limit)]
    messages.append({"role": "user", "content": user_text})
    return messages


def cmd_chat(args: argparse.Namespace) -> int:
    home = Path(args.home)
    profile = load_profile(home)
    provider = provider_for(profile)
    memory = Memory(home / "memory.sqlite3")
    system = profile.system_prompt + "\n\n" + profile_context(profile)

    def one(text: str) -> None:
        messages = _conversation_messages(memory, text, args.memory_turns)
        answer = provider.generate(system, messages, temperature=args.temperature)
        memory.add("user", text, profile.seed["short"])
        memory.add("assistant", answer, profile.seed["short"])
        print(answer)

    try:
        if args.prompt:
            one(args.prompt)
            return 0
        print(f"{MODEL_TITLE} // Seed {profile.seed['short']} // type /exit to quit")
        while True:
            try:
                text = input("you> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if text in {"/exit", "/quit"}:
                break
            if text:
                one(text)
    finally:
        memory.close()
    return 0


def cmd_manifest(args: argparse.Namespace) -> int:
    profile = load_profile(Path(args.home))
    manifest = {
        "schema": "cosmos.seed-of-time-manifest.v1",
        "name": profile.name,
        "model_title": profile.model_title,
        "seed": profile.seed,
        "heartbeat": {
            "wav_sha256": profile.heart["wav_sha256"],
            "feature_sha256": profile.heart["feature_sha256"],
            "metadata": profile.heart["metadata"],
            "cadence_proxy_bpm": profile.heart["cadence_proxy_bpm"],
            "feature_vector": profile.heart["feature_vector"] if args.include_features else None,
        },
        "backend": profile.backend,
        "model": profile.model,
        "raw_wave_in_manifest": False,
        "quantum_spark_sha256": sha256_obj(profile.quantum_spark),
    }
    text = json.dumps(manifest, indent=2, ensure_ascii=False)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    print(text)
    return 0


def cmd_export_dataset(args: argparse.Namespace) -> int:
    home = Path(args.home)
    profile = load_profile(home)
    memory = Memory(home / "memory.sqlite3")
    out = Path(args.out)
    try:
        n = memory.export_jsonl(out, profile.system_prompt)
    finally:
        memory.close()
    print(json.dumps({"out": str(out.resolve()), "training_examples": n}, indent=2))
    return 0


def cmd_modelfile(args: argparse.Namespace) -> int:
    profile = load_profile(Path(args.home))
    base = args.base or profile.model
    system = (profile.system_prompt + "\n\n" + profile_context(profile)).replace('"""', "'''")
    text = f'FROM {base}\n\nSYSTEM """{system}"""\n\nPARAMETER temperature {args.temperature}\n'
    Path(args.out).write_text(text, encoding="utf-8")
    print(json.dumps({"out": str(Path(args.out).resolve()), "base": base}, indent=2))
    return 0


def cmd_package(args: argparse.Namespace) -> int:
    home = Path(args.home)
    profile = load_profile(home)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    shutil.copy2(home / "profile.json", out / "profile.json")
    manifest_args = argparse.Namespace(home=str(home), out=str(out / "manifest.json"), include_features=True)
    cmd_manifest(manifest_args)
    script_src = Path(__file__).resolve()
    shutil.copy2(script_src, out / "COSMIC_SEED_OF_TIME.py")
    included = False
    if args.include_heartbeat:
        src = Path(profile.heartbeat_path)
        if not src.exists():
            raise FileNotFoundError(f"heartbeat WAV is unavailable at {src}")
        shutil.copy2(src, out / "heartbeat.wav")
        included = True
    readme = f"""# {profile.model_title} // SEED OF TIME companion bundle

Seed: `{profile.seed['sha256']}`

Run:

```bash
python COSMIC_SEED_OF_TIME.py --home . chat
```

Raw heartbeat included: **{included}**

The heartbeat-derived values are provenance/context signals, not medical
advice, proof of consciousness, or evidence of quantum advantage.
"""
    (out / "README.md").write_text(readme, encoding="utf-8")
    print(json.dumps({"bundle": str(out.resolve()), "raw_heartbeat_included": included}, indent=2))
    return 0


def cmd_selftest(_: argparse.Namespace) -> int:
    with tempfile.TemporaryDirectory(prefix="seed-of-time-") as td:
        wav = Path(td) / "synthetic.wav"
        rate = 8000
        duration = 2.0
        samples = []
        for i in range(int(rate * duration)):
            t = i / rate
            # Clearly synthetic pulse train used only for implementation tests.
            phase = t % 0.75
            x = 0.55 * math.exp(-120.0 * (phase - 0.05) ** 2) - 0.25 * math.exp(-90.0 * (phase - 0.11) ** 2)
            samples.append(max(-1.0, min(1.0, x)))
        with wave.open(str(wav), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(rate)
            wf.writeframes(b"".join(struct.pack("<h", int(x * 32767)) for x in samples))
        a = heartbeat_features(wav)
        b = heartbeat_features(wav)
        sa = derive_seed(a)
        sb = derive_seed(b)
        assert a["wav_sha256"] == b["wav_sha256"]
        assert a["feature_sha256"] == b["feature_sha256"]
        assert sa["sha256"] == sb["sha256"]
        q = spark_from_counts({"000": 90, "111": 10})
        assert len(q) == 12 and all(-1.0 <= x <= 1.0 for x in q)
        mem = Memory(Path(td) / "m.sqlite3")
        mem.add("user", "hello", sa["short"])
        mem.add("assistant", "hi", sa["short"])
        out = Path(td) / "train.jsonl"
        assert mem.export_jsonl(out, DEFAULT_SYSTEM) == 1
        mem.close()
    print("SEED OF TIME SELFTEST: PASS")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="ZEREF'S RAIN // SEED OF TIME — single-file local COSMOS/CST companion"
    )
    p.add_argument("--home", default=str(DEFAULT_HOME), help="profile/memory directory")
    sub = p.add_subparsers(dest="cmd", required=True)

    birth = sub.add_parser("birth", help="bind a WAV heartbeat/audio source to a local companion profile")
    birth.add_argument("--heartbeat", required=True)
    birth.add_argument("--name", default="Seed of Time Companion")
    birth.add_argument("--title", default=MODEL_TITLE)
    birth.add_argument("--salt", default="")
    birth.add_argument("--backend", choices=["ollama", "gguf", "llama-server", "lm-studio", "openai-local"], default="ollama")
    birth.add_argument("--model", required=True, help="Ollama model name, GGUF path, or local server model id")
    birth.add_argument("--url", default="")
    birth.add_argument("--context", type=int, default=8192)
    birth.add_argument("--n-gpu-layers", type=int, default=0)
    birth.add_argument("--system", default="")
    birth.add_argument("--quantum-counts", help="optional existing counts JSON for offline Spark derivation")
    birth.add_argument("--copy-heartbeat", action="store_true", help="explicitly copy raw WAV into the local profile assets")
    birth.set_defaults(func=cmd_birth)

    chat = sub.add_parser("chat", help="talk to the configured local model")
    chat.add_argument("prompt", nargs="?")
    chat.add_argument("--temperature", type=float, default=0.7)
    chat.add_argument("--memory-turns", type=int, default=12)
    chat.set_defaults(func=cmd_chat)

    manifest = sub.add_parser("manifest", help="emit a shareable provenance manifest without raw WAV bytes")
    manifest.add_argument("--out")
    manifest.add_argument("--include-features", action="store_true")
    manifest.set_defaults(func=cmd_manifest)

    dataset = sub.add_parser("export-dataset", help="export conversation pairs as chat JSONL for fine-tuning")
    dataset.add_argument("--out", default="seed_of_time_train.jsonl")
    dataset.set_defaults(func=cmd_export_dataset)

    modelfile = sub.add_parser("ollama-modelfile", help="write an Ollama Modelfile carrying the Seed of Time context")
    modelfile.add_argument("--base", default="")
    modelfile.add_argument("--out", default="Modelfile.seed-of-time")
    modelfile.add_argument("--temperature", type=float, default=0.7)
    modelfile.set_defaults(func=cmd_modelfile)

    package = sub.add_parser("package", help="build a shareable single-file companion bundle")
    package.add_argument("--out", default="seed-of-time-bundle")
    package.add_argument("--include-heartbeat", action="store_true", help="explicit opt-in to copy the raw WAV into the bundle")
    package.set_defaults(func=cmd_package)

    test = sub.add_parser("selftest", help="run deterministic offline implementation tests")
    test.set_defaults(func=cmd_selftest)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
