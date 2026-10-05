package dev.beastbox.device

import android.os.Handler
import android.os.Looper
import java.util.concurrent.CopyOnWriteArraySet

/** BLE advertising lifecycle as shown in the UI and the foreground notification. */
sealed class AdvertisingStatus {
    data object Off : AdvertisingStatus()
    data object Starting : AdvertisingStatus()
    data class Advertising(val name: String, val clients: Int) : AdvertisingStatus()
    data class Failed(val reason: String) : AdvertisingStatus()
}

/**
 * Process-wide hand-off between the WebView (MainActivity) and the BLE service.
 * All listener callbacks run on the main thread.
 */
object BeastHub {
    private val main = Handler(Looper.getMainLooper())
    private val stateListeners = CopyOnWriteArraySet<(BeastState) -> Unit>()
    private val commandListeners = CopyOnWriteArraySet<(CommandFrame, String) -> Unit>()
    private val statusListeners = CopyOnWriteArraySet<(AdvertisingStatus) -> Unit>()

    @Volatile var state: BeastState = BeastState.EMPTY
        private set

    @Volatile var status: AdvertisingStatus = AdvertisingStatus.Off
        private set

    /** Called by the JavascriptInterface (any thread) with a fresh snapshot from the page. */
    fun reportFromWeb(report: BeastState) {
        main.post {
            val next = BeastProtocol.mergeReport(state, report)
            if (next !== state) publish(next)
        }
    }

    /** Called by the GATT server (binder thread) when a BLE client writes a valid command. */
    fun commandFromBle(frame: CommandFrame, source: String) {
        main.post {
            publish(BeastProtocol.applyCommand(state, frame.command))
            commandListeners.forEach { it(frame, source) }
        }
    }

    fun setStatus(next: AdvertisingStatus) {
        main.post {
            status = next
            statusListeners.forEach { it(next) }
        }
    }

    private fun publish(next: BeastState) {
        state = next
        stateListeners.forEach { it(next) }
    }

    fun addStateListener(l: (BeastState) -> Unit) { stateListeners += l }
    fun removeStateListener(l: (BeastState) -> Unit) { stateListeners -= l }
    fun addCommandListener(l: (CommandFrame, String) -> Unit) { commandListeners += l }
    fun removeCommandListener(l: (CommandFrame, String) -> Unit) { commandListeners -= l }
    fun addStatusListener(l: (AdvertisingStatus) -> Unit) { statusListeners += l; l(status) }
    fun removeStatusListener(l: (AdvertisingStatus) -> Unit) { statusListeners -= l }
}
