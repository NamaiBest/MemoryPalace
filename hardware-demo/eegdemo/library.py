"""Captured media and the moments built from it.

The phone finalises a recording locally and only reports a content:// URI, which
nothing off the device can open. It then uploads the bytes here, and this module
pairs them with the detector context that caused the stop, producing the Moment
records the web UI renders.
"""
import json
import os
import re
import shutil
import subprocess
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

POSTER_SECONDS = 1.0
RETRY_INTERVAL_S = 120
POSTER_TIMEOUT = 20
MAX_UPLOAD_BYTES = 512 * 1024 * 1024
META_DIRECT_VIDEO_BYTES = 6 * 1024 * 1024

SUFFIXES = {"video/mp4": ".mp4", "video/quicktime": ".mov", "image/jpeg": ".jpg",
            "image/png": ".png"}


def _iso(ts):
    return datetime.fromtimestamp(ts, timezone.utc).isoformat().replace("+00:00", "Z")


class Library:
    def __init__(self, output, emit, elastic=None, vision=None, storage=None,
                 legacy_runs=None, session_id=None, user_id=None):
        self.dir = Path(storage) if storage else Path(output) / "media"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.emit = emit
        self.elastic = elastic
        self.vision = vision
        self.lock = threading.RLock()
        self.session_id = session_id or Path(output).name
        self.user_id = user_id or os.environ.get("MEMORYPALACE_USER_ID", "demo-user")
        self.catalog = self.dir / "moments.json"
        self.moments = self._load_catalog()
        if self._normalize_moments():
            self._persist()
        self.contexts = {}
        if legacy_runs:
            self._migrate_legacy_runs(Path(legacy_runs))
        if ((self.elastic and self.elastic.configured)
                or (self.vision and self.vision.configured)):
            if self.moments:
                threading.Thread(target=self._enrich_and_index_all, daemon=True,
                                 name="memory-library-enrichment").start()
            self._start_retry_loop()

    def _load_catalog(self):
        if not self.catalog.exists():
            return []
        try:
            data = json.loads(self.catalog.read_text())
            if not isinstance(data, list) or not all(isinstance(item, dict) for item in data):
                raise ValueError("catalog must be an array of moment objects")
            return data
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            backup = self.catalog.with_suffix(".json.bak")
            try:
                data = json.loads(backup.read_text())
                if isinstance(data, list):
                    self.emit("memory_catalog_recovered", {"backup": str(backup),
                                                            "count": len(data)})
                    return data
            except (OSError, ValueError, json.JSONDecodeError):
                pass
            raise RuntimeError(f"memory catalog is unreadable: {exc}") from exc

    def _persist(self):
        """Atomically replace the catalog while retaining one recoverable generation."""
        temporary = self.catalog.with_suffix(".json.tmp")
        backup = self.catalog.with_suffix(".json.bak")
        payload = json.dumps(self.moments, indent=2, allow_nan=False)
        with temporary.open("w") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        if self.catalog.exists():
            shutil.copy2(self.catalog, backup)
        os.replace(temporary, self.catalog)

    @staticmethod
    def _keywords(text, limit=12):
        stop = {"about", "after", "again", "from", "have", "into", "moment", "that",
                "their", "there", "these", "this", "with", "would", "your"}
        words = re.findall(r"[a-zA-Z][a-zA-Z0-9'-]{2,}", text.lower())
        counts = {}
        for word in words:
            if word not in stop:
                counts[word] = counts.get(word, 0) + 1
        return [word for word, _ in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
                [:limit]]

    def _normalize_moments(self):
        """Add new searchable fields without replacing any existing memory data."""
        changed = False
        for moment in self.moments:
            defaults = {
                "sessionId": "legacy-import",
                "userId": self.user_id,
                "spikeIntensity": moment.get("confidence", 0.5),
                "spikeConfidence": moment.get("confidence", 0.5),
                "aiDescription": moment.get("summary", ""),
                "semanticTitle": self._fallback_title(moment),
                "keywords": self._keywords(
                    " ".join((moment.get("summary", ""), moment.get("transcript", "")))),
                "topics": [],
                "transcript": "",
                "processing": {
                    "extraction": "complete",
                    "analysis": "pending" if self.vision and self.vision.configured
                    else "not_configured",
                    "indexing": "pending" if self.elastic and self.elastic.configured
                    else "not_configured",
                },
            }
            for key, value in defaults.items():
                if key not in moment:
                    moment[key] = value
                    changed = True
            processing = moment.setdefault("processing", {})
            for key, value in defaults["processing"].items():
                if key not in processing:
                    processing[key] = value
                    changed = True
        return changed

    @staticmethod
    def _fallback_title(moment):
        existing = str(moment.get("semanticTitle", "")).strip()
        if existing:
            return existing[:80]
        transcript = re.sub(r"\s+", " ", str(moment.get("transcript", ""))).strip()
        if transcript:
            words = transcript.split()[:9]
            title = " ".join(words).rstrip(".,!?;:")
            return (title[:77] + "…") if len(title) > 78 else title
        event = moment.get("eventType", "load")
        labels = {"surprise": "Unexpected moment", "excitement": "Exciting moment",
                  "capture": "Live captured moment",
                  "insight": "Insight moment",
                  "error": "Correction moment", "load": "Focused moment"}
        return labels.get(event, "Captured moment")

    @staticmethod
    def _read_events(path):
        if not path.is_file():
            return []
        events = []
        try:
            with path.open() as handle:
                for line in handle:
                    if line.strip():
                        events.append(json.loads(line))
        except (OSError, json.JSONDecodeError):
            return []
        return sorted(events, key=lambda event: event.get("wall_time", 0))

    def _legacy_contexts(self, events):
        demos, starts, stops, loads = {}, {}, [], []
        for event in events:
            kind, detail = event.get("type"), event.get("detail", {})
            when = event.get("wall_time", 0)
            if kind == "demo_capture_requested" and detail.get("recording_id"):
                demos[detail["recording_id"]] = dict(detail)
            elif kind == "command_acknowledged" and detail.get("recording_id"):
                recording_id = detail["recording_id"]
                if detail.get("state") == "recording":
                    starts[recording_id] = when
                elif (detail.get("state") == "stopped" and detail.get("media_path")
                      and recording_id in starts):
                    stops.append({"recording_id": recording_id, "wall_time": when})
            elif kind == "load_trigger":
                loads.append({"wall_time": when, "detail": dict(detail)})
        return demos, starts, stops, loads

    def _migrate_legacy_runs(self, runs):
        """Copy pre-catalog captures into the durable library without deleting originals."""
        if not runs.is_dir():
            return
        known = {moment.get("id") for moment in self.moments}
        imported = []
        for run in sorted(path for path in runs.iterdir() if path.is_dir()):
            media_dir = run / "media"
            if not media_dir.is_dir():
                continue
            events = self._read_events(run / "events.jsonl")
            demos, starts, stops, loads = self._legacy_contexts(events)
            used_recordings = set()
            media_events = [event for event in events if event.get("type") == "media_stored"]
            by_id = {event.get("detail", {}).get("media_id"): event for event in media_events}
            for source in sorted(media_dir.glob("*.mp4"), key=lambda path: path.stat().st_mtime):
                media_id = source.stem
                moment_id = f"capture-{media_id[:8]}"
                if moment_id in known:
                    continue
                event = by_id.get(media_id, {})
                captured_at = event.get("wall_time", source.stat().st_mtime)
                candidates = [stop for stop in stops
                              if stop["recording_id"] not in used_recordings
                              and stop["wall_time"] <= captured_at]
                stop = candidates[0] if candidates else None
                recording_id = stop["recording_id"] if stop else None
                if recording_id:
                    used_recordings.add(recording_id)
                context = dict(demos.get(recording_id, {}))
                if context:
                    context.update({"demo": True,
                                    "duration_seconds": context.pop("seconds", 10)})
                elif recording_id:
                    start, finish = starts[recording_id], stop["wall_time"]
                    matching = [load for load in loads if start <= load["wall_time"] <= finish]
                    if matching:
                        context = dict(matching[-1]["detail"])
                if recording_id and not context.get("started_at"):
                    context["started_at"] = starts[recording_id]

                target = self.dir / source.name
                if not target.exists():
                    shutil.copy2(source, target)
                poster_source = source.with_suffix(".jpg")
                poster = self.dir / poster_source.name
                if poster_source.is_file() and not poster.exists():
                    shutil.copy2(poster_source, poster)
                if not poster.is_file():
                    poster = None

                z = context.get("z_score")
                sequence = max((item.get("sequence", 0) for item in self.moments), default=0) + 1
                moment = {
                    "id": moment_id,
                    "sequence": sequence,
                    "timestamp": _iso(captured_at),
                    "eventType": context.get("demo_event", "load"),
                    "demo": bool(context.get("demo")),
                    "confidence": min(0.99, max(0.5, 0.5 + z / 30))
                        if z is not None else 0.5,
                    "spikeIntensity": min(0.99, max(0.5, 0.5 + z / 30))
                        if z is not None else 0.5,
                    "spikeConfidence": 0.95 if context.get("demo") else 0.5,
                    "sessionId": run.name,
                    "userId": self.user_id,
                    "media": {
                        "thumbnailUrl": f"/api/media/{poster.name}" if poster else "",
                        "videoUrl": f"/api/media/{target.name}",
                        "alt": "Captured point-of-view footage",
                    },
                    "contextWindow": {
                        "start": _iso(context.get("started_at", captured_at)),
                        "end": _iso(context.get("started_at", captured_at)
                                    + context.get("duration_seconds", 0)),
                    },
                    "annotation": "",
                    "status": "candidate",
                    "summary": self._summary(context, "legacy capture"),
                    "semanticTitle": self._fallback_title({
                        "eventType": context.get("demo_event", "load"),
                    }),
                    "aiDescription": self._summary(context, "legacy capture"),
                    "keywords": self._keywords(self._summary(context, "legacy capture")),
                    "topics": [],
                    "transcript": "",
                    "processing": {
                        "extraction": "complete",
                        "analysis": "pending" if self.vision and self.vision.configured
                        else "not_configured",
                        "indexing": "pending" if self.elastic and self.elastic.configured
                        else "not_configured",
                    },
                    "detector": context or None,
                    "recordingId": recording_id,
                }
                self.moments.append(moment)
                known.add(moment_id)
                imported.append(moment_id)
        if imported:
            self._persist()
            self.emit("legacy_memories_imported", {"count": len(imported),
                                                   "moments": imported})

    def _start_retry_loop(self):
        """Re-run the sweep periodically, so a transient failure heals without a restart.

        Enrichment and indexing already run in the background the moment a clip lands,
        and the sweep at startup picks up anything left incomplete. What was missing is
        the middle: a Meta call that dropped on a broken pipe, or an Elastic write that
        timed out, stayed "failed" for the life of the backend, and only a restart —
        which happened to re-run the sweep — ever fixed it. That read as indexing being
        something someone had to ask for. The sweep only touches moments that are not
        complete, so once everything is done each pass costs a list scan and nothing else.
        """
        def loop():
            while True:
                time.sleep(RETRY_INTERVAL_S)
                try:
                    self._enrich_and_index_all()
                except Exception as exc:  # never let the retry thread itself die
                    self.emit("retry_sweep_failed", {"error": str(exc)[:200]})
        threading.Thread(target=loop, daemon=True, name="memory-library-retry").start()

    def _enrich_and_index_all(self):
        for moment in list(self.moments):
            if moment.get("status") == "deleted":
                self._purge_deleted(moment)
                continue
            needs_analysis = (self.vision and self.vision.enabled
                              and (moment.get("vision", {}).get("status") != "complete"
                                   or self.vision.needs_grounding(moment)))
            needs_index = (self.elastic and self.elastic.configured
                           and moment.get("processing", {}).get("indexing") != "complete")
            if not needs_analysis and not needs_index:
                continue
            video_url = moment.get("media", {}).get("videoUrl", "")
            media_path = self.path_for(video_url.rsplit("/", 1)[-1]) if video_url else None
            self._enrich_and_index(moment["id"], media_path)

    def _purge_deleted(self, moment):
        """Make a local deletion stick in Elastic, retrying until it does.

        Deleting a moment removes it locally and asks Elastic to drop its document. If
        that request fails, the document stays behind carrying whatever status it had
        when it was indexed, which is "candidate". Search excludes documents whose own
        status says "deleted", so a document that never received the delete is not
        excluded by anything: the moment keeps coming back in search and in Memory
        Guard's retrieval after the person deleted it.

        Nothing retried that, so a delete issued during an Elastic outage was lost for
        good. This runs on the same sweep as enrichment and indexing, so the deletion
        heals the moment Elastic is reachable again. "purged" marks the ones that are
        done, so a completed deletion is not retried on every pass.
        """
        if not (self.elastic and self.elastic.configured):
            return
        processing = moment.get("processing") or {}
        if processing.get("indexing") != "complete":
            return
        try:
            self.elastic.delete_moment(moment["id"])
        except Exception as exc:
            self.emit("elastic_purge_failed", {
                "moment": moment["id"], "error": str(exc)[:200],
            })
            return
        with self.lock:
            for stored in self.moments:
                if stored["id"] == moment["id"]:
                    stored.setdefault("processing", {})["indexing"] = "purged"
                    break
            self._persist()
        self.emit("elastic_moment_purged", {"moment": moment["id"]})

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
        moment["recordingId"] = recording_id
        with self.lock:
            self.moments.append(moment)
            self._persist()
        self.emit("media_stored", {"media_id": media_id, "bytes": len(data),
                                   "moment": moment["id"], "has_poster": poster is not None})
        if ((self.elastic and self.elastic.configured)
                or (self.vision and self.vision.configured)):
            # The phone must receive its upload acknowledgement immediately. Sponsor
            # inference runs after durable capture and never blocks or deletes media.
            threading.Thread(target=self._enrich_and_index,
                             args=(moment["id"], target), daemon=True,
                             name=f"enrich-{moment['id']}").start()
        return moment

    def _enrich_and_index(self, moment_id, media_path):
        with self.lock:
            moment = next((item for item in self.moments if item["id"] == moment_id), None)
            if moment is None or moment.get("status") == "deleted":
                return
            current = dict(moment)
        vision_status = current.get("vision", {}).get("status")
        needs_grounding = (self.vision and self.vision.enabled
                           and self.vision.needs_grounding(current))
        if (media_path and self.vision and self.vision.enabled
                and (vision_status != "complete" or needs_grounding)):
            current = self._enrich_meta(moment_id, media_path)
        elif self.vision and self.vision.configured and vision_status != "complete":
            with self.lock:
                moment = next((item for item in self.moments
                               if item["id"] == moment_id), None)
                if moment is not None:
                    moment.setdefault("processing", {})["analysis"] = "failed"
                    moment["vision"] = {
                        "provider": "meta", "model": self.vision.model,
                        "status": "failed",
                        "error": self.vision.last_error or "video is unavailable",
                    }
                    self._persist()
                    current = dict(moment)
        if self.elastic and self.elastic.configured:
            with self.lock:
                stored = next((item for item in self.moments
                               if item["id"] == moment_id), None)
                deleted = stored is None or stored.get("status") == "deleted"
            if not deleted:
                self._index_elastic(current, media_path)

    def _enrich_meta(self, moment_id, media_path):
        try:
            with self.lock:
                stored = next((item for item in self.moments
                               if item["id"] == moment_id), {})
                poster_url = stored.get("media", {}).get("thumbnailUrl", "")
            poster_path = self.path_for(poster_url.rsplit("/", 1)[-1]) \
                if poster_url else None
            analysis_path = (poster_path if poster_path
                             and media_path.stat().st_size > META_DIRECT_VIDEO_BYTES
                             else media_path)
            result = self.vision.describe(analysis_path, context={
                "timestamp": stored.get("timestamp"),
                "existingTitle": stored.get("semanticTitle"),
                "existingDescription": stored.get("aiDescription"),
                "transcript": stored.get("transcript", "")[:1600],
            })
            with self.lock:
                moment = next((item for item in self.moments
                               if item["id"] == moment_id), None)
                if moment is None:
                    return {}
                moment["semanticTitle"] = result.pop("title")
                moment["aiDescription"] = result.pop("description")
                moment["keywords"] = result.pop("keywords")
                moment["topics"] = result.pop("topics")
                moment["vision"] = result
                moment.setdefault("processing", {})["analysis"] = "complete"
                if self.elastic and self.elastic.configured:
                    moment["processing"]["indexing"] = "pending"
                self._persist()
                updated = dict(moment)
            self.emit("moment_semantics_saved", {
                "moment": moment_id, "title": updated["semanticTitle"],
                "provider": "meta",
            })
            return updated
        except Exception as exc:
            with self.lock:
                moment = next((item for item in self.moments
                               if item["id"] == moment_id), None)
                if moment is None:
                    return {}
                moment["vision"] = {
                    "provider": "meta", "model": self.vision.model,
                    "status": "failed", "error": str(exc)[:300],
                }
                moment.setdefault("processing", {})["analysis"] = "failed"
                self._persist()
                updated = dict(moment)
            self.emit("meta_video_description_failed", {
                "moment": moment_id, "error": str(exc)[:500],
            })
            return updated

    def _index_elastic(self, moment, media_path=None):
        try:
            self.elastic.index_moment(moment, media_path)
            with self.lock:
                current = next((item for item in self.moments
                                if item["id"] == moment["id"]), None)
                deleted = current is None or current.get("status") == "deleted"
                if current is not None and not deleted:
                    current.setdefault("processing", {})["indexing"] = "complete"
                    self._persist()
            # A delete can race an embedding request already in flight. Deleting the
            # just-written document again closes that window deterministically.
            if deleted:
                self.elastic.delete_moment(moment["id"])
        except Exception as exc:
            # Elastic enrichment is additive. Never lose a real camera capture
            # because the sponsor service or network is unavailable.
            self.emit("elastic_index_failed", {"moment": moment["id"],
                                                "error": str(exc)[:500]})
            with self.lock:
                current = next((item for item in self.moments
                                if item["id"] == moment["id"]), None)
                if current is not None and current.get("status") != "deleted":
                    current.setdefault("processing", {})["indexing"] = "failed"
                    self._persist()

    def delete_moment(self, moment_id):
        """Soft-delete one moment durably while retaining the original media files."""
        with self.lock:
            moment = next((item for item in self.moments
                           if item.get("id") == moment_id), None)
            if moment is None:
                raise ValueError("moment not found")
            if moment.get("status") != "deleted":
                moment["status"] = "deleted"
                moment["deletedAt"] = _iso(time.time())
                self._persist()
            deleted = dict(moment)

        elastic_removed = False
        if self.elastic and self.elastic.configured:
            try:
                self.elastic.delete_moment(moment_id)
                elastic_removed = True
                # Every other writer mutates the catalog under the lock, so this one does
                # too. "purged" stops the retry sweep re-deleting a document that is gone.
                with self.lock:
                    moment.setdefault("processing", {})["indexing"] = "purged"
                    self._persist()
            except Exception as exc:
                # Deliberately left for the retry sweep. Search filters on the document's
                # own status field, so a document that never received this delete still
                # reads "candidate" and is not filtered by anything. The deletion has to
                # actually reach Elastic; it cannot be assumed away.
                self.emit("elastic_delete_failed", {
                    "moment": moment_id, "error": str(exc)[:500],
                })
        self.emit("moment_deleted", {
            "moment": moment_id, "media_retained": True,
            "elastic_removed": elastic_removed,
        })
        return deleted

    def _build(self, media_id, video, poster, context, source):
        now = time.time()
        sequence = max((moment.get("sequence", 0) for moment in self.moments), default=0) + 1
        z = context.get("z_score")
        intensity = min(0.99, max(0.5, 0.5 + z / 30)) if z is not None else 0.5
        summary = self._summary(context, source)
        return {
            "id": f"capture-{media_id[:8]}",
            "sequence": sequence,
            "timestamp": _iso(now),
            "eventType": context.get("demo_event", "load"),
            "demo": bool(context.get("demo")),
            # Rank score, not a calibrated probability. The detector reports a
            # z-score against this session's own baseline; squashing it to 0..1
            # keeps the UI's ordering meaningful without implying a likelihood.
            "confidence": intensity,
            "spikeIntensity": intensity,
            "spikeConfidence": context.get(
                "spike_confidence", 0.95 if context.get("demo") else 0.5),
            "sessionId": self.session_id,
            "userId": self.user_id,
            "media": {
                "thumbnailUrl": f"/api/media/{poster.name}" if poster else "",
                "videoUrl": f"/api/media/{video.name}",
                "alt": "Captured point-of-view footage",
            },
            "contextWindow": {
                "start": _iso(context.get("started_at", now - 30)),
                "end": _iso(context["started_at"] + context.get("duration_seconds", 30))
                    if "started_at" in context else _iso(now)},
            "annotation": "",
            "status": "candidate",
            "summary": summary,
            "semanticTitle": self._fallback_title({
                "eventType": context.get("demo_event", "load"),
            }),
            "aiDescription": summary,
            "keywords": self._keywords(summary),
            "topics": [],
            "transcript": "",
            "processing": {
                "extraction": "complete",
                "analysis": "pending" if self.vision and self.vision.configured
                else "not_configured",
                "indexing": "pending" if self.elastic and self.elastic.configured
                else "not_configured",
            },
            "detector": context or None,
        }

    def _summary(self, context, source):
        if context.get("demo"):
            label = ({"surprise": "surprise", "excitement": "excitement"}
                     .get(context.get("demo_event"), "neural spike"))
            return f"A {context['duration_seconds']}-second moment captured with the {label} demo trigger."
        if context.get("manual_capture"):
            return (f"A {context.get('duration_seconds', 10)}-second live moment recorded "
                    "manually with the phone camera.")
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

    def attach_keepsake(self, moment_id, data, fmt):
        """Store a generated keepsake beside the moment's own media and record its URL.

        It lives in the same media directory as the clip and poster so the existing
        /media route serves it with no new plumbing, and it is written into the durable
        catalog so a restart does not lose it.
        """
        suffix = {"webp": ".webp", "png": ".png", "jpeg": ".jpg", "jpg": ".jpg"}.get(fmt, ".webp")
        # Same <32 hex>.<ext> shape as every other stored file, so the media route's
        # strict name check does not have to be loosened to serve keepsakes.
        name = f"{uuid.uuid4().hex}{suffix}"
        (self.dir / name).write_bytes(data)
        url = f"/api/media/{name}"
        with self.lock:
            moment = next((item for item in self.moments
                           if item.get("id") == moment_id), None)
            if moment is None:
                raise ValueError("moment not found")
            moment["keepsakeUrl"] = url
            moment["keepsakeCreatedAt"] = _iso(time.time())
            self._persist()
            return dict(moment)

    def path_for(self, name):
        """Resolve a stored file, refusing anything that escapes the media dir."""
        candidate = (self.dir / name).resolve()
        if candidate.parent != self.dir.resolve() or not candidate.is_file():
            return None
        return candidate

    def status(self):
        return {"count": len(self.moments), "dir": str(self.dir),
                "persistent": self.catalog.exists(), "catalog": str(self.catalog)}
