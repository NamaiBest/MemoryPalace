"""The evening email: what your day held, if you never went back to look at it.

MemoryPalace only works if someone actually opens it. Capture is automatic, review is
not, and a gallery nobody revisits is just a hard drive. This closes that loop by sending
the day's recap, written by Meta Muse Spark, to the person who lived it.

It only sends when the day went unreviewed. If you already went through your moments,
keeping some, writing a note, making a keepsake, then you do not need an email about it,
and a digest that arrives anyway trains you to ignore digests.
"""
import base64
import json
import os
import smtplib
import urllib.error
import urllib.request
import threading
import time
from datetime import datetime, timedelta
from email.message import EmailMessage
from email.utils import formataddr
from pathlib import Path
from zoneinfo import ZoneInfo


ZONE = ZoneInfo("America/New_York")
CHECK_INTERVAL_S = 600
# Gmail rejects a message over 25 MB and the mail API caps the payload at 40 MB, so the
# budget sits below both. Clips run about 4 MB each, posters about 30 KB, which is why
# every poster travels and only some clips do.
ATTACHMENT_BUDGET = 18 * 1024 * 1024


class DigestError(RuntimeError):
    pass


def _truthy(value):
    return str(value).strip().lower() in ("1", "true", "yes", "on")


class DailyDigest:
    def __init__(self, emit, library, guard, *, state_dir=None):
        self.emit = emit
        self.library = library
        self.guard = guard
        self.hour = max(0, min(23, int(os.environ.get("MEMORYPALACE_DIGEST_HOUR", "21"))))
        self.recipient = os.environ.get("MEMORYPALACE_DIGEST_TO", "").strip()
        self.sender = os.environ.get("MEMORYPALACE_DIGEST_FROM", "").strip() or self.recipient
        self.host = os.environ.get("SMTP_HOST", "").strip()
        self.port = int(os.environ.get("SMTP_PORT", "587"))
        self.user = os.environ.get("SMTP_USER", "").strip()
        self.password = os.environ.get("SMTP_PASSWORD", "")
        self.enabled = _truthy(os.environ.get("MEMORYPALACE_DIGEST_ENABLED", "0"))
        # Conference and campus networks routinely block outbound SMTP, and this one
        # does: Gmail on 587 and 465 are both unreachable while HTTPS is fine. An HTTPS
        # mail API therefore works where smtplib cannot, and takes precedence when a key
        # is present.
        self.api_key = os.environ.get("RESEND_API_KEY", "").strip()
        self.api_url = os.environ.get("RESEND_URL", "https://api.resend.com/emails")
        self.state = Path(state_dir or ".") / "digest-state.json"
        self.last_error = None

    @property
    def transport(self):
        """Which way mail can leave, if any."""
        if self.api_key and self.sender:
            return "https"
        if self.host and self.sender:
            return "smtp"
        return None

    @property
    def deliverable(self):
        """True when a message could actually be sent, not merely composed."""
        return bool(self.transport and self.recipient)

    def status(self):
        return {"enabled": self.enabled, "hour": self.hour,
                "deliverable": self.deliverable, "transport": self.transport,
                "recipientConfigured": bool(self.recipient),
                "smtpConfigured": bool(self.host),
                "lastSent": self._last_sent(), "error": self.last_error}

    # ---------------------------------------------------------------- state
    def _last_sent(self):
        try:
            return json.loads(self.state.read_text()).get("lastSent")
        except (OSError, ValueError):
            return None

    def _record_sent(self, day):
        try:
            self.state.write_text(json.dumps({"lastSent": day}))
        except OSError as exc:
            self.emit("digest_state_write_failed", {"error": str(exc)[:200]})

    # ---------------------------------------------------------------- content
    @staticmethod
    def _reviewed(moment):
        """Did the person actually engage with this moment, rather than just record it?"""
        return (moment.get("status") in ("kept", "deleted")
                or bool((moment.get("annotation") or "").strip())
                or bool(moment.get("keepsakeUrl")))

    def moments_for(self, day, days=1):
        """Every live moment in a window of local days ending on `day`, oldest first."""
        days = max(1, min(14, int(days)))
        end_day = datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=ZONE)
        start = end_day - timedelta(days=days - 1)
        end = end_day + timedelta(days=1)
        out = []
        for moment in self.library.moments:
            if moment.get("status") == "deleted":
                continue
            stamp = moment.get("timestamp")
            if not stamp:
                continue
            try:
                when = datetime.fromisoformat(stamp.replace("Z", "+00:00")).astimezone(ZONE)
            except ValueError:
                continue
            if start <= when < end:
                out.append(dict(moment))
        out.sort(key=lambda item: item.get("timestamp", ""))
        return out

    def attachments_for(self, moments):
        """Posters always, clips while they fit inside the budget.

        Every moment's poster travels because they are tiny, about 30 KB, so the mail
        always shows what the day looked like. Clips average 4 MB, so attaching them all
        would exceed what Gmail accepts. The strongest moments get their video first and
        the message says plainly how many were left behind, rather than silently
        truncating and letting the reader wonder.
        """
        files, used, skipped = [], 0, 0
        for moment in moments:
            poster = (moment.get("media") or {}).get("thumbnailUrl", "")
            path = self.library.path_for(poster.rsplit("/", 1)[-1]) if poster else None
            if path is not None:
                data = path.read_bytes()
                used += len(data)
                files.append({"filename": path.name, "content": data})
        for moment in sorted(moments, key=lambda m: -float(m.get("confidence") or 0)):
            clip = (moment.get("media") or {}).get("videoUrl", "")
            path = self.library.path_for(clip.rsplit("/", 1)[-1]) if clip else None
            if path is None:
                continue
            size = path.stat().st_size
            if used + size > ATTACHMENT_BUDGET:
                skipped += 1
                continue
            used += size
            files.append({"filename": path.name, "content": path.read_bytes()})
        return files, used, skipped

    def build(self, day=None, days=1, moment_ids=None, attach=False):
        """Compose the digest. Raises rather than sending an empty or pointless email."""
        day = day or datetime.now(ZONE).strftime("%Y-%m-%d")
        if moment_ids:
            wanted = [m for m in (dict(x) for x in self.library.moments)
                      if m.get("id") in set(moment_ids) and m.get("status") != "deleted"]
            wanted.sort(key=lambda item: item.get("timestamp", ""))
            moments = wanted
            if not moments:
                raise DigestError("none of those moments exist")
        else:
            moments = self.moments_for(day, days)
        if not moments:
            raise DigestError(f"no moments were captured on {day}")
        unreviewed = [m for m in moments if not self._reviewed(m)]
        if not self.guard.configured:
            raise DigestError(f"{self.guard.label} is not configured, so no recap can be written")
        label = day if days == 1 and not moment_ids else None
        recap = self.guard.day_recap(moments, label or f"{len(moments)} chosen moments")
        pretty = (datetime.strptime(day, "%Y-%m-%d").strftime("%A %d %B") if label
                  else (f"The last {days} days" if not moment_ids
                        else f"{len(moments)} moments you chose"))
        lines = [f"  {datetime.fromisoformat(m['timestamp'].replace('Z', '+00:00')).astimezone(ZONE):%H:%M}"
                 f"  {m.get('semanticTitle') or 'Captured moment'}" for m in moments]
        body = (
            f"{pretty}\n\n{recap['answer']}\n\n"
            f"The {len(moments)} moment{'' if len(moments) == 1 else 's'} themselves:\n"
            + "\n".join(lines)
            + "\n\nOpen them: http://127.0.0.1:3000\n"
            f"\nWritten by {recap['providerLabel']}. You are getting this because "
            f"{len(unreviewed)} of these went unreviewed today.\n"
        )
        files, bytes_used, skipped = self.attachments_for(moments) if attach else ([], 0, 0)
        if attach:
            body += (f"\n{len(files)} file{'' if len(files) == 1 else 's'} attached"
                     + (f", and {skipped} clip{'' if skipped == 1 else 's'} left out to "
                        "keep the message deliverable" if skipped else "") + ".\n")
        return {
            "day": day,
            "attachments": files,
            "attachedBytes": bytes_used,
            "clipsSkipped": skipped,
            # "Your Saturday 19 September" reads well; "Your The last 2 days" does not,
            # so the possessive is only used when the label is a single named day.
            "subject": (f"Your {pretty}" if label else pretty)
                       + f", in {len(moments)} moment"
                       + ("" if len(moments) == 1 else "s"),
            "body": body,
            "recap": recap["answer"],
            "moments": [{"id": m["id"], "title": m.get("semanticTitle"),
                         "timestamp": m.get("timestamp"),
                         "reviewed": self._reviewed(m)} for m in moments],
            "unreviewed": len(unreviewed),
            "provider": recap["providerLabel"],
            "model": recap["model"],
        }

    # ---------------------------------------------------------------- delivery
    def _send_https(self, to, subject, body, files=()):
        """Post the mail through an HTTPS API, for networks that block SMTP."""
        payload = {"from": f"MemoryPalace <{self.sender}>", "to": [to],
                   "subject": subject, "text": body}
        if files:
            payload["attachments"] = [
                {"filename": f["filename"],
                 "content": base64.b64encode(f["content"]).decode("ascii")}
                for f in files]
        request = urllib.request.Request(
            self.api_url, data=json.dumps(payload).encode(), method="POST",
            headers={"Authorization": f"Bearer {self.api_key}",
                     "Content-Type": "application/json",
                     # Without an explicit agent, urllib sends "Python-urllib/3.x",
                     # which the API's edge blocks with a Cloudflare 1010 before the
                     # request ever reaches Resend. The key was never the problem.
                     "User-Agent": "MemoryPalace/1.0",
                     "Accept": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.loads(response.read() or b"{}")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")[:300]
            raise DigestError(f"mail API returned HTTP {exc.code}: {detail}") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise DigestError(f"mail API unreachable: {exc}") from exc

    def send(self, day=None, force=False, to=None, days=1, moment_ids=None, attach=False):
        """Send the digest. `to` overrides the configured recipient for a one-off."""
        recipient = (to or self.recipient or "").strip()
        digest = self.build(day, days=days, moment_ids=moment_ids, attach=attach)
        if not force and digest["unreviewed"] == 0:
            raise DigestError("every moment that day was already reviewed, so nothing was sent")
        if not recipient:
            raise DigestError("no recipient: pass one, or set MEMORYPALACE_DIGEST_TO")
        if "@" not in recipient or len(recipient) > 254:
            raise DigestError("that does not look like an email address")
        if not self.transport:
            raise DigestError("no way to send: set RESEND_API_KEY, or SMTP_HOST, "
                              "plus MEMORYPALACE_DIGEST_FROM")

        if self.transport == "https":
            result = self._send_https(recipient, digest["subject"], digest["body"],
                                      digest.get("attachments") or ())
            self.last_error = None
            self._record_sent(digest["day"])
            self.emit("digest_sent", {"day": digest["day"], "to": recipient,
                                      "transport": "https", "id": result.get("id")})
            return {**{k: v for k, v in digest.items() if k != "attachments"},
                    "attachedFiles": len(digest.get("attachments") or []),
                    "transport": "https", "to": recipient}

        message = EmailMessage()
        message["Subject"] = digest["subject"]
        message["From"] = formataddr(("MemoryPalace", self.sender))
        message["To"] = recipient
        message.set_content(digest["body"])
        for item in digest.get("attachments") or []:
            kind = "video" if item["filename"].endswith((".mp4", ".mov")) else "image"
            sub = item["filename"].rsplit(".", 1)[-1].replace("jpg", "jpeg")
            message.add_attachment(item["content"], maintype=kind, subtype=sub,
                                   filename=item["filename"])
        try:
            # 465 is implicit TLS; 587 and 25 negotiate it, and a server that does not
            # offer STARTTLS (a local relay, a catcher during testing) still works rather
            # than failing on a hard starttls() call.
            if self.port == 465:
                with smtplib.SMTP_SSL(self.host, self.port, timeout=30) as smtp:
                    if self.user:
                        smtp.login(self.user, self.password)
                    smtp.send_message(message)
            else:
                with smtplib.SMTP(self.host, self.port, timeout=30) as smtp:
                    smtp.ehlo()
                    if smtp.has_extn("starttls"):
                        smtp.starttls()
                        smtp.ehlo()
                    if self.user:
                        smtp.login(self.user, self.password)
                    smtp.send_message(message)
        except (smtplib.SMTPException, OSError) as exc:
            self.last_error = f"sending failed: {exc}"[:300]
            self.emit("digest_send_failed", {"day": digest["day"], "error": self.last_error})
            raise DigestError(self.last_error) from exc
        self.last_error = None
        self._record_sent(digest["day"])
        self.emit("digest_sent", {"day": digest["day"], "to": recipient,
                                  "transport": "smtp",
                                  "unreviewed": digest["unreviewed"]})
        return {**{k: v for k, v in digest.items() if k != "attachments"},
                "attachedFiles": len(digest.get("attachments") or []),
                "transport": "smtp", "to": recipient}

    # ---------------------------------------------------------------- schedule
    def start(self):
        """Check periodically rather than sleeping until the hour, so a laptop that was
        closed over the send time still sends once it wakes."""
        if not self.enabled:
            return
        def loop():
            while True:
                try:
                    now = datetime.now(ZONE)
                    day = now.strftime("%Y-%m-%d")
                    if now.hour >= self.hour and self._last_sent() != day:
                        try:
                            self.send(day)
                        except DigestError as exc:
                            # A quiet day or an unconfigured mailer is not an error worth
                            # retrying every ten minutes, so the day is marked done.
                            self.emit("digest_skipped", {"day": day, "reason": str(exc)[:200]})
                            self._record_sent(day)
                except Exception as exc:  # never let the scheduler thread die
                    self.emit("digest_loop_failed", {"error": str(exc)[:200]})
                time.sleep(CHECK_INTERVAL_S)
        threading.Thread(target=loop, daemon=True, name="memorypalace-digest").start()
        self.emit("digest_scheduled", {"hour": self.hour, "deliverable": self.deliverable})
