package dev.beastbox.device

import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertSame
import org.junit.Assert.assertTrue
import org.junit.Test
import java.nio.charset.StandardCharsets.UTF_8
import java.util.UUID

class BeastProtocolTest {

    // ---- commands -------------------------------------------------------------------------

    @Test fun binaryOpcodesDecode() {
        assertEquals(CommandFrame(BeastCommand.FEED), BeastProtocol.decodeCommand(byteArrayOf(0x01)))
        assertEquals(CommandFrame(BeastCommand.PLAY), BeastProtocol.decodeCommand(byteArrayOf(0x02)))
        assertEquals(CommandFrame(BeastCommand.TALK), BeastProtocol.decodeCommand(byteArrayOf(0x03)))
        assertEquals(CommandFrame(BeastCommand.ATTACK), BeastProtocol.decodeCommand(byteArrayOf(0x04)))
    }

    @Test fun binaryTalkCarriesUtf8Text() {
        val bytes = byteArrayOf(0x03) + "hello beast \u2728".toByteArray(UTF_8)
        assertEquals(CommandFrame(BeastCommand.TALK, "hello beast \u2728"), BeastProtocol.decodeCommand(bytes))
    }

    @Test fun nonTalkPayloadIsIgnored() {
        assertEquals(CommandFrame(BeastCommand.FEED), BeastProtocol.decodeCommand(byteArrayOf(0x01, 0x41, 0x42)))
    }

    @Test fun textCommandsDecodeCaseInsensitively() {
        assertEquals(CommandFrame(BeastCommand.FEED), BeastProtocol.decodeCommand("feed".toByteArray(UTF_8)))
        assertEquals(CommandFrame(BeastCommand.PLAY), BeastProtocol.decodeCommand(" PLAY \n".toByteArray(UTF_8)))
        assertEquals(CommandFrame(BeastCommand.ATTACK), BeastProtocol.decodeCommand("Attack".toByteArray(UTF_8)))
        assertEquals(
            CommandFrame(BeastCommand.TALK, "how are you"),
            BeastProtocol.decodeCommand("talk how   are\tyou".toByteArray(UTF_8)),
        )
        assertEquals(CommandFrame(BeastCommand.TALK), BeastProtocol.decodeCommand("talk".toByteArray(UTF_8)))
    }

    @Test fun invalidCommandsAreRejected() {
        assertNull(BeastProtocol.decodeCommand(null))
        assertNull(BeastProtocol.decodeCommand(ByteArray(0)))
        assertNull(BeastProtocol.decodeCommand(byteArrayOf(0x00)))
        assertNull(BeastProtocol.decodeCommand(byteArrayOf(0x05)))
        assertNull(BeastProtocol.decodeCommand(byteArrayOf(0xFF.toByte())))
        assertNull(BeastProtocol.decodeCommand("   ".toByteArray(UTF_8)))
        assertNull(BeastProtocol.decodeCommand("pet".toByteArray(UTF_8)))
        assertNull(BeastProtocol.decodeCommand("feeding".toByteArray(UTF_8)))
    }

    @Test fun commandRoundTripsForEveryCommand() {
        for (cmd in BeastCommand.entries) {
            val frame = CommandFrame(cmd, if (cmd == BeastCommand.TALK) "hi there" else "")
            assertEquals(frame, BeastProtocol.decodeCommand(BeastProtocol.encodeCommand(frame)))
        }
    }

    @Test fun encodeCommandIsOneByteExceptTalk() {
        assertArrayEquals(byteArrayOf(0x01), BeastProtocol.encodeCommand(CommandFrame(BeastCommand.FEED, "ignored")))
        assertArrayEquals(byteArrayOf(0x04), BeastProtocol.encodeCommand(CommandFrame(BeastCommand.ATTACK)))
        assertArrayEquals(byteArrayOf(0x03, 0x68, 0x69), BeastProtocol.encodeCommand(CommandFrame(BeastCommand.TALK, "hi")))
    }

    @Test fun talkTextIsBoundedAndCleaned() {
        val long = "\u00E9".repeat(200) // 2 bytes each in UTF-8
        val encoded = BeastProtocol.encodeCommand(CommandFrame(BeastCommand.TALK, long))
        assertEquals(1 + BeastProtocol.MAX_TALK_BYTES, encoded.size)
        val decoded = BeastProtocol.decodeCommand(encoded)!!
        assertEquals(60, decoded.text.length)
        assertEquals("a b", BeastProtocol.decodeCommand(byteArrayOf(0x03) + "a\u0000\u0007b".toByteArray(UTF_8))!!.text)
    }

    @Test fun binaryTalkCutMidCodePointDoesNotLeakReplacementChar() {
        val bytes = byteArrayOf(0x03) + "\u00E9".repeat(70).toByteArray(UTF_8) // 140 bytes, cut at 120 boundary-safe
        val bytesOdd = byteArrayOf(0x03, 0x61) + "\u00E9".repeat(70).toByteArray(UTF_8) // cut lands mid code point
        assertFalse(BeastProtocol.decodeCommand(bytes)!!.text.contains('\uFFFD'))
        assertFalse(BeastProtocol.decodeCommand(bytesOdd)!!.text.contains('\uFFFD'))
    }

    @Test fun opcodesAreStable() {
        assertEquals(listOf(1, 2, 3, 4), BeastCommand.entries.map { it.opcode })
        assertEquals(listOf("feed", "play", "talk", "attack"), BeastCommand.entries.map { it.word })
    }

    // ---- state ----------------------------------------------------------------------------

    @Test fun stateEncodesToFixedLayout() {
        val state = BeastState(
            displayName = "Sparky", species = "Voltpup", stage = 2, xp = 0x1234, bond = 55, energy = 80,
            lastCommand = BeastCommand.PLAY, seq = 7,
        )
        assertArrayEquals(
            byteArrayOf(1, 2, 80, 55, 0x34, 0x12, 2, 7),
            BeastProtocol.encodeState(state),
        )
    }

    @Test fun stateRoundTrips() {
        val state = BeastState(stage = 3, xp = 140, bond = 100, energy = 0, lastCommand = BeastCommand.ATTACK, seq = 255)
        val frame = BeastProtocol.decodeState(BeastProtocol.encodeState(state))!!
        assertEquals(StateFrame(1, 3, 0, 100, 140, BeastCommand.ATTACK, 255), frame)
    }

    @Test fun stateClampsOutOfRangeValues() {
        val state = BeastState(stage = 9, xp = 1_000_000, bond = 300, energy = 150, seq = 256 + 3)
        val frame = BeastProtocol.decodeState(BeastProtocol.encodeState(state))!!
        assertEquals(3, frame.stage)
        assertEquals(0xFFFF, frame.xp)
        assertEquals(100, frame.bond)
        assertEquals(100, frame.energy)
        assertEquals(3, frame.seq)
        val negative = BeastProtocol.decodeState(BeastProtocol.encodeState(BeastState(stage = -1, xp = -5, bond = -1, energy = -1)))!!
        assertEquals(0, negative.stage)
        assertEquals(0, negative.xp)
        assertEquals(0, negative.bond)
        assertEquals(0, negative.energy)
    }

    @Test fun emptyStateHasUnknownEnergyAndNoCommand() {
        val bytes = BeastProtocol.encodeState(BeastState.EMPTY)
        assertEquals(BeastProtocol.STATE_FRAME_SIZE, bytes.size)
        assertArrayEquals(byteArrayOf(1, 0, 0xFF.toByte(), 0, 0, 0, 0, 0), bytes)
        assertNull(BeastProtocol.decodeState(bytes)!!.lastCommand)
    }

    @Test fun stateFitsDefaultMtuNotification() {
        assertTrue(BeastProtocol.STATE_FRAME_SIZE <= 20) // ATT MTU 23 - 3 bytes header
    }

    @Test fun decodeStateRejectsShortOrWrongVersion() {
        assertNull(BeastProtocol.decodeState(byteArrayOf(1, 2, 3)))
        assertNull(BeastProtocol.decodeState(byteArrayOf(2, 0, 0, 0, 0, 0, 0, 0)))
    }

    @Test fun applyCommandRecordsAndWrapsSeq() {
        val s = BeastProtocol.applyCommand(BeastState(seq = 255), BeastCommand.FEED)
        assertEquals(BeastCommand.FEED, s.lastCommand)
        assertEquals(0, s.seq)
    }

    @Test fun mergeReportOnlyBumpsSeqOnChange() {
        val prev = BeastState(displayName = "Sparky", stage = 1, xp = 10, lastCommand = BeastCommand.TALK, seq = 4)
        val same = BeastProtocol.mergeReport(prev, BeastState(displayName = "Sparky", stage = 1, xp = 10))
        assertSame(prev, same)
        val changed = BeastProtocol.mergeReport(prev, BeastState(displayName = "Sparky", stage = 1, xp = 12))
        assertEquals(12, changed.xp)
        assertEquals(BeastCommand.TALK, changed.lastCommand)
        assertEquals(5, changed.seq)
    }

    @Test fun nameCharacteristicFallsBackToSpecies() {
        assertArrayEquals("Sparky".toByteArray(UTF_8), BeastProtocol.encodeName(BeastState(displayName = "Sparky", species = "Voltpup")))
        assertArrayEquals("Voltpup".toByteArray(UTF_8), BeastProtocol.encodeName(BeastState(species = "Voltpup")))
        assertArrayEquals("Beast Box".toByteArray(UTF_8), BeastProtocol.encodeName(BeastState.EMPTY))
    }

    // ---- advertised name ------------------------------------------------------------------

    @Test fun advertisedNameUsesBeastBoxPrefix() {
        assertEquals("Beast Box \u00B7 Sparky", BeastProtocol.advertisedName("Sparky"))
        assertEquals("Beast Box", BeastProtocol.advertisedName(""))
        assertEquals("Beast Box", BeastProtocol.advertisedName(null))
        assertEquals("Beast Box", BeastProtocol.advertisedName("\u2728\u2728"))
    }

    @Test fun advertisedNameFitsScanResponseForLongestAllowedName() {
        val name = BeastProtocol.advertisedName("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
        assertEquals("Beast Box \u00B7 ABCDEFGHIJKLMNOP", name)
        assertTrue(name.toByteArray(UTF_8).size <= BeastProtocol.MAX_ADVERTISED_NAME_BYTES)
    }

    @Test fun advertisedNameNeverImpersonatesMuseGadgets() {
        for (input in listOf("MuseGadget", "MuseGadgetA1B2C3", "musegadget 1")) {
            val name = BeastProtocol.advertisedName(input)
            assertTrue(name.startsWith("Beast Box"))
            assertFalse(name.startsWith("MuseGadget", ignoreCase = true))
        }
    }

    @Test fun sanitizeMatchesWebStoreRules() {
        assertEquals("Ziggy O'Bolt-2", BeastProtocol.sanitizeName("  Ziggy <O'Bolt-2>  "))
        assertEquals("A B", BeastProtocol.sanitizeName("A\u00B7\u00B7B"))
        assertEquals(16, BeastProtocol.sanitizeName("x".repeat(40)).length)
    }

    @Test fun truncateUtf8KeepsCodePointsWhole() {
        assertEquals("ab", BeastProtocol.truncateUtf8("ab\u00E9", 3))
        assertEquals("ab\u00E9", BeastProtocol.truncateUtf8("ab\u00E9", 4))
        assertEquals("", BeastProtocol.truncateUtf8("\uD83D\uDC09", 3)) // dragon emoji, 4 bytes
    }

    // ---- UUIDs ----------------------------------------------------------------------------

    @Test fun uuidsAreDistinctRandomVersion4AndNotBluetoothBase() {
        val custom = listOf(BeastUuids.SERVICE, BeastUuids.STATE, BeastUuids.NAME, BeastUuids.COMMAND)
        assertEquals(custom.size, custom.toSet().size)
        for (u in custom) {
            assertEquals(4, u.version())
            assertNotEquals("-0000-1000-8000-00805f9b34fb", u.toString().substring(8))
        }
        assertEquals(UUID.fromString("00002902-0000-1000-8000-00805f9b34fb"), BeastUuids.CCCD)
    }
}
