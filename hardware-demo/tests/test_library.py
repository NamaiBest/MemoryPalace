import sys
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


if __name__ == "__main__":
    unittest.main()
