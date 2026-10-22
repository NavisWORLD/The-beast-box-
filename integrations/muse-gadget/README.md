# Beast Box gadget for Meta Muse

Make The Beast Box pairable as a device in **Meta Muse** (Meta's personal AI
agent app) through Meta's official third-party device path,
[Muse Gadgets](https://gadgets.muse.ai/), and its open source
[Linux Device SDK](https://github.com/facebookincubator/muse-gadget-sdk/tree/main/linux)
(Apache 2.0).

> **Community gadget.** Built with Meta's open source Muse Gadget SDK. It is
> **not made by or endorsed by Meta.**
>
> **Honest labels.** A Beast Box beast is a game companion. It is not a person
> and not a conscious mind. Its look and moves come from recorded IBM quantum
> counts used as a **fixed seed** for a classical simulation, not from a live
> quantum link.
>
> Not to be confused with [`packages/beastbox-muse`](../../packages/beastbox-muse),
> which reads the InteraXon *Muse* EEG headband. This folder is for Meta's Muse app.

```
 Muse app (phone) ──Bluetooth pairing──▶ Linux gadget (Raspberry Pi) ──bridge──▶ Beast Box browser tab
        ▲                                   │  musegadget service (Meta SDK)          (live beast)
        └──────── Muse cloud ◀──Noise/WSS───┘  + Beast Box commands                       │
                                               + beastbox-bridge ◀──── state ────────────┘
```

The phone pairs with the **Linux gadget** over Bluetooth, once. After that the
gadget keeps an encrypted connection to your Muse and runs the commands Muse
sends it. A browser can't advertise Bluetooth, so the gadget does the Muse part
and a small **bridge** carries commands on to a linked Beast Box browser tab.

## What Muse can do with it

| Command | What it does |
|---|---|
| `beastbox.status` | Name, species, island, element, temperament, mood, growth stage, xp, bond, energy |
| `beastbox.feed` | Feed the beast (optional `food`), by the game's care rules |
| `beastbox.play` | Play: `game` = `spark` (default), `pet`, or `train` with `hits` out of 6 |
| `beastbox.talk` | Say something (`message`); get an in-character reply |
| `beastbox.attack` | Use a seeded attack move (optional `move`); animates in a linked browser tab |
| `beastbox.moves` | List the beast's four seeded attack moves |
| `beastbox.lost_cosmos` | Lost Cosmos progress, when a source has it |
| `beastbox.link` | Link a browser tab with the short code it shows (`code`) |
| `beastbox.links` | List linked browser tabs and whether they're connected |

The SDK's own commands (`system.run`, `file.read`, `file.write`,
`device.health`) stay as they are; nothing is removed.

Ask Muse things like *"How's my Beast Box beast doing?"*, *"Feed my beast some
star berries"*, *"Tell my beast good morning"*, or *"Make my beast attack."*

### Where the beast comes from

Each command uses the first source that works and says which one it used:

1. **Live browser beast**, through the bridge, when a linked tab is open.
   Changes happen to the beast in that browser. If no tab is open, `status`
   shows the last state the tab sent, labelled as such.
2. **Beast Box connector** (`beastbox_url` + `beastbox_token`), the MCP server
   at `/api/mcp` in `apps/beastbox-cloud`, via its tools `get_beast`,
   `get_care_status`, `get_lost_cosmos_progress`, `list_moves`, `feed_beast`,
   `play_with_beast` and `talk_to_beast`. (Being built separately; this gadget
   speaks MCP Streamable HTTP and parses `structuredContent` or JSON text.)
3. **The gadget's saved copy**, seeded from an exported browser beast. Care on
   this copy uses the same numbers as `lib/companion/session.mjs` and stays on
   the gadget; it is not written back to the browser.

`talk` replies come from the linked browser beast; otherwise from the Glacecoil
Ollama model (`companion-glacecoil`) if it's installed on the gadget; otherwise
from `beastbox.companion_local` if `beastbox_repo` points at a checkout;
otherwise from a small built-in template. Every reply passes an honesty filter
(no claims of being conscious, all-knowing, or quantum-linked).

## Requirements

- **A Linux computer with Bluetooth LE** that stays on: a Raspberry Pi 3B+, 4,
  5 or Zero 2 W, or any Linux box with BLE. Raspberry Pi OS Bullseye or later,
  Debian 11+, or Ubuntu 22.04+ (the SDK also supports Arch).
  **It can't run on an iPhone, Android phone or Windows PC**; the phone only
  runs the Muse app. (WSL has no Bluetooth LE.)
- An account with **sudo** on that machine, and Python 3.9+.
- The **Muse app** on your phone, with a Muse account (the gadgets site says
  Muse is available to subscribers in the United States).
- A **Muse SDK token** (`mgst_…`) from
  [gadgets.muse.ai/settings/sdk-tokens](https://gadgets.muse.ai/settings/sdk-tokens).

## Set it up (Cory's steps)

1. **Create the SDK token.** Sign in at
   [gadgets.muse.ai/settings/sdk-tokens](https://gadgets.muse.ai/settings/sdk-tokens),
   create a token, and read the [Gadget SDK Terms](https://gadgets.muse.ai/sdk-terms).
   Keep it private (see the rules below).

2. **Install on the Raspberry Pi** (or the Linux box that will be the gadget),
   as the account Muse should use:

   ```sh
   git clone --depth 1 https://github.com/NavisWORLD/The-beast-box-.git
   cd The-beast-box-/integrations/muse-gadget
   less install.sh                       # read it first
   bash install.sh                       # paste the mgst_ token at the hidden prompt
   ```

   Or pass it from the environment, without it landing in your shell history:
   `read -rs MUSE_GADGET_SDK_TOKEN && export MUSE_GADGET_SDK_TOKEN && bash install.sh`.
   Useful flags: `--run-as USER` (an account without sudo is safer),
   `--beastbox-url URL` (the connector), `--snapshot FILE` (a browser export),
   `--allow-origin URL` (a browser origin for the bridge), `--dry-run`.

   The installer downloads the SDK at the pinned commit, adds the Beast Box
   commands, runs the SDK's own installer (it asks before giving Muse your
   account), sets the name **Beast Box**, starts `musegadget` and
   `beastbox-bridge`, and opens Bluetooth pairing for 10 minutes.

3. **Pair in the Muse app** while pairing is open:
   1. **Settings > Devices >** turn on **Developer mode**.
   2. **Settings > Devices > Add Device** (the **+** in the top right).
   3. Choose **`MuseGadgetXXXXXX`** — the exact name the installer printed.
      (The SDK fixes this Bluetooth name; the app requires it. After pairing,
      the gadget registers with Muse as "Beast Box".)
   4. Muse warns that this is a community device. Continue if it's yours.
   5. When asked for Wi-Fi, pick the network shown; no password is needed.

   To pair again later: `sudo musegadget pair`.

4. **Give the gadget a beast**, any of:
   - **Link the browser** (live; see below), or
   - set `beastbox_url`/`beastbox_token` in the config for the connector, or
   - export the browser beast and load it: in the Beast Box tab's developer
     console run `copy(localStorage.getItem('beastbox-companion-session-v1'))`,
     paste into `beast.json` on the Pi, then
     `musegadget-beastbox import-snapshot beast.json`.

5. **Try it:** `musegadget-beastbox status` on the Pi, then ask Muse
   *"How's my Beast Box beast?"*

### Link a browser beast (the Pair bridge)

1. In Beast Box, tap **Pair** (once the panel is wired up; see
   [`browser/README.md`](browser/README.md)). It shows a code like `K7QM-2XRP`.
2. On the Pi run `musegadget-beastbox link K7QM-2XRP`, or tell Muse
   *"Link my Beast Box browser with code K7QM-2XRP."*
3. Muse commands now reach that tab's beast live, and its state flows back.
   Revoke with `musegadget-beastbox unlink LINK_ID` or from the browser.

The code is single use and expires in 10 minutes; the browser's token is
random, stored hashed on the gadget, and revocable. Each linked tab has its
own queue and state. Details: [`BRIDGE.md`](BRIDGE.md).

**HTTPS note:** a page served over HTTPS (like the Vercel app) can't call a
plain `http://` address on your LAN; browsers block it as mixed content. Use
the bridge from a locally served Beast Box (`http://localhost:3000`), give the
bridge a certificate (`bridge_tls_cert`/`bridge_tls_key`, e.g. from Tailscale
or mkcert), or relay through the connector backend later (see BRIDGE.md).

## Configuration

`~/.config/beastbox-musegadget/config.json` in the run-as account's home
(mode 0600; the installer writes it). Muse runs commands with a clean
environment, so settings live here rather than in environment variables:

```json
{
  "beastbox_url": "https://your-beast-box.example",
  "beastbox_token": "…Beast Box connector token, not the Muse SDK token…",
  "snapshot": "/home/pi/beast.json",
  "beastbox_repo": "/home/pi/The-beast-box-",
  "ollama_host": "http://127.0.0.1:11434",
  "companion_model": "companion-glacecoil",
  "bridge_port": 8787,
  "bridge_origins": ["http://localhost:3000"],
  "bridge_tls_cert": "",
  "bridge_tls_key": ""
}
```

Gadget state lives in `~/.local/state/beastbox-musegadget/` (0700): the saved
beast, bridge links (token hashes only) and the bridge's local admin token.

## SDK token rules (from the Gadget SDK Terms)

- The token is **personal** to you. **Never commit, publish or share it.** This
  repo never stores it: `install.sh` reads it from `MUSE_GADGET_SDK_TOKEN` or a
  hidden prompt and writes it only to `/var/lib/musegadget/sdk_token` (root,
  0600) on the gadget.
- **Personal, non-commercial use.** Don't embed it in a device you sell,
  advertise, list publicly or in a store, or give away as a promotion or reward.
- **At most 50 devices** per token, including ones you give to others.
- **Don't claim Meta made or endorses** the device.
- If Meta revokes the token, stop using it and remove it from any device you gave away.
- The SDK and tokens are "as is", not a supported product, and may stop working.

## Privacy note (required before anyone else pairs it)

If you give this gadget to someone else, tell them this **before** they pair it
with their Muse account:

- **What it receives from Muse:** only the commands Muse decides to run and
  their parameters (for example the text of a `talk` message, a food name, a
  pairing code). It does not receive your other Muse chats.
- **What it does with that:** applies the command to the Beast Box beast and
  answers Muse with the beast's state or reply. A `talk` message goes to the
  linked browser tab, the local Ollama model, the local companion layer, or the
  configured Beast Box connector — whichever is the source in use — and the
  last 80 lines of beast chat are kept with the beast (in the browser or in
  `~/.local/state/beastbox-musegadget/beast.json`), like chatting in Beast Box.
- **What leaves the machine:** only to the places you configured — the Muse
  service (the SDK's own connection), your linked browser tab, and
  `beastbox_url` if set. Nothing is sent to the gadget's author or any
  analytics service. Logs record command names and outcomes, never parameters
  or replies (the SDK's rule).
- **Access:** like every Linux Muse gadget, Muse can also run shell commands
  and read/write files as the account chosen at install (the SDK's
  `system.run`, `file.read`, `file.write`). Use `--run-as` with an account
  without sudo if you don't want that to include admin rights.
- **Removal:** `bash install.sh --uninstall --purge` deletes the pairing and all
  gadget data; also remove the device in the Muse app (Settings > Devices).

The gadget never uses one person's Muse data for anyone else, and is meant to
be paired with your own Muse account.

## How it plugs into the SDK

The Linux SDK has no plugin system. Its documented way to add a command
([`linux/AGENTS.md`](https://github.com/facebookincubator/muse-gadget-sdk/blob/main/linux/AGENTS.md#adding-a-command))
is to add a spec to `COMMAND_SPECS` and a branch in `Executor.run` in
`executor.py`. [`sdk_patch/apply.py`](sdk_patch/apply.py) does exactly that,
additively, on a copy of the SDK pinned in `sdk_patch/SDK_COMMIT`:

- copies [`sdk_patch/beastbox_commands.py`](sdk_patch/beastbox_commands.py)
  into the package; it registers the specs from
  [`beastbox_musegadget/specs.py`](beastbox_musegadget/specs.py) and runs each
  command in a child process **as the run-as account** via the SDK's
  `_child_options()`, never as root;
- adds one `if` to `Executor.run`;
- lets `MUSEGADGET_DISPLAY_NAME` set the registered name (default: hostname).

It refuses to patch an SDK whose code doesn't match, instead of guessing. Muse
sees the commands after the service restarts and re-registers.

## SDK limits found

- **No plugin hook:** custom commands mean patching `executor.py` (done here,
  pinned and additive). A newer SDK may need `apply.py` updated.
- **Bluetooth name is fixed** to `MuseGadget` + six hex digits; the app checks
  it against the node id. "MuseGadget Beast Box" isn't possible. The name sent
  at registration (`display_name`) is set to "Beast Box"; whether and where the
  Muse app shows that name is not verified.
- **Linux devices only pair over BLE** from the Muse app on iOS/Android;
  pairing opens only while `musegadget pair` runs (10 minutes).
- **Commands are request/response with time limits** (30 s default; this
  gadget uses 20 s, 60 s for `talk`). Devices can push messages to Muse with
  `musegadget send-user-msg`, but there's no streaming UI.
- **No Linux simulator.** The SDK's LVGL/SDL simulator is for the ESP32 board
  UI only. The Linux SDK's tests run without Bluetooth; there's no dry-run mode
  for pairing.
- **The SDK grants shell and file access** (`system.run` etc.) to the run-as
  account; that's the SDK's design, not something this gadget adds.
- Tokens and the SDK are unsupported and may change or stop at any time.

## Tested vs not tested

Tested (no Bluetooth needed): the SDK's own 159 tests, also on the patched SDK;
this folder's Python tests (care rules on a fixture beast, every command, the
Ollama and connector paths against local fakes, the bridge's code/token/revoke
rules and per-link isolation, and a fake Muse `link.invoke` through the
patched SDK `Executor` to a fake browser tab); Node tests that run the real
browser client module and the real `lib/companion` session functions against
the real bridge and check that a `muse-command beastbox.feed` changes the
browser beast; a JS/Python parity test for the seeded moves; ShellCheck and an
`install.sh --dry-run`. CI: [`.github/workflows/muse-gadget.yml`](../../.github/workflows/muse-gadget.yml).

**Not tested:** real pairing with the Muse app, the live Muse connection, and
the full `install.sh` on a Raspberry Pi. The build machine had no Bluetooth,
no SDK token and no phone. The Beast Box connector's real `/api/mcp` wasn't
available, so its tool result shapes are assumed; the "Pair" panel in the web
app isn't wired yet (that app was out of scope here).

## Manage it

```sh
musegadget info                                   # BLE name, node id, paired?
musegadget-beastbox status | feed | talk "hi"     # same as Muse would
musegadget-beastbox links | link CODE | unlink ID # browser links
sudo journalctl -u musegadget -u beastbox-bridge -f
sudo musegadget pair                              # pair again
bash install.sh --uninstall [--purge]             # remove it
```

## Develop

```sh
cd integrations/muse-gadget
python3 -m pytest tests                         # MUSE_SDK_DIR=/path/to/muse-gadget-sdk/linux for SDK tests
node --test tests/
shellcheck install.sh
```

Files: `beastbox_musegadget/` (commands, router, bridge, companion, moves),
`sdk_patch/` (SDK patch + pinned commit), `browser/` (bridge client),
`systemd/`, `tests/`, [`BRIDGE.md`](BRIDGE.md), [`ESP32_NOTES.md`](ESP32_NOTES.md).

License: Apache 2.0, like the SDK. `sdk_patch/beastbox_commands.py` is added to
Meta's Apache-2.0 SDK at install time.
