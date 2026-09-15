package com.rosefall.tracker.network

import android.content.Context
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.IOException
import javax.net.ssl.SSLException

class ApiClient(context: Context, val baseUrl: String) {
    private val cookieJar = PersistentCookieJar(
        context.getSharedPreferences("tracking-native-auth", Context.MODE_PRIVATE)
    )
    private val client = OkHttpClient.Builder().cookieJar(cookieJar).build()
    private val json = Json { ignoreUnknownKeys = true }

    suspend fun get(path: String): JsonElement = request("GET", path)

    suspend fun post(path: String, body: JsonObject = JsonObject(emptyMap())): JsonElement =
        request("POST", path, body)

    suspend fun login(identifier: String, password: String) {
        post(
            "/api/auth/login",
            JsonObject(
                mapOf(
                    "username_or_email" to JsonPrimitive(identifier),
                    "password" to JsonPrimitive(password),
                )
            ),
        )
    }

    suspend fun logout() {
        runCatching { post("/api/auth/logout") }
        cookieJar.clear()
    }

    suspend fun oidcStatus(): JsonElement = get("/api/auth/oidc/status")

    suspend fun exchangeOidc(code: String, verifier: String) {
        post(
            "/api/auth/oidc/mobile/exchange",
            JsonObject(
                mapOf(
                    "code" to JsonPrimitive(code),
                    "verifier" to JsonPrimitive(verifier),
                )
            ),
        )
    }

    private suspend fun request(method: String, path: String, body: JsonObject? = null): JsonElement =
        withContext(Dispatchers.IO) {
            val builder = Request.Builder().url(baseUrl.trimEnd('/') + path)
            val requestBody = body?.toString()?.toRequestBody(JSON)
            when (method) {
                "GET" -> builder.get()
                "POST" -> builder.post(requestBody ?: EMPTY_BODY)
                else -> error("Unsupported method: $method")
            }
            try {
                client.newCall(builder.build()).execute().use { response ->
                    val text = response.body?.string().orEmpty()
                    if (!response.isSuccessful) throw ApiException(response.code, apiMessage(text))
                    if (text.isBlank()) JsonObject(emptyMap()) else json.parseToJsonElement(text)
                }
            } catch (error: SSLException) {
                throw IOException(
                    "HTTPS negotiation failed. Check the address and certificate; if this is an HTTP-only LAN server, use http:// explicitly.",
                    error,
                )
            }
        }

    private fun apiMessage(text: String): String = runCatching {
        val value = json.parseToJsonElement(text) as JsonObject
        (value["detail"] as? JsonPrimitive)?.content ?: text
    }.getOrDefault(text.ifBlank { "The server returned an error." })

    companion object {
        private val JSON = "application/json; charset=utf-8".toMediaType()
        private val EMPTY_BODY = ByteArray(0).toRequestBody()
    }
}

class ApiException(val status: Int, message: String) : IOException(message)
