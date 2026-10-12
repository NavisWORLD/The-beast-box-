package dev.beastbox.device

import android.util.Log
import org.json.JSONObject

/**
 * Receives main-frame, exact-origin WebMessageListener messages only. It never exposes Bluetooth control to JS.
 */
class BeastBridge(private val isTrustedPage: () -> Boolean) {

    fun receive(message: String?) {
        if (!isTrustedPage() || message == null || message.length > 8192) return
        val envelope = runCatching { JSONObject(message) }.getOrNull() ?: return
        when (envelope.optString("kind")) {
            "state" -> reportState(envelope.optString("json"))
            "log" -> log(envelope.optString("message"))
        }
    }

    private fun reportState(json: String?) {
        if (!isTrustedPage() || json == null || json.length > 4096) return
        val state = runCatching { parse(JSONObject(json)) }.getOrNull() ?: return
        BeastHub.reportFromWeb(state)
    }

    private fun log(message: String?) {
        if (isTrustedPage()) Log.i(TAG, (message ?: "").take(300))
    }

    companion object {
        private const val TAG = "BeastBoxBridge"

        fun parse(o: JSONObject): BeastState = BeastState(
            displayName = BeastProtocol.sanitizeName(o.optString("displayName", "")),
            species = BeastProtocol.sanitizeName(o.optString("species", "")),
            stage = o.optInt("stage", 0).coerceIn(0, 3),
            xp = o.optInt("xp", 0).coerceAtLeast(0),
            bond = o.optInt("bond", 0).coerceIn(0, 100),
            energy = if (o.has("energy") && !o.isNull("energy")) o.optInt("energy", 0).coerceIn(0, 100) else BeastProtocol.UNKNOWN,
        )

        /** JSON handed to `window.__beastBoxDevice.receive(...)` in the page. */
        fun commandJson(frame: CommandFrame, source: String): String = JSONObject()
            .put("command", frame.command.word)
            .put("text", frame.text)
            .put("source", source)
            .toString()
    }
}
