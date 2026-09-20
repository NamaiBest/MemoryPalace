"""Small local/LAN backend. Credentials stay out of URLs and session logs."""
import hmac
import json
import threading
import time
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit
from zoneinfo import ZoneInfo

from .agent import AgentError, MemoryGuard
from .elastic_store import ElasticStore
from .library import MAX_UPLOAD_BYTES, Library
from .pipeline import Pipeline
from .recording import PhoneRecorder, TestVideoRecorder
from .vision import MetaVideoDescriber


MEDIA_TYPES = {".mp4": "video/mp4", ".mov": "video/quicktime",
               ".jpg": "image/jpeg", ".png": "image/png"}


class Runtime:
    def __init__(self, output, source="synthetic", recorder="test-video", token="", notch=60,
                 library_dir=None, legacy_runs=None):
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
        self.elastic = ElasticStore(self.emit)
        self.vision = MetaVideoDescriber(self.emit)
        self.guard = MemoryGuard(self.emit)
        self.library = Library(self.output, self.emit, self.elastic, self.vision,
                               storage=library_dir, legacy_runs=legacy_runs,
                               session_id=self.output.name)
        self.timed_capture = None
        self.capture_timer = None

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
        if self.timed_capture and self.timed_capture["recording_id"] == state.get("recording_id"):
            # Demo buttons promise a fixed-length clip, independent of synthetic EEG.
            return
        if state["state"] in ("starting", "recording"):
            # Capture why we stopped before stopping, so the uploaded media can be
            # paired with the detector reading that caused it.
            self.library.note_trigger(state.get("recording_id"), detail)
            self.recorder.stop("sustained_eeg_load")
        else:
            self.emit("trigger_without_recording", {})

    def status(self):
        return {"eeg": self.pipeline.status(), "recording": self.recorder.status(),
                "library": self.library.status(), "session_dir": str(self.output),
                "timed_capture": self.timed_capture, "elastic": self.elastic.status(),
                "vision": self.vision.status(), "agent": self.guard.status()}

    @staticmethod
    def _date_bounds(date_scope):
        if not date_scope:
            return None, None
        try:
            start = datetime.strptime(date_scope, "%Y-%m-%d").replace(
                tzinfo=ZoneInfo("America/New_York"))
        except (TypeError, ValueError) as exc:
            raise ValueError("date must be YYYY-MM-DD") from exc
        end = start + timedelta(days=1) - timedelta(microseconds=1)
        return (start.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
                end.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"))

    def _local_guard_answer(self, question, moments, retrieval_engine, date_scope):
        if not moments:
            scope = f" on {date_scope}" if date_scope else ""
            answer = f"I do not have any saved moments{scope}. Try another date or capture one first."
            selected = []
        else:
            lower = question.lower()
            if any(word in lower for word in ("strong", "intense", "spike", "critical")):
                selected = sorted(moments, key=lambda item: item.get(
                    "spikeIntensity", item.get("confidence", 0)), reverse=True)[:3]
                lead = "The strongest saved moments are:"
            elif any(word in lower for word in ("recent", "latest", "last")):
                selected = sorted(moments, key=lambda item: item.get("timestamp", ""),
                                  reverse=True)[:3]
                lead = "The most recent saved moments are:"
            else:
                terms = {word.strip(".,?!:;()[]").lower() for word in question.split()
                         if len(word.strip(".,?!:;()[]")) >= 3}
                ranked = []
                for moment in moments:
                    text = " ".join((moment.get("aiDescription", ""),
                                     moment.get("summary", ""),
                                     moment.get("transcript", ""),
                                     " ".join(moment.get("keywords", [])),
                                     " ".join(moment.get("topics", [])))).lower()
                    ranked.append((sum(term in text for term in terms), moment))
                ranked.sort(key=lambda item: (item[0], item[1].get("timestamp", "")),
                            reverse=True)
                selected = [item for score, item in ranked[:3] if score > 0]
                if not selected:
                    selected = sorted(moments, key=lambda item: item.get("timestamp", ""),
                                      reverse=True)[:3]
                lead = "These saved moments are the closest match:"
            lines = []
            for moment in selected:
                title = moment.get("semanticTitle") or "Captured moment"
                reference = f"Moment #{int(moment.get('sequence', 0)):03d}: {title}"
                description = (moment.get("aiDescription") or moment.get("summary")
                               or "Captured moment")
                intensity = round(100 * moment.get(
                    "spikeIntensity", moment.get("confidence", 0)))
                lines.append(f"[{reference}] {description} (intensity {intensity}%)")
            answer = lead + "\n" + "\n".join(f"• {line}" for line in lines)
        self.emit("memory_guard_answered", {
            "provider": "local", "model": "grounded-catalog",
            "retrieval_engine": retrieval_engine, "moments": len(selected),
            "date": date_scope,
        })
        return {"answer": answer, "provider": "local",
                "providerLabel": "Local Memory Guard", "model": "grounded-catalog",
                "retrievalEngine": retrieval_engine,
                "momentIds": [item.get("id") for item in selected]}

    def ask_guard(self, question, date_scope=None):
        question = question.strip()
        if not question:
            raise ValueError("question must not be empty")
        if len(question) > 2000:
            raise ValueError("question must be at most 2000 characters")
        date_from, date_to = self._date_bounds(date_scope)
        retrieval_engine = "local-recent"
        moments = []
        if self.elastic.configured:
            try:
                moments = self.elastic.search(
                    question, limit=8, date_from=date_from, date_to=date_to)
                retrieval_engine = "elastic-rrf-jina-v5-omni"
            except Exception as exc:
                self.emit("memory_guard_elastic_fallback", {"error": str(exc)[:500]})
        with self.lock:
            local = {moment["id"]: dict(moment) for moment in self.library.moments}
        if date_from:
            local = {moment_id: moment for moment_id, moment in local.items()
                     if date_from <= moment.get("timestamp", "") <= date_to}
        if moments:
            # Elastic ranks the ids; the durable catalog supplies the latest transcript and
            # metadata even if asynchronous re-indexing is still finishing.
            moments = [local.get(moment.get("id"), moment) for moment in moments]
        else:
            moments = sorted(local.values(), key=lambda item: item.get("timestamp", ""),
                             reverse=True)[:8]
        if not self.guard.configured or self.guard.last_error:
            return self._local_guard_answer(
                question, moments, retrieval_engine, date_scope)
        try:
            return self.guard.answer(question, moments, retrieval_engine)
        except AgentError as exc:
            # A valid credential can still be unusable because billing, quota, or the
            # selected model is unavailable. Keep the question useful and label the
            # fallback honestly rather than surfacing a dead agent window.
            self.emit("memory_guard_local_fallback", {
                "provider": self.guard.provider, "error": str(exc)[:500],
            })
            return self._local_guard_answer(
                question, moments, retrieval_engine, date_scope)

    def start_capture(self, body):
        seconds, event = body.get("seconds", 10), body.get("demo_event", "surprise")
        if type(seconds) is not int or seconds not in (10, 30):
            raise ValueError("capture length must be 10 or 30 seconds")
        if event not in ("surprise", "load"):
            raise ValueError("demo_event must be surprise or load")
        if not isinstance(self.recorder, PhoneRecorder):
            raise ValueError("timed captures require --recorder phone")
        result = self.recorder.start()
        if self.capture_timer:
            self.capture_timer.cancel()
        self.capture_timer = None
        self.timed_capture = {"recording_id": result["recording_id"], "seconds": seconds,
                              "demo_event": event, "started_at": None, "ends_at": None}
        self.library.note_trigger(result["recording_id"], {
            "demo": True, "demo_event": event, "duration_seconds": seconds,
            "z_score": 12.0, "spike_confidence": 0.95,
            "detection_threshold": self.pipeline.cfg.detector.z_threshold})
        self.emit("demo_capture_requested", self.timed_capture)
        return result

    def acknowledge(self, body):
        result = self.recorder.ack(body)
        capture = self.timed_capture
        if (capture and body.get("recording_id") == capture["recording_id"]
                and result["state"] == "recording" and self.recorder.state == "recording"
                and capture["started_at"] is None):
            capture["started_at"] = time.time()
            capture["ends_at"] = capture["started_at"] + capture["seconds"]
            self.library.contexts[capture["recording_id"]]["started_at"] = capture["started_at"]
            self.capture_timer = threading.Timer(capture["seconds"], self.finish_capture,
                                                 args=(capture["recording_id"],))
            self.capture_timer.daemon = True
            self.capture_timer.start()
        return result

    def finish_capture(self, recording_id):
        with self.lock:
            if self.recorder.recording_id == recording_id and self.recorder.state == "recording":
                self.recorder.stop("demo_capture_complete")

    def close(self):
        with self.lock:
            if self.capture_timer:
                self.capture_timer.cancel()
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
            parsed = urlsplit(self.path)
            route = parsed.path
            if route == "/search":
                try:
                    params = parse_qs(parsed.query)
                    query = params.get("q", [""])[0]
                    limit = int(params.get("limit", ["20"])[0])
                    if not 1 <= limit <= 50:
                        raise ValueError("limit must be between 1 and 50")
                    event_type = params.get("event_type", [None])[0]
                    if event_type and event_type not in ("surprise", "insight", "error", "load"):
                        raise ValueError("unsupported event_type")
                    minimum = params.get("min_intensity",
                                         params.get("min_confidence", [None]))[0]
                    maximum = params.get("max_intensity",
                                         params.get("max_confidence", [None]))[0]
                    min_intensity = float(minimum) if minimum is not None else None
                    max_intensity = float(maximum) if maximum is not None else None
                    if min_intensity is not None and not 0 <= min_intensity <= 1:
                        raise ValueError("min_intensity must be between 0 and 1")
                    if max_intensity is not None and not 0 <= max_intensity <= 1:
                        raise ValueError("max_intensity must be between 0 and 1")
                    if (min_intensity is not None and max_intensity is not None
                            and min_intensity > max_intensity):
                        raise ValueError("min_intensity must not exceed max_intensity")
                    date_from = params.get("date_from", [None])[0]
                    date_to = params.get("date_to", [None])[0]
                    session_id = params.get("session_id", [None])[0]
                    user_id = params.get("user_id", [None])[0]
                    sort = params.get("sort", ["relevance"])[0]
                    for label, value in (("session_id", session_id), ("user_id", user_id)):
                        if value and len(value) > 128:
                            raise ValueError(f"{label} must be at most 128 characters")
                    hits = runtime.elastic.search(
                        query, limit, event_type, min_intensity, max_intensity,
                        date_from, date_to, session_id, user_id, sort)
                    return self.send(200, {"moments": hits, "engine": "elastic-rrf-jina-v5-omni"})
                except ValueError as exc:
                    return self.send(400, {"error": str(exc)})
                except Exception as exc:
                    runtime.emit("elastic_search_failed", {"error": str(exc)[:500]})
                    return self.send(503, {"error": str(exc), "elastic": runtime.elastic.status()})
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
                if route == "/agent/chat":
                    # Model inference can take seconds and must never hold the EEG/capture lock.
                    return self.send(200, runtime.ask_guard(
                        str(body.get("question", "")), body.get("date")))
                with runtime.lock:
                    runtime.pipeline.watchdog()
                    if self.path == "/eeg":
                        result = runtime.pipeline.ingest(body)
                    elif self.path == "/recording/capture":
                        # Explicit demo controls use real media, without an EEG prerequisite.
                        result = runtime.start_capture(body)
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
                    elif self.path == "/settings/detection-threshold":
                        result = runtime.pipeline.set_threshold(body.get("value"))
                    elif self.path == "/commands/ack" and isinstance(runtime.recorder, PhoneRecorder):
                        result = runtime.acknowledge(body)
                    elif self.path == "/markers":
                        label = body.get("label")
                        if label not in ("easy_start", "hard_start", "task_end", "blink", "jaw_clench", "head_movement",
                                         # Oddball calibration: stimulus onsets and session bounds, so
                                         # each EEG window can be labelled standard vs target afterwards.
                                         "calibration_start", "calibration_end",
                                         "oddball_standard", "oddball_target"):
                            raise ValueError("unsupported task/artifact marker")
                        result = {"label": label, "last_sample_end_ms": runtime.pipeline.expected_ms}
                        detail = body.get("detail")
                        if isinstance(detail, dict):
                            result["detail"] = detail
                        runtime.emit("task_marker", result)
                    else:
                        return self.send(404, {"error": "not found"})
                self.send(200, result)
            except (KeyError, TypeError, ValueError, OverflowError) as exc:
                self.send(400, {"error": str(exc)})
            except AgentError as exc:
                self.send(503, {"error": str(exc), "agent": runtime.guard.status()})
            except Exception as exc:
                runtime.emit("backend_error", {"error": str(exc)})
                self.send(500, {"error": "backend error; inspect events.jsonl"})

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

        def log_message(self, *args):
            pass

    return ThreadingHTTPServer((host, port), Handler)
