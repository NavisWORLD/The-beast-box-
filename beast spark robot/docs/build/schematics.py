"""ZEREF SPARK subsystem schematics (net-label style). DESIGN TARGET — not built or bench-tested.
Designators match BOM_electrical.csv. [OB] = on-board part of a bought module, [ADD] = added part."""
import schemdraw
import schemdraw.elements as elm
OUT = "/workspace/zeref-spark/docs/schematics"
FOOT = "DESIGN TARGET — not built or bench-tested · ESTIMATE values need verification · [OB] = on-board module part · [ADD] = added part"
CRED = "System logic: Cory Davis (NavisWORLD) · schematic drawn by an AI assistant from that logic · same net name = connected"
NET = "#b0006a"

def sheet(name, title, sub, modules, passives, cols=4):
    with schemdraw.Drawing(show=False, canvas="matplotlib") as d:
        d.config(fontsize=12, unit=2)
        y = -0.8
        for lab, pins in modules:
            P = [elm.IcPin(name=pn, pin=num, side="right") for pn, num, net in reversed(pins)]
            h = 0.9 * len(pins) + 0.6
            e = elm.Ic(pins=P, size=(6.0, h), pinspacing=0.9, edgepadH=0.3, lblsize=11).theta(0)
            e.at((6.5, y - 1.6)).anchor(pins[0][0])
            d += e
            d += elm.Label().at((0, y - 0.5)).label(lab, fontsize=11.5, halign="left", color="#101633")
            for pn, num, net in pins:
                l = elm.Line().at(getattr(e, pn)).right().length(1.2)
                d += l
                d += elm.Label().at(l.end).label(net, loc="right", fontsize=12, color=NET)
            y = y - 1.6 - 0.9 * (len(pins) - 1) - 2.4
        x0, yt = 16.5, -1.2
        for i, (ref, val, top, bot, kind) in enumerate(passives):
            x = x0 + (i % cols) * 4.6
            yy = yt - (i // cols) * 6.4
            d += elm.Label().at((x, yy + 0.4)).label(top, fontsize=11.5, color=NET)
            d += elm.Line().at((x, yy)).down().length(0.4)
            E = {"R": lambda: elm.Resistor(), "C": lambda: elm.Capacitor(), "CP": lambda: elm.Capacitor(polar=True),
                 "TVS": lambda: elm.Zener(), "LED": lambda: elm.LED(), "SW": lambda: elm.Switch(), "F": lambda: elm.Fuse()}[kind]()
            d += E.down().label(f"{ref}\n{val}", loc="bottom", fontsize=10.5)
            d += elm.Line().down().length(0.4)
            if bot == "GND":
                d += elm.Ground()
            else:
                d += elm.Label().at((d.here[0], d.here[1] - 0.4)).label(bot, fontsize=11.5, color=NET)
        top_y = 1.2
        d += elm.Label().at((0, top_y + 1.0)).label(title, fontsize=16, halign="left", color="#101633")
        d += elm.Label().at((0, top_y + 0.2)).label(sub, fontsize=11, halign="left", color="#444")
        yb = min(y, yt - ((len(passives) - 1) // cols + 1) * 6.4) - 0.5
        d += elm.Label().at((0, yb)).label(FOOT, fontsize=10.5, halign="left", color=NET)
        d += elm.Label().at((0, yb - 0.6)).label(CRED, fontsize=10.5, halign="left", color="#444")
        d.save(f"{OUT}/{name}.png", dpi=170); d.save(f"{OUT}/{name}.svg")
    print("wrote", name)

ESP = "U0 ESP32-S3 DevKitC-1 (RB-001) [OB LDO]"
sheet("A_power", "Sheet A — Power: USB-C, protection, charger / load-share / boost, battery sense",
      "U1 = Adafruit PowerBoost 1000C [OB: MCP73871 charger, TPS61090 boost, EN/LBO pull-ups, caps] · BT1 LiPo has its own PCM [OB]",
      [("J1 USB-C breakout, pedestal [OB 5.1k CC]", [("VBUS", "A4", "VBUS_IN"), ("D+", "A6", "USB_DP"), ("D-", "A7", "USB_DM"), ("GND", "A1", "GND")]),
       ("U1 PowerBoost 1000C (ZS-B02), head", [("USB", "", "VBUS"), ("BAT", "", "VBAT_F"), ("EN", "", "PB_EN"), ("5V", "", "5V_SYS"), ("GND", "", "GND")]),
       ("BT1 1S LiPo 503450, protected (ZS-B01)", [("+", "", "VBAT"), ("-", "", "GND")]),
       (ESP, [("5V", "", "5V_SYS"), ("USB_D+", "19", "USB_DP"), ("USB_D-", "20", "USB_DM"), ("GPIO5", "5", "VBAT_SENSE"), ("GND", "", "GND")])],
      [("F1", "PTC 2.0A hold\n6V 1812 [ADD]", "VBUS_IN", "VBUS", "F"),
       ("D2", "SMBJ5.0A TVS\n[ADD]", "VBUS", "GND", "TVS"),
       ("C1", "10uF 10V X5R\n0805 [ADD]", "VBUS", "GND", "C"),
       ("C2", "47uF 10V polymer\n[ADD] at U1 USB", "VBUS", "GND", "CP"),
       ("F2", "PTC 2.0A hold\n1812 [ADD, opt]", "VBAT", "VBAT_F", "F"),
       ("SW1", "SS12D00 slide\nclosed = OFF", "PB_EN", "GND", "SW"),
       ("C3", "220uF 10V polymer\nlow-ESR [ADD]", "5V_SYS", "GND", "CP"),
       ("C4", "100nF 16V X7R\n0603 [ADD]", "5V_SYS", "GND", "C"),
       ("C6", "10uF 10V X5R\n[ADD] at U0 5V", "5V_SYS", "GND", "C"),
       ("R1", "100k 1% 0.1W\n0603 [ADD]", "VBAT", "VBAT_SENSE", "R"),
       ("R2", "100k 1% 0.1W\n0603 [ADD]", "VBAT_SENSE", "GND", "R"),
       ("C5", "100nF 16V X7R\n[ADD]", "VBAT_SENSE", "GND", "C"),
       ("D1", "USBLC6-2SC6 ESD\non USB_DP/DM [ADD]", "USB_DP", "GND", "TVS")])

sheet("B_i2c0_sensors", "Sheet B — I2C0 sensors: GPIO8 SDA0 / GPIO9 SCL0 (REPO pins), 400 kHz",
      "BH1750 0x23 · MAX30102 0x57 · ICM-42688-P 0x68 · BME280 0x76 — no conflicts (AS7341 0x39 is on I2C1). GNSS on UART GPIO17/18 (REPO).",
      [(ESP, [("GPIO8", "8", "SDA0"), ("GPIO9", "9", "SCL0"), ("GPIO17", "17", "GNSS_TX→RX"), ("GPIO18", "18", "GNSS_RX←TX"), ("3V3", "", "3V3")]),
       ("U3 ICM-42688-P (RB-002) sled", [("VIN", "", "3V3"), ("SDA", "", "SDA0"), ("SCL", "", "SCL0"), ("GND", "", "GND")]),
       ("U4 BME280 (RB-004) sled", [("VIN", "", "3V3"), ("SDA", "", "SDA0"), ("SCL", "", "SCL0"), ("GND", "", "GND")]),
       ("U5 BH1750 (RB-003) right pod", [("VIN", "", "3V3"), ("SDA", "", "SDA0"), ("SCL", "", "SCL0"), ("ADDR", "", "GND (0x23)"), ("GND", "", "GND")]),
       ("U6 MAX30102 (RB-005, opt) chest", [("VIN", "", "3V3"), ("SDA", "", "SDA0"), ("SCL", "", "SCL0"), ("GND", "", "GND")]),
       ("U7 NEO-M9N GNSS (RB-007, opt) head", [("VIN", "", "3V3"), ("TX", "", "GNSS_TX→RX"), ("RX", "", "GNSS_RX←TX"), ("GND", "", "GND")])],
      [("R3", "2.2k 1% 0.1W\n[ADD / DNP*]", "3V3", "SDA0", "R"), ("R4", "2.2k 1% 0.1W\n[ADD / DNP*]", "3V3", "SCL0", "R"),
       ("C7", "100nF X7R U3\n[OB or ADD]", "3V3", "GND", "C"), ("C8", "100nF X7R U4\n[OB or ADD]", "3V3", "GND", "C"),
       ("C9", "100nF X7R U5\n[OB or ADD]", "3V3", "GND", "C"), ("C10", "100nF X7R U6\n[OB or ADD]", "3V3", "GND", "C"),
       ("C11", "10uF 10V X5R\nU7 bulk [ADD]", "3V3", "GND", "C")])

sheet("C_audio", "Sheet C — Audio: INMP441 mic on I2S0 (REPO 12/13/14) · MAX98357A on I2S1 (DECIDED 15/16/7, SD = GPIO6)",
      "R7 holds the amp in shutdown at boot (see calc in guide). SPK1 = 28 mm 8 ohm ~1 W (ZS-E06): firmware volume cap.",
      [(ESP, [("GPIO12", "12", "BCLK0_E"), ("GPIO13", "13", "WS0_E"), ("GPIO14", "14", "SD0"), ("GPIO15", "15", "BCLK1"), ("GPIO16", "16", "LRC1"), ("GPIO7", "7", "DIN1"), ("GPIO6", "6", "AMP_SD")]),
       ("U8 INMP441 (RB-006) left pod [OB 100nF]", [("VDD", "", "3V3"), ("SCK", "", "BCLK0"), ("WS", "", "WS0"), ("SD", "", "SD0"), ("L/R", "", "GND (left)"), ("GND", "", "GND")]),
       ("U9 MAX98357A (ZS-E05) head [OB 1M SD pull-up]", [("VIN", "", "5V_SYS"), ("BCLK", "", "BCLK1"), ("LRC", "", "LRC1"), ("DIN", "", "DIN1"), ("SD", "", "AMP_SD"), ("OUT+", "", "SPK+"), ("OUT-", "", "SPK-"), ("GND", "", "GND")])],
      [("R5", "33R 0.1W\n[ADD, opt]", "BCLK0_E", "BCLK0", "R"), ("R6", "33R 0.1W\n[ADD, opt]", "WS0_E", "WS0", "R"),
       ("R7", "22k 1% 0.1W\n[ADD]", "AMP_SD", "GND", "R"), ("C12", "100uF 10V\nelectrolytic [ADD]", "5V_SYS", "GND", "CP"),
       ("C13", "10uF 10V X5R\n[ADD]", "5V_SYS", "GND", "C")], cols=3)

sheet("D_led_chain", "Sheet D — WS2812B chain, 48 LEDs, data on GPIO4 (DECIDED) through a 3.3 V → 5 V buffer",
      "chest ring 12 → eye L 5 → eye R 5 → pod L 12 → pod R 12 → crown 2 · each LED has its own 100nF [OB] · no flyback diodes needed",
      [(ESP, [("GPIO4", "4", "LED_3V3"), ("GND", "", "GND")]),
       ("U2 SN74AHCT1G125 (or 1/4 74AHCT125)", [("A", "2", "LED_3V3"), ("OE_n", "1", "GND"), ("VCC", "5", "5V_SYS"), ("Y", "4", "LED_5V"), ("GND", "3", "GND")]),
       ("LED1..48 WS2812B (ZS-E01/E02/E03)", [("DIN", "", "DIN_1"), ("5V", "", "5V_SYS"), ("GND", "", "GND"), ("DOUT48", "", "n.c.")])],
      [("R8", "330R 1% 0.1W\n[ADD] (300-500R)", "LED_5V", "DIN_1", "R"), ("C14", "100nF X7R 16V\n[ADD] at U2", "5V_SYS", "GND", "C"),
       ("C15", "1000uF 10V\nelectrolytic [ADD]\nat chest ring", "5V_SYS", "GND", "CP"), ("C16", "100uF 10V\n[ADD] pod L", "5V_SYS", "GND", "CP"),
       ("C17", "100uF 10V\n[ADD] pod R", "5V_SYS", "GND", "CP"), ("C18", "100uF 10V\n[ADD] eyes", "5V_SYS", "GND", "CP")], cols=3)

sheet("E_crystal_station", "Sheet E — Crystal station (pins DECIDED): AS7341 on I2C1 (GPIO10/11), LED drivers, UV reed interlock",
      "LED supply = VBUS after F1 (pedestal, docked only) · S1 in SERIES with UV LED = hardware interlock · SHIELD_SENSE HIGH = shield seated",
      [(ESP, [("GPIO10", "10", "SDA1"), ("GPIO11", "11", "SCL1"), ("GPIO41", "41", "AS_INT"), ("GPIO1", "1", "G_WHITE"), ("GPIO2", "2", "G_UV"), ("GPIO21", "21", "G_IR"), ("GPIO40", "40", "SHIELD_SENSE"), ("3V3", "", "3V3")]),
       ("U10 AS7341 breakout (ZS-S01) via J2 pogo [OB LDO, 10k pull-ups]", [("VIN", "", "VBUS"), ("SDA", "", "SDA1_P"), ("SCL", "", "SCL1_P"), ("INT", "", "AS_INT"), ("GND", "", "GND")]),
       ("Q1 / Q2 / Q3 AO3400A N-MOSFET (ZS-S08)", [("Q1 G", "", "G1 (via R14)"), ("Q1 D", "", "Q1_D"), ("Q2 G", "", "G2 (via R15)"), ("Q2 D", "", "Q2_D"), ("Q3 G", "", "G3 (via R16)"), ("Q3 D", "", "Q3_D"), ("S (all)", "", "GND")]),
       ("D3 TPD4E05U06 ESD at J2 [ADD]", [("IO1", "", "SDA1_P"), ("IO2", "", "SCL1_P"), ("IO3", "", "VBUS"), ("GND", "", "GND")])],
      [("R9", "4.7k 1% 0.1W\n[ADD]", "3V3", "SDA1", "R"), ("R10", "4.7k 1% 0.1W\n[ADD]", "3V3", "SCL1", "R"),
       ("R11", "100R 0.1W\n[ADD]", "SDA1", "SDA1_P", "R"), ("R12", "100R 0.1W\n[ADD]", "SCL1", "SCL1_P", "R"),
       ("R13", "10k 1%\n[ADD / DNP]", "3V3", "AS_INT", "R"),
       ("C19", "10uF 10V X5R\n[ADD]", "VBUS", "GND", "C"), ("C20", "100nF X7R\n[ADD]", "VBUS", "GND", "C"),
       ("R14", "100R gate\n0.1W", "G_WHITE", "G1", "R"), ("R15", "100R gate\n0.1W", "G_UV", "G2", "R"), ("R16", "100R gate\n0.1W", "G_IR", "G3", "R"),
       ("R17", "100k pull-down", "G1", "GND", "R"), ("R18", "100k pull-down", "G2", "GND", "R"), ("R19", "100k pull-down", "G3", "GND", "R"),
       ("D4", "white LED\n(ZS-S04)", "VBUS", "W_K", "LED"), ("R20", "100R 1%\n0.125W 0805", "W_K", "Q1_D", "R"),
       ("S1", "reed NO (ZS-S09)\nshield magnet", "VBUS", "UV_5V", "SW"), ("D5", "UV 365nm LED\n(ZS-S05)", "UV_5V", "UV_K", "LED"),
       ("R21", "68R 1%\n0.125W 0805", "UV_K", "Q2_D", "R"), ("D6", "IR 940nm LED\n(ZS-S06, opt)", "VBUS", "IR_K", "LED"),
       ("R22", "180R 1%\n0.125W 0805", "IR_K", "Q3_D", "R"), ("R23", "12k 1% 0.1W", "UV_5V", "SHIELD_SENSE", "R"),
       ("R24", "20k 1% 0.1W", "SHIELD_SENSE", "GND", "R"), ("C21", "10uF 10V X5R\nat LED board", "VBUS", "GND", "C")], cols=6)
