package com.meta.wearable.dat.externalsampleapps.cameraaccess

import android.util.Log
import java.net.HttpURLConnection
import java.net.URL
import java.net.URLEncoder
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.TimeoutCancellationException
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject

/** LAN command client for the hackathon. The sample owns SDK permissions and video recording. */
class DemoBackend(
    private val baseUrl: String,
    private val token: String,
    private val execute: suspend (JSONObject) -> JSONObject,
) {
  private val completed = LinkedHashMap<String, JSONObject>()

  fun start(scope: CoroutineScope) = scope.launch {
    while (isActive) {
      try {
        val command = exchange("/commands").optJSONObject("command")
        if (command != null) {
          val id = command.getString("id")
          if (command.getDouble("expires_at") * 1000 > System.currentTimeMillis()) {
            val result = completed[id] ?: try {
              execute(command)
            } catch (timeout: TimeoutCancellationException) {
              JSONObject().put("state", "error").put("error", "Recording operation timed out")
            } catch (cancelled: CancellationException) {
              throw cancelled
            } catch (error: Exception) {
              JSONObject().put("state", "error").put("error", error.message ?: "Recording failed")
            }
            result.put("id", id).put("recording_id", command.getString("recording_id"))
            // Cache BEFORE transmitting: a lost ack must not repeat the hardware action.
            completed[id] = result
            if (completed.size > 100) completed.remove(completed.keys.first())
            exchange("/commands/ack", result)
          }
        }
      } catch (cancelled: CancellationException) {
        throw cancelled
      } catch (error: Exception) {
        Log.w("HackMIT", "Backend unavailable: ${error.javaClass.simpleName}")
      }
      delay(250)
    }
  }

  /**
   * Send a finished recording to the backend. Called after the stop is acknowledged, never
   * before: a multi-megabyte upload over a phone link takes far longer than the command's
   * expiry, so blocking the ack on it would fail every clip worth keeping.
   */
  suspend fun upload(bytes: ByteArray, contentType: String, recordingId: String): Boolean =
      withContext(Dispatchers.IO) {
        val query = URLEncoder.encode(recordingId, "UTF-8")
        val url = URL("${baseUrl.trimEnd('/')}/media/upload?recording_id=$query")
        val connection = url.openConnection() as HttpURLConnection
        try {
          connection.connectTimeout = 5000
          connection.readTimeout = 120_000
          connection.requestMethod = "POST"
          connection.doOutput = true
          connection.setFixedLengthStreamingMode(bytes.size)
          connection.setRequestProperty("Authorization", "Bearer $token")
          connection.setRequestProperty("Content-Type", contentType)
          connection.outputStream.use { it.write(bytes) }
          val code = connection.responseCode
          if (code != 200) Log.w("HackMIT", "Media upload rejected: HTTP $code")
          code == 200
        } finally {
          connection.disconnect()
        }
      }

  private suspend fun exchange(path: String, body: JSONObject? = null): JSONObject =
      withContext(Dispatchers.IO) {
        val connection = URL(baseUrl.trimEnd('/') + path).openConnection() as HttpURLConnection
        try {
          connection.connectTimeout = 2000
          connection.readTimeout = 2000
          connection.setRequestProperty("Authorization", "Bearer $token")
          if (body != null) {
            connection.requestMethod = "POST"
            connection.doOutput = true
            connection.setRequestProperty("Content-Type", "application/json")
            connection.outputStream.use { it.write(body.toString().toByteArray(Charsets.UTF_8)) }
          }
          check(connection.responseCode == 200) { "Backend HTTP ${connection.responseCode}" }
          connection.inputStream.bufferedReader().use { JSONObject(it.readText()) }
        } finally {
          connection.disconnect()
        }
      }
}
