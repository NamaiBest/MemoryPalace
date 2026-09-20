import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT.parent / "confusion-detector")]

from eegdemo.digest import DailyDigest, DigestError


class FakeLibrary:
    def __init__(self, moments):
        self.moments = moments


class FakeGuard:
    configured = True
    label = "Meta Muse Spark"

    def __init__(self):
        self.calls = []

    def day_recap(self, moments, day):
        self.calls.append((len(moments), day))
        return {"answer": "A long day.", "providerLabel": self.label, "model": "muse-spark-1.3"}


def moment(mid, stamp, **extra):
    base = {"id": mid, "timestamp": stamp, "status": "candidate",
            "semanticTitle": f"Moment {mid}", "annotation": ""}
    base.update(extra)
    return base


class DigestTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.events = []
        # 14:00 and 23:00 New York on the 19th, either side of UTC midnight, so the
        # local-day grouping is actually exercised rather than assumed.
        self.moments = [
            moment("a", "2026-09-19T18:00:00Z"),
            moment("b", "2026-09-20T03:00:00Z"),
            moment("c", "2026-09-21T18:00:00Z"),
        ]
        self.guard = FakeGuard()

    def tearDown(self):
        self.dir.cleanup()

    def build(self, env=None):
        with patch.dict(os.environ, env or {}, clear=False):
            return DailyDigest(lambda k, d: self.events.append((k, d)),
                               FakeLibrary(self.moments), self.guard,
                               state_dir=self.dir.name)

    def test_groups_by_local_day_not_utc(self):
        """A moment at 23:00 local is still the same evening, though UTC has rolled over."""
        digest = self.build()
        ids = [m["id"] for m in digest.moments_for("2026-09-19")]
        self.assertEqual(ids, ["a", "b"])

    def test_refuses_a_day_with_no_moments(self):
        digest = self.build()
        with self.assertRaises(DigestError):
            digest.build("2026-09-25")

    def test_counts_only_the_unreviewed(self):
        """Keeping, annotating or drawing a moment all count as having looked at it."""
        self.moments = [
            moment("kept", "2026-09-19T18:00:00Z", status="kept"),
            moment("noted", "2026-09-19T18:05:00Z", annotation="worth keeping"),
            moment("drawn", "2026-09-19T18:10:00Z", keepsakeUrl="/api/media/x.webp"),
            moment("ignored", "2026-09-19T18:15:00Z"),
        ]
        built = self.build().build("2026-09-19")
        self.assertEqual(built["unreviewed"], 1)
        self.assertEqual(len(built["moments"]), 4)

    def test_a_fully_reviewed_day_sends_nothing(self):
        self.moments = [moment("kept", "2026-09-19T18:00:00Z", status="kept")]
        digest = self.build({"SMTP_HOST": "localhost", "MEMORYPALACE_DIGEST_TO": "a@b.c",
                             "MEMORYPALACE_DIGEST_FROM": "a@b.c"})
        with self.assertRaises(DigestError):
            digest.send("2026-09-19")

    def test_sending_needs_a_configured_mailer(self):
        digest = self.build({"SMTP_HOST": "", "MEMORYPALACE_DIGEST_TO": ""})
        self.assertFalse(digest.deliverable)
        with self.assertRaises(DigestError):
            digest.send("2026-09-19")

    def test_recap_is_written_by_the_agent_over_the_whole_day(self):
        self.build().build("2026-09-19")
        self.assertEqual(self.guard.calls, [(2, "2026-09-19")])


if __name__ == "__main__":
    unittest.main()
