  // Injected by prepare.py into the pinned CameraAccess sample.
  // Session connection, camera permission and preview are started explicitly in the phone UI.
  // Backend commands record video-only, using the sample's actual HEVC-to-MP4 writer.
  private var demoRecordingId: String? = null
  private var demoSavedUri: String? = null
  // demoBackend is declared ahead of init by prepare.py: this fragment is injected below
  // init, and Kotlin will not let init assign a property declared later in the class.

  /**
   * Send the finished MP4 to the backend so it can reach the web UI. The phone only reports a
   * content:// URI, which nothing off the device can resolve, so the bytes have to travel.
   * Fired without blocking the command result: the ack must land well inside the command's
   * expiry, and a multi-megabyte upload will not.
   */
  private fun uploadDemoMedia(uri: android.net.Uri, recordingId: String) {
    val backend = demoBackend ?: return
    viewModelScope.launch(kotlinx.coroutines.Dispatchers.IO) {
      try {
        val resolver = getApplication<android.app.Application>().contentResolver
        val bytes = resolver.openInputStream(uri)?.use { it.readBytes() }
        if (bytes == null || bytes.isEmpty()) {
          Log.w(TAG, "Nothing to upload for $recordingId")
          return@launch
        }
        val type = resolver.getType(uri) ?: "video/mp4"
        val sent = backend.upload(bytes, type, recordingId)
        Log.i(TAG, "Media upload for $recordingId: ${if (sent) "ok" else "failed"} (${bytes.size} bytes)")
      } catch (cancelled: kotlinx.coroutines.CancellationException) {
        throw cancelled
      } catch (error: Exception) {
        Log.w(TAG, "Media upload failed: ${error.message}")
      }
    }
  }

  private suspend fun executeDemoCommand(command: org.json.JSONObject): org.json.JSONObject {
    val id = command.getString("recording_id")
    return when (command.getString("action")) {
      "start" -> {
        check(_uiState.value.isStreaming) { "Start the camera preview on the phone first" }
        check(!videoRecorder.isRecording.value) { "A recording is already running" }
        demoRecordingId = id
        demoSavedUri = null
        // Audio on: the captured clip is intended for transcription later, and a
        // video-only file cannot be transcribed after the fact. Needs RECORD_AUDIO
        // granted, otherwise the recorder falls back to video-only on its own.
        _uiState.update { it.copy(activePreview = null, includeAudioInStream = true) }
        videoRecorder.setIncludeAudio(true)
        try {
          videoRecorder.startRecording(csdCollector.complete())
          kotlinx.coroutines.withTimeout(5000) {
            videoRecorder.hasStartedWriting.first { it }
          }
          check(videoRecorder.isRecording.value) { "Recording stopped during startup" }
          org.json.JSONObject().put("state", "recording")
        } catch (error: Exception) {
          // This also runs on timeout: do not leave a failed start recording indefinitely.
          kotlinx.coroutines.withContext(kotlinx.coroutines.NonCancellable) {
            videoRecorder.stopRecording()
            stopStreaming()
          }
          throw error
        }
      }
      "stop" -> {
        // Only guard the id while a clip is actually open; the point is to avoid stopping
        // someone else's recording. With nothing running a stop is a harmless no-op, and
        // enforcing it there deadlocks: a refused start leaves demoRecordingId holding an
        // older clip's id, so every later stop mismatches and the recorder is stuck in
        // "error" with no way back short of restarting the app.
        if (videoRecorder.isRecording.value) {
          check(demoRecordingId == null || demoRecordingId == id) { "Recording ID mismatch" }
          when (val result = videoRecorder.stopRecording()) {
            is RecordingResult.Completed -> {
              demoSavedUri = result.uri.toString()
              // Deliberately not setting activePreview: that opens a review sheet over
              // the live view, which is noise when captures are driven remotely.
              uploadDemoMedia(result.uri, id)
            }
            else -> {
              stopStreaming()
              error("Recording stopped, but no completed MP4 was returned")
            }
          }
        }
        // The stream stays up on purpose. Tearing it down here is what made every
        // completed clip disable the next one: isStreaming would be false, so the
        // following start was refused with "start the camera preview first" until a
        // human re-tapped Preview. Leaving it running makes repeated captures
        // hands-free, at the cost of the camera staying powered between clips — an
        // acceptable trade for a demo, and worth revisiting for all-day wear.
        org.json.JSONObject().put("state", "stopped")
            .put("media_path", demoSavedUri ?: org.json.JSONObject.NULL)
      }
      else -> error("Unsupported command")
    }
  }

