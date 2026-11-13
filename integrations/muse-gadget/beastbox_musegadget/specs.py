"""Muse command specs for the Beast Box gadget.

Same shape as COMMAND_SPECS in the SDK's executor.py: a description, required
and optional parameters (each with a type and a description), and timeout_ms.
Muse reads these when the gadget registers. This module is pure data so the
SDK service (which runs as root) can import it without running any gadget code.
"""

COMMAND_SPECS = {
    "beastbox.status": {
        "description": (
            "Check the Beast Box beast (a game companion, not a conscious being): name, species, island, "
            "element, temperament, mood, growth stage, and stats (xp, bond, energy). Reads the live browser "
            "beast when one is linked, otherwise the Beast Box connector or this gadget's saved copy."
        ),
        "required": {},
        "optional": {},
        "timeout_ms": 20000,
    },
    "beastbox.feed": {
        "description": "Feed the Beast Box beast. Raises bond and xp by the game's care rules and returns the new state.",
        "required": {},
        "optional": {"food": {"type": "string", "description": "What to feed it, for flavour (e.g. 'star berries')."}},
        "timeout_ms": 20000,
    },
    "beastbox.play": {
        "description": (
            "Play with the Beast Box beast. game 'spark' (default) or 'pet' are quick care actions; "
            "'train' scores a training round with hits out of 6."
        ),
        "required": {},
        "optional": {
            "game": {"type": "string", "description": "spark, pet or train. Default spark."},
            "hits": {"type": "integer", "description": "For train: hits out of 6. Default 3."},
        },
        "timeout_ms": 20000,
    },
    "beastbox.talk": {
        "description": (
            "Say something to the Beast Box beast and get its in-character reply, from the linked browser "
            "beast, the local Glacecoil companion model if installed, or a built-in fallback. Replies are "
            "a game character speaking, not a conscious mind."
        ),
        "required": {"message": {"type": "string", "description": "What to say to the beast."}},
        "optional": {},
        "timeout_ms": 60000,
    },
    "beastbox.attack": {
        "description": (
            "Make the beast perform one of its seeded attack moves. The animation plays in a linked "
            "Beast Box browser tab; without one, this returns the move that would play."
        ),
        "required": {},
        "optional": {"move": {"type": "string", "description": "Move name, id or style (beam, slash, burst, quake). Default: the beast picks."}},
        "timeout_ms": 20000,
    },
    "beastbox.moves": {
        "description": "List the beast's seeded attack moves (deterministic from its genome).",
        "required": {},
        "optional": {},
        "timeout_ms": 20000,
    },
    "beastbox.lost_cosmos": {
        "description": "Report Lost Cosmos game progress for the beast, if it is available from the browser, the connector or a saved snapshot.",
        "required": {},
        "optional": {},
        "timeout_ms": 20000,
    },
    "beastbox.link": {
        "description": (
            "Link a Beast Box browser tab to this gadget so Muse commands reach the live beast. The user "
            "taps Pair in the browser and reads out the short code it shows (like ABCD-2345)."
        ),
        "required": {"code": {"type": "string", "description": "The code shown in the browser."}},
        "optional": {},
        "timeout_ms": 15000,
    },
    "beastbox.links": {
        "description": "List linked Beast Box browser tabs and whether each is connected right now.",
        "required": {},
        "optional": {},
        "timeout_ms": 15000,
    },
}
