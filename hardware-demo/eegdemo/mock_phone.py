"""Exercise the actual phone polling/ack protocol using a test-pattern MP4 recorder."""
import json
import threading
import time
from pathlib import Path

from .client import request
from .recording import TestVideoRecorder


class MockPhone:
    def __init__(self, url, output, token=""):
        self.url, self.token = url, token
        self.output = Path(output)
        self.output.mkdir(parents=True, exist_ok=True)
        self.finished = threading.Event()
        self.ready = threading.Event()
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.recording_id = None
        self.completed = {}

    def emit(self, kind, detail):
        with (self.output / "mock-phone.jsonl").open("a") as handle:
            handle.write(json.dumps({"type": kind, "detail": detail, "wall_time": time.time()}) + "\n")

    def run(self):
        recorder = TestVideoRecorder(self.output, self.emit)
        try:
            while not self.finished.is_set():
                try:
                    command = request(self.url, "/commands", token=self.token)["command"]
                    self.ready.set()
                    if command and command["expires_at"] > time.time():
                        cid = command["id"]
                        if cid not in self.completed:
                            try:
                                if command["action"] == "start":
                                    self.recording_id = command["recording_id"]
                                    result = recorder.start()
                                elif command["action"] == "stop":
                                    if self.recording_id != command["recording_id"]:
                                        raise ValueError("recording ID mismatch")
                                    result = recorder.stop(command["reason"])
                                else:
                                    raise ValueError("unsupported command")
                                ack = {"state": result["state"], "media_path": result["media_path"]}
                            except Exception as exc:
                                ack = {"state": "error", "error": str(exc)}
                            ack.update(id=cid, recording_id=command["recording_id"])
                            self.completed[cid] = ack
                        request(self.url, "/commands/ack", self.completed[cid], self.token)
                except Exception as exc:
                    self.emit("transport_error", {"error": str(exc)})
                self.finished.wait(0.1)
        finally:
            recorder.close()

    def start(self):
        self.thread.start()
        return self

    def close(self):
        self.finished.set()
        self.thread.join(timeout=30)
