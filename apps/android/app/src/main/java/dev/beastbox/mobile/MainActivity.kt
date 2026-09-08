package dev.beastbox.mobile

import android.app.Activity
import android.os.Bundle
import android.text.InputType
import android.view.View
import android.widget.*
import org.json.JSONObject
import java.util.concurrent.Executors

class MainActivity : Activity() {
    private val worker = Executors.newSingleThreadExecutor()
    private var runtime: RuntimeClient? = null
    private lateinit var output: TextView
    private lateinit var prompt: EditText
    private lateinit var model: EditText
    private lateinit var url: EditText
    private lateinit var provider: Spinner
    private val controls = mutableListOf<View>()
    private val kinds = listOf("reference-a", "reference-b", "ollama")

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val layout = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(24, 28, 24, 24)
        }
        val scroll = ScrollView(this).apply { addView(layout) }
        setContentView(scroll)
        fun label(text: String) = TextView(this).apply { this.text = text; layout.addView(this) }
        label("BEAST BOX · 0.6.0 candidate").textSize = 24f
        label("On-device Python runtime · debug signed sideload build").textSize = 14f
        label("Reference A/B are deterministic text fixtures, not language models. Ollama requires an engine and weights running on this Android device. No engine or weights are bundled.")
        provider = Spinner(this).apply {
            adapter = ArrayAdapter(this@MainActivity, android.R.layout.simple_spinner_dropdown_item,
                listOf("Reference A · deterministic fixture", "Reference B · deterministic fixture", "Ollama · loopback only"))
            layout.addView(this)
        }
        model = EditText(this).apply { hint = "Ollama model label"; setSingleLine(); layout.addView(this) }
        url = EditText(this).apply {
            hint = "Loopback URL, no credentials"
            inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_URI
            setSingleLine(); layout.addView(this)
        }
        val prefs = getSharedPreferences("provider", MODE_PRIVATE)
        provider.setSelection(kinds.indexOf(prefs.getString("kind", "reference-a")).coerceAtLeast(0))
        model.setText(prefs.getString("model", "qwen2.5:3b"))
        url.setText(prefs.getString("url", "http://127.0.0.1:11434"))
        fun button(text: String, action: () -> Unit) {
            val button = Button(this).apply { this.text = text; setOnClickListener { action() } }
            controls.add(button); layout.addView(button)
        }
        button("Apply provider / swap model") {
            val kind = kinds[provider.selectedItemPosition]
            val modelText = model.text.toString()
            val urlText = url.text.toString()
            execute {
                val result = requireNotNull(runtime).configure(kind, modelText, urlText)
                val accepted = result.getJSONObject("provider")
                check(prefs.edit().putString("kind", accepted.getString("kind"))
                    .putString("model", accepted.getString("model"))
                    .putString("url", accepted.getString("url")).commit()) { "Could not save provider settings" }
                result
            }
        }
        prompt = EditText(this).apply {
            hint = "Message (retained on this device)"
            minLines = 2
            inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_FLAG_MULTI_LINE
            layout.addView(this)
        }
        button("Send") { val text = prompt.text.toString(); execute { requireNotNull(runtime).send(text) } }
        button("Inspect retained state") { execute { requireNotNull(runtime).inspect() } }
        button("Restart runtime · keep memory") { execute { requireNotNull(runtime).restart() } }
        label("Memory stays in app-private storage across restarts and model changes. Uninstalling or clearing app data removes it. Do not enter passwords or API keys. Remote model URLs are unsupported.")
        output = label("Starting embedded Python…").apply { setTextIsSelectable(true); textSize = 14f }
        execute {
            runtime = RuntimeClient(applicationContext)
            requireNotNull(runtime).configure(prefs.getString("kind", "reference-a")!!,
                prefs.getString("model", "")!!, prefs.getString("url", "")!!)
        }
    }

    private fun execute(action: () -> JSONObject) {
        controls.forEach { it.isEnabled = false }
        output.text = "Working…"
        worker.execute {
            val message = try { action().toString(2) }
            catch (error: Exception) { "Operation failed; no fixture fallback.\n${error.message}" }
            runOnUiThread {
                if (!isDestroyed) {
                    output.text = message
                    controls.forEach { it.isEnabled = true }
                }
            }
        }
    }

    override fun onDestroy() {
        worker.execute { runtime?.close(); runtime = null }
        worker.shutdown()
        super.onDestroy()
    }
}
