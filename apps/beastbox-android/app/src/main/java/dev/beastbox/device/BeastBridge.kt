package dev.beastbox.device

import android.util.Log
import android.webkit.JavascriptInterface
import org.json.JSONObject

/**
 * Exposed to page JavaScript as `window.BeastBoxNative`. It only accepts state reports while the
 * WebView's top-level page is on the configured origin; it never exposes Bluetooth control to JS.
 */
class BeastBridge(private val isTrustedPage: () -> Boolean) {

    @JavascriptInterface
    fun reportState(json: String?) {
        if (!isTrustedPage() || json == null || json.length > 4096) return
        val state = runCatching { parse(JSONObject(json)) }.getOrNull() ?: return
        BeastHub.reportFromWeb(state)
    }

    @JavascriptInterface
    fun log(message: String?) {
        if (isTrustedPage()) Log.i(TAG, (message ?: "").take(300))
    }

    @JavascriptInterface
    fun bridgeVersion(): Int = 1

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
