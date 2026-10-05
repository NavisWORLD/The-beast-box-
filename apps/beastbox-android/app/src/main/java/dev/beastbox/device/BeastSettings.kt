package dev.beastbox.device

import android.content.Context
import android.net.Uri

/** Which web app the WebView wraps. Production Beast Box sits behind Vercel SSO, so it is opt-in. */
enum class WebTarget(val label: String, val url: String) {
    SPARK_BEASTS(
        "Spark Beasts (live, default)",
        "https://www.beastboxcosmos.xyz/spark/index.html",
    ),
    BEAST_BOX_PRODUCTION(
        "Beast Box home",
        "https://www.beastboxcosmos.xyz/",
    ),
    CUSTOM("Custom https URL", ""),
}

class BeastSettings(context: Context) {
    private val prefs = context.applicationContext.getSharedPreferences("beastbox_device", Context.MODE_PRIVATE)

    var target: WebTarget
        get() = runCatching { WebTarget.valueOf(prefs.getString(KEY_TARGET, null) ?: "") }.getOrDefault(WebTarget.SPARK_BEASTS)
        set(value) = prefs.edit().putString(KEY_TARGET, value.name).apply()

    var customUrl: String
        get() = prefs.getString(KEY_CUSTOM_URL, "") ?: ""
        set(value) = prefs.edit().putString(KEY_CUSTOM_URL, value.trim()).apply()

    /** Android only puts the adapter name in the GAP name, so the phone's BT name is changed while on. */
    var renameAdapter: Boolean
        get() = prefs.getBoolean(KEY_RENAME, true)
        set(value) = prefs.edit().putBoolean(KEY_RENAME, value).apply()

    /** Original phone Bluetooth name, kept across crashes so it can always be restored. */
    var savedAdapterName: String?
        get() = prefs.getString(KEY_SAVED_NAME, null)
        set(value) = prefs.edit().apply { if (value == null) remove(KEY_SAVED_NAME) else putString(KEY_SAVED_NAME, value) }.apply()

    val startUrl: String
        get() = when (target) {
            WebTarget.CUSTOM -> customUrl.takeIf { isAllowedUrl(it) } ?: WebTarget.SPARK_BEASTS.url
            else -> target.url
        }

    companion object {
        private const val KEY_TARGET = "web_target"
        private const val KEY_CUSTOM_URL = "custom_url"
        private const val KEY_RENAME = "rename_adapter"
        private const val KEY_SAVED_NAME = "saved_adapter_name"

        fun isAllowedUrl(url: String): Boolean {
            val uri = runCatching { Uri.parse(url) }.getOrNull() ?: return false
            return uri.scheme == "https" && !uri.host.isNullOrBlank()
        }

        /** scheme://host[:port] used to scope the JavaScript bridge. */
        fun originOf(url: String?): String? {
            val uri = runCatching { Uri.parse(url ?: return null) }.getOrNull() ?: return null
            val host = uri.host ?: return null
            val port = if (uri.port == -1) "" else ":${uri.port}"
            return "${uri.scheme}://$host$port".lowercase()
        }
    }
}
