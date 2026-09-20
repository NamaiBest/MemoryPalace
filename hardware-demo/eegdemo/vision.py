"""Meta Muse Spark video understanding for durable cognitive moments."""
import base64
import json
import os
import time
import urllib.error
import urllib.request


DEFAULT_URL = "https://api.meta.ai/v1/responses"
DEFAULT_MODEL = "muse-spark-1.3"
MAX_INLINE_VIDEO_BYTES = 32 * 1024 * 1024


class VisionError(RuntimeError):
    pass


class MetaVideoDescriber:
    def __init__(self, emit, *, api_key=None, url=None, model=None):
        self.emit = emit
        self.api_key = api_key if api_key is not None else os.environ.get(
            "MODEL_API_KEY", "")
        self.url = url or os.environ.get("META_VIDEO_URL", DEFAULT_URL)
        self.model = model or os.environ.get("META_VIDEO_MODEL", DEFAULT_MODEL)
        self.available = True
        self.last_error = None

    @property
    def configured(self):
        return bool(self.api_key)

    @property
    def enabled(self):
        return self.configured and self.available

    def status(self):
        return {"provider": "meta", "model": self.model,
                "configured": self.configured, "available": self.available,
                "error": self.last_error}

    @staticmethod
    def _output_text(payload):
        if isinstance(payload.get("output_text"), str):
            return payload["output_text"].strip()
        return "\n".join(
            content.get("text", "")
            for item in payload.get("output", [])
            for content in item.get("content", [])
            if content.get("type") in ("output_text", "text")
        ).strip()

    @staticmethod
    def _json_output(text):
        text = text.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
            if text.lstrip().startswith("json"):
                text = text.lstrip()[4:].lstrip()
        return json.loads(text)

    def _request(self, payload):
        encoded = json.dumps(payload, allow_nan=False).encode()
        for attempt in range(3):
            request = urllib.request.Request(
                self.url, data=encoded, method="POST",
                headers={"Authorization": f"Bearer {self.api_key}",
                         "Content-Type": "application/json", "Accept": "application/json"},
            )
            try:
                with urllib.request.urlopen(request, timeout=150) as response:
                    return json.loads(response.read())
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode(errors="replace")[:500]
                self.last_error = (
                    f"Meta video understanding returned HTTP {exc.code}: {detail}")
                if exc.code in (401, 402, 403):
                    self.available = False
                    raise VisionError(self.last_error) from exc
                if exc.code not in (429, 500, 502, 503, 504) or attempt == 2:
                    raise VisionError(self.last_error) from exc
            except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as exc:
                self.last_error = f"Meta video understanding connection failed: {exc}"
                if attempt == 2:
                    raise VisionError(self.last_error) from exc
            time.sleep(1.5 * (attempt + 1))
        raise VisionError(self.last_error or "Meta video understanding request failed")

    def describe(self, path):
        if not self.configured:
            raise VisionError("set MODEL_API_KEY")
        if not self.available:
            raise VisionError(self.last_error or "Meta video understanding is unavailable")
        size = path.stat().st_size
        if size > MAX_INLINE_VIDEO_BYTES:
            raise VisionError(
                f"video is {size} bytes; inline Meta enrichment limit is "
                f"{MAX_INLINE_VIDEO_BYTES} bytes")
        mime = "video/quicktime" if path.suffix.lower() == ".mov" else "video/mp4"
        video_url = f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"
        schema = {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "title": {"type": "string", "maxLength": 80},
                "description": {"type": "string", "maxLength": 600},
                "keywords": {"type": "array", "items": {"type": "string"},
                             "maxItems": 10},
                "topics": {"type": "array", "items": {"type": "string"},
                           "maxItems": 6},
            },
            "required": ["title", "description", "keywords", "topics"],
        }
        payload = {
            "model": self.model,
            "instructions": (
                "Analyze this first-person memory clip conservatively. Return a short, "
                "specific title and a factual description of visible actions, objects, "
                "setting, and useful context. Include only grounded keywords and topics. "
                "Do not infer identity, emotion, diagnosis, or private attributes."
            ),
            "input": [{
                "type": "message", "role": "user", "content": [
                    {"type": "input_text", "text": (
                        "Describe this captured moment for semantic memory search."
                    )},
                    {"type": "input_video", "video_url": video_url},
                ],
            }],
            "text": {"format": {"type": "json_schema", "name": "memory_moment",
                                  "strict": True, "schema": schema}},
            # Muse Spark reasoning and visible JSON share this budget. A small cap can
            # complete reasoning without leaving room for the output object.
            "max_output_tokens": 3000,
        }
        try:
            result = self._request(payload)
            text = self._output_text(result)
            data = self._json_output(text)
            title = str(data["title"]).strip()[:80]
            description = str(data["description"]).strip()[:600]
            if not title or not description:
                raise ValueError("title and description must not be empty")
            output = {
                "title": title,
                "description": description,
                "keywords": [str(item).strip()[:60] for item in data["keywords"][:10]
                             if str(item).strip()],
                "topics": [str(item).strip()[:60] for item in data["topics"][:6]
                           if str(item).strip()],
                "provider": "meta", "model": self.model, "status": "complete",
            }
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            self.last_error = f"Meta video understanding response failed: {exc}"
            raise VisionError(self.last_error) from exc
        self.last_error = None
        self.emit("meta_video_described", {
            "model": self.model, "title": output["title"],
            "keywords": len(output["keywords"]),
        })
        return output
