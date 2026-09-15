package com.rosefall.tracker.webapp

import android.app.DownloadManager
import android.content.Context
import android.content.Intent
import android.graphics.Color
import android.net.Uri
import android.net.http.SslError
import android.os.Bundle
import android.os.Environment
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.webkit.CookieManager
import android.webkit.DownloadListener
import android.webkit.SslErrorHandler
import android.webkit.URLUtil
import android.webkit.ValueCallback
import android.webkit.WebChromeClient
import android.webkit.WebResourceRequest
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Button
import android.widget.EditText
import android.widget.FrameLayout
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.OnBackPressedCallback
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat

class MainActivity : ComponentActivity() {
    private val preferences by lazy { getSharedPreferences(PREFERENCES, Context.MODE_PRIVATE) }
    private var webView: WebView? = null
    private var fileCallback: ValueCallback<Array<Uri>>? = null

    private val fileChooser = registerForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
        fileCallback?.onReceiveValue(WebChromeClient.FileChooserParams.parseResult(result.resultCode, result.data))
        fileCallback = null
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        onBackPressedDispatcher.addCallback(this, object : OnBackPressedCallback(true) {
            override fun handleOnBackPressed() {
                if (webView?.canGoBack() == true) webView?.goBack() else finish()
            }
        })
        val savedUrl = preferences.getString(SERVER_URL, null) ?: BuildConfig.DEFAULT_SERVER_URL.takeIf(String::isNotBlank)
        if (savedUrl == null) showServerSetup() else showWebApp(savedUrl, savedInstanceState)
    }

    private fun insetRoot(child: View): FrameLayout = FrameLayout(this).apply {
        setBackgroundColor(Color.rgb(15, 17, 23))
        addView(child, FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT))
        ViewCompat.setOnApplyWindowInsetsListener(this) { view, insets ->
            val bars = insets.getInsets(WindowInsetsCompat.Type.systemBars() or WindowInsetsCompat.Type.displayCutout())
            view.setPadding(bars.left, bars.top, bars.right, bars.bottom)
            insets
        }
    }

    private fun showServerSetup(currentValue: String = "", error: String? = null) {
        destroyWebView()
        val density = resources.displayMetrics.density
        val card = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER_VERTICAL
            setPadding((24 * density).toInt(), (32 * density).toInt(), (24 * density).toInt(), (32 * density).toInt())
        }
        card.addView(TextView(this).apply {
            text = "Connect your library"
            textSize = 28f
            setTextColor(Color.WHITE)
        })
        card.addView(TextView(this).apply {
            text = "Use HTTP for a trusted local server or HTTPS for a secured deployment."
            textSize = 16f
            setTextColor(Color.rgb(190, 192, 204))
            setPadding(0, (12 * density).toInt(), 0, (18 * density).toInt())
        })
        val input = EditText(this).apply {
            hint = "https://tracker.example.com"
            setHintTextColor(Color.GRAY)
            setTextColor(Color.WHITE)
            setText(currentValue)
            isSingleLine = true
            tag = "server-url-input"
        }
        card.addView(input, ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT)
        error?.let { message -> card.addView(TextView(this).apply { text = message; setTextColor(Color.rgb(248, 113, 113)) }) }
        card.addView(Button(this).apply {
            text = "Connect"
            tag = "connect-button"
            setOnClickListener {
                runCatching { ServerUrl.normalize(input.text.toString()) }
                    .onSuccess { url -> preferences.edit().putString(SERVER_URL, url).apply(); showWebApp(url, null) }
                    .onFailure { problem -> showServerSetup(input.text.toString(), problem.message) }
            }
        })
        setContentView(insetRoot(card))
    }

    @Suppress("SetJavaScriptEnabled")
    private fun showWebApp(serverUrl: String, state: Bundle?) {
        destroyWebView()
        val browser = WebView(this)
        webView = browser
        CookieManager.getInstance().apply { setAcceptCookie(true); setAcceptThirdPartyCookies(browser, false) }
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
                if (uri.scheme == "http" || uri.scheme == "https") return false
                runCatching { startActivity(Intent(Intent.ACTION_VIEW, uri)) }
                return true
            }

            override fun onReceivedSslError(view: WebView, handler: SslErrorHandler, error: SslError) {
                handler.cancel()
                showServerSetup(serverUrl, "HTTPS certificate validation failed. Fix the certificate, or use http:// only for a trusted HTTP server.")
            }
        }
        browser.webChromeClient = object : WebChromeClient() {
            override fun onShowFileChooser(webView: WebView, callback: ValueCallback<Array<Uri>>, params: FileChooserParams): Boolean {
                fileCallback?.onReceiveValue(null)
                fileCallback = callback
                return runCatching { fileChooser.launch(params.createIntent()); true }
                    .getOrElse { fileCallback = null; callback.onReceiveValue(null); false }
            }
        }
        browser.setDownloadListener(DownloadListener { url, userAgent, disposition, mimeType, _ ->
            val filename = URLUtil.guessFileName(url, disposition, mimeType)
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
        setContentView(insetRoot(browser))
        if (state == null || browser.restoreState(state) == null) browser.loadUrl(serverUrl)
    }

    override fun onSaveInstanceState(outState: Bundle) {
        webView?.saveState(outState)
        super.onSaveInstanceState(outState)
    }

    private fun destroyWebView() {
        fileCallback?.onReceiveValue(null)
        fileCallback = null
        webView?.destroy()
        webView = null
    }

    override fun onDestroy() {
        destroyWebView()
        super.onDestroy()
    }

    companion object {
        private const val PREFERENCES = "tracking-web"
        private const val SERVER_URL = "server-url"
    }
}
