package com.rosefall.tracker

import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onNodeWithText
import org.junit.Rule
import org.junit.Test

class MainActivityTest {
    @get:Rule
    val composeRule = createAndroidComposeRule<MainActivity>()

    @Test
    fun firstLaunchShowsNativeServerConfiguration() {
        composeRule.onNodeWithText("Connect your library").assertExists()
        composeRule.onNodeWithText("Server address").assertExists()
        composeRule.onNodeWithText("Continue").assertExists()
    }
}
