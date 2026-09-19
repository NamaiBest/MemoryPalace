"""Captured media and the moments built from it.

The phone finalises a recording locally and only reports a content:// URI, which
nothing off the device can open. It then uploads the bytes here, and this module
pairs them with the detector context that caused the stop, producing the Moment
records the web UI renders.
"""
import shutil
import subprocess
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

POSTER_SECONDS = 1.0
POSTER_TIMEOUT = 20
MAX_UPLOAD_BYTES = 512 * 1024 * 1024

SUFFIXES = {"video/mp4": ".mp4", "video/quicktime": ".mov", "image/jpeg": ".jpg",
            "image/png": ".png"}


def _iso(ts):
    return datetime.fromtimestamp(ts, timezone.utc).isoformat().replace("+00:00", "Z")


class Library:
    def __init__(self, output, emit):
        self.dir = Path(output) / "media"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.emit = emit
        self.moments = []
        self.contexts = {}

    def note_trigger(self, recording_id, detail):
        """Remember why a recording was stopped, to attach to its media later."""
        if recording_id:
            self.contexts[recording_id] = dict(detail)

    def _poster(self, video):
        """Extract a single frame so the carousel has something to show."""
        if not shutil.which("ffmpeg"):
            return None
        poster = video.with_suffix(".jpg")
        try:
            subprocess.run(
                ["ffmpeg", "-nostdin", "-loglevel", "error", "-y",
                 "-ss", str(POSTER_SECONDS), "-i", str(video),
                 "-frames:v", "1", "-q:v", "4", str(poster)],
                timeout=POSTER_TIMEOUT, check=True,
                stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        except (subprocess.SubprocessError, OSError) as exc:
            self.emit("poster_failed", {"video": video.name, "error": str(exc)[:200]})
            return None
        return poster if poster.exists() and poster.stat().st_size else None

    def store(self, data, content_type, recording_id=None, source="phone"):
        if not data:
            raise ValueError("upload was empty")
        if len(data) > MAX_UPLOAD_BYTES:
            raise ValueError(f"upload exceeds {MAX_UPLOAD_BYTES} bytes")

        media_id = uuid.uuid4().hex
        target = self.dir / f"{media_id}{SUFFIXES.get(content_type, '.bin')}"
        target.write_bytes(data)

        poster = self._poster(target) if content_type.startswith("video/") else target
        context = self.contexts.pop(recording_id, {}) if recording_id else {}
        moment = self._build(media_id, target, poster, context, source)
        self.moments.append(moment)
        self.emit("media_stored", {"media_id": media_id, "bytes": len(data),
                                   "moment": moment["id"], "has_poster": poster is not None})
        return moment

    def _build(self, media_id, video, poster, context, source):
        now = time.time()
        sequence = len(self.moments) + 1
        z = context.get("z_score")
        return {
            "id": f"capture-{media_id[:8]}",
            "sequence": sequence,
            "timestamp": _iso(now),
            "eventType": "load",
            # Rank score, not a calibrated probability. The detector reports a
            # z-score against this session's own baseline; squashing it to 0..1
            # keeps the UI's ordering meaningful without implying a likelihood.
            "confidence": min(0.99, max(0.5, 0.5 + z / 30)) if z is not None else 0.5,
            "media": {
                "thumbnailUrl": f"/api/media/{poster.name}" if poster else "",
                "videoUrl": f"/api/media/{video.name}",
                "alt": "Captured point-of-view footage",
            },
            "contextWindow": {"start": _iso(now - 30), "end": _iso(now)},
            "annotation": "",
            "status": "candidate",
            "summary": self._summary(context, source),
            "detector": context or None,
        }

    def _summary(self, context, source):
        if not context:
            return f"Captured from the {source} with no detector context attached."
        z = context.get("z_score")
        at = context.get("sample_time_s")
        parts = []
        if z is not None:
            parts.append(f"z = {z:+.1f} against this session's baseline")
        if at is not None:
            parts.append(f"{at:.0f}s into the session")
        return "Sustained elevated load" + (" at " + ", ".join(parts) if parts else "") + "."

    def path_for(self, name):
        """Resolve a stored file, refusing anything that escapes the media dir."""
        candidate = (self.dir / name).resolve()
        if candidate.parent != self.dir.resolve() or not candidate.is_file():
            return None
        return candidate

    def status(self):
        return {"count": len(self.moments), "dir": str(self.dir)}
