#!/usr/bin/env python3
"""Fail-closed repository security/IP consistency checks for The Beast Box.

This is intentionally dependency-free so it can run in local development and
GitHub Actions before packaging or release. It scans the checked-out tree, not
historical Git objects. Historical-secret response still requires credential
rotation and, where appropriate, history cleanup.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

ERRORS: list[str] = []
WARNINGS: list[str] = []


def error(message: str) -> None:
    ERRORS.append(message)


def warn(message: str) -> None:
    WARNINGS.append(message)


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return ""


def require_file(rel: str) -> Path:
    path = ROOT / rel
    if not path.is_file():
        error(f"missing required file: {rel}")
    return path


# --- Required policy/provenance surface ------------------------------------
required_files = [
    "LICENSE",
    "LICENSE_HISTORY.md",
    "IP_NOTICE.md",
    "IP_PROVENANCE.md",
    "COMMERCIAL_RIGHTS.md",
    "SECURITY.md",
    ".github/CODEOWNERS",
    ".github/dependabot.yml",
    ".github/PULL_REQUEST_TEMPLATE.md",
    "docs/REPOSITORY_SECURITY.md",
]
for required in required_files:
    require_file(required)

license_text = read_text(ROOT / "LICENSE")
if "THE BEAST BOX PROPRIETARY SOURCE-AVAILABLE LICENSE v1.0" not in license_text:
    error("root LICENSE is not the expected permission-required Beast Box license")
if "Permission required. Ask first." not in license_text:
    error("root LICENSE is missing the explicit permission-required boundary")

history_text = read_text(ROOT / "LICENSE_HISTORY.md")
if "Historical MIT boundary" not in history_text:
    error("LICENSE_HISTORY.md must preserve the historical MIT boundary")

codeowners = read_text(ROOT / ".github/CODEOWNERS")
if "* @NavisWORLD" not in codeowners:
    error("CODEOWNERS must keep @NavisWORLD as the default owner")
for critical in ("/LICENSE @NavisWORLD", "/SECURITY.md @NavisWORLD", "/.github/ @NavisWORLD"):
    if critical not in codeowners:
        error(f"CODEOWNERS missing critical rule: {critical}")

# --- Package-license consistency ------------------------------------------
pyproject = read_text(ROOT / "pyproject.toml")
if 'License :: OSI Approved :: MIT License' in pyproject or 'license = {text = "MIT"}' in pyproject:
    error("pyproject.toml still advertises MIT after the permission-required transition")
if 'license = {file = "LICENSE"}' not in pyproject:
    error("pyproject.toml must point package license metadata at root LICENSE")
if 'License :: Other/Proprietary License' not in pyproject:
    error("pyproject.toml must use the proprietary license classifier")

for rel in ("rust/cst-core/Cargo.toml", "rust/cosmic-cypher/Cargo.toml"):
    text = read_text(ROOT / rel)
    if re.search(r'^\s*license\s*=\s*["\']MIT["\']', text, flags=re.MULTILINE):
        error(f"{rel} still advertises MIT")
    if 'license-file = "../../LICENSE"' not in text:
        error(f"{rel} must point at the root permission-required LICENSE")

commercial = read_text(ROOT / "COMMERCIAL_RIGHTS.md")
if "PolyForm Noncommercial" in commercial:
    error("COMMERCIAL_RIGHTS.md still grants the superseded PolyForm noncommercial permission")
if "permission-required" not in commercial.lower():
    error("COMMERCIAL_RIGHTS.md must identify the current permission-required boundary")

# --- Secret-bearing file names --------------------------------------------
forbidden_exact = {
    ".env",
    "credentials.json",
    "service-account.json",
    "id_rsa",
    "id_ed25519",
}
forbidden_suffixes = {".pem", ".key", ".p12", ".pfx"}

for path in ROOT.rglob("*"):
    if not path.is_file():
        continue
    rel = path.relative_to(ROOT).as_posix()
    if rel.startswith((".git/", "build/", "dist/", "rust/target/", ".venv/", "venv/")):
        continue
    if rel == ".env.example":
        continue
    if path.name in forbidden_exact or path.suffix.lower() in forbidden_suffixes:
        error(f"secret-bearing/private-key style file must not be tracked: {rel}")

# .env.example may name secrets but must not contain values.
env_example = ROOT / ".env.example"
if env_example.is_file():
    for line_no, raw in enumerate(read_text(env_example).splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip().strip('"\'')
        if value and not (
            value.startswith("${")
            or value.startswith("<")
            or value.lower() in {"changeme", "example", "dummy", "placeholder"}
        ):
            error(f".env.example line {line_no} contains a non-empty credential-style value for {key.strip()}")

# --- High-confidence live-secret signatures -------------------------------
secret_patterns = [
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b")),
    ("GitHub fine-grained token", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b")),
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("Hugging Face token", re.compile(r"\bhf_[A-Za-z0-9]{20,}\b")),
    ("OpenAI-style secret", re.compile(r"\bsk-[A-Za-z0-9_-]{32,}\b")),
    (
        "private key",
        re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----"),
    ),
]

text_extensions = {
    ".py", ".md", ".txt", ".toml", ".yml", ".yaml", ".json", ".jsonl",
    ".js", ".ts", ".tsx", ".jsx", ".rs", ".go", ".java", ".cs", ".swift",
    ".sh", ".ps1", ".bat", ".cmd", ".html", ".css", ".xml", ".ini", ".cfg",
}

for path in ROOT.rglob("*"):
    if not path.is_file() or path.suffix.lower() not in text_extensions:
        continue
    rel = path.relative_to(ROOT).as_posix()
    if rel.startswith((".git/", "build/", "dist/", "rust/target/", ".venv/", "venv/")):
        continue
    try:
        if path.stat().st_size > 2_000_000:
            continue
    except OSError:
        continue
    text = read_text(path)
    for label, pattern in secret_patterns:
        if pattern.search(text):
            error(f"possible {label} detected in {rel}")

# --- Workflow hygiene ------------------------------------------------------
workflow_dir = ROOT / ".github/workflows"
if workflow_dir.is_dir():
    for workflow in sorted(workflow_dir.glob("*.y*ml")):
        text = read_text(workflow)
        if "pull_request_target:" in text:
            error(f"{workflow.relative_to(ROOT)} uses pull_request_target; explicit owner security review required")
        for match in re.finditer(r"uses:\s*([^\s]+)@([^\s]+)", text):
            action, ref = match.groups()
            if action.startswith("actions/"):
                continue
            if not re.fullmatch(r"[0-9a-fA-F]{40}", ref):
                warn(f"third-party Action is not pinned to an immutable commit SHA: {action}@{ref} in {workflow.name}")

# --- Ignore rules ----------------------------------------------------------
gitignore = read_text(ROOT / ".gitignore")
for required_ignore in (".env", "*.sqlite*", "*.gguf", "*.safetensors", ".cosmic-cypher/"):
    if required_ignore not in gitignore:
        error(f".gitignore missing sensitive/generated pattern: {required_ignore}")

# --- Results ---------------------------------------------------------------
for message in WARNINGS:
    print(f"WARNING: {message}")

if ERRORS:
    for message in ERRORS:
        print(f"ERROR: {message}", file=sys.stderr)
    print(f"security audit failed: {len(ERRORS)} error(s), {len(WARNINGS)} warning(s)", file=sys.stderr)
    raise SystemExit(1)

print(f"security audit passed: 0 errors, {len(WARNINGS)} warning(s)")
