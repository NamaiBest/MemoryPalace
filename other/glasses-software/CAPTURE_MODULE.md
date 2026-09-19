# The capture-trigger module: real API, verified against Meta's own sample code

Everything below is pulled from Meta's actual `CameraAccess` sample
([facebook/meta-wearables-dat-android](https://github.com/facebook/meta-wearables-dat-android)),
not guessed. Two things changed from the earlier design once I read the real SDK:
**photo burst replaces video as the primary capture**, and the app is **React Native
with one small native module**, not pure Kotlin or pure RN.

---

## 1. It's a start/stop pair over a live stream, not a "record(30)" call

The real API (`Session` → `Camera` → `Stream`):

```kotlin
val session = Wearables.createSession(AutoDeviceSelector()).getOrElse { error ->
    throw IllegalStateException(error.description)
}
session.start()

val camera = session.addCamera(
    StreamConfiguration(videoQuality = VideoQuality.MEDIUM, frameRate = 24)
).getOrElse { error -> throw IllegalStateException(error.description) }

camera.stream.start()
```

`StreamState` transitions `STOPPED → STARTING → STARTED → STREAMING → STOPPING →
STOPPED → CLOSED`. There is no single call that means "record for 30 seconds" - you
start the stream, do something with frames while `STREAMING`, then stop it yourself.

## 2. Photo burst, not video - and this is a real change from the earlier plan

The SDK exposes a second, much simpler primitive sitting right next to video:

```kotlin
camera.stream.capturePhoto()
    .onSuccess { photoData -> savePhoto(photoData.data) }
    .onFailure { error, _ -> showCaptureError(error.description) }
```

Full video recording (Meta's `VideoRecorder.kt`) means muxing raw HEVC frames to MP4,
handling audio/video sync with a watchdog, and managing a `MediaMuxer` - real
complexity, verified by reading their actual recorder class. `capturePhoto()` is one
call, one result, one file.

**Use `capturePhoto()` in a loop for the 30-second capture** - one still every ~2-3
seconds, the same idea as SenseCam (the dementia-care research this whole feature is
modeled on, which never recorded video either). Simpler code, less to debug in 36
hours, and closer to the evidence base you're already citing. Video stays a stretch
goal, not the baseline.

## 3. This is what actually makes capture-forward work, mechanically

Earlier docs argued "capture-forward avoids the battery cost of continuous recording"
without saying *how* that maps onto Meta's API. Now it's concrete, and it's a two-tier
lifecycle:

| Tier | Cost | When |
|---|---|---|
| `DeviceSession` | Cheap - a connection, comparable to any BLE link | **Held open the whole time the wearer has the app running** |
| `Camera` + `Stream` | The actual camera/radio cost | **Opened only when a spike fires, closed right after** |

```
app launch:  session.start()                       <- stays open
   ...
spike fires: camera = session.addCamera(...)        <- camera turns on HERE
             camera.stream.start()
             wait for StreamState.STREAMING
             loop capturePhoto() every ~2.5s for 30s
             camera.stop()                           <- camera turns off HERE
   ...
app running, camera off, waiting for the next spike
```

The session-level connection is the thing you can leave alive; the camera is the thing
you must not.

## 4. There is real startup latency - budget for it, don't fight it

`STARTING → STREAMING` is a real transition, not instantaneous - it involves the
Bluetooth/radio handshake with actual hardware. Meta's own sample additionally waits up
to 500 ms just for the first video keyframe once streaming begins
(`KEYFRAME_WAIT_MAX_MS`). Nobody has published an exact number for glasses hardware
because it depends on radio conditions, so **measure it on the real device the first
day you have hardware access** - do not assume it is instant.

This is not a new problem, it is the same one already solved: the confusion-detector's
persistence filter already spends ~15 s deciding whether to fire before it does
anything. A camera-startup delay of even a couple of seconds disappears inside a budget
that size. Capture-forward was always going to eat some latency; this is just where a
slice of it goes.

## 5. React Native + one native module, not a single native Kotlin app

This is the fork from last time, now resolved with evidence rather than a coin flip.

**Crown's official SDK is JavaScript** - Web, React Native, Node.js (planned). There is
**no documented raw BLE GATT protocol** for Crown; I searched specifically for it and
found nothing public. Reverse-engineering an undocumented protocol under hackathon time
pressure is a bad bet.

**Meta's DAT SDK is native-only** - Kotlin for Android, Swift for iOS, no official JS
binding. A community Expo/RN wrapper exists
([circus-kitchens/expo-meta-wearables-dat](https://github.com/circus-kitchens/expo-meta-wearables-dat))
but is **iOS-only today**; Android support is described by its own author as "around
the corner," i.e. not shipped.

So on Android specifically, neither pure path is available: you cannot talk to Crown
without JS, and you cannot talk to Meta's SDK without native code. The one architecture
that actually works today:

```
React Native app
  |
  |-- JS: Neurosity SDK -> Crown BLE -> features -> N400/LOAD detector
  |        (this is most of the app, and it is all JS - officially supported)
  |
  '-- on spike: call a small custom Native Module (Kotlin)
                 -> Session / Camera / Stream / capturePhoto()
                 -> returns file paths as a Promise
```

The native module is small on purpose: it does exactly the lifecycle in §3, nothing
else. Everything else - BLE ingest, filtering, the detector, calibration UI - stays in
JS where Crown's own SDK already lives.

## 6. Native module skeleton (Kotlin side, callable from JS)

Design-level skeleton, not a tested build - it needs Meta's SDK dependency and a real
Android project to compile, which is outside what this sandbox can run. Validate it
against Meta's **Mock Device Kit** in Android Studio before touching real glasses.

```kotlin
class SpikeCaptureModule(reactContext: ReactApplicationContext) :
    ReactContextBaseJavaModule(reactContext) {

  override fun getName() = "SpikeCapture"

  private var session: DeviceSession? = null

  @ReactMethod
  fun connect(promise: Promise) {
    session = Wearables.createSession(AutoDeviceSelector()).getOrElse {
      return promise.reject("CONNECT_FAILED", it.description)
    }
    session!!.start()
    promise.resolve(true)
  }

  // Called from JS the instant the detector fires. captureSeconds comes from the same
  // SpikeEvent shape used in contract.py, so the JS and Kotlin sides agree on shape.
  @ReactMethod
  fun captureOnSpike(captureSeconds: Double, promise: Promise) {
    val s = session ?: return promise.reject("NOT_CONNECTED", "call connect() first")
    val camera = s.addCamera(StreamConfiguration(VideoQuality.MEDIUM, frameRate = 24))
        .getOrElse { return promise.reject("CAMERA_FAILED", it.description) }

    camera.stream.start()
    // production: await StreamState.STREAMING via the state Flow before capturing,
    // with a timeout - do not sleep a fixed guess.

    val paths = Arguments.createArray()
    val shots = (captureSeconds / 2.5).toInt().coerceAtLeast(1)
    repeat(shots) {
      camera.stream.capturePhoto().onSuccess { photo ->
        paths.pushString(saveToDisk(photo.data))
      }
      Thread.sleep(2500)   // production: coroutine delay, not a blocking sleep
    }

    camera.stop()
    val result = Arguments.createMap().apply {
      putBoolean("ok", true)
      putArray("media_paths", paths)
    }
    promise.resolve(result)
  }
}
```

The JS side calls this the moment its own detector (running against the Crown stream)
crosses threshold - no HTTP hop, no second process, because both halves now live in the
same React Native app.

## 7. What changes in this repo

`src/glasses/meta_dat.py`'s HTTP-bridge design assumed a *separate* phone app the
Python side talks to over the network. That was written before the real API was known.
With Crown ingest and the DAT trigger now living in the *same* React Native app, the
Python bridge in this folder becomes what it always should have been: **the contract
definition and a way to test the event flow before the RN app exists**, not part of the
shipped architecture. Keep it for that - `contract.py`'s `SpikeEvent` JSON shape is
exactly what `captureOnSpike` should mirror on the Kotlin/JS side.
