import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT.parent / "confusion-detector")]
from eegdemo.client import request
from eegdemo.fixture import packet, synthetic_window
from eegdemo.pipeline import Pipeline, CROWN_CHANNELS
from eegdemo.recording import PhoneRecorder
from eegdemo.server import Runtime, create_server


class MemoryGuardRuntimeTests(unittest.TestCase):
    def test_date_scope_uses_boston_day_boundaries(self):
        start, end = Runtime._date_bounds("2026-09-19")
        self.assertEqual(start, "2026-09-19T04:00:00Z")
        self.assertEqual(end, "2026-09-20T03:59:59.999999Z")

    def test_local_guard_answers_from_saved_moments(self):
        runtime = object.__new__(Runtime)
        events = []
        runtime.emit = lambda kind, detail: events.append((kind, detail))
        result = runtime._local_guard_answer("strongest moment", [{
            "id": "capture-1", "sequence": 1,
            "semanticTitle": "Reading a book", "summary": "Reading a book",
            "spikeIntensity": 0.91, "timestamp": "2026-09-19T15:00:00Z",
        }], "local-recent", "2026-09-19")
        self.assertIn("Moment #001: Reading a book", result["answer"])
        self.assertNotIn("capture-1", result["answer"])
        self.assertEqual(result["provider"], "local")
        self.assertEqual(result["momentIds"], ["capture-1"])
        self.assertEqual(events[0][0], "memory_guard_answered")


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.events, self.triggers = [], []
        self.p = Pipeline(lambda k, d: self.events.append((k, d)), self.triggers.append)

    def feed(self, i, high=False):
        return self.p.ingest(packet(synthetic_window(i, high), i * 4000))

    def calibrate(self):
        for i in range(30): self.feed(i)
        self.assertEqual(self.p.phase, "ready")

    def test_real_feature_chain_requires_four_independent_windows(self):
        self.calibrate()
        for i in range(30, 33): self.feed(i, True)
        self.assertEqual(self.triggers, [])
        self.feed(33, True)
        self.assertEqual(len(self.triggers), 1)
        self.assertEqual(self.triggers[0]["sample_time_s"], 136)

    def test_packet_boundaries_do_not_change_results(self):
        for i in range(34): self.feed(i, i >= 30)
        other_triggers = []
        other = Pipeline(lambda *args: None, other_triggers.append)
        all_data = np.concatenate([synthetic_window(i, i >= 30) for i in range(34)], axis=1)
        pos, n = 0, 17
        while pos < all_data.shape[1]:
            n = (n * 13) % 701 + 1
            other.ingest(packet(all_data[:, pos:pos+n], pos * 1000 / 256))
            pos += n
        self.assertEqual(other.windows, self.p.windows)
        self.assertEqual(other_triggers, self.triggers)

    def test_reordered_crown_channels_use_f5_f6(self):
        data = synthetic_window(0)
        original = packet(data, 0)
        shuffled = packet(data[::-1], 0)
        shuffled["epoch"]["info"]["channelNames"] = CROWN_CHANNELS[::-1]
        q = Pipeline(lambda *args: None, lambda *args: None)
        self.p.ingest(original); q.ingest(shuffled)
        self.assertEqual(self.p.calibrator.samples, q.calibrator.samples)

    def test_retry_does_not_count_twice(self):
        self.feed(0)
        result = self.feed(0)
        self.assertFalse(result["accepted"])
        self.assertEqual(self.p.windows, 1)

    def test_gap_breaks_elevated_run(self):
        self.calibrate()
        for i in range(30, 33): self.feed(i, True)
        self.feed(34, True)
        self.assertEqual(self.p.detector.run, 1)
        self.assertEqual(self.triggers, [])

    def test_stall_clears_partial_window_and_run(self):
        self.calibrate()
        self.feed(30, True)
        self.p.ingest(packet(synthetic_window(31)[:, :16], 124000))
        self.p.last_arrival = time.monotonic() - 6
        self.p.watchdog()
        self.assertEqual(self.p.detector.run, 0)
        self.assertEqual(self.p.buffer.shape[1], 0)
        self.assertFalse(self.p.status()["signal_connected"])

    def test_artifact_breaks_run(self):
        self.calibrate()
        self.feed(30, True)
        self.p.ingest(packet(np.full((8, 1024), 5000.0), 124000))
        self.assertEqual(self.p.detector.run, 0)

    def test_flatline_cannot_calibrate(self):
        for i in range(30): self.p.ingest(packet(np.zeros((8, 1024)), i * 4000))
        self.assertEqual(self.p.phase, "calibration_failed")

    def test_rejects_invalid_or_foreign_data_before_mutation(self):
        cases = []
        for value in (float("nan"), float("inf")):
            body = packet(synthetic_window(0), 0); body["epoch"]["data"][0][0] = value; cases.append(body)
        body = packet(synthetic_window(0), 0); body["epoch"]["info"]["samplingRate"] = 128; cases.append(body)
        body = packet(synthetic_window(0), 0); body["source"] = "crown"; cases.append(body)
        body = packet(synthetic_window(0), 0); body["epoch"]["info"]["channelNames"][0] = "Fz"; cases.append(body)
        for body in cases:
            with self.assertRaises(ValueError): self.p.ingest(body)
        self.assertEqual(self.p.windows, 0)

    def test_crown_rejects_old_data_and_publisher_changes(self):
        p = Pipeline(lambda *args: None, lambda *args: None, source="crown")
        with self.assertRaises(ValueError): p.ingest(packet(synthetic_window(0), 0, source="crown"))
        now = time.time() * 1000
        p.ingest(packet(synthetic_window(0)[:, :16], now, source="crown"))
        with self.assertRaises(ValueError):
            p.ingest(packet(synthetic_window(0)[:, :16], now + 62.5, stream_id="new", source="crown"))


class PhoneTests(unittest.TestCase):
    def setUp(self):
        self.r = PhoneRecorder(None, lambda *args: None)
        self.r.commands()

    def ack(self, state):
        return self.r.ack({"id": self.r.pending["id"], "recording_id": self.r.recording_id, "state": state})

    def test_only_ack_confirms_start_and_stop(self):
        self.r.start(); self.assertEqual(self.r.state, "starting")
        self.ack("recording"); self.assertEqual(self.r.state, "recording")
        self.r.stop("load"); self.assertEqual(self.r.state, "stopping")
        command = dict(self.r.commands()["command"])
        self.assertEqual(self.r.commands()["command"], command)
        self.r.stop("repeat"); self.assertEqual(self.r.pending, command)
        self.ack("stopped"); self.assertEqual(self.r.state, "stopped")

    def test_expired_command_is_error_not_success(self):
        self.r.start(); self.r.pending["expires_at"] = 0
        self.assertEqual(self.r.status()["state"], "error")
        with self.assertRaises(ValueError): self.r.start()
        self.r.stop("recovery"); self.ack("stopped")
        self.r.start(); self.assertEqual(self.r.state, "starting")

    def test_repeated_ack_is_idempotent_and_cannot_stop_new_clip(self):
        self.r.start(); self.ack("recording"); self.r.stop("load")
        ack = {"id": self.r.pending["id"], "recording_id": self.r.recording_id, "state": "stopped"}
        first = self.r.ack(ack)
        self.r.start()
        self.assertEqual(self.r.ack(ack), first)
        self.assertEqual(self.r.state, "starting")

    def test_wrong_recording_or_state_rejected(self):
        self.r.start()
        with self.assertRaises(ValueError): self.ack("stopped")
        with self.assertRaises(ValueError):
            self.r.ack({"id": self.r.pending["id"], "recording_id": "wrong", "state": "recording"})


class HTTPTests(unittest.TestCase):
    def test_demo_capture_without_eeg_starts_timer_only_after_ack(self):
        with tempfile.TemporaryDirectory() as temp, contextlib.redirect_stdout(io.StringIO()):
            runtime = Runtime(Path(temp) / "session", recorder="phone", token="test-token")
            server = create_server(runtime, port=0)
            thread = threading.Thread(target=server.serve_forever); thread.start()
            url = f"http://127.0.0.1:{server.server_port}"
            def call(path, body=None): return request(url, path, body, "test-token")
            try:
                with self.assertRaisesRegex(RuntimeError, "401"):
                    request(url, "/recording/capture", {"seconds": 10})
                call("/commands")
                for seconds in (0, 11, 300, True, "10"):
                    with self.assertRaisesRegex(RuntimeError, "400"):
                        call("/recording/capture", {"seconds": seconds})
                with self.assertRaisesRegex(RuntimeError, "400"):
                    call("/recording/capture", {"seconds": 10, "demo_event": "insight"})
                for seconds, event in ((10, "surprise"), (30, "load")):
                    call("/recording/capture", {"seconds": seconds, "demo_event": event})
                    self.assertIsNone(runtime.capture_timer)
                    self.assertNotEqual(runtime.pipeline.phase, "ready")
                    cmd = call("/commands")["command"]
                    ack = {"id": cmd["id"], "recording_id": cmd["recording_id"], "state": "recording"}
                    with patch("eegdemo.server.threading.Timer") as timer:
                        call("/commands/ack", ack)
                        call("/commands/ack", ack)  # retries must not extend the clip
                        timer.assert_called_once_with(seconds, runtime.finish_capture, args=(cmd["recording_id"],))
                        timer.return_value.start.assert_called_once()
                        # EEG cannot prematurely cut short an explicitly timed demo.
                        with runtime.lock:
                            runtime.trigger({"z_score": 20})
                        self.assertEqual(runtime.recorder.state, "recording")
                        runtime.finish_capture("old-recording-id")
                        self.assertEqual(runtime.recorder.state, "recording")
                        runtime.finish_capture(cmd["recording_id"])
                    stop = call("/commands")["command"]
                    self.assertEqual(stop["reason"], "demo_capture_complete")
                    call("/commands/ack", {"id": stop["id"], "recording_id": stop["recording_id"], "state": "stopped"})
                    with patch.object(runtime.library, "_poster", return_value=None):
                        moment = runtime.library.store(b"demo-media", "video/mp4", cmd["recording_id"])
                    self.assertTrue(moment["demo"])
                    self.assertEqual(moment["eventType"], event)
                    self.assertEqual(moment["recordingId"], cmd["recording_id"])
                    self.assertIn(f"{seconds}-second", moment["summary"])
            finally:
                server.shutdown(); server.server_close(); thread.join(); runtime.close()

    def test_http_calibration_to_acknowledged_stop_and_auth(self):
        with tempfile.TemporaryDirectory() as temp, contextlib.redirect_stdout(io.StringIO()):
            runtime = Runtime(Path(temp) / "session", recorder="phone", token="test-token")
            server = create_server(runtime, port=0)
            thread = threading.Thread(target=server.serve_forever); thread.start()
            url = f"http://127.0.0.1:{server.server_port}"
            def call(path, body=None): return request(url, path, body, "test-token")
            try:
                with self.assertRaisesRegex(RuntimeError, "401"): request(url, "/status")
                with self.assertRaisesRegex(RuntimeError, "400"): call("/recording/start", {})
                with self.assertRaisesRegex(RuntimeError, "400"): call("/eeg", {})
                self.assertEqual(call("/settings/detection-threshold", {"value": 2.7}),
                                 {"z_threshold": 2.7})
                self.assertEqual(call("/status")["eeg"]["detection_threshold"], 2.7)
                with self.assertRaisesRegex(RuntimeError, "400"):
                    call("/settings/detection-threshold", {"value": 8})
                for i in range(30): call("/eeg", packet(synthetic_window(i), i * 4000))
                call("/commands")
                call("/recording/start", {})
                cmd = call("/commands")["command"]
                call("/commands/ack", {"id": cmd["id"], "recording_id": cmd["recording_id"], "state": "recording"})
                for i in range(30, 34): call("/eeg", packet(synthetic_window(i, True), i * 4000))
                self.assertEqual(call("/status")["recording"]["state"], "stopping")
                cmd = call("/commands")["command"]
                self.assertEqual(cmd["action"], "stop")
                call("/commands/ack", {"id": cmd["id"], "recording_id": cmd["recording_id"], "state": "stopped"})
                self.assertEqual(call("/status")["recording"]["state"], "stopped")
            finally:
                server.shutdown(); server.server_close(); thread.join(); runtime.close()
            events = [json.loads(s) for s in (Path(temp) / "session/events.jsonl").read_text().splitlines()]
            self.assertEqual(sum(e["type"] == "load_trigger" for e in events), 1)


if __name__ == "__main__": unittest.main()
