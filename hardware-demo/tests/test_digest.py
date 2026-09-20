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


class CustomRecipientTests(DigestTests):
    """A one-off recipient, and the HTTPS transport that conference wifi allows."""

    def test_custom_recipient_overrides_the_configured_one(self):
        sent = {}

        digest = self.build({"RESEND_API_KEY": "key", "MEMORYPALACE_DIGEST_FROM": "me@x.co",
                             "MEMORYPALACE_DIGEST_TO": "default@x.co"})
        digest._send_https = lambda to, subject, body, files=(): sent.update(to=to) or {"id": "1"}
        result = digest.send("2026-09-19", to="someone@else.com")
        self.assertEqual(sent["to"], "someone@else.com")
        self.assertEqual(result["to"], "someone@else.com")
        self.assertEqual(result["transport"], "https")

    def test_https_wins_when_both_are_configured(self):
        digest = self.build({"RESEND_API_KEY": "key", "SMTP_HOST": "localhost",
                             "MEMORYPALACE_DIGEST_FROM": "me@x.co"})
        self.assertEqual(digest.transport, "https")

    def test_a_malformed_address_is_refused_before_sending(self):
        digest = self.build({"RESEND_API_KEY": "key", "MEMORYPALACE_DIGEST_FROM": "me@x.co"})
        digest._send_https = lambda *a, **k: self.fail("should not have sent")
        with self.assertRaises(DigestError):
            digest.send("2026-09-19", to="not-an-address")


class AttachmentTests(DigestTests):
    """Posters always travel; clips travel while they fit."""

    class Lib(FakeLibrary):
        def __init__(self, moments, sizes):
            super().__init__(moments)
            self.sizes = sizes
            self.dir = Path(".")

        def path_for(self, name):
            import tempfile
            size = self.sizes.get(name)
            if size is None:
                return None
            f = Path(tempfile.gettempdir()) / name
            if not f.exists() or f.stat().st_size != size:
                f.write_bytes(b"\0" * size)
            return f

    def _digest(self, sizes, moments):
        d = self.build()
        d.library = self.Lib(moments, sizes)
        return d

    def test_only_clips_travel_and_only_what_fits(self):
        moments = [
            {"id": "a", "confidence": 0.9, "timestamp": "2026-09-19T18:00:00Z",
             "media": {"thumbnailUrl": "/m/a.jpg", "videoUrl": "/m/a.mp4"}},
            {"id": "b", "confidence": 0.5, "timestamp": "2026-09-19T18:01:00Z",
             "media": {"thumbnailUrl": "/m/b.jpg", "videoUrl": "/m/b.mp4"}},
        ]
        sizes = {"a.jpg": 1000, "b.jpg": 1000,
                 "a.mp4": 10 * 1024 * 1024, "b.mp4": 10 * 1024 * 1024}
        files, used, skipped = self._digest(sizes, moments).attachments_for(moments)
        names = [f["filename"] for f in files]
        self.assertEqual(names, ["a.mp4"])          # clips only, no stills
        self.assertEqual(skipped, 1)                # the one over budget is counted
        self.assertLess(used, 18 * 1024 * 1024)

    def test_a_whole_day_never_attaches_clips_by_accident(self):
        """attach only means something alongside an explicit selection."""
        digest = self.build()
        built = digest.build("2026-09-19", attach=True)
        self.assertEqual(built["attachments"], [])
        self.assertEqual(built["clipsSkipped"], 0)

    def test_a_window_spans_several_local_days(self):
        digest = self.build()
        self.assertEqual([m["id"] for m in digest.moments_for("2026-09-21", days=3)],
                         ["a", "b", "c"])
        self.assertEqual([m["id"] for m in digest.moments_for("2026-09-21", days=1)],
                         ["c"])

    def test_explicit_moments_override_the_window(self):
        built = self.build().build("2026-09-19", moment_ids=["c"])
        self.assertEqual([m["id"] for m in built["moments"]], ["c"])
