package com.rosefall.tracker.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val DarkColors = darkColorScheme(
    primary = Color(0xFFA78BFA),
    secondary = Color(0xFF67E8F9),
    background = Color(0xFF0F1117),
    surface = Color(0xFF171A23),
    surfaceVariant = Color(0xFF232735),
)

private val LightColors = lightColorScheme(
    primary = Color(0xFF6D28D9),
    secondary = Color(0xFF0E7490),
    background = Color(0xFFF7F7FB),
    surface = Color.White,
    surfaceVariant = Color(0xFFEDEDF5),
)

@Composable
fun TrackingTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = if (isSystemInDarkTheme()) DarkColors else LightColors,
        content = content,
    )
}
