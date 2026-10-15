# Notes: showing the beast on a small ESP32 screen

Not built; notes only. The Linux gadget above is the supported Beast Box
gadget. An ESP32 board would be a second, separate gadget paired to the same
Muse account, using the SDK's [`esp32/`](https://github.com/facebookincubator/muse-gadget-sdk/tree/main/esp32)
firmware.

## Cheapest path: no firmware changes

Boards marked "images" in the ESP32 README (for example the Waveshare
ESP32-C6-LCD-1.47, M5Stack StickS3, ESP32-S3-BOX-3, Seeed SenseCAP Indicator)
already show pictures Muse sends them. So:

1. Flash a stock SDK build for the board (`tools/board.sh <board> build flash`,
   or `tools/muse/board.sh build <board>` for full-UI boards) and pair it with
   the same SDK token (it counts toward the 50-device limit).
2. Give Muse a picture of the beast. The missing piece is a sprite: add a
   `beastbox.sprite` action to the bridge that asks the linked browser tab for
   `canvas.toDataURL('image/png')` of the pixel beast (`components/pixel-beast.tsx`),
   and a matching Linux gadget command that returns it (base64, under the
   256 KB message limit), or saves it to a file Muse can read with `file.read`.
3. Ask Muse: *"Show my Beast Box beast on the little screen."* Muse fetches the
   sprite from the Linux gadget and sends it to the ESP32 board.

`tools/image_for_display.py` in the SDK shows the sizes and formats each
screen wants (small LCDs are ~172×320; e-paper is 1-bit or 6-colour).

## Custom firmware path (more work)

Following `esp32/AGENTS.md` "Adding a command": advertise a
`beastbox.show` command in `build_register_json()` (`main/noise_control.cpp`)
and handle it in `on_ws_command()` (`main/app.c`), off the Noise task, by
fetching the sprite PNG over the LAN from the Linux gadget's bridge (a new
read-only, token-protected `GET /v1/sprite`) and drawing it with the existing
image path (`link_image_fetch`). The SDK's LVGL/SDL simulator
(`esp32/simulator/`) previews the UI at 412×412 without hardware.

## Honest labels on the screen

If the board shows text, keep it: "Game companion · seeded by recorded IBM
counts". Don't show anything implying Meta made the device.
