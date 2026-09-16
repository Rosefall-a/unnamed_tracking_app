package com.rosefall.tracker

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import com.rosefall.tracker.ui.theme.TrackingTheme

class MainActivity : ComponentActivity() {
    private var oidcCallback by mutableStateOf<Uri?>(null)

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        oidcCallback = intent.oidcCallback()
        enableEdgeToEdge()
        setContent {
            TrackingTheme {
                TrackingApp(oidcCallback = oidcCallback, onOidcConsumed = { oidcCallback = null })
            }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        oidcCallback = intent.oidcCallback()
    }

    private fun Intent.oidcCallback(): Uri? = data?.takeIf {
        it.scheme == "tracking-native" && it.host == "oidc" && it.path == "/callback"
    }
}
