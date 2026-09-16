package com.rosefall.tracker

import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Test

class ServerUrlTest {
    @Test fun addsHttpsWhenSchemeIsMissing() {
        assertEquals("https://tracker.example.com", ServerUrl.normalize(" tracker.example.com/ "))
    }

    @Test fun retainsLanHttpAddressAndPort() {
        assertEquals("http://192.168.1.20:5173", ServerUrl.normalize("http://192.168.1.20:5173/"))
    }

    @Test fun rejectsNonWebSchemesAndCredentials() {
        assertThrows(IllegalArgumentException::class.java) { ServerUrl.normalize("file:///tmp/app") }
        assertThrows(IllegalArgumentException::class.java) { ServerUrl.normalize("https://user:pass@example.com") }
    }

    @Test fun rejectsQueryAndFragment() {
        assertThrows(IllegalArgumentException::class.java) { ServerUrl.normalize("https://example.com/?x=1") }
        assertThrows(IllegalArgumentException::class.java) { ServerUrl.normalize("https://example.com/#login") }
    }
}
