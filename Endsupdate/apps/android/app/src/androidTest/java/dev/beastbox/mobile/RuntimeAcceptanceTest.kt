package dev.beastbox.mobile

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.FixMethodOrder
import org.junit.Test
import org.junit.runner.RunWith
import org.junit.runners.MethodSorters
import java.io.File

/** CI invokes each phase in a separate instrumentation process, retaining app data. */
@RunWith(AndroidJUnit4::class)
@FixMethodOrder(MethodSorters.NAME_ASCENDING)
class RuntimeAcceptanceTest {
    private val context = InstrumentationRegistry.getInstrumentation().targetContext
    private val directory = "acceptance-runtime"
    private fun receipt(phase: Int) = File(context.filesDir, "android-phase-$phase.json")
    private fun inspection(value: JSONObject) = value.getJSONObject("inspection")
    private fun save(phase: Int, result: JSONObject) {
        result.put("phase", phase).put("pid", android.os.Process.myPid())
        receipt(phase).writeText(result.toString(2))
    }
    private fun prior(phase: Int) = JSONObject(receipt(phase).readText())
    private fun assertRetained(expected: JSONObject, actual: JSONObject) {
        for (key in listOf("system_id", "checkpoint_sha256", "memory_digest", "state_sha256", "ledger_head", "turn")) {
            assertEquals(key, expected.get(key), actual.get(key))
        }
        assertTrue(actual.getBoolean("valid"))
    }
    private fun assertRecall(result: JSONObject, fixture: String, turn: Int) {
        assertTrue(result.getString("response").contains("deterministic fixture $fixture"))
        assertEquals(turn, inspection(result).getInt("turn"))
        val hits = result.getJSONArray("memory_hits")
        assertTrue((0 until hits.length()).any { hits.getJSONObject(it).getString("text").contains("cobalt lighthouse") })
    }

    @Test fun phase1InitializeAndWriteA() {
        File(context.filesDir, directory).deleteRecursively()
        (1..3).forEach { receipt(it).delete() }
        RuntimeClient(context, directory).use { runtime ->
            assertEquals(0, inspection(runtime.inspect()).getInt("turn"))
            val result = runtime.send("Remember the cobalt lighthouse")
            assertTrue(result.getString("response").contains("deterministic fixture A"))
            assertEquals(1, inspection(result).getInt("turn"))
            assertTrue(File(context.filesDir, "$directory/runtime.sqlite3").isFile)
            save(1, result)
        }
    }

    @Test fun phase2ReopenAndWriteB() {
        RuntimeClient(context, directory).use { runtime ->
            val before = inspection(prior(1))
            assertRetained(before, inspection(runtime.inspect()))
            assertRetained(before, inspection(runtime.configure("reference-b", "", "")))
            val result = runtime.send("Recall the cobalt lighthouse")
            assertRecall(result, "B", 2)
            assertEquals(before.getString("system_id"), inspection(result).getString("system_id"))
            assertRetained(inspection(result), inspection(runtime.restart()))
            save(2, result)
        }
    }

    @Test fun phase3ReopenAndWriteA() {
        RuntimeClient(context, directory).use { runtime ->
            val before = inspection(prior(2))
            assertRetained(before, inspection(runtime.inspect()))
            assertRetained(before, inspection(runtime.configure("reference-a", "", "")))
            val result = runtime.send("Recall the cobalt lighthouse again")
            assertRecall(result, "A", 3)
            assertEquals(inspection(prior(1)).getString("system_id"), inspection(result).getString("system_id"))
            for (url in listOf("https://example.com", "http://user:secret@localhost:11434", "http://10.0.2.2:11434")) {
                var rejected = false
                try { runtime.configure("ollama", "qwen2.5:3b", url) }
                catch (_: Exception) { rejected = true }
                assertTrue("Provider URL must fail closed", rejected)
                assertRetained(inspection(result), inspection(runtime.inspect()))
            }
            save(3, result)
        }
    }
}
