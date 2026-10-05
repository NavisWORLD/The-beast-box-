# Beast Box Device for Android (EXPERIMENTAL)

Turns an Android phone into a Bluetooth LE **Beast Box device**. The app wraps the Beast Box web app in a
WebView and uses Android's native `BluetoothLeAdvertiser` plus a `BluetoothGattServer` to advertise as a BLE
peripheral named **`Beast Box · <beast name>`**. Browsers can't advertise BLE; native Android apps can.

> Status: **experimental v0.1, debug build, not tested on a real phone yet.** CI builds it, runs the JVM
> unit tests for the command and state encoding, and runs Android lint. Nothing here has been run on hardware.

Beasts are game companions. The quantum data behind Spark Beasts is recorded historical IBM counts used as
fixed seeds. It is not a live quantum link.

## This is not a Muse gadget

The app advertises under **Beast Box's own name** and its **own random 128-bit service UUID**. It never uses
the `MuseGadget` name prefix, Meta's service UUIDs, or the Muse pairing protocol, and it does not try to look
like a Meta device. The Muse app won't list it, and that's intended. See [Muse findings](#muse-findings) below.
Muse is linked through the existing Beast Box paths instead: the Linux gadget (`integrations/muse-gadget/`,
built separately on a Raspberry Pi with your own SDK token) and the Beast Box MCP connector (`/api/mcp`).

## Install (sideload)

1. On the phone, open the pre-release **`beastbox-android-experimental-v0.1`** on GitHub and download
   `beastbox-android-experimental-v0.1-debug.apk`. You can also grab it from the
   `beastbox-android-experimental-v0.1-debug` artifact of a green **Beast Box Android device (experimental)**
   workflow run.
2. Open the APK. Android will ask you to allow installs from that source (Chrome or Files):
   **Settings → Apps → Special app access → Install unknown apps → [your browser/files app] → Allow**.
3. Install it. Play Protect may warn that the app is from an unknown developer, because it's a debug-signed
   build. Choose **Install anyway** if you trust this build. You can check its SHA-256 against the `.sha256` file.
4. Every CI build gets a new debug signing key, so **uninstall the old build before you install a newer one**.
   Android refuses an update signed with a different key.

Requires Android 8.0+ (API 26) and a phone whose Bluetooth chip supports peripheral mode. Most phones from
2017 on do. The app reports it clearly if yours doesn't.

## Use

- The top bar has a **BLE** on/off toggle, a status line and **⚙ settings**.
- Switching BLE on asks for **Nearby devices** (`BLUETOOTH_ADVERTISE`, `BLUETOOTH_CONNECT`) on Android 12+, plus
  **Notifications** on Android 13+, and asks you to turn Bluetooth on if it's off. While the app advertises,
  a foreground-service notification **"Beast Box device is advertising"** stays up, with a **Stop** action.
  No scanning and no location permission are used.
- **Settings**:
  - Web app: **Spark Beasts (public, default)**
    `https://navisworld.github.io/Cosmic-synapse-the-living-universe-sim-engine-/arcade/spark-beasts/`,
    **Beast Box web app** `https://the-beast-box-zerefs-end.vercel.app` (behind Vercel SSO), or a
    **custom https URL**.
  - **Rename phone Bluetooth while advertising** (on by default). Android only puts the adapter's own name
    in the BLE advert, so the app temporarily renames the phone's Bluetooth to `Beast Box · <name>` and
    restores the original name when you switch BLE off. The original is saved, so it can still be restored
    after a crash. If you turn renaming off, the advert carries the beast name as service data (≤ 11 bytes)
    and the GAP name stays your phone's name.
- Spark a beast in the page. The advertised name follows the active beast's nickname, or its species if it
  has no nickname.

## GATT profile (Beast Box v1)

| Item | UUID | Properties | Format |
|---|---|---|---|
| Service | `1bc69ab8-18b7-4e30-8f34-d487921bca20` | primary, advertised | |
| State | `2cb2ab9b-0a00-4207-9498-639765b9de85` | Read, Notify (CCCD `0x2902`) | 8 bytes, see below |
| Name | `7b8f3cee-5038-4229-86fd-a330f0272738` | Read | UTF-8 beast name (nickname, else species) |
| Command | `83b3dc8c-1766-4fb7-9594-d6681020c2e0` | Write, Write Without Response | see below |

**State frame v1** (little endian, always 8 bytes, so it fits a default-MTU notify):

| Byte | Field |
|---|---|
| 0 | version = `0x01` |
| 1 | stage `0` (no beast yet) … `3` |
| 2 | energy `0…100`, `0xFF` = unknown |
| 3 | bond `0…100` |
| 4–5 | xp, uint16 (saturates at 65535) |
| 6 | last command opcode (`0` = none) |
| 7 | seq, uint8. It goes up by one on every change, so subscribers can see updates. |

**Command frame.** Binary: one opcode byte, `0x01` feed, `0x02` play, `0x03` talk, `0x04` attack. For
talk, up to 120 bytes of UTF-8 text can follow the opcode. For hand testing, UTF-8 text also works:
`feed`, `play`, `attack`, `talk hello there` (not case-sensitive). An unknown command gets ATT error `0x80`.

Encoding lives in [`BeastProtocol.kt`](app/src/main/java/dev/beastbox/device/BeastProtocol.kt) and is covered by
[`BeastProtocolTest.kt`](app/src/test/java/dev/beastbox/device/BeastProtocolTest.kt).

## Test advertising with nRF Connect

On a **second** phone, install **nRF Connect for Mobile** (Nordic Semiconductor; Android or iOS).

1. On the Beast Box phone, open the app, spark or select a beast, and switch **BLE** on. Wait for the status
   line to read `Advertising as "Beast Box · <name>" · 0 connected`.
2. In nRF Connect, open **Scanner** and tap **Scan**. Look for **`Beast Box · <name>`**. Add a filter on the
   name "Beast Box" if the list is busy. Tap the row to see the advert: the complete 128-bit service UUID
   `1bc69ab8-…-d487921bca20` is in the primary packet, and the name is in the scan response.
3. Tap **Connect**. Under **Unknown Service** `1bc69ab8-…`:
   - **State** `2cb2ab9b-…`: tap the read arrow (↓). You should get 8 bytes starting `01`, for example
     `01-02-50-37-34-12-00-07`. Tap the triple-arrow icon to **enable notifications**.
   - **Name** `7b8f3cee-…`: read it and switch the display to UTF-8 to see the beast name.
   - **Command** `83b3dc8c-…`: tap write (↑). Choose **TEXT** and send `play`, or choose **BYTE ARRAY** and
     send `02`. The Beast Box phone shows a toast `play from ble:xx:xx`, the page presses its Play care
     action, and a State notification arrives with byte 6 = `02` and seq + 1. Also try `feed`, `attack`, and
     `talk hello` (the page's chat replies).
4. Switch BLE off on the Beast Box phone. The advert disappears, nRF Connect disconnects, and the phone's
   Bluetooth name goes back to the original.

Another Beast Box phone can't scan for peers yet. This build only advertises. A peer-scan mode would be the
next step, and it would need `BLUETOOTH_SCAN`.

## Web app bridge (`window.BeastBoxNative`)

After each page load on the configured origin, the app injects
[`assets/beastbox-bridge.js`](app/src/main/assets/beastbox-bridge.js):

- **Page → phone.** About every 1.5 s, the bridge sends `{displayName, species, stage, xp, bond, energy}` to
  `BeastBoxNative.reportState(json)`. If the page defines `window.BeastBoxDevice.getState()`, that is used
  first. This is the explicit hook for the Beast Box web app. Otherwise the bridge reads the Spark Beasts
  local store (`localStorage["spark-beasts-v1"]`, active beast).
- **Phone → page.** A BLE command calls `window.__beastBoxDevice.receive(json)` with
  `{command, text, source}`. The bridge always dispatches a `beastbox:command` `CustomEvent` on `window`. If
  `window.BeastBoxDevice.onCommand(cmd)` returns `true`, the page has handled the command. Otherwise a
  best-effort Spark Beasts adapter takes over. Spark Beasts has no feed or attack buttons, so those map onto
  its nearest care actions:

  | BLE command | Spark Beasts control |
  |---|---|
  | feed | `#act-rest` (Rest; restores energy) |
  | play | `#act-play` (Play) |
  | attack | `#act-focus` (Focus training) |
  | talk | fills `#chat-input` and submits `#chat-form` |

The bridge only accepts calls while the top-level page is on the configured origin, and it never lets page
JS control Bluetooth. A same-origin page can only report state.

## Muse findings

These come from a review of [facebookincubator/muse-gadget-sdk](https://github.com/facebookincubator/muse-gadget-sdk)
and the [Gadget SDK Token Terms](https://gadgets.muse.ai/sdk-terms), checked October 2026.

- **The protocol is open.** The SDK is Apache-2.0 and ships two device targets: ESP32 firmware and a Linux /
  Raspberry Pi Python client. There is no Android or iOS *device* target. A gadget advertises over BLE as
  `MuseGadgetXXXXXX` with the SDK's GATT service. The Muse app (iOS or Android, **Settings → Devices →
  Developer mode**) lists only devices with that prefix. Pairing is "community pairing v5" (P-256 ECDH,
  HKDF-SHA256, AES-256-GCM) with `pairing_auth: none`, which means no manufacturer attestation. After
  pairing, the gadget keeps a Noise XX session to the user's Muse VM and runs the commands Muse sends.
- **Access is token-gated.** Every gadget needs an SDK token (`mgst_…`) from gadgets.muse.ai. The terms
  limit use to personal, non-commercial use with your own Muse account. The token is personal and may not
  be published. It may be embedded in at most 50 shared devices, and never in devices that are sold or
  listed in a marketplace or app store. You may not say Meta made or endorsed the device, or get around
  restrictions. Meta can withdraw the SDK and tokens at any time.
- **Could Muse legitimately see a phone-hosted device?** Technically, the protocol has no hardware check, and
  the terms talk about "devices you build" without naming hardware. So a **private, personally built port**
  of the Linux client to Android, using Cory's own token and never distributed, doesn't seem to be ruled
  out by the terms as written. But:
  1. There is no official Android device SDK. It would be our own reimplementation, which Meta doesn't
     support.
  2. To be discovered, the device would have to advertise the `MuseGadget` prefix and the SDK's UUIDs, which
     this project chose not to use.
  3. The Muse app itself runs on a phone. A phone usually can't discover its own advert, so a second phone
     would be needed.
  4. Shipping it in a public GitHub release with a token baked in would break the "don't publish the token"
     and listing rules. A token could only be entered on the device at runtime.

  **Conclusion: not *clearly* permitted, so Muse-protocol compatibility is not implemented here.**
  The legitimate paths stay the Linux gadget (`integrations/muse-gadget/`) and the MCP connector (`/api/mcp`).

## Limits

- **Untested on a real phone.** Only the JVM unit tests and lint run in CI. BLE peripheral behaviour differs
  by vendor, and some phones (or Android builds) have no peripheral mode at all.
- **WebView isn't Chrome.** Microphone, camera and sensor prompts (Spark Beasts "Muse / sensors" features,
  voice) aren't granted inside the WebView in this build. Web Bluetooth, WebUSB and other Chrome-only APIs
  aren't available. Google sign-in, and some SSO providers, refuse to run in WebViews
  (`disallowed_useragent`), so the **Vercel-SSO production URL may not get past login**. Spark Beasts, or
  any public URL, is the default for that reason. "Open in browser" in settings is the fallback. `localStorage`
  in the WebView is separate from Chrome's, so beasts sparked in Chrome won't appear in the app (and the
  reverse).
- The page must be open, in the foreground or in recents, for commands to reach the creature. The GATT
  server keeps serving the last-known state if it isn't.
- Renaming changes the phone's Bluetooth name for every app while advertising. Turn it off in settings if you
  don't want that.
- Debug-signed only. A new key per CI build means you have to uninstall before each update.
- Only legacy (31-byte) advertising is used. Names are limited to 16 characters, as in the web store.
- No pairing or bonding and no encryption: any nearby BLE client can read the state and send
  feed/play/talk/attack. That is fine for a game companion, but don't put anything private in the beast name.

## Build

The box doesn't need the Android SDK. CI runs
[`.github/workflows/beastbox-android.yml`](../../.github/workflows/beastbox-android.yml) with JDK 17,
Android SDK 35 and Gradle 8.11.1:

```sh
cd apps/beastbox-android
gradle --no-daemon testDebugUnitTest lintDebug assembleDebug
```

If you push a tag `beastbox-android-experimental-v*`, CI also publishes a not-latest pre-release with the
debug APK and its SHA-256.
