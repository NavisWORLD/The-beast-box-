package dev.beastbox.device

import java.nio.charset.StandardCharsets
import java.util.UUID

/**
 * Beast Box's own BLE GATT profile. Pure Kotlin (no Android types) so it is unit tested on the JVM.
 *
 * These UUIDs were generated at random for Beast Box. They are not Meta / Muse Gadget UUIDs and the
 * advertised name never uses the "MuseGadget" prefix: this device is a Beast Box, not a Muse gadget.
 */
object BeastUuids {
    /** Primary Beast Box service (random 128-bit, advertised). */
    val SERVICE: UUID = UUID.fromString("1bc69ab8-18b7-4e30-8f34-d487921bca20")

    /** Read + Notify. Compact 8-byte state frame, see [BeastProtocol.encodeState]. */
    val STATE: UUID = UUID.fromString("2cb2ab9b-0a00-4207-9498-639765b9de85")

    /** Read. UTF-8 display name of the live beast (falls back to species name). */
    val NAME: UUID = UUID.fromString("7b8f3cee-5038-4229-86fd-a330f0272738")

    /** Write / Write Without Response. One command frame, see [BeastProtocol.decodeCommand]. */
    val COMMAND: UUID = UUID.fromString("83b3dc8c-1766-4fb7-9594-d6681020c2e0")

    /** Standard Bluetooth SIG Client Characteristic Configuration Descriptor (enables notify). */
    val CCCD: UUID = UUID.fromString("00002902-0000-1000-8000-00805f9b34fb")
}

enum class BeastCommand(val opcode: Int, val word: String) {
    FEED(0x01, "feed"),
    PLAY(0x02, "play"),
    TALK(0x03, "talk"),
    ATTACK(0x04, "attack");

    companion object {
        fun fromOpcode(opcode: Int): BeastCommand? = entries.firstOrNull { it.opcode == opcode }
        fun fromWord(word: String): BeastCommand? = entries.firstOrNull { it.word == word.lowercase() }
    }
}

/** A decoded command. [text] is only meaningful for [BeastCommand.TALK]. */
data class CommandFrame(val command: BeastCommand, val text: String = "")

/** Live creature snapshot reported by the WebView. Beasts are game companions. */
data class BeastState(
    val displayName: String = "",
    val species: String = "",
    /** 0 = no beast sparked yet, otherwise 1..3. */
    val stage: Int = 0,
    val xp: Int = 0,
    val bond: Int = 0,
    /** 0..100, or [BeastProtocol.UNKNOWN] when the page doesn't expose it. */
    val energy: Int = BeastProtocol.UNKNOWN,
    val lastCommand: BeastCommand? = null,
    /** Wrapping 0..255 counter; bumps on every change so BLE clients can see updates. */
    val seq: Int = 0,
) {
    val shownName: String get() = displayName.ifBlank { species }

    companion object {
        val EMPTY = BeastState()
    }
}

/** Fields that come back out of an 8-byte state frame (the name lives in its own characteristic). */
data class StateFrame(
    val version: Int,
    val stage: Int,
    val energy: Int,
    val bond: Int,
    val xp: Int,
    val lastCommand: BeastCommand?,
    val seq: Int,
)

object BeastProtocol {
    const val STATE_VERSION = 1
    const val STATE_FRAME_SIZE = 8
    const val UNKNOWN = 0xFF
    const val MAX_TALK_BYTES = 120

    /** Name budget so the GAP name fits a legacy 31-byte scan response (2 bytes AD header). */
    const val MAX_ADVERTISED_NAME_BYTES = 29
    const val NAME_PREFIX = "Beast Box"
    const val NAME_SEPARATOR = " \u00B7 " // " · "

    /** Same character rule and 16-char limit as the Spark Beasts web store (sanitizeDisplayName). */
    fun sanitizeName(raw: String?): String =
        (raw ?: "").replace(Regex("[^A-Za-z0-9 '\\-]"), " ").replace(Regex("\\s+"), " ").trim().take(16)

    /** "Beast Box · <name>", truncated on a code-point boundary to fit the scan response. */
    fun advertisedName(beastName: String?): String {
        val clean = sanitizeName(beastName)
        if (clean.isEmpty()) return NAME_PREFIX
        return truncateUtf8(NAME_PREFIX + NAME_SEPARATOR + clean, MAX_ADVERTISED_NAME_BYTES).trimEnd()
    }

    /**
     * State frame v1, little endian, always [STATE_FRAME_SIZE] bytes so it fits a default-MTU notify:
     *  [0] version (1)  [1] stage 0..3  [2] energy 0..100 or 0xFF  [3] bond 0..100
     *  [4..5] xp uint16 (saturates at 65535)  [6] last command opcode (0 = none)  [7] seq uint8
     */
    fun encodeState(state: BeastState): ByteArray {
        val xp = state.xp.coerceIn(0, 0xFFFF)
        val energy = if (state.energy == UNKNOWN) UNKNOWN else state.energy.coerceIn(0, 100)
        return byteArrayOf(
            STATE_VERSION.toByte(),
            state.stage.coerceIn(0, 3).toByte(),
            energy.toByte(),
            state.bond.coerceIn(0, 100).toByte(),
            (xp and 0xFF).toByte(),
            ((xp ushr 8) and 0xFF).toByte(),
            (state.lastCommand?.opcode ?: 0).toByte(),
            (state.seq and 0xFF).toByte(),
        )
    }

    fun decodeState(bytes: ByteArray): StateFrame? {
        if (bytes.size < STATE_FRAME_SIZE) return null
        val u = { i: Int -> bytes[i].toInt() and 0xFF }
        if (u(0) != STATE_VERSION) return null
        return StateFrame(
            version = u(0),
            stage = u(1),
            energy = u(2),
            bond = u(3),
            xp = u(4) or (u(5) shl 8),
            lastCommand = BeastCommand.fromOpcode(u(6)),
            seq = u(7),
        )
    }

    fun encodeName(state: BeastState): ByteArray = state.shownName.ifBlank { NAME_PREFIX }.toByteArray(StandardCharsets.UTF_8)

    /** Binary command: [opcode] followed, for TALK only, by up to [MAX_TALK_BYTES] of UTF-8 text. */
    fun encodeCommand(frame: CommandFrame): ByteArray {
        val head = byteArrayOf(frame.command.opcode.toByte())
        if (frame.command != BeastCommand.TALK || frame.text.isEmpty()) return head
        return head + truncateUtf8(cleanTalk(frame.text), MAX_TALK_BYTES).toByteArray(StandardCharsets.UTF_8)
    }

    /**
     * Accepts either the binary form (first byte 0x01..0x04) or, for hand-typed testing in nRF Connect,
     * UTF-8 text such as "feed", "PLAY", "attack" or "talk hello there". Returns null when invalid.
     */
    fun decodeCommand(bytes: ByteArray?): CommandFrame? {
        if (bytes == null || bytes.isEmpty()) return null
        val first = bytes[0].toInt() and 0xFF
        BeastCommand.fromOpcode(first)?.let { cmd ->
            val text = if (cmd == BeastCommand.TALK && bytes.size > 1) {
                cleanTalk(String(bytes, 1, minOf(bytes.size - 1, MAX_TALK_BYTES), StandardCharsets.UTF_8))
            } else ""
            return CommandFrame(cmd, text)
        }
        val raw = String(bytes, StandardCharsets.UTF_8).trim()
        if (raw.isEmpty()) return null
        val word = raw.substringBefore(' ')
        val cmd = BeastCommand.fromWord(word) ?: return null
        val rest = if (cmd == BeastCommand.TALK) cleanTalk(raw.substringAfter(' ', "")) else ""
        return CommandFrame(cmd, truncateUtf8(rest, MAX_TALK_BYTES))
    }

    /** Next state after a command lands: records it and bumps seq so subscribers get a notify. */
    fun applyCommand(state: BeastState, command: BeastCommand): BeastState =
        state.copy(lastCommand = command, seq = (state.seq + 1) and 0xFF)

    /** Merges a fresh WebView report, keeping last command and bumping seq only if something changed. */
    fun mergeReport(previous: BeastState, report: BeastState): BeastState {
        val next = report.copy(lastCommand = previous.lastCommand, seq = previous.seq)
        return if (next == previous) previous else next.copy(seq = (previous.seq + 1) and 0xFF)
    }

    private fun cleanTalk(text: String): String =
        text.replace(Regex("\\p{Cntrl}"), " ").replace(Regex("\\s+"), " ").trim().replace("\uFFFD", "")

    /** Truncates to at most [maxBytes] UTF-8 bytes without splitting a code point. */
    fun truncateUtf8(text: String, maxBytes: Int): String {
        if (text.toByteArray(StandardCharsets.UTF_8).size <= maxBytes) return text
        val out = StringBuilder()
        var used = 0
        var i = 0
        while (i < text.length) {
            val cp = text.codePointAt(i)
            val chunk = String(Character.toChars(cp))
            val size = chunk.toByteArray(StandardCharsets.UTF_8).size
            if (used + size > maxBytes) break
            out.append(chunk)
            used += size
            i += Character.charCount(cp)
        }
        return out.toString()
    }
}
