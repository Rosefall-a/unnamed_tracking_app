package com.rosefall.tracker

import android.content.Context
import android.net.Uri
import android.util.Base64
import java.security.MessageDigest
import java.security.SecureRandom

object OidcLogin {
    private const val PREFERENCES = "tracking-native-oidc"
    private const val VERIFIER = "pending-verifier"

    fun begin(context: Context, baseUrl: String, providerSlug: String): Uri {
        val random = ByteArray(64).also(SecureRandom()::nextBytes)
        val verifier = Base64.encodeToString(random, Base64.URL_SAFE or Base64.NO_WRAP or Base64.NO_PADDING)
        val challenge = Base64.encodeToString(
            MessageDigest.getInstance("SHA-256").digest(verifier.toByteArray(Charsets.US_ASCII)),
            Base64.URL_SAFE or Base64.NO_WRAP or Base64.NO_PADDING,
        )
        context.getSharedPreferences(PREFERENCES, Context.MODE_PRIVATE)
            .edit().putString(VERIFIER, verifier).apply()
        val providerPath = providerSlug.takeIf { it.isNotBlank() && it != "default" }
            ?.let { "/$it" }.orEmpty()
        return Uri.parse("${baseUrl.trimEnd('/')}/api/auth/oidc/mobile/login$providerPath")
            .buildUpon().appendQueryParameter("challenge", challenge).build()
    }

    fun consumeVerifier(context: Context): String? {
        val preferences = context.getSharedPreferences(PREFERENCES, Context.MODE_PRIVATE)
        val verifier = preferences.getString(VERIFIER, null)
        preferences.edit().remove(VERIFIER).apply()
        return verifier
    }
}
