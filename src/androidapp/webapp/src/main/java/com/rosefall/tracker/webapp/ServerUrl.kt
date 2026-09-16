package com.rosefall.tracker.webapp

import java.net.URI

object ServerUrl {
    fun normalize(rawValue: String): String {
        val trimmed = rawValue.trim()
        require(trimmed.isNotEmpty()) { "Enter your tracking server address." }
        val withScheme = if ("://" in trimmed) trimmed else "${defaultScheme(trimmed)}://$trimmed"
        val uri = URI(withScheme)
        require(uri.scheme == "http" || uri.scheme == "https") { "Use an http:// or https:// address." }
        require(!uri.host.isNullOrBlank() && uri.userInfo == null) { "Enter a valid server address." }
        require(uri.fragment == null && uri.query == null) { "The server address cannot contain a query or fragment." }
        return withScheme.trimEnd('/')
    }

    private fun defaultScheme(authority: String): String {
        val host = authority.substringBefore('/').substringBefore(':').lowercase()
        val privateIpv4 = host.startsWith("10.") || host.startsWith("192.168.") ||
            Regex("^172\\.(1[6-9]|2[0-9]|3[01])\\.").containsMatchIn(host)
        return if (host == "localhost" || host == "127.0.0.1" || host == "10.0.2.2" || privateIpv4) "http" else "https"
    }
}
