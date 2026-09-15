package com.rosefall.tracker

import androidx.test.core.app.ActivityScenario
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.junit.Assert.assertNotNull
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class MainActivityTest {
    @Test fun firstLaunchShowsServerConfiguration() {
        ActivityScenario.launch(MainActivity::class.java).use { scenario ->
            scenario.onActivity { activity ->
                assertNotNull(activity.window.decorView.findViewWithTag("server-url-input"))
                assertNotNull(activity.window.decorView.findViewWithTag("connect-button"))
            }
        }
    }
}
