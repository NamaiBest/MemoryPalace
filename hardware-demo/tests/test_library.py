import sys
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT.parent / "confusion-detector")]
from eegdemo.library import Library


class LibraryTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.events = []
        self.library = Library(self.dir.name,
                               lambda k, d: self.events.append((k, d)))

    def tearDown(self):
        self.dir.cleanup()

    def test_stores_bytes_and_builds_a_moment(self):
        moment = self.library.store(b"not-really-a-video", "video/mp4")
        self.assertEqual(moment["eventType"], "load")
        self.assertEqual(moment["status"], "candidate")
        self.assertTrue(moment["media"]["videoUrl"].endswith(".mp4"))
        self.assertEqual(self.library.moments, [moment])

    def test_trigger_context_reaches_the_moment(self):
        self.library.note_trigger("rec-1", {"z_score": 12.0, "sample_time_s": 144.0})
        moment = self.library.store(b"x", "video/mp4", recording_id="rec-1")
        self.assertEqual(moment["detector"]["z_score"], 12.0)
        self.assertIn("z = +12.0", moment["summary"])
        # A high z must rank above an unattributed capture, without ever reaching 1.0:
        # this is an ordering score, not a calibrated probability.
        self.assertGreater(moment["confidence"], 0.5)
        self.assertLess(moment["confidence"], 1.0)

    def test_context_is_consumed_once(self):
        self.library.note_trigger("rec-1", {"z_score": 9.0})
        self.library.store(b"x", "video/mp4", recording_id="rec-1")
        second = self.library.store(b"y", "video/mp4", recording_id="rec-1")
        self.assertIsNone(second["detector"])

    def test_rejects_empty_upload(self):
        with self.assertRaises(ValueError):
            self.library.store(b"", "video/mp4")
        self.assertEqual(self.library.moments, [])

    def test_rejects_oversized_upload(self):
        with patch("eegdemo.library.MAX_UPLOAD_BYTES", 8):
            with self.assertRaises(ValueError):
                self.library.store(b"x" * 9, "video/mp4")
        self.assertEqual(self.library.moments, [])

    def test_path_for_refuses_escapes(self):
        moment = self.library.store(b"x", "video/mp4")
        name = moment["media"]["videoUrl"].split("/")[-1]
        self.assertIsNotNone(self.library.path_for(name))
        for bad in ("../../../etc/passwd", "..", "", "nope.mp4"):
            self.assertIsNone(self.library.path_for(bad), bad)

    def test_sequence_increments(self):
        first = self.library.store(b"x", "video/mp4")
        second = self.library.store(b"y", "video/mp4")
        self.assertEqual((first["sequence"], second["sequence"]), (1, 2))

    def test_catalog_survives_library_restart(self):
        first = self.library.store(b"x", "video/mp4")
        restored = Library(self.dir.name, lambda k, d: self.events.append((k, d)))
        self.assertEqual([moment["id"] for moment in restored.moments], [first["id"]])
        self.assertTrue(restored.status()["persistent"])
        second = restored.store(b"y", "video/mp4")
        self.assertEqual(second["sequence"], 2)

    def test_imports_legacy_run_without_removing_original(self):
        root = Path(self.dir.name)
        runs = root / "runs"
        old = runs / "20260919-old"
        media = old / "media"
        media.mkdir(parents=True)
        media_id = "abc123456789"
        original = media / f"{media_id}.mp4"
        original.write_bytes(b"old-memory")
        (media / f"{media_id}.jpg").write_bytes(b"poster")
        recording_id = "recording-old"
        events = [
            {"type": "demo_capture_requested", "wall_time": 100,
             "detail": {"recording_id": recording_id, "seconds": 10,
                        "demo_event": "surprise", "started_at": None, "ends_at": None}},
            {"type": "command_acknowledged", "wall_time": 101,
             "detail": {"recording_id": recording_id, "state": "recording"}},
            {"type": "command_acknowledged", "wall_time": 111,
             "detail": {"recording_id": recording_id, "state": "stopped",
                        "media_path": "phone.mp4"}},
            {"type": "media_stored", "wall_time": 112,
             "detail": {"media_id": media_id, "moment": "capture-abc12345"}},
        ]
        (old / "events.jsonl").write_text(
            "".join(json.dumps(event) + "\n" for event in events))
        durable = root / "durable"

        migrated = Library(root / "new-run", lambda k, d: self.events.append((k, d)),
                           storage=durable, legacy_runs=runs)

        self.assertEqual(len(migrated.moments), 1)
        self.assertEqual(migrated.moments[0]["eventType"], "surprise")
        self.assertEqual(migrated.moments[0]["recordingId"], recording_id)
        self.assertTrue((durable / original.name).is_file())
        self.assertTrue(original.is_file(), "migration must never remove the original")

        again = Library(root / "another-run", lambda *_: None,
                        storage=durable, legacy_runs=runs)
        self.assertEqual(len(again.moments), 1, "migration must be idempotent")

    def test_new_moment_is_indexed_without_mutating_saved_media(self):
        class Elastic:
            configured = True

            def __init__(self):
                self.indexed = []

            def index_moment(self, moment, media_path=None):
                self.indexed.append(moment)

        elastic = Elastic()
        library = Library(self.dir.name, lambda k, d: self.events.append((k, d)),
                          elastic=elastic)
        with patch.object(library, "_poster", return_value=None), \
                patch("eegdemo.library.threading.Thread"):
            moment = library.store(b"video", "video/mp4")
        library._index_elastic(moment)
        self.assertEqual(elastic.indexed[-1]["id"], moment["id"])
        self.assertEqual(moment["processing"]["indexing"], "complete")
        media_path = library.path_for(moment["media"]["videoUrl"].split("/")[-1])
        self.assertEqual(media_path.read_bytes(), b"video")
        restored = Library(self.dir.name, lambda *_: None)
        self.assertEqual(restored.moments[0]["id"], moment["id"])

    def test_meta_semantics_are_persisted_before_elastic_indexing(self):
        class Vision:
            configured = True
            enabled = True
            model = "muse-spark-1.3"
            last_error = None

            def describe(self, path):
                return {"title": "Preparing the EEG headset",
                        "description": "A headset and red sensor wires rest on a desk.",
                        "keywords": ["headset", "sensor wires", "desk"],
                        "topics": ["EEG setup"], "provider": "meta",
                        "model": self.model, "status": "complete"}

        class Elastic:
            configured = True

            def __init__(self):
                self.indexed = []

            def index_moment(self, moment, media_path=None):
                self.indexed.append(dict(moment))

        elastic = Elastic()
        library = Library(self.dir.name, lambda k, d: self.events.append((k, d)),
                          elastic=elastic, vision=Vision())
        with patch.object(library, "_poster", return_value=None), \
                patch("eegdemo.library.threading.Thread"):
            moment = library.store(b"video", "video/mp4")
        path = library.path_for(moment["media"]["videoUrl"].split("/")[-1])
        library._enrich_and_index(moment["id"], path)
        self.assertEqual(moment["semanticTitle"], "Preparing the EEG headset")
        self.assertEqual(moment["processing"]["analysis"], "complete")
        self.assertEqual(moment["processing"]["indexing"], "complete")
        self.assertEqual(elastic.indexed[-1]["semanticTitle"],
                         "Preparing the EEG headset")
        restored = Library(self.dir.name, lambda *_: None)
        self.assertEqual(restored.moments[0]["semanticTitle"],
                         "Preparing the EEG headset")


    def test_incomplete_work_is_retried_without_a_restart(self):
        """A transient failure must heal on its own, not wait for the next backend start."""
        import threading
        import time as _time

        class Elastic:
            configured = True

        calls = []
        done = threading.Event()

        with patch("eegdemo.library.RETRY_INTERVAL_S", 0.02), \
                patch.object(Library, "_enrich_and_index_all",
                             lambda self: (calls.append(_time.monotonic()), done.set())):
            Library(self.dir.name, lambda *_: None, elastic=Elastic())
            self.assertTrue(done.wait(2.0), "retry sweep never ran")
            # It keeps going, not just once. Assert while the patches are still active:
            # the loop re-reads the interval each pass, and would otherwise sleep 120s.
            deadline = _time.monotonic() + 2.0
            while len(calls) < 3 and _time.monotonic() < deadline:
                _time.sleep(0.02)
            self.assertGreaterEqual(len(calls), 3, "retry sweep should repeat periodically")


if __name__ == "__main__":
    unittest.main()
