#!/usr/bin/env bash
set -euo pipefail
root="$(git rev-parse --show-toplevel)"
exec "${PYTHON:-python}" "$root/scripts/security_audit.py"
