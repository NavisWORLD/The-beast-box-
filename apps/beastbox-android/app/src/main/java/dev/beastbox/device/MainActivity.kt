package dev.beastbox.device

import android.annotation.SuppressLint
import android.app.Activity
import android.app.AlertDialog
import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothManager
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Color
import android.net.Uri
import android.os.Bundle
import android.text.InputType
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.webkit.WebChromeClient
import android.webkit.WebResourceRequest
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Button
import android.widget.CheckBox
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.RadioButton
import android.widget.RadioGroup
import android.widget.Switch
import android.widget.TextView
import android.widget.Toast
import org.json.JSONObject

/**
 * Wraps the Beast Box / Spark Beasts web app in a WebView and owns the BLE on/off toggle.
 * Platform widgets only (no AppCompat) to keep this experiment small.
 */
@SuppressLint("UseSwitchCompatOrMaterialCode")
class MainActivity : Activity() {

    private lateinit var settings: BeastSettings
    private lateinit var webView: WebView
    private lateinit var toggle: Switch
    private lateinit var statusText: TextView
    private var updatingToggle = false

    /** Origin of the page currently shown; written on the UI thread, read by the JS bridge thread. */
    @Volatile private var currentOrigin: String? = null
    @Volatile private var allowedOrigin: String? = null

    private val commandListener: (CommandFrame, String) -> Unit = { frame, source -> deliverToPage(frame, source) }
    private val statusListener: (AdvertisingStatus) -> Unit = { status -> renderStatus(status) }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        settings = BeastSettings(this)
        setContentView(buildLayout())
        configureWebView()
        BeastHub.addCommandListener(commandListener)
        BeastHub.addStatusListener(statusListener)
        loadConfiguredUrl()
    }

    override fun onDestroy() {
        BeastHub.removeCommandListener(commandListener)
        BeastHub.removeStatusListener(statusListener)
        webView.destroy()
        super.onDestroy()
    }

    @Suppress("OVERRIDE_DEPRECATION", "DEPRECATION")
    override fun onBackPressed() {
        if (webView.canGoBack()) webView.goBack() else super.onBackPressed()
    }

    // ---- UI -----------------------------------------------------------------------------------

    private fun buildLayout(): View {
        val pad = (12 * resources.displayMetrics.density).toInt()
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setBackgroundColor(Color.rgb(12, 10, 24))
        }
        val bar = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            setPadding(pad, pad / 2, pad, pad / 2)
        }
        val texts = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        texts.addView(TextView(this).apply {
            text = getString(R.string.bar_title)
            setTextColor(Color.rgb(255, 214, 102))
            textSize = 15f
        })
        statusText = TextView(this).apply {
            setTextColor(Color.rgb(200, 200, 220))
            textSize = 12f
        }
        texts.addView(statusText)
        bar.addView(texts, LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
        toggle = Switch(this).apply {
            text = getString(R.string.toggle_label)
            setTextColor(Color.WHITE)
            contentDescription = getString(R.string.toggle_description)
            setOnCheckedChangeListener { _, on -> if (!updatingToggle) onToggle(on) }
        }
        bar.addView(toggle)
        bar.addView(Button(this).apply {
            text = getString(R.string.settings_button)
            contentDescription = getString(R.string.settings_title)
            setOnClickListener { showSettings() }
        })
        root.addView(bar, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT))
        webView = WebView(this)
        root.addView(webView, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f))
        return root
    }

    private fun renderStatus(status: AdvertisingStatus) {
        statusText.text = when (status) {
            AdvertisingStatus.Off -> getString(R.string.status_off)
            AdvertisingStatus.Starting -> getString(R.string.status_starting)
            is AdvertisingStatus.Advertising -> getString(R.string.status_advertising, status.name, status.clients)
            is AdvertisingStatus.Failed -> getString(R.string.status_failed, status.reason)
        }
        val on = status is AdvertisingStatus.Advertising || status is AdvertisingStatus.Starting
        if (toggle.isChecked != on) {
            updatingToggle = true
            toggle.isChecked = on
            updatingToggle = false
        }
    }

    // ---- WebView ------------------------------------------------------------------------------

    @SuppressLint("SetJavaScriptEnabled", "JavascriptInterface")
    private fun configureWebView() {
        webView.settings.apply {
            javaScriptEnabled = true
            domStorageEnabled = true // Spark Beasts keeps the beast in localStorage
            mediaPlaybackRequiresUserGesture = true
            mixedContentMode = WebSettings.MIXED_CONTENT_NEVER_ALLOW
            allowFileAccess = false
            allowContentAccess = false
        }
        webView.addJavascriptInterface(BeastBridge { isTrustedPage() }, "BeastBoxNative")
        webView.webChromeClient = WebChromeClient()
        webView.webViewClient = object : WebViewClient() {
            override fun shouldOverrideUrlLoading(view: WebView, request: WebResourceRequest): Boolean {
                val url = request.url
                // http(s) (including Vercel SSO hops) stays in the WebView; other schemes go to the OS.
                if (url.scheme == "https" || url.scheme == "http") return false
                runCatching { startActivity(Intent(Intent.ACTION_VIEW, url)) }
                return true
            }

            override fun onPageStarted(view: WebView, url: String?, favicon: android.graphics.Bitmap?) {
                currentOrigin = BeastSettings.originOf(url)
            }

            override fun doUpdateVisitedHistory(view: WebView, url: String?, isReload: Boolean) {
                currentOrigin = BeastSettings.originOf(url)
            }

            override fun onPageFinished(view: WebView, url: String?) {
                currentOrigin = BeastSettings.originOf(url)
                if (isTrustedPage()) view.evaluateJavascript(bridgeScript, null)
            }
        }
    }

    private val bridgeScript: String by lazy {
        assets.open("beastbox-bridge.js").bufferedReader().use { it.readText() }
    }

    private fun isTrustedPage(): Boolean {
        val allowed = allowedOrigin ?: return false
        return currentOrigin == allowed
    }

    private fun loadConfiguredUrl() {
        val url = settings.startUrl
        allowedOrigin = BeastSettings.originOf(url)
        webView.loadUrl(url)
    }

    private fun deliverToPage(frame: CommandFrame, source: String) {
        if (!isTrustedPage()) return
        val js = "window.__beastBoxDevice&&window.__beastBoxDevice.receive(" +
            JSONObject.quote(BeastBridge.commandJson(frame, source)) + ")"
        webView.evaluateJavascript(js, null)
        Toast.makeText(this, getString(R.string.toast_command, frame.command.word, source), Toast.LENGTH_SHORT).show()
    }

    // ---- toggle + permissions -----------------------------------------------------------------

    private fun onToggle(on: Boolean) {
        if (!on) {
            BeastBleService.stop(this)
            return
        }
        val toAsk = BlePermissions.missing(this) +
            BlePermissions.optional().filter { checkSelfPermission(it) != PackageManager.PERMISSION_GRANTED }
        if (toAsk.isNotEmpty()) {
            requestPermissions(toAsk.toTypedArray(), REQ_PERMISSIONS)
            return
        }
        startAdvertisingIfReady()
    }

    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode != REQ_PERMISSIONS) return
        if (BlePermissions.granted(this)) startAdvertisingIfReady()
        else {
            renderStatus(AdvertisingStatus.Failed(getString(R.string.permissions_denied)))
        }
    }

    @SuppressLint("MissingPermission") // BLUETOOTH_CONNECT is verified by BlePermissions.granted() first
    private fun startAdvertisingIfReady() {
        if (!BlePermissions.granted(this)) return
        val adapter = getSystemService(BluetoothManager::class.java)?.adapter
        if (adapter == null) {
            renderStatus(AdvertisingStatus.Failed(getString(R.string.no_bluetooth)))
            return
        }
        if (!adapter.isEnabled) {
            @Suppress("DEPRECATION")
            startActivityForResult(Intent(BluetoothAdapter.ACTION_REQUEST_ENABLE), REQ_ENABLE_BT)
            return
        }
        BeastBleService.start(this)
    }

    @Suppress("OVERRIDE_DEPRECATION", "DEPRECATION")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode != REQ_ENABLE_BT) return
        if (resultCode == RESULT_OK) startAdvertisingIfReady()
        else renderStatus(AdvertisingStatus.Failed(getString(R.string.bluetooth_off)))
    }

    // ---- settings -----------------------------------------------------------------------------

    private fun showSettings() {
        val pad = (16 * resources.displayMetrics.density).toInt()
        val box = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(pad, pad / 2, pad, 0)
        }
        val group = RadioGroup(this)
        val ids = HashMap<Int, WebTarget>()
        WebTarget.entries.forEach { target ->
            val rb = RadioButton(this).apply {
                id = View.generateViewId()
                text = target.label
            }
            ids[rb.id] = target
            group.addView(rb)
            if (target == settings.target) rb.isChecked = true
        }
        box.addView(group)
        val custom = EditText(this).apply {
            hint = getString(R.string.custom_url_hint)
            inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_URI
            setText(settings.customUrl)
        }
        box.addView(custom)
        box.addView(TextView(this).apply {
            text = getString(R.string.sso_note)
            textSize = 12f
        })
        val rename = CheckBox(this).apply {
            text = getString(R.string.rename_label)
            isChecked = settings.renameAdapter
        }
        box.addView(rename)
        AlertDialog.Builder(this)
            .setTitle(R.string.settings_title)
            .setView(box)
            .setPositiveButton(R.string.save) { _, _ ->
                val target = ids[group.checkedRadioButtonId] ?: WebTarget.SPARK_BEASTS
                val customUrl = custom.text.toString().trim()
                if (target == WebTarget.CUSTOM && !BeastSettings.isAllowedUrl(customUrl)) {
                    Toast.makeText(this, R.string.custom_url_invalid, Toast.LENGTH_LONG).show()
                    return@setPositiveButton
                }
                settings.target = target
                settings.customUrl = customUrl
                settings.renameAdapter = rename.isChecked
                loadConfiguredUrl()
            }
            .setNeutralButton(R.string.open_in_browser) { _, _ ->
                runCatching { startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(settings.startUrl))) }
            }
            .setNegativeButton(android.R.string.cancel, null)
            .show()
    }

    companion object {
        private const val REQ_PERMISSIONS = 41
        private const val REQ_ENABLE_BT = 42
    }
}
