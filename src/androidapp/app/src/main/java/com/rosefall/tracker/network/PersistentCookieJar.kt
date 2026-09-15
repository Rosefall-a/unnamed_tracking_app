package com.rosefall.tracker.network

import android.content.SharedPreferences
import okhttp3.Cookie
import okhttp3.CookieJar
import okhttp3.HttpUrl
import org.json.JSONArray
import org.json.JSONObject

class PersistentCookieJar(private val preferences: SharedPreferences) : CookieJar {
    private val cookies = mutableListOf<Cookie>()

    init {
        preferences.getString(KEY, null)?.let { stored ->
            runCatching {
                val array = JSONArray(stored)
                repeat(array.length()) { index -> decode(array.getJSONObject(index))?.let(cookies::add) }
            }
        }
        removeExpired()
    }

    @Synchronized
    override fun saveFromResponse(url: HttpUrl, responseCookies: List<Cookie>) {
        responseCookies.forEach { incoming ->
            cookies.removeAll { it.name == incoming.name && it.domain == incoming.domain && it.path == incoming.path }
            if (incoming.expiresAt > System.currentTimeMillis()) cookies.add(incoming)
        }
        persist()
    }

    @Synchronized
    override fun loadForRequest(url: HttpUrl): List<Cookie> {
        removeExpired()
        return cookies.filter { it.matches(url) }
    }

    @Synchronized
    fun clear() {
        cookies.clear()
        preferences.edit().remove(KEY).apply()
    }

    private fun removeExpired() {
        if (cookies.removeAll { it.expiresAt <= System.currentTimeMillis() }) persist()
    }

    private fun persist() {
        val array = JSONArray()
        cookies.forEach { cookie ->
            array.put(JSONObject().apply {
                put("name", cookie.name)
                put("value", cookie.value)
                put("domain", cookie.domain)
                put("path", cookie.path)
                put("expiresAt", cookie.expiresAt)
                put("secure", cookie.secure)
                put("httpOnly", cookie.httpOnly)
                put("hostOnly", cookie.hostOnly)
            })
        }
        preferences.edit().putString(KEY, array.toString()).apply()
    }

    private fun decode(value: JSONObject): Cookie? = runCatching {
        Cookie.Builder()
            .name(value.getString("name"))
            .value(value.getString("value"))
            .apply {
                if (value.getBoolean("hostOnly")) hostOnlyDomain(value.getString("domain"))
                else domain(value.getString("domain"))
                path(value.getString("path"))
                expiresAt(value.getLong("expiresAt"))
                if (value.getBoolean("secure")) secure()
                if (value.getBoolean("httpOnly")) httpOnly()
            }
            .build()
    }.getOrNull()

    companion object { private const val KEY = "native-session-cookies" }
}
