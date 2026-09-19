"""Explicit recording lifecycle; a remote stop is complete only after acknowledgement."""
import shutil
import signal
import subprocess
import threading
import time
import uuid
from pathlib import Path


class TestVideoRecorder:
    def __init__(self, output, emit):
        self.output, self.emit = Path(output), emit
        self.state, self.process, self.path = "idle", None, None
        self.log_handle = None

    def start(self):
        if self.state in ("recording", "starting", "stopping"):
            raise ValueError("a recording is already active")
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            raise ValueError("ffmpeg is required for test-video mode; install it first")
        self.path = self.output / f"simulated-camera-{uuid.uuid4().hex[:8]}.mp4"
        self.log_handle = (self.path.with_suffix(".ffmpeg.log")).open("w")
        self.process = subprocess.Popen(
            [ffmpeg, "-hide_banner", "-loglevel", "error", "-progress", "pipe:1",
             "-stats_period", "0.1", "-y", "-re", "-f", "lavfi",
             "-i", "testsrc2=size=640x360:rate=15", "-an", "-c:v", "libx264",
             "-preset", "ultrafast", "-threads", "1", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
             str(self.path)], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=self.log_handle)
        # Some Macs take several seconds to launch an Intel FFmpeg binary. A living
        # process is not evidence of recording; wait for its first encoded frame.
        writing = threading.Event()
        def read_progress():
            for line in self.process.stdout:
                if line.startswith(b"frame="):
                    try:
                        if int(line.split(b"=", 1)[1]) > 0:
                            writing.set()
                    except ValueError:
                        pass
        self.progress_thread = threading.Thread(target=read_progress, daemon=True)
        self.progress_thread.start()
        deadline = time.monotonic() + 25
        while not writing.wait(0.1) and self.process.poll() is None and time.monotonic() < deadline:
            pass
        if not writing.is_set() or self.process.poll() is not None:
            if self.process.poll() is None:
                self.process.kill()
            self.process.wait()
            self.progress_thread.join(timeout=1)
            self.process.stdout.close()
            self.log_handle.close()
            self.state = "error"
            raise ValueError(f"FFmpeg failed; see {self.path.with_suffix('.ffmpeg.log')}")
        self.state = "recording"
        self.emit("recording_started", {"mode": "test-video", "media_path": str(self.path)})
        return self.status()

    def stop(self, reason):
        if self.state != "recording":
            return self.status()
        self.state = "stopping"
        self.emit("stop_requested", {"reason": reason})
        try:
            # SIGINT asks FFmpeg to write its trailer. Unlike stdin 'q', this also
            # works when an FFmpeg build disables interactive stdin on a pipe.
            self.process.send_signal(signal.SIGINT)
            self.process.wait(timeout=10)
            if self.process.returncode not in (0, 255) or not self.path.exists() or self.path.stat().st_size == 0:
                raise RuntimeError("FFmpeg failed to finalize the recording")
            self.state = "stopped"
            self.emit("recording_stopped", {"media_path": str(self.path), "reason": reason})
        except (OSError, subprocess.TimeoutExpired, RuntimeError) as exc:
            self.process.kill()
            self.process.wait()
            self.state = "error"
            self.emit("recording_error", {"error": str(exc)})
        finally:
            self.progress_thread.join(timeout=1)
            self.process.stdout.close()
            self.log_handle.close()
        return self.status()

    def status(self):
        if self.state == "recording" and self.process.poll() is not None:
            self.state = "error"
            self.log_handle.close()
        return {"mode": "test-video", "state": self.state,
                "media_path": str(self.path) if self.path else None}

    def close(self):
        self.stop("server_shutdown")


class PhoneRecorder:
    def __init__(self, output, emit):
        self.emit = emit
        self.state, self.pending = "idle", None
        self.acknowledged = {}
        self.last_poll = None
        self.media_path = None
        self.recording_id = None

    def issue(self, action, reason):
        self.pending = {"id": uuid.uuid4().hex, "action": action,
                        "recording_id": self.recording_id, "reason": reason,
                        "expires_at": time.time() + (30 if action == "start" else 15)}
        self.state = "starting" if action == "start" else "stopping"
        self.emit("command_queued", self.pending)
        return self.status()

    def start(self):
        self.expire()
        if self.state in ("starting", "recording", "stopping", "error"):
            raise ValueError("phone recording is active or uncertain; resolve it before restarting")
        if self.last_poll is None or time.monotonic() - self.last_poll > 5:
            raise ValueError("phone is not polling the backend")
        self.recording_id = uuid.uuid4().hex
        self.media_path = None
        return self.issue("start", "manual_start")

    def stop(self, reason):
        self.expire()
        if self.state == "stopping":
            return self.status()
        if self.state not in ("recording", "starting", "error"):
            return self.status()
        return self.issue("stop", reason)

    def expire(self):
        if self.pending and time.time() > self.pending["expires_at"]:
            self.emit("command_expired", self.pending)
            self.pending = None
            self.state = "error"

    def commands(self):
        self.last_poll = time.monotonic()
        self.expire()
        return {"command": self.pending}

    def ack(self, body):
        command_id = body.get("id")
        if command_id in self.acknowledged:
            return self.acknowledged[command_id]
        self.expire()
        if not self.pending or self.pending["id"] != command_id:
            raise ValueError("unknown, expired, or superseded command")
        expected = "recording" if self.pending["action"] == "start" else "stopped"
        if body.get("state") not in (expected, "error"):
            raise ValueError(f"acknowledgement must report {expected} or error")
        if body.get("recording_id") != self.recording_id:
            raise ValueError("acknowledgement recording_id does not match")
        self.state = body["state"]
        self.media_path = body.get("media_path")
        self.emit("command_acknowledged", body)
        self.pending = None
        result = self.status()
        self.acknowledged[command_id] = result
        # Bound retry cache while preserving recent command acknowledgements.
        if len(self.acknowledged) > 100:
            del self.acknowledged[next(iter(self.acknowledged))]
        return result

    def status(self):
        self.expire()
        return {"mode": "phone", "state": self.state, "pending": self.pending,
                "recording_id": self.recording_id, "media_path": self.media_path,
                "phone_connected": self.last_poll is not None and time.monotonic() - self.last_poll < 5}

    def close(self):
        if self.state in ("starting", "recording", "stopping", "error"):
            self.emit("shutdown_phone_warning", {"message": "Stop recording on the phone; backend is shutting down."})
