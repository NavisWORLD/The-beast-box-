**EXPERIMENTAL debug build. It has not been tested on a real phone yet.**

Beast Box Device for Android turns a phone into a BLE peripheral named `Beast Box · <beast name>`. It wraps the live
`https://www.beastboxcosmos.xyz/spark/index.html` experience in a WebView and exposes a small GATT profile: beast state (read + notify),
the beast's name (read), and a command characteristic for feed / play / talk / attack. It uses Beast Box's own
random service UUID `1bc69ab8-18b7-4e30-8f34-d487921bca20`. It is **not** a Muse gadget and does not
impersonate one.

- Install: download `beastbox-android-experimental-v0.2-debug.apk` on the phone, allow "Install unknown apps"
  for your browser or files app, and install. Debug-signed: uninstall the old build before you install a newer one.
- Test: switch **BLE** on, then on a second phone use nRF Connect → Scanner → `Beast Box · <name>` → Connect.
  Read or subscribe to State and write `play` (text) or `02` (bytes) to Command.
- Requires Android 8.0+ and a phone whose Bluetooth chip supports BLE peripheral mode.

Full details, the GATT layout, the Muse findings and the known limits are in `apps/beastbox-android/README.md`.
Beasts are game companions. The quantum data behind them is recorded historical IBM counts used as fixed seeds.
