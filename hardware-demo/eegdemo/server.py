"""Small local/LAN backend. Credentials stay out of URLs and session logs."""
import hmac
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

from .library import MAX_UPLOAD_BYTES, Library
from .pipeline import Pipeline
from .recording import PhoneRecorder, TestVideoRecorder


MEDIA_TYPES = {".mp4": "video/mp4", ".mov": "video/quicktime",
               ".jpg": "image/jpeg", ".png": "image/png"}


class Runtime:
    def __init__(self, output, source="synthetic", recorder="test-video", token="", notch=60):
        self.output = Path(output).resolve()
        self.output.mkdir(parents=True, exist_ok=False)
        self.token = token
        self.lock = threading.RLock()
        self.events = []
        self.journal = (self.output / "events.jsonl").open("a", buffering=1)
        self.raw = (self.output / "eeg.jsonl").open("a", buffering=1)
        cls = PhoneRecorder if recorder == "phone" else TestVideoRecorder
        self.recorder = cls(self.output, self.emit)
        self.pipeline = Pipeline(self.emit, self.trigger, source, notch)
        self.library = Library(self.output, self.emit)

    def emit(self, kind, detail):
        event = {"type": kind, "wall_time": time.time(), "detail": detail}
        if kind == "eeg":
            self.raw.write(json.dumps(event, allow_nan=False) + "\n")
        else:
            self.journal.write(json.dumps(event, allow_nan=False) + "\n")
            self.events.append(event)
            self.events = self.events[-200:]
            if kind != "window":
                print(f"[{kind}] {json.dumps(detail, allow_nan=False)}", flush=True)

    def trigger(self, detail):
        self.emit("load_trigger", detail)
        state = self.recorder.status()
        if state["state"] in ("starting", "recording"):
            # Capture why we stopped before stopping, so the uploaded media can be
            # paired with the detector reading that caused it.
            self.library.note_trigger(state.get("recording_id"), detail)
            self.recorder.stop("sustained_eeg_load")
        else:
            self.emit("trigger_without_recording", {})

    def status(self):
        return {"eeg": self.pipeline.status(), "recording": self.recorder.status(),
                "library": self.library.status(), "session_dir": str(self.output)}

    def close(self):
        with self.lock:
            self.recorder.close()
            (self.output / "summary.json").write_text(json.dumps(self.status(), indent=2))
            self.journal.close()
            self.raw.close()


def create_server(runtime, host="127.0.0.1", port=8771):
    if host not in ("127.0.0.1", "localhost", "::1") and len(runtime.token) < 16:
        raise ValueError("LAN mode requires DEMO_TOKEN with at least 16 characters")

    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(10)

        def send(self, code, body):
            encoded = json.dumps(body, allow_nan=False).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(encoded)

        def authorized(self):
            supplied = self.headers.get("Authorization", "")
            if runtime.token and not hmac.compare_digest(supplied, f"Bearer {runtime.token}"):
                self.send(401, {"error": "invalid bearer token"})
                return False
            return True

        def send_file(self, path):
            data = path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", MEDIA_TYPES.get(path.suffix, "application/octet-stream"))
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "private, max-age=3600")
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if not self.authorized():
                return
            route = urlsplit(self.path).path
            with runtime.lock:
                if route in ("/health", "/status"):
                    self.send(200, runtime.status())
                elif route == "/events":
                    self.send(200, {"events": runtime.events})
                elif route == "/moments":
                    self.send(200, {"moments": runtime.library.moments})
                elif route.startswith("/media/"):
                    path = runtime.library.path_for(unquote(route[len("/media/"):]))
                    if path is None:
                        return self.send(404, {"error": "not found"})
                    self.send_file(path)
                elif route == "/commands" and isinstance(runtime.recorder, PhoneRecorder):
                    self.send(200, runtime.recorder.commands())
                else:
                    self.send(404, {"error": "not found"})

        def do_POST(self):
            if not self.authorized():
                return
            route = urlsplit(self.path).path
            if route == "/media/upload":
                return self.do_upload()
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 1024 * 1024:
                    return self.send(413, {"error": "request must contain 1..1048576 bytes"})
                body = json.loads(self.rfile.read(length))
                if not isinstance(body, dict):
                    raise ValueError("JSON body must be an object")
                with runtime.lock:
                    runtime.pipeline.watchdog()
                    if self.path == "/eeg":
                        result = runtime.pipeline.ingest(body)
                    elif self.path == "/recording/start":
                        if runtime.pipeline.phase != "ready" or runtime.pipeline.last_arrival is None:
                            raise ValueError("complete calibration with a connected EEG source first")
                        result = runtime.recorder.start()
                        runtime.pipeline.detector.run = 0
                        runtime.pipeline.detector.last_fire_t = -1e9
                    elif self.path == "/recording/stop":
                        result = runtime.recorder.stop("manual_stop")
                    elif self.path == "/calibration/reset":
                        if runtime.recorder.status()["state"] not in ("idle", "stopped"):
                            raise ValueError("stop and confirm recording before recalibration")
                        runtime.pipeline.reset()
                        result = runtime.status()
                    elif self.path == "/commands/ack" and isinstance(runtime.recorder, PhoneRecorder):
                        result = runtime.recorder.ack(body)
                    elif self.path == "/markers":
                        label = body.get("label")
                        if label not in ("easy_start", "hard_start", "task_end", "blink", "jaw_clench", "head_movement"):
                            raise ValueError("unsupported task/artifact marker")
                        result = {"label": label, "last_sample_end_ms": runtime.pipeline.expected_ms}
                        runtime.emit("task_marker", result)
                    else:
                        return self.send(404, {"error": "not found"})
                self.send(200, result)
            except (KeyError, TypeError, ValueError, OverflowError) as exc:
                self.send(400, {"error": str(exc)})
            except Exception as exc:
                runtime.emit("backend_error", {"error": str(exc)})

        def do_upload(self):
            """Binary media from the phone. Read outside the lock: a large upload over
            a slow link must not stall EEG ingestion or the command poll."""
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= MAX_UPLOAD_BYTES:
                    return self.send(413, {"error": f"upload must be 1..{MAX_UPLOAD_BYTES} bytes"})
                content_type = self.headers.get("Content-Type", "application/octet-stream")
                recording_id = parse_qs(urlsplit(self.path).query).get("recording_id", [None])[0]

                remaining, chunks = length, []
                while remaining > 0:
                    chunk = self.rfile.read(min(remaining, 1 << 20))
                    if not chunk:
                        return self.send(400, {"error": "upload ended early"})
                    chunks.append(chunk)
                    remaining -= len(chunk)

                with runtime.lock:
                    moment = runtime.library.store(b"".join(chunks), content_type, recording_id)
                self.send(200, {"moment": moment})
            except (TypeError, ValueError) as exc:
                self.send(400, {"error": str(exc)})
            except Exception as exc:
                runtime.emit("backend_error", {"error": str(exc)})
                self.send(500, {"error": "upload failed"})
                self.send(500, {"error": "backend error; inspect events.jsonl"})

        def log_message(self, *args):
            pass

    return ThreadingHTTPServer((host, port), Handler)
