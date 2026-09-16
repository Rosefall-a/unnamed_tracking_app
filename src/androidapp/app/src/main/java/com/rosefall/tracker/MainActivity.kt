package com.rosefall.tracker

import android.app.DownloadManager
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.os.Environment
import android.view.Menu
import android.view.MenuItem
import android.view.ViewGroup
import android.webkit.CookieManager
import android.webkit.DownloadListener
import android.webkit.URLUtil
import android.webkit.ValueCallback
import android.webkit.WebChromeClient
import android.webkit.WebResourceRequest
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.Toast
import androidx.activity.OnBackPressedCallback
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity

class MainActivity : AppCompatActivity() {
    private val preferences by lazy { getSharedPreferences(PREFERENCES, Context.MODE_PRIVATE) }
    private var webView: WebView? = null
    private var fileCallback: ValueCallback<Array<Uri>>? = null

    private val fileChooser = registerForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
        val callback = fileCallback ?: return@registerForActivityResult
        callback.onReceiveValue(WebChromeClient.FileChooserParams.parseResult(result.resultCode, result.data))
        fileCallback = null
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        onBackPressedDispatcher.addCallback(this, object : OnBackPressedCallback(true) {
            override fun handleOnBackPressed() {
                val browser = webView
                if (browser?.canGoBack() == true) browser.goBack() else finish()
            }
        })

        val savedUrl = preferences.getString(SERVER_URL, null)
            ?: BuildConfig.DEFAULT_SERVER_URL.takeIf { it.isNotBlank() }
        if (savedUrl == null) showServerSetup() else showWebApp(savedUrl, savedInstanceState)
    }

    override fun onCreateOptionsMenu(menu: Menu): Boolean {
        menu.add("Reload").setShowAsAction(MenuItem.SHOW_AS_ACTION_IF_ROOM)
        menu.add("Change server")
        menu.add("Open in browser")
        return true
    }

    override fun onOptionsItemSelected(item: MenuItem): Boolean = when (item.title.toString()) {
        "Reload" -> { webView?.reload(); true }
        "Change server" -> { showServerSetup(preferences.getString(SERVER_URL, "")); true }
        "Open in browser" -> {
            webView?.url?.let { startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(it))) }
            true
        }
        else -> super.onOptionsItemSelected(item)
    }

    private fun showServerSetup(currentValue: String? = null, error: String? = null) {
        title = "Connect to server"
        webView?.destroy()
        webView = null
        val padding = (24 * resources.displayMetrics.density).toInt()
        val layout = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(padding, padding, padding, padding)
        }
        layout.addView(TextView(this).apply {
            text = "Enter the address of your self-hosted tracking app. HTTPS is recommended."
            textSize = 18f
        })
        val input = EditText(this).apply {
            hint = "https://tracker.example.com"
            setText(currentValue.orEmpty())
            tag = "server-url-input"
            isSingleLine = true
        }
        layout.addView(input, ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT)
        if (error != null) layout.addView(TextView(this).apply { text = error; setTextColor(0xffb91c1c.toInt()) })
        layout.addView(Button(this).apply {
            text = "Connect"
            tag = "connect-button"
            setOnClickListener {
                try {
                    val url = ServerUrl.normalize(input.text.toString())
                    preferences.edit().putString(SERVER_URL, url).apply()
                    showWebApp(url, null)
                } catch (exception: IllegalArgumentException) {
                    showServerSetup(input.text.toString(), exception.message)
                }
            }
        })
        setContentView(layout)
        invalidateOptionsMenu()
    }

    @Suppress("SetJavaScriptEnabled")
    private fun showWebApp(serverUrl: String, state: Bundle?) {
        title = "Tracking App"
        val browser = WebView(this)
        webView = browser
        CookieManager.getInstance().apply {
            setAcceptCookie(true)
            setAcceptThirdPartyCookies(browser, false)
        }
        browser.settings.apply {
            javaScriptEnabled = true
            domStorageEnabled = true
            databaseEnabled = true
            allowFileAccess = false
            allowContentAccess = true
            mediaPlaybackRequiresUserGesture = true
        }
        browser.webViewClient = object : WebViewClient() {
            override fun shouldOverrideUrlLoading(view: WebView, request: WebResourceRequest): Boolean {
                val uri = request.url
                return if (uri.scheme == "http" || uri.scheme == "https") {
                    false
                } else {
                    runCatching { startActivity(Intent(Intent.ACTION_VIEW, uri)) }
                    true
                }
            }
        }
        browser.webChromeClient = object : WebChromeClient() {
            override fun onShowFileChooser(
                webView: WebView,
                callback: ValueCallback<Array<Uri>>,
                params: FileChooserParams,
            ): Boolean {
                fileCallback?.onReceiveValue(null)
                fileCallback = callback
                return runCatching { fileChooser.launch(params.createIntent()); true }
                    .getOrElse { fileCallback = null; callback.onReceiveValue(null); false }
            }
        }
        browser.setDownloadListener(DownloadListener { url, userAgent, contentDisposition, mimeType, _ ->
            val filename = URLUtil.guessFileName(url, contentDisposition, mimeType)
            val request = DownloadManager.Request(Uri.parse(url)).apply {
                setMimeType(mimeType)
                addRequestHeader("User-Agent", userAgent)
                CookieManager.getInstance().getCookie(url)?.let { addRequestHeader("Cookie", it) }
                setTitle(filename)
                setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED)
                setDestinationInExternalPublicDir(Environment.DIRECTORY_DOWNLOADS, filename)
            }
            (getSystemService(DOWNLOAD_SERVICE) as DownloadManager).enqueue(request)
            Toast.makeText(this, "Downloading $filename", Toast.LENGTH_SHORT).show()
        })
        setContentView(browser)
        if (state == null || browser.restoreState(state) == null) browser.loadUrl(serverUrl)
        invalidateOptionsMenu()
    }

    override fun onSaveInstanceState(outState: Bundle) {
        webView?.saveState(outState)
        super.onSaveInstanceState(outState)
    }

    override fun onDestroy() {
        fileCallback?.onReceiveValue(null)
        fileCallback = null
        webView?.destroy()
        webView = null
        super.onDestroy()
    }

    companion object {
        private const val PREFERENCES = "tracking-app"
        private const val SERVER_URL = "server-url"
    }
}
