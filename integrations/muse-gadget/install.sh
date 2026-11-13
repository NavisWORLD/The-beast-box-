#!/usr/bin/env bash
# Install the Beast Box gadget for Meta Muse on a Linux box with Bluetooth LE.
#
#   MUSE_GADGET_SDK_TOKEN=mgst_... bash install.sh            # or run it and paste the token at the prompt
#   bash install.sh --dry-run                                  # show what it would do
#   bash install.sh --uninstall [--purge]
#
# What it does:
#   1. Downloads Meta's Muse Linux Device SDK at the commit pinned in
#      sdk_patch/SDK_COMMIT and adds the Beast Box commands to it
#      (sdk_patch/apply.py, the SDK's documented "add a command" path).
#   2. Saves your SDK token in /var/lib/musegadget/sdk_token (root only).
#   3. Runs the SDK's own installer from that patched copy: system packages,
#      /opt/musegadget, BlueZ settings, and the musegadget systemd service.
#   4. Installs beastbox_musegadget into the SDK's venv, a drop-in that names
#      the device "Beast Box", and the beastbox-bridge service.
#   5. Opens Bluetooth pairing and prints the steps for the Muse app.
#
# This is a community gadget built with Meta's open source SDK. It is not made
# by or endorsed by Meta. The SDK token is personal: never commit or share it.

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SDK_TARBALL_URL="https://codeload.github.com/facebookincubator/muse-gadget-sdk/tar.gz"
PREFIX="/opt/musegadget"
VENV="$PREFIX/venv"
STATE_DIR="/var/lib/musegadget"
SDK_UNIT="/etc/systemd/system/musegadget.service"
DROPIN="/etc/systemd/system/musegadget.service.d/beastbox.conf"
BRIDGE_UNIT="/etc/systemd/system/beastbox-bridge.service"
TOKEN_RE='^mgst_[A-Za-z0-9_-]{42}[AEIMQUYcgkosw048]$'

say() { printf '\033[1m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[33mwarning:\033[0m %s\n' "$*" >&2; }
die() { printf '\033[31merror:\033[0m %s\n' "$*" >&2; exit 1; }

usage() {
    cat <<USAGE
Usage: install.sh [options]

  --run-as USER        Account Muse's commands (and the bridge) run as.
                       Default: the account running this installer.
  --display-name NAME  Name the gadget registers with Muse. Default: Beast Box.
  --sdk-dir DIR        Use a local muse-gadget-sdk checkout (repo root or its
                       linux/ directory) instead of downloading the pinned commit.
  --beastbox-url URL   Beast Box connector base URL (also BEASTBOX_URL; token
                       from BEASTBOX_TOKEN). Written to the gadget config.
  --snapshot FILE      Exported browser beast to load onto the gadget.
  --allow-origin URL   Browser origin allowed to use the bridge (repeatable).
                       Default: http://localhost:3000 and http://127.0.0.1:3000.
  --bridge-port PORT   Bridge port. Default: 8787.
  --no-bridge          Don't install the beastbox-bridge service.
  --no-pair            Install without opening Bluetooth pairing.
  --yes                Don't ask for confirmation.
  --dry-run            Print the system changes instead of making them.
  --uninstall          Remove the Beast Box parts and then the SDK.
  --purge              With --uninstall: also forget the pairing and gadget state.
  -h, --help           Show this help.

The SDK token comes from MUSE_GADGET_SDK_TOKEN or a hidden prompt. Create it at
https://gadgets.muse.ai/settings/sdk-tokens and read https://gadgets.muse.ai/sdk-terms.
USAGE
}

run() {
    if [ "$DRY_RUN" = 1 ]; then
        { printf '[dry-run]'; printf ' %q' "$@"; printf '\n'; } >&2
    else
        "$@"
    fi
}

as_root() { if [ "$(id -u)" -eq 0 ]; then run "$@"; else run sudo "$@"; fi; }
systemd_running() { [ -d /run/systemd/system ]; }

cleanup() { if [ -n "${WORK:-}" ] && [ -d "$WORK" ]; then rm -rf "$WORK"; fi; }

# --- Checks --------------------------------------------------------------------

check_system() {
    [ "$(uname -s)" = Linux ] || die "The Beast Box gadget runs on Linux (a Raspberry Pi or any Linux box with Bluetooth LE). It can't run on iPhone, Android, macOS or Windows."
    if grep -qi microsoft /proc/version 2>/dev/null; then
        warn "this looks like WSL, which has no Bluetooth LE for pairing."
    fi
    command -v python3 >/dev/null || die "python3 is required."
    command -v curl >/dev/null || die "curl is required."
    command -v tar >/dev/null || die "tar is required."
    if [ -z "$(ls /sys/class/bluetooth 2>/dev/null)" ]; then
        warn "no Bluetooth adapter found. You can install, but pairing with the Muse app needs Bluetooth LE."
    fi
}

read_token() {
    SDK_TOKEN="${MUSE_GADGET_SDK_TOKEN:-}"
    if [ -z "$SDK_TOKEN" ] && [ "$NO_PAIR" = 0 ] && [ "$ASSUME_YES" = 0 ] && [ -r /dev/tty ]; then
        printf 'Muse SDK token (mgst_...; input hidden, Enter to keep the saved one): ' >/dev/tty
        IFS= read -r -s SDK_TOKEN </dev/tty || SDK_TOKEN=""
        printf '\n' >/dev/tty
    fi
    if [ -n "$SDK_TOKEN" ] && ! [[ "$SDK_TOKEN" =~ $TOKEN_RE ]]; then
        die "that SDK token is not valid; copy it again from gadgets.muse.ai/settings/sdk-tokens."
    fi
    if [ -z "$SDK_TOKEN" ] && [ "$NO_PAIR" = 0 ] && [ "$DRY_RUN" = 0 ] && ! as_root test -s "$STATE_DIR/sdk_token"; then
        die "no SDK token. Create one at https://gadgets.muse.ai/settings/sdk-tokens, then run: MUSE_GADGET_SDK_TOKEN=mgst_... bash install.sh"
    fi
}

# --- SDK -----------------------------------------------------------------------

fetch_sdk() {
    WORK="$(mktemp -d "${TMPDIR:-/tmp}/beastbox-musegadget.XXXXXX")"
    if [ -n "$SDK_DIR" ]; then
        local src="$SDK_DIR"
        if [ -d "$src/linux/src/musegadget" ]; then src="$src/linux"; fi
        [ -d "$src/src/musegadget" ] || die "$SDK_DIR is not a muse-gadget-sdk checkout."
        say "Using the SDK from $src"
        cp -R "$src" "$WORK/linux"
    else
        local commit
        commit="$(tr -d '[:space:]' <"$HERE/sdk_patch/SDK_COMMIT")"
        say "Downloading the Muse Linux Device SDK at ${commit:0:12}"
        curl -fsSL "$SDK_TARBALL_URL/$commit" | tar -xz -C "$WORK"
        mv "$WORK/muse-gadget-sdk-$commit/linux" "$WORK/linux"
        rm -rf "$WORK/muse-gadget-sdk-$commit"
    fi
    rm -rf "$WORK/linux/.venv"
    say "Adding the Beast Box commands to the SDK"
    python3 "$HERE/sdk_patch/apply.py" "$WORK/linux" >/dev/null
}

save_token() {
    [ -n "$SDK_TOKEN" ] || return 0
    say "Saving your SDK token (root only, $STATE_DIR/sdk_token)"
    as_root install -d -m 0700 "$STATE_DIR"
    # printf is a shell builtin, so the token never appears in a process list.
    printf '%s\n' "$SDK_TOKEN" | as_root install -m 0600 /dev/stdin "$STATE_DIR/sdk_token"
}

run_sdk_installer() {
    local args=(--from "$WORK/linux" --no-pair)
    if [ -n "$RUN_AS" ]; then args+=(--run-as "$RUN_AS"); fi
    if [ "$ASSUME_YES" = 1 ]; then args+=(--yes); fi
    say "Running the SDK's installer (it asks before giving Muse your account)"
    run bash "$WORK/linux/install.sh" "${args[@]}"
}

# --- Beast Box parts -----------------------------------------------------------

resolve_account() {
    local from_unit=""
    if [ -f "$SDK_UNIT" ]; then
        from_unit="$(sed -n 's/^Environment=MUSEGADGET_RUN_AS=//p' "$SDK_UNIT" | head -1)"
    fi
    RUN_AS="${from_unit:-${RUN_AS:-}}"
    if [ -z "$RUN_AS" ]; then
        if [ "$(id -u)" -ne 0 ]; then RUN_AS="$(id -un)"; else RUN_AS="${SUDO_USER:-}"; fi
    fi
    if [ -z "$RUN_AS" ] || [ "$RUN_AS" = root ]; then
        die "choose the account with --run-as USER (not root)."
    fi
    RUN_HOME="$(getent passwd "$RUN_AS" | cut -d: -f6)"
    [ -n "$RUN_HOME" ] || die "account '$RUN_AS' does not exist."
}

install_gadget_package() {
    say "Installing the Beast Box gadget into $VENV"
    # Build from a copy so no build files land in your checkout.
    mkdir -p "$WORK/gadget"
    cp -R "$HERE/pyproject.toml" "$HERE/README.md" "$HERE/beastbox_musegadget" "$WORK/gadget/"
    as_root "$PREFIX/bin/uv" pip install --quiet --python "$VENV/bin/python" --no-deps --reinstall "$WORK/gadget"
    as_root ln -sf "$VENV/bin/musegadget-beastbox" /usr/local/bin/musegadget-beastbox
}

as_account() {
    if [ "$(id -un)" = "$RUN_AS" ]; then
        run "$@"
    elif [ "$(id -u)" -eq 0 ]; then
        run runuser -u "$RUN_AS" -- "$@"
    else
        run sudo -u "$RUN_AS" "$@"
    fi
}

write_config() {
    local config="$RUN_HOME/.config/beastbox-musegadget/config.json"
    if [ "$DRY_RUN" = 0 ] && as_root test -f "$config"; then
        say "Keeping the gadget config at $config"
        return
    fi
    say "Writing the gadget config at $config (readable only by $RUN_AS)"
    local origins="${ORIGINS:-http://localhost:3000,http://127.0.0.1:3000}"
    # The Beast Box token goes through stdin, never the command line.
    printf '%s' "${BEASTBOX_TOKEN:-}" | as_account env HOME="$RUN_HOME" python3 -c '
import json, os, sys
url, port, origins, path = sys.argv[1:5]
token = sys.stdin.read().strip()
cfg = {"beastbox_url": url, "beastbox_token": token, "bridge_port": int(port),
       "bridge_origins": [o for o in origins.split(",") if o]}
os.makedirs(os.path.dirname(path), mode=0o700, exist_ok=True)
fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
with os.fdopen(fd, "w") as f:
    json.dump(cfg, f, indent=2)
' "${BEASTBOX_URL:-}" "$BRIDGE_PORT" "$origins" "$config"
}

import_snapshot() {
    [ -n "$SNAPSHOT" ] || return 0
    [ -r "$SNAPSHOT" ] || die "cannot read $SNAPSHOT"
    say "Loading $SNAPSHOT onto the gadget"
    as_account env HOME="$RUN_HOME" "$VENV/bin/musegadget-beastbox" import-snapshot "$SNAPSHOT"
}

install_units() {
    say "Naming the device \"$DISPLAY_NAME\" in Muse ($DROPIN)"
    as_root install -d -m 0755 "$(dirname "$DROPIN")"
    sed "s/@DISPLAY_NAME@/${DISPLAY_NAME//\//\\/}/" "$HERE/systemd/musegadget-beastbox.conf" | as_root tee "$DROPIN" >/dev/null
    if [ "$NO_BRIDGE" = 0 ]; then
        say "Installing the beastbox-bridge service (runs as $RUN_AS, port $BRIDGE_PORT)"
        sed "s/@RUN_AS@/$RUN_AS/" "$HERE/systemd/beastbox-bridge.service" | as_root tee "$BRIDGE_UNIT" >/dev/null
    fi
    if systemd_running; then
        as_root systemctl daemon-reload
        as_root systemctl restart musegadget.service
        if [ "$NO_BRIDGE" = 0 ]; then as_root systemctl enable --now beastbox-bridge.service; fi
    else
        warn "systemd is not running; the services are installed but not started."
    fi
}

pair() {
    if [ "$DRY_RUN" = 0 ] && as_root test -s "$STATE_DIR/pairing.json"; then
        say "Already paired; the gadget will reconnect to your Muse."
        return
    fi
    if [ "$NO_PAIR" = 1 ]; then
        say "Skipping pairing. Run 'sudo musegadget pair' when you're ready."
        return
    fi
    cat <<STEPS

Pair with your Muse (pairing stays open for 10 minutes):
  1. In the Muse app on your phone: Settings > Devices > turn on Developer mode.
  2. Settings > Devices > Add Device (the + in the top right).
  3. Choose the device named MuseGadgetXXXXXX shown below. It registers as "$DISPLAY_NAME".
  4. Muse warns that this is a community device. Continue if it's yours.
  5. When asked for Wi-Fi, pick the network shown; no password is needed.

STEPS
    as_root /usr/local/bin/musegadget pair || warn "not paired. Run 'sudo musegadget pair' to try again."
}

summary() {
    echo
    as_root /usr/local/bin/musegadget info || true
    local ip
    ip="$(hostname -I 2>/dev/null | awk '{print $1}')"
    cat <<DONE

Try it: ask Muse "How is my Beast Box beast doing?" or "Feed my beast."
On this machine: musegadget-beastbox status

Link a browser beast (live care and attack animations):
  bridge URL: http://${ip:-<this-machine>}:$BRIDGE_PORT
  Tap Pair in Beast Box, then run: musegadget-beastbox link CODE
  (or tell Muse: "link my Beast Box browser with code CODE")

Logs:   sudo journalctl -u musegadget -u beastbox-bridge -f
Remove: bash $HERE/install.sh --uninstall
DONE
}

# --- Uninstall -----------------------------------------------------------------

uninstall() {
    resolve_account
    say "Removing the Beast Box gadget"
    if systemd_running && [ -f "$BRIDGE_UNIT" ]; then
        as_root systemctl disable --now beastbox-bridge.service >/dev/null 2>&1 || true
    fi
    as_root rm -f "$BRIDGE_UNIT" "$DROPIN" /usr/local/bin/musegadget-beastbox
    if [ "$PURGE" = 1 ]; then
        as_root rm -rf "$RUN_HOME/.local/state/beastbox-musegadget" "$RUN_HOME/.config/beastbox-musegadget"
        say "Removed the gadget's saved beast, bridge links and config."
    fi
    fetch_sdk
    local args=(--uninstall)
    if [ "$PURGE" = 1 ]; then args+=(--purge); fi
    run bash "$WORK/linux/install.sh" "${args[@]}"
    say "Also remove the device in the Muse app: Settings > Devices."
}

main() {
    RUN_AS="" DISPLAY_NAME="Beast Box" SDK_DIR="" SNAPSHOT="" ORIGINS="" BRIDGE_PORT=8787
    NO_BRIDGE=0 NO_PAIR=0 ASSUME_YES=0 DRY_RUN=0 UNINSTALL=0 PURGE=0
    while [ $# -gt 0 ]; do
        case "$1" in
            --run-as) RUN_AS="${2:?--run-as needs a value}"; shift 2 ;;
            --display-name) DISPLAY_NAME="${2:?--display-name needs a value}"; shift 2 ;;
            --sdk-dir) SDK_DIR="${2:?--sdk-dir needs a value}"; shift 2 ;;
            --beastbox-url) BEASTBOX_URL="${2:?--beastbox-url needs a value}"; shift 2 ;;
            --snapshot) SNAPSHOT="${2:?--snapshot needs a value}"; shift 2 ;;
            --allow-origin) ORIGINS="${ORIGINS:+$ORIGINS,}${2:?--allow-origin needs a value}"; shift 2 ;;
            --bridge-port) BRIDGE_PORT="${2:?--bridge-port needs a value}"; shift 2 ;;
            --no-bridge) NO_BRIDGE=1; shift ;;
            --no-pair) NO_PAIR=1; shift ;;
            --yes|-y) ASSUME_YES=1; shift ;;
            --dry-run) DRY_RUN=1; shift ;;
            --uninstall) UNINSTALL=1; shift ;;
            --purge) PURGE=1; shift ;;
            -h|--help) usage; exit 0 ;;
            *) usage >&2; die "unknown option: $1" ;;
        esac
    done
    [[ "$BRIDGE_PORT" =~ ^[0-9]+$ ]] || die "--bridge-port must be a number."
    [[ "$DISPLAY_NAME" =~ ^[A-Za-z0-9\ ._-]{1,40}$ ]] || die "--display-name may use letters, digits, spaces, dots, dashes and underscores (max 40)."
    trap cleanup EXIT
    if [ "$UNINSTALL" = 1 ]; then uninstall; return; fi
    if [ "$DRY_RUN" = 1 ]; then say "Dry run: system changes are printed, not made."; fi

    check_system
    read_token
    fetch_sdk
    save_token
    run_sdk_installer
    resolve_account
    install_gadget_package
    write_config
    import_snapshot
    install_units
    pair
    summary
}

# Everything runs from main, so a truncated download never runs a partial script.
main "$@"
