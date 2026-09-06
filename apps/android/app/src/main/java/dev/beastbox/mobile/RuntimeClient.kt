package dev.beastbox.mobile

import android.content.Context
import com.chaquo.python.PyObject
import com.chaquo.python.Python
import org.json.JSONObject
import java.io.File

/** Construct and call on one worker thread: Python SQLite connections are thread confined. */
class RuntimeClient(context: Context, directory: String = "beast-runtime") : AutoCloseable {
    private val bridge: PyObject = Python.getInstance().getModule("beast_android")
        .callAttr("AndroidRuntime", File(context.filesDir, directory).absolutePath)

    fun inspect(): JSONObject = decode(bridge.callAttr("inspect"))
    fun send(text: String): JSONObject = decode(bridge.callAttr("send", text))
    fun configure(kind: String, model: String, url: String): JSONObject =
        decode(bridge.callAttr("configure", kind, model, url))
    fun restart(): JSONObject = decode(bridge.callAttr("restart"))
    override fun close() { bridge.callAttr("close") }
    private fun decode(value: PyObject): JSONObject = JSONObject(value.toString())
}
