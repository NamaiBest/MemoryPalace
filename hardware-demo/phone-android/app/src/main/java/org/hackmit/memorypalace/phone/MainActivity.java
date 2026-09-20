package org.hackmit.memorypalace.phone;

import android.Manifest;
import android.app.Activity;
import android.content.Context;
import android.content.pm.PackageManager;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.LinearGradient;
import android.graphics.Paint;
import android.graphics.RadialGradient;
import android.graphics.Shader;
import android.graphics.SurfaceTexture;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.graphics.drawable.RippleDrawable;
import android.hardware.camera2.CameraCaptureSession;
import android.hardware.camera2.CameraCharacteristics;
import android.hardware.camera2.CameraDevice;
import android.hardware.camera2.CameraManager;
import android.hardware.camera2.CaptureRequest;
import android.hardware.camera2.params.StreamConfigurationMap;
import android.media.MediaRecorder;
import android.os.Bundle;
import android.os.Handler;
import android.os.HandlerThread;
import android.util.Log;
import android.util.Size;
import android.view.Gravity;
import android.view.Surface;
import android.view.TextureView;
import android.view.View;
import android.view.ViewGroup;
import android.view.Window;
import android.view.WindowInsets;
import android.widget.FrameLayout;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.Space;
import android.widget.TextView;

import org.json.JSONObject;

import java.io.BufferedInputStream;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicReference;

/**
 * Standalone phone-camera recorder for the MemoryPalace LAN protocol.
 *
 * Pairing starts backend polling only. A start command opens the phone's rear camera;
 * stop finalizes the clip, releases the camera, acknowledges the action, and uploads the
 * MP4. It deliberately has no Meta Wearables SDK dependency.
 */
public final class MainActivity extends Activity {
  private static final String TAG = "MemoryPalacePhone";
  private static final int PERMISSIONS_REQUEST = 10;

  private TextureView preview;
  private TextView stateText;
  private LinearLayout statusPanel;
  private LinearLayout pairingPanel;
  private Button pairButton;
  private TextView pairingStatus;
  private View idleMessage;
  private final Handler uiHandler = new Handler(android.os.Looper.getMainLooper());
  private boolean pairingStarted;
  private PhoneCamera camera;
  private BackendClient backend;

  @Override
  protected void onCreate(Bundle savedInstanceState) {
    super.onCreate(savedInstanceState);
    configureSystemUi();

    FrameLayout root = new FrameLayout(this);
    root.addView(new AmbientBackdrop(this), new FrameLayout.LayoutParams(
        ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
    preview = new TextureView(this);
    preview.setAlpha(0f);
    root.addView(preview, new FrameLayout.LayoutParams(
        ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));

    LinearLayout idle = new LinearLayout(this);
    idle.setOrientation(LinearLayout.VERTICAL);
    idle.setGravity(Gravity.CENTER);
    idle.setPadding(dp(36), dp(96), dp(36), dp(150));
    TextView readyPill = label("SESSION READY", 11, 0xff91a0ff, Typeface.BOLD);
    readyPill.setGravity(Gravity.CENTER);
    readyPill.setLetterSpacing(0.16f);
    readyPill.setPadding(dp(16), dp(8), dp(16), dp(8));
    readyPill.setBackground(rounded(0x1f9fa8ff, dp(99), 0x309fa8ff, 1));
    idle.addView(readyPill, wrapCentered());
    TextView idleTitle = label("Ready when you are.", 32, Color.WHITE, Typeface.NORMAL);
    idleTitle.setTypeface(Typeface.create("sans-serif", Typeface.NORMAL));
    idleTitle.setGravity(Gravity.CENTER);
    LinearLayout.LayoutParams idleTitleParams = wrapCentered();
    idleTitleParams.topMargin = dp(22);
    idle.addView(idleTitle, idleTitleParams);
    TextView idleCopy = label(
        "Trigger a moment from the dashboard.\nYour camera stays off until capture begins.",
        16, 0xffaeb5c5, Typeface.NORMAL);
    idleCopy.setGravity(Gravity.CENTER);
    idleCopy.setLineSpacing(0, 1.18f);
    LinearLayout.LayoutParams idleCopyParams = wrapCentered();
    idleCopyParams.topMargin = dp(14);
    idle.addView(idleCopy, idleCopyParams);
    idleMessage = idle;
    idleMessage.setVisibility(View.GONE);
    root.addView(idleMessage, new FrameLayout.LayoutParams(
        ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));

    statusPanel = new LinearLayout(this);
    statusPanel.setOrientation(LinearLayout.VERTICAL);
    statusPanel.setPadding(dp(20), dp(17), dp(20), dp(17));
    statusPanel.setBackground(rounded(0xe61a1d29, dp(24), 0x337f8ca8, 1));
    statusPanel.setVisibility(android.view.View.GONE);
    TextView sessionEyebrow = label("MEMORYPALACE  •  META DEMO", 10, 0xff8d96aa, Typeface.BOLD);
    sessionEyebrow.setLetterSpacing(0.14f);
    statusPanel.addView(sessionEyebrow);
    stateText = label("Connecting…", 15, 0xfff5f7ff, Typeface.BOLD);
    stateText.setPadding(0, dp(7), 0, 0);
    statusPanel.addView(stateText);
    FrameLayout.LayoutParams panelParams = new FrameLayout.LayoutParams(
        ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT, Gravity.BOTTOM);
    panelParams.setMargins(dp(18), dp(18), dp(18), dp(24));
    root.addView(statusPanel, panelParams);

    pairingPanel = new LinearLayout(this);
    pairingPanel.setOrientation(LinearLayout.VERTICAL);
    pairingPanel.setGravity(Gravity.CENTER_HORIZONTAL);
    pairingPanel.setPadding(dp(24), dp(42), dp(24), dp(28));

    LinearLayout brandRow = new LinearLayout(this);
    brandRow.setGravity(Gravity.CENTER_VERTICAL);
    TextView mark = label("∞", 25, 0xff7892ff, Typeface.BOLD);
    brandRow.addView(mark, new LinearLayout.LayoutParams(dp(35), dp(40)));
    TextView brand = label("MemoryPalace", 17, Color.WHITE, Typeface.BOLD);
    brandRow.addView(brand);
    Space topSpacer = new Space(this);
    brandRow.addView(topSpacer, new LinearLayout.LayoutParams(0, 1, 1));
    TextView demoPill = label("DEMO", 10, 0xffc8ceff, Typeface.BOLD);
    demoPill.setLetterSpacing(0.14f);
    demoPill.setPadding(dp(12), dp(7), dp(12), dp(7));
    demoPill.setBackground(rounded(0x1f9fa8ff, dp(99), 0x2f9fa8ff, 1));
    brandRow.addView(demoPill);
    pairingPanel.addView(brandRow, new LinearLayout.LayoutParams(
        ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));

    Space flexibleTop = new Space(this);
    pairingPanel.addView(flexibleTop, new LinearLayout.LayoutParams(1, 0, 0.45f));

    LinearLayout heroCard = new LinearLayout(this);
    heroCard.setOrientation(LinearLayout.VERTICAL);
    heroCard.setGravity(Gravity.CENTER_HORIZONTAL);
    heroCard.setPadding(dp(24), dp(28), dp(24), dp(28));
    heroCard.setBackground(rounded(0xd91a1c29, dp(30), 0x337b849d, 1));

    GlassesGlyph glasses = new GlassesGlyph(this);
    heroCard.addView(glasses, new LinearLayout.LayoutParams(dp(230), dp(112)));

    TextView eyebrow = label("META WEARABLES", 11, 0xff91a0ff, Typeface.BOLD);
    eyebrow.setLetterSpacing(0.18f);
    LinearLayout.LayoutParams eyebrowParams = wrapCentered();
    eyebrowParams.topMargin = dp(10);
    heroCard.addView(eyebrow, eyebrowParams);

    TextView pairingTitle = label("See it. Save it.\nRevisit it.", 36, Color.WHITE, Typeface.NORMAL);
    pairingTitle.setTypeface(Typeface.create("sans-serif", Typeface.NORMAL));
    pairingTitle.setGravity(Gravity.CENTER);
    pairingTitle.setLineSpacing(0, 0.94f);
    LinearLayout.LayoutParams titleParams = wrapCentered();
    titleParams.topMargin = dp(14);
    heroCard.addView(pairingTitle, titleParams);

    TextView pairingCopy = label(
        "Pair your glasses to begin a private memory session.\nFor this demo, your phone becomes the camera.",
        15, 0xffb7becd, Typeface.NORMAL);
    pairingCopy.setGravity(Gravity.CENTER);
    pairingCopy.setLineSpacing(0, 1.18f);
    LinearLayout.LayoutParams copyParams = wrapCentered();
    copyParams.topMargin = dp(16);
    heroCard.addView(pairingCopy, copyParams);

    pairingPanel.addView(heroCard, new LinearLayout.LayoutParams(
        ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));

    Space flexibleBottom = new Space(this);
    pairingPanel.addView(flexibleBottom, new LinearLayout.LayoutParams(1, 0, 0.36f));

    pairButton = new Button(this);
    pairButton.setText("Pair Meta glasses   →");
    pairButton.setTextColor(Color.WHITE);
    pairButton.setTextSize(16);
    pairButton.setTypeface(Typeface.create("sans-serif-medium", Typeface.NORMAL));
    pairButton.setAllCaps(false);
    pairButton.setGravity(Gravity.CENTER);
    pairButton.setPadding(dp(18), 0, dp(18), 0);
    pairButton.setBackground(primaryButtonBackground());
    pairButton.setStateListAnimator(null);
    pairButton.setOnClickListener(view -> beginPairing());

    pairingStatus = label("Camera stays off until a moment begins", 12, 0xff8f98aa, Typeface.NORMAL);
    pairingStatus.setGravity(Gravity.CENTER);
    LinearLayout.LayoutParams buttonParams = new LinearLayout.LayoutParams(
        ViewGroup.LayoutParams.MATCH_PARENT, dp(60));
    pairingPanel.addView(pairButton, buttonParams);
    LinearLayout.LayoutParams statusParams = wrapCentered();
    statusParams.topMargin = dp(14);
    pairingPanel.addView(pairingStatus, statusParams);
    FrameLayout.LayoutParams pairingParams = new FrameLayout.LayoutParams(
        ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT);
    root.addView(pairingPanel, pairingParams);
    root.setOnApplyWindowInsetsListener((view, insets) -> {
      int top = insets.getSystemWindowInsetTop();
      int bottom = insets.getSystemWindowInsetBottom();
      pairingPanel.setPadding(dp(24), dp(22) + top, dp(24), dp(18) + bottom);
      panelParams.bottomMargin = dp(16) + bottom;
      statusPanel.setLayoutParams(panelParams);
      return insets;
    });
    setContentView(root);
  }

  private void configureSystemUi() {
    Window window = getWindow();
    window.setStatusBarColor(Color.TRANSPARENT);
    window.setNavigationBarColor(0xff070910);
    window.getDecorView().setSystemUiVisibility(
        View.SYSTEM_UI_FLAG_LAYOUT_STABLE | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN);
  }

  private int dp(int value) {
    return Math.round(value * getResources().getDisplayMetrics().density);
  }

  private TextView label(String value, float size, int color, int style) {
    TextView view = new TextView(this);
    view.setText(value);
    view.setTextSize(size);
    view.setTextColor(color);
    view.setTypeface(Typeface.create("sans-serif", style));
    return view;
  }

  private LinearLayout.LayoutParams wrapCentered() {
    return new LinearLayout.LayoutParams(
        ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT);
  }

  private GradientDrawable rounded(int color, float radius, int strokeColor, int strokeDp) {
    GradientDrawable drawable = new GradientDrawable();
    drawable.setColor(color);
    drawable.setCornerRadius(radius);
    if (strokeDp > 0) drawable.setStroke(dp(strokeDp), strokeColor);
    return drawable;
  }

  private RippleDrawable primaryButtonBackground() {
    GradientDrawable fill = new GradientDrawable(
        GradientDrawable.Orientation.LEFT_RIGHT,
        new int[] {0xff4969ff, 0xff7658f6});
    fill.setCornerRadius(dp(22));
    return new RippleDrawable(
        android.content.res.ColorStateList.valueOf(0x33ffffff), fill, null);
  }

  private static final class AmbientBackdrop extends View {
    private final Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);

    AmbientBackdrop(Context context) {
      super(context);
      setLayerType(View.LAYER_TYPE_SOFTWARE, null);
    }

    @Override
    protected void onDraw(Canvas canvas) {
      super.onDraw(canvas);
      canvas.drawColor(0xff070910);
      float width = getWidth();
      float height = getHeight();
      paint.setShader(new RadialGradient(width * 0.12f, height * 0.18f, width * 0.78f,
          new int[] {0x553851a4, 0x183851a4, Color.TRANSPARENT},
          new float[] {0f, 0.52f, 1f}, Shader.TileMode.CLAMP));
      canvas.drawCircle(width * 0.12f, height * 0.18f, width * 0.78f, paint);
      paint.setShader(new RadialGradient(width * 0.98f, height * 0.56f, width * 0.62f,
          new int[] {0x334e2e75, 0x124e2e75, Color.TRANSPARENT},
          new float[] {0f, 0.55f, 1f}, Shader.TileMode.CLAMP));
      canvas.drawCircle(width * 0.98f, height * 0.56f, width * 0.62f, paint);
      paint.setShader(null);
    }
  }

  private static final class GlassesGlyph extends View {
    private final Paint glow = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint line = new Paint(Paint.ANTI_ALIAS_FLAG);

    GlassesGlyph(Context context) {
      super(context);
      setLayerType(View.LAYER_TYPE_SOFTWARE, null);
      glow.setStyle(Paint.Style.STROKE);
      glow.setStrokeWidth(18f);
      glow.setColor(0x337c87ff);
      glow.setMaskFilter(new android.graphics.BlurMaskFilter(18f,
          android.graphics.BlurMaskFilter.Blur.NORMAL));
      line.setStyle(Paint.Style.STROKE);
      line.setStrokeWidth(7f);
      line.setStrokeCap(Paint.Cap.ROUND);
    }

    @Override
    protected void onDraw(Canvas canvas) {
      super.onDraw(canvas);
      float w = getWidth();
      float h = getHeight();
      float y = h * 0.56f;
      float lensW = w * 0.32f;
      float lensH = h * 0.46f;
      float left = w * 0.12f;
      float right = w - left - lensW;
      line.setShader(new LinearGradient(0, 0, w, 0,
          new int[] {0xff58a6ff, 0xff8c70ff, 0xffe56ac8}, null, Shader.TileMode.CLAMP));
      canvas.drawRoundRect(left, y - lensH / 2, left + lensW, y + lensH / 2,
          lensH * 0.42f, lensH * 0.42f, glow);
      canvas.drawRoundRect(right, y - lensH / 2, right + lensW, y + lensH / 2,
          lensH * 0.42f, lensH * 0.42f, glow);
      canvas.drawRoundRect(left, y - lensH / 2, left + lensW, y + lensH / 2,
          lensH * 0.42f, lensH * 0.42f, line);
      canvas.drawRoundRect(right, y - lensH / 2, right + lensW, y + lensH / 2,
          lensH * 0.42f, lensH * 0.42f, line);
      canvas.drawLine(left + lensW, y - 3, right, y - 3, line);
      canvas.drawLine(left, y - lensH * 0.28f, w * 0.02f, y - lensH * 0.52f, line);
      canvas.drawLine(right + lensW, y - lensH * 0.28f, w * 0.98f, y - lensH * 0.52f, line);
      line.setShader(null);
    }
  }

  private void beginPairing() {
    if (pairingStarted) return;
    pairingStarted = true;
    pairButton.setEnabled(false);
    pairButton.setAlpha(0.72f);
    pairingStatus.setTextColor(0xffb9c1ff);
    pairingStatus.setText("Searching for nearby Meta glasses…");
    if (hasCameraPermission()) {
      runPairingSequence();
    } else {
      requestPermissions(new String[] {Manifest.permission.CAMERA, Manifest.permission.RECORD_AUDIO},
          PERMISSIONS_REQUEST);
    }
  }

  private void runPairingSequence() {
    pairingStatus.setText("Meta glasses found  •  securing connection");
    uiHandler.postDelayed(() -> pairingStatus.setText("Pairing in demo mode…"), 650);
    uiHandler.postDelayed(() -> pairingStatus.setText("Connected  •  starting your session"), 1300);
    uiHandler.postDelayed(() -> {
      pairingPanel.animate().alpha(0f).setDuration(320).withEndAction(() -> {
        pairingPanel.setVisibility(android.view.View.GONE);
        idleMessage.setVisibility(View.VISIBLE);
        statusPanel.setAlpha(0f);
        statusPanel.setVisibility(android.view.View.VISIBLE);
        statusPanel.animate().alpha(1f).setDuration(260).start();
        showState("Meta glasses paired (demo) · starting session…");
        startRuntime();
      }).start();
    }, 1950);
  }

  @Override
  public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] results) {
    super.onRequestPermissionsResult(requestCode, permissions, results);
    if (requestCode == PERMISSIONS_REQUEST && hasCameraPermission()) {
      runPairingSequence();
    } else if (requestCode == PERMISSIONS_REQUEST) {
      pairingStarted = false;
      pairButton.setEnabled(true);
      pairButton.setAlpha(1f);
      pairingStatus.setTextColor(0xffffa8a8);
      pairingStatus.setText("Camera permission is required for demo capture");
    }
  }

  private boolean hasCameraPermission() {
    return checkSelfPermission(Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED;
  }

  private void startRuntime() {
    if (camera != null) return;
    camera = new PhoneCamera(this, preview, this::showState, visible -> runOnUiThread(() -> {
      preview.setAlpha(visible ? 1f : 0f);
      idleMessage.setVisibility(visible ? android.view.View.GONE : android.view.View.VISIBLE);
    }));
    camera.start();
    backend = new BackendClient(BuildConfig.DEMO_BACKEND_URL, BuildConfig.DEMO_TOKEN,
        camera, this::showState);
    backend.start();
  }

  private void showState(String message) {
    Log.i(TAG, message);
    runOnUiThread(() -> stateText.setText(message + "\nSecure LAN · " + BuildConfig.DEMO_BACKEND_URL));
  }

  @Override
  protected void onDestroy() {
    uiHandler.removeCallbacksAndMessages(null);
    if (backend != null) backend.close();
    if (camera != null) camera.close();
    super.onDestroy();
  }

  private interface StatusSink {
    void set(String message);
  }

  private interface CameraVisibility {
    void set(boolean visible);
  }

  private static final class BackendClient {
    private final String baseUrl;
    private final String token;
    private final PhoneCamera camera;
    private final StatusSink status;
    private final ScheduledExecutorService executor = Executors.newSingleThreadScheduledExecutor();
    private final LinkedHashMap<String, JSONObject> completed = new LinkedHashMap<>();

    BackendClient(String baseUrl, String token, PhoneCamera camera, StatusSink status) {
      this.baseUrl = trimSlash(baseUrl);
      this.token = token;
      this.camera = camera;
      this.status = status;
    }

    void start() {
      status.set("Meta glasses paired (demo) · connecting to server…");
      executor.scheduleWithFixedDelay(this::pollOnce, 0, 250, TimeUnit.MILLISECONDS);
    }

    void close() {
      executor.shutdownNow();
    }

    private void pollOnce() {
      try {
        JSONObject command = request("GET", "/commands", null).optJSONObject("command");
        if (command == null) {
          if (camera.isIdle()) {
            status.set("Session connected · camera off · ready for a moment");
          }
          return;
        }
        String commandId = command.getString("id");
        if (command.getDouble("expires_at") * 1000 <= System.currentTimeMillis()) return;

        boolean newlyExecuted = !completed.containsKey(commandId);
        JSONObject result = completed.get(commandId);
        File media = null;
        if (result == null) {
          try {
            String action = command.getString("action");
            String recordingId = command.getString("recording_id");
            if ("start".equals(action)) {
              status.set("Session active · starting moment capture…");
              camera.startRecording(recordingId);
              result = new JSONObject().put("state", "recording");
              status.set("Session active · recording moment");
            } else if ("stop".equals(action)) {
              status.set("Session active · saving captured moment…");
              media = camera.stopRecording(recordingId);
              result = new JSONObject().put("state", "stopped")
                  .put("media_path", media == null ? JSONObject.NULL : media.getAbsolutePath());
              status.set("Saved locally · acknowledging stop");
            } else {
              throw new IllegalArgumentException("Unsupported action: " + action);
            }
          } catch (Exception error) {
            Log.e(TAG, "Command failed", error);
            result = new JSONObject().put("state", "error")
                .put("error", error.getMessage() == null ? "Recording failed" : error.getMessage());
            status.set("Capture error · " + result.optString("error"));
          }
          result.put("id", commandId)
              .put("recording_id", command.getString("recording_id"));
          completed.put(commandId, result);
          while (completed.size() > 100) completed.remove(completed.keySet().iterator().next());
        }

        request("POST", "/commands/ack", result);
        if (newlyExecuted && media != null && "stopped".equals(result.optString("state"))) {
          status.set("Uploading " + media.getName() + "…");
          upload(media, command.getString("recording_id"));
          status.set("Moment uploaded · camera off · ready for next capture");
        }
      } catch (Exception error) {
        Log.w(TAG, "Backend unavailable: " + error.getClass().getSimpleName());
        status.set("Glasses paired (demo) · waiting for MemoryPalace server");
      }
    }

    private JSONObject request(String method, String path, JSONObject body) throws Exception {
      HttpURLConnection connection = (HttpURLConnection) new URL(baseUrl + path).openConnection();
      try {
        connection.setConnectTimeout(2000);
        connection.setReadTimeout(2000);
        connection.setRequestMethod(method);
        connection.setRequestProperty("Authorization", "Bearer " + token);
        if (body != null) {
          byte[] encoded = body.toString().getBytes(StandardCharsets.UTF_8);
          connection.setDoOutput(true);
          connection.setFixedLengthStreamingMode(encoded.length);
          connection.setRequestProperty("Content-Type", "application/json");
          try (OutputStream output = connection.getOutputStream()) {
            output.write(encoded);
          }
        }
        int code = connection.getResponseCode();
        InputStream stream = code >= 200 && code < 300
            ? connection.getInputStream() : connection.getErrorStream();
        String response = readAll(stream);
        if (code != 200) throw new IllegalStateException("Backend HTTP " + code + ": " + response);
        return new JSONObject(response);
      } finally {
        connection.disconnect();
      }
    }

    private void upload(File media, String recordingId) throws Exception {
      String query = URLEncoder.encode(recordingId, StandardCharsets.UTF_8.name());
      HttpURLConnection connection = (HttpURLConnection) new URL(
          baseUrl + "/media/upload?recording_id=" + query).openConnection();
      try {
        connection.setConnectTimeout(5000);
        connection.setReadTimeout(120_000);
        connection.setRequestMethod("POST");
        connection.setDoOutput(true);
        connection.setFixedLengthStreamingMode(media.length());
        connection.setRequestProperty("Authorization", "Bearer " + token);
        connection.setRequestProperty("Content-Type", "video/mp4");
        try (InputStream input = new BufferedInputStream(new FileInputStream(media));
             OutputStream output = connection.getOutputStream()) {
          byte[] buffer = new byte[1024 * 1024];
          int count;
          while ((count = input.read(buffer)) != -1) output.write(buffer, 0, count);
        }
        if (connection.getResponseCode() != 200) {
          throw new IllegalStateException("Upload HTTP " + connection.getResponseCode());
        }
      } finally {
        connection.disconnect();
      }
    }

    private static String readAll(InputStream stream) throws Exception {
      if (stream == null) return "";
      try (InputStream input = stream; ByteArrayOutputStream output = new ByteArrayOutputStream()) {
        byte[] buffer = new byte[8192];
        int count;
        while ((count = input.read(buffer)) != -1) output.write(buffer, 0, count);
        return output.toString(StandardCharsets.UTF_8.name());
      }
    }

    private static String trimSlash(String value) {
      while (value.endsWith("/")) value = value.substring(0, value.length() - 1);
      return value;
    }
  }

  private static final class PhoneCamera {
    private final Activity activity;
    private final TextureView texture;
    private final StatusSink status;
    private final CameraVisibility visibility;
    private HandlerThread cameraThread;
    private Handler handler;
    private volatile CameraDevice device;
    private CameraCaptureSession session;
    private MediaRecorder recorder;
    private String cameraId;
    private Size videoSize;
    private int sensorOrientation;
    private volatile boolean cameraRequested;
    private volatile boolean closed;
    private volatile boolean recording;
    private String activeRecordingId;
    private File activeFile;

    PhoneCamera(Activity activity, TextureView texture, StatusSink status, CameraVisibility visibility) {
      this.activity = activity;
      this.texture = texture;
      this.status = status;
      this.visibility = visibility;
    }

    boolean isIdle() {
      return !cameraRequested && !recording;
    }

    void start() {
      cameraThread = new HandlerThread("memory-palace-camera");
      cameraThread.start();
      handler = new Handler(cameraThread.getLooper());
      texture.setSurfaceTextureListener(new TextureView.SurfaceTextureListener() {
        @Override public void onSurfaceTextureAvailable(SurfaceTexture surface, int width, int height) {
          // Pairing and surface creation must never activate the camera.
        }
        @Override public void onSurfaceTextureSizeChanged(SurfaceTexture surface, int width, int height) {}
        @Override public boolean onSurfaceTextureDestroyed(SurfaceTexture surface) { return true; }
        @Override public void onSurfaceTextureUpdated(SurfaceTexture surface) {}
      });
    }

    @SuppressWarnings("MissingPermission")
    private void openCamera(CountDownLatch opened, AtomicReference<Exception> failure) {
      handler.post(() -> {
        try {
          if (closed || !cameraRequested) throw new IllegalStateException("Capture cancelled");
          CameraManager manager = (CameraManager) activity.getSystemService(Context.CAMERA_SERVICE);
          for (String id : manager.getCameraIdList()) {
            CameraCharacteristics c = manager.getCameraCharacteristics(id);
            Integer facing = c.get(CameraCharacteristics.LENS_FACING);
            if (facing != null && facing == CameraCharacteristics.LENS_FACING_BACK) {
              cameraId = id;
              sensorOrientation = c.get(CameraCharacteristics.SENSOR_ORIENTATION) == null
                  ? 90 : c.get(CameraCharacteristics.SENSOR_ORIENTATION);
              StreamConfigurationMap map = c.get(CameraCharacteristics.SCALER_STREAM_CONFIGURATION_MAP);
              videoSize = chooseSize(map == null ? null : map.getOutputSizes(MediaRecorder.class));
              break;
            }
          }
          if (cameraId == null) throw new IllegalStateException("No rear camera found");
          manager.openCamera(cameraId, new CameraDevice.StateCallback() {
            @Override public void onOpened(CameraDevice camera) {
              if (closed || !cameraRequested) {
                camera.close();
                failure.set(new IllegalStateException("Capture cancelled"));
                opened.countDown();
                return;
              }
              device = camera;
              opened.countDown();
            }
            @Override public void onDisconnected(CameraDevice camera) {
              camera.close();
              device = null;
              failure.set(new IllegalStateException("Phone camera disconnected"));
              opened.countDown();
              status.set("Phone camera disconnected");
            }
            @Override public void onError(CameraDevice camera, int error) {
              camera.close();
              device = null;
              failure.set(new IllegalStateException("Phone camera error " + error));
              opened.countDown();
              status.set("Phone camera error " + error);
            }
          }, handler);
        } catch (Exception error) {
          failure.set(error);
          opened.countDown();
          Log.e(TAG, "Could not open phone camera", error);
          status.set("Could not open phone camera · " + error.getMessage());
        }
      });
    }

    void startRecording(String recordingId) throws Exception {
      if (recording || cameraRequested) throw new IllegalStateException("A recording is already running");
      if (closed || !texture.isAvailable()) throw new IllegalStateException("Keep the phone app open to capture");
      cameraRequested = true;
      CountDownLatch opened = new CountDownLatch(1);
      AtomicReference<Exception> openFailure = new AtomicReference<>();
      openCamera(opened, openFailure);
      if (!opened.await(8, TimeUnit.SECONDS) || openFailure.get() != null || device == null) {
        cameraRequested = false;
        handler.post(this::abortRecorder);
        throw new IllegalStateException("Could not open phone camera", openFailure.get());
      }
      visibility.set(true);
      CountDownLatch latch = new CountDownLatch(1);
      AtomicReference<Exception> failure = new AtomicReference<>();
      handler.post(() -> {
        try {
          if (closed || !cameraRequested || device == null) throw new IllegalStateException("Capture cancelled");
          closeSession();
          activeRecordingId = recordingId;
          File directory = activity.getExternalFilesDir(android.os.Environment.DIRECTORY_MOVIES);
          if (directory == null) directory = activity.getFilesDir();
          activeFile = new File(directory, "memory-palace-" + recordingId + ".mp4");
          recorder = new MediaRecorder(activity);
          boolean audio = activity.checkSelfPermission(Manifest.permission.RECORD_AUDIO)
              == PackageManager.PERMISSION_GRANTED;
          if (audio) recorder.setAudioSource(MediaRecorder.AudioSource.MIC);
          recorder.setVideoSource(MediaRecorder.VideoSource.SURFACE);
          recorder.setOutputFormat(MediaRecorder.OutputFormat.MPEG_4);
          recorder.setOutputFile(activeFile.getAbsolutePath());
          recorder.setVideoEncodingBitRate(6_000_000);
          recorder.setVideoFrameRate(30);
          recorder.setVideoSize(videoSize.getWidth(), videoSize.getHeight());
          recorder.setVideoEncoder(MediaRecorder.VideoEncoder.H264);
          if (audio) {
            recorder.setAudioEncoder(MediaRecorder.AudioEncoder.AAC);
            recorder.setAudioEncodingBitRate(128_000);
            recorder.setAudioSamplingRate(44_100);
          }
          recorder.setOrientationHint(sensorOrientation);
          recorder.prepare();

          SurfaceTexture surfaceTexture = texture.getSurfaceTexture();
          if (surfaceTexture == null) throw new IllegalStateException("Preview surface is unavailable");
          surfaceTexture.setDefaultBufferSize(videoSize.getWidth(), videoSize.getHeight());
          Surface previewSurface = new Surface(surfaceTexture);
          Surface recorderSurface = recorder.getSurface();
          CaptureRequest.Builder request = device.createCaptureRequest(CameraDevice.TEMPLATE_RECORD);
          request.addTarget(previewSurface);
          request.addTarget(recorderSurface);
          request.set(CaptureRequest.CONTROL_MODE, CaptureRequest.CONTROL_MODE_AUTO);
          device.createCaptureSession(List.of(previewSurface, recorderSurface),
              new CameraCaptureSession.StateCallback() {
                @Override public void onConfigured(CameraCaptureSession configured) {
                  if (closed || !cameraRequested) {
                    configured.close();
                    failure.set(new IllegalStateException("Capture cancelled"));
                    latch.countDown();
                    return;
                  }
                  session = configured;
                  try {
                    configured.setRepeatingRequest(request.build(), null, handler);
                    recorder.start();
                    recording = true;
                  } catch (Exception error) {
                    failure.set(error);
                  } finally {
                    latch.countDown();
                  }
                }
                @Override public void onConfigureFailed(CameraCaptureSession failed) {
                  failure.set(new IllegalStateException("Could not configure recording session"));
                  latch.countDown();
                }
              }, handler);
        } catch (Exception error) {
          failure.set(error);
          latch.countDown();
        }
      });
      if (!latch.await(10, TimeUnit.SECONDS)) failure.set(new IllegalStateException("Camera start timed out"));
      if (failure.get() != null) {
        cameraRequested = false;
        CountDownLatch cleanup = new CountDownLatch(1);
        handler.post(() -> {
          abortRecorder();
          cleanup.countDown();
        });
        cleanup.await(5, TimeUnit.SECONDS);
        throw failure.get();
      }
    }

    File stopRecording(String recordingId) throws Exception {
      // A stop after a rejected/expired start is a recovery command. Treat it as an
      // idempotent no-op so the backend can leave its error state without restarting the app.
      if (!recording || recorder == null) return null;
      if (!recordingId.equals(activeRecordingId)) throw new IllegalStateException("Recording ID mismatch");
      CountDownLatch latch = new CountDownLatch(1);
      AtomicReference<Exception> failure = new AtomicReference<>();
      AtomicReference<File> saved = new AtomicReference<>();
      handler.post(() -> {
        try {
          closeSession();
          recorder.stop();
          saved.set(activeFile);
        } catch (Exception error) {
          failure.set(error);
        } finally {
          try {
            recorder.reset();
            recorder.release();
          } catch (Exception ignored) {}
          recorder = null;
          recording = false;
          activeRecordingId = null;
          activeFile = null;
          releaseCamera();
          latch.countDown();
        }
      });
      if (!latch.await(15, TimeUnit.SECONDS)) throw new IllegalStateException("Camera stop timed out");
      if (failure.get() != null) throw failure.get();
      File result = saved.get();
      if (result == null || !result.isFile() || result.length() == 0) {
        throw new IllegalStateException("Camera returned an empty recording");
      }
      return result;
    }

    private void closeSession() {
      if (session != null) {
        session.close();
        session = null;
      }
    }

    private void abortRecorder() {
      closeSession();
      if (recorder != null) {
        try { recorder.reset(); } catch (Exception ignored) {}
        recorder.release();
        recorder = null;
      }
      if (activeFile != null && activeFile.isFile()) activeFile.delete();
      activeFile = null;
      activeRecordingId = null;
      recording = false;
      releaseCamera();
    }

    private void releaseCamera() {
      closeSession();
      if (device != null) {
        device.close();
        device = null;
      }
      cameraRequested = false;
      visibility.set(false);
    }

    void close() {
      closed = true;
      cameraRequested = false;
      if (handler != null) {
        handler.post(() -> {
          closeSession();
          if (recorder != null) {
            try { recorder.stop(); } catch (Exception ignored) {}
            recorder.release();
            recorder = null;
          }
          if (device != null) {
            device.close();
            device = null;
          }
          recording = false;
        });
      }
      if (cameraThread != null) cameraThread.quitSafely();
    }

    private static Size chooseSize(Size[] choices) {
      if (choices == null || choices.length == 0) return new Size(1280, 720);
      Size best = choices[0];
      for (Size candidate : choices) {
        if (candidate.getWidth() == 1280 && candidate.getHeight() == 720) return candidate;
        long pixels = (long) candidate.getWidth() * candidate.getHeight();
        long bestPixels = (long) best.getWidth() * best.getHeight();
        if (pixels <= 1920L * 1080L && pixels > bestPixels) best = candidate;
      }
      return best;
    }
  }
}
