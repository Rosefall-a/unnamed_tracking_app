package com.rosefall.tracker.webapp

import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Test

class ServerUrlTest {
    @Test fun preservesExplicitProtocols() {
        assertEquals("http://tracker.lan:8080", ServerUrl.normalize("http://tracker.lan:8080/"))
        assertEquals("https://tracker.example.com", ServerUrl.normalize("https://tracker.example.com"))
    }

    @Test fun choosesSafeDefaults() {
        assertEquals("http://192.168.1.20:5173", ServerUrl.normalize("192.168.1.20:5173"))
        assertEquals("https://tracker.example.com", ServerUrl.normalize("tracker.example.com"))
    }

    @Test fun rejectsNonWebProtocols() {
        assertThrows(IllegalArgumentException::class.java) { ServerUrl.normalize("file:///tmp/index.html") }
    }
}
