package dev.beastbox.device

import java.net.URI
import java.util.Locale

/** Exact HTTPS origin used by the WebMessageListener and both bridge directions. */
object WebOrigin {
    fun of(url: String?): String? {
        if (url.isNullOrBlank()) return null
        val uri = runCatching { URI(url) }.getOrNull() ?: return null
        if (!uri.scheme.equals("https", ignoreCase = true) || uri.rawUserInfo != null) return null
        val host = uri.host?.lowercase(Locale.ROOT)?.takeIf { it.isNotBlank() } ?: return null
        val port = uri.port
        if (port != -1 && port !in 1..65535) return null
        val normalizedHost = if (host.contains(':') && !host.startsWith('[')) "[$host]" else host
        return "https://$normalizedHost" + if (port == -1 || port == 443) "" else ":$port"
    }

    fun accepts(allowedOrigin: String?, sourceUrl: String?, isMainFrame: Boolean): Boolean =
        isMainFrame && allowedOrigin != null && of(sourceUrl) == allowedOrigin
}
