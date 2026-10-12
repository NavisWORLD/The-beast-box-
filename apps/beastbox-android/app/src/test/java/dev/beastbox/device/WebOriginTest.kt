package dev.beastbox.device

import org.junit.Assert.*
import org.junit.Test

class WebOriginTest {
    @Test fun normalizesDefaultHttpsPortAndCase() {
        assertEquals("https://www.beastboxcosmos.xyz", WebOrigin.of("HTTPS://WWW.BEASTBOXCOSMOS.XYZ:443/spark/index.html?state=1"))
        assertEquals("https://localhost:8443", WebOrigin.of("https://localhost:8443/game"))
    }

    @Test fun rejectsCredentialsMalformedUrlsAndOtherSchemes() {
        for (url in listOf(null, "", "http://beastboxcosmos.xyz", "file:///beast.html",
            "https://owner:password@beastboxcosmos.xyz/", "https://beastboxcosmos.xyz:0/",
            "https://beastboxcosmos.xyz:65536/", "https:///no-host", "https://host with spaces/")) {
            assertNull(url, WebOrigin.of(url))
        }
    }

    @Test fun requiresExactOriginAndMainFrame() {
        val allowed = "https://www.beastboxcosmos.xyz"
        assertTrue(WebOrigin.accepts(allowed, "$allowed:443/sol-game", true))
        assertFalse(WebOrigin.accepts(allowed, "$allowed/", false))
        assertFalse(WebOrigin.accepts(allowed, "https://www.beastboxcosmos.xyz.evil.example/", true))
        assertFalse(WebOrigin.accepts(allowed, "https://beastboxcosmos.xyz/", true))
        assertFalse(WebOrigin.accepts(allowed, "$allowed:8443/", true))
        assertFalse(WebOrigin.accepts(null, "$allowed/", true))
    }
}
