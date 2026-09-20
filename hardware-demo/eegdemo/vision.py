"""Meta Muse Spark video understanding for durable cognitive moments."""
import base64
import json
import os
import re
import time
import urllib.error
import urllib.request


DEFAULT_URL = "https://api.meta.ai/v1/responses"
DEFAULT_MODEL = "muse-spark-1.3"
MAX_INLINE_VIDEO_BYTES = 32 * 1024 * 1024
GROUNDING_VERSION = "meta-web-v1"
EVENT_TERMS = re.compile(
    r"\b(auditorium|conference|hackathon|sponsor|stage|keynote|venue|event)\b",
    re.IGNORECASE,
)


class VisionError(RuntimeError):
    pass


class MetaVideoDescriber:
    def __init__(self, emit, *, api_key=None, url=None, model=None,
                 event_context=None, web_search=None):
        self.emit = emit
        self.api_key = api_key if api_key is not None else os.environ.get(
            "MODEL_API_KEY", "")
        self.url = url or os.environ.get("META_VIDEO_URL", DEFAULT_URL)
        self.model = model or os.environ.get("META_VIDEO_MODEL", DEFAULT_MODEL)
        self.event_context = (event_context if event_context is not None else
                              os.environ.get("MEMORYPALACE_EVENT_CONTEXT",
                                             "HackMIT 2026 at MIT")).strip()
        configured_web_search = os.environ.get("META_WEB_SEARCH", "1").lower() \
            not in ("0", "false", "no", "off")
        self.web_search = (configured_web_search if web_search is None
                           else bool(web_search))
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
                "webSearchEnabled": self.web_search,
                "eventContextConfigured": bool(self.event_context),
                "error": self.last_error}

    def needs_grounding(self, moment):
        """Upgrade older event-like descriptions once, without reprocessing the library."""
        if not self.web_search or not self.event_context:
            return False
        if moment.get("vision", {}).get("groundingVersion") == GROUNDING_VERSION:
            return False
        text = " ".join(str(value) for value in (
            moment.get("semanticTitle", ""), moment.get("aiDescription", ""),
            " ".join(moment.get("keywords", [])), " ".join(moment.get("topics", [])),
            moment.get("transcript", ""),
        ))
        return bool(EVENT_TERMS.search(text))

    @staticmethod
    def _output_text(payload):
        if isinstance(payload.get("output_text"), str):
            return payload["output_text"].strip()
        messages = []
        for item in payload.get("output", []):
            parts = [content.get("text", "") for content in item.get("content", [])
                     if content.get("type") in ("output_text", "text")
                     and content.get("text")]
            if parts:
                messages.append("\n".join(parts))
        # Tool-using Responses can emit brief progress messages before the final answer.
        return messages[-1].strip() if messages else ""

    @staticmethod
    def _json_output(text):
        text = text.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
            if text.lstrip().startswith("json"):
                text = text.lstrip()[4:].lstrip()
        return json.loads(text)

    @staticmethod
    def _truncate(text, limit):
        text = str(text).strip()
        if len(text) <= limit:
            return text
        shortened = text[:limit + 1].rsplit(" ", 1)[0].rstrip(" ,.;:-")
        return shortened or text[:limit]

    @staticmethod
    def _web_provenance(payload):
        used = any(item.get("type") == "web_search_call"
                   for item in payload.get("output", []) if isinstance(item, dict))
        sources = []
        seen = set()
        for item in payload.get("output", []):
            if not isinstance(item, dict):
                continue
            for content in item.get("content", []):
                for annotation in content.get("annotations", []):
                    citation = annotation.get("url_citation", annotation)
                    url = citation.get("url") if isinstance(citation, dict) else None
                    if not url or url in seen:
                        continue
                    seen.add(url)
                    sources.append({
                        "title": str(citation.get("title", "Public web source"))[:160],
                        "url": str(url)[:1000],
                    })
        return used, sources[:6]

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

    @staticmethod
    def _schema():
        return {
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

    def _ground_semantics(self, data, context):
        """Resolve public proper nouns separately from private media perception."""
        payload = {
            "model": self.model,
            "instructions": (
                "Ground public context for a first-person memory. You must use web search "
                "to verify any public event, organization, venue, or product name. The "
                "operator context is a clue, not proof. Use a proper noun only when the "
                "observed description, transcript, or public results support it. Otherwise "
                "keep the original generic wording. Preserve all factual visible details. "
                "Do not infer identity, emotion, diagnosis, intent, or private attributes. "
                "Return one compact JSON object only, without Markdown or commentary, with "
                "exactly these keys: title, description, keywords, topics, sourceUrls. "
                "sourceUrls must contain only public pages actually used for verification."
            ),
            "input": (
                f"Operator context: {self.event_context}\n"
                f"Capture timestamp: {context.get('timestamp', 'unknown')}\n"
                f"Fresh media analysis: {json.dumps(data, allow_nan=False)}\n"
                f"Existing catalog title: {context.get('existingTitle', '')}\n"
                f"Existing catalog description: {context.get('existingDescription', '')}\n"
                f"Recorded transcript: {context.get('transcript', '')}"
            ),
            "tools": [{"type": "web_search"}],
            "tool_choice": "auto",
            "reasoning": {"effort": "low"},
            "max_output_tokens": 4000,
        }
        result = self._request(payload)
        grounded = self._json_output(self._output_text(result))
        used, sources = self._web_provenance(result)
        for url in grounded.pop("sourceUrls", []):
            url = str(url)
            if url and not any(source["url"] == url for source in sources):
                sources.append({"title": "Public web source", "url": url[:1000]})
        return grounded, used, sources

    def describe(self, path, context=None):
        if not self.configured:
            raise VisionError("set MODEL_API_KEY")
        if not self.available:
            raise VisionError(self.last_error or "Meta video understanding is unavailable")
        size = path.stat().st_size
        if size > MAX_INLINE_VIDEO_BYTES:
            raise VisionError(
                f"video is {size} bytes; inline Meta enrichment limit is "
                f"{MAX_INLINE_VIDEO_BYTES} bytes")
        suffix = path.suffix.lower()
        is_image = suffix in (".jpg", ".jpeg", ".png")
        mime = ({".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}
                .get(suffix, "video/quicktime" if suffix == ".mov" else "video/mp4"))
        media_url = f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"
        media_block = ({"type": "input_image", "image_url": media_url}
                       if is_image else {"type": "input_video", "video_url": media_url})
        context = context or {}
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
                        "Describe this captured moment for semantic memory search. "
                        f"Capture timestamp: {context.get('timestamp', 'unknown')}."
                    )},
                    media_block,
                ],
            }],
            "text": {"format": {"type": "json_schema", "name": "memory_moment",
                                  "strict": True, "schema": self._schema()}},
            # Muse Spark reasoning and visible JSON share this budget. A small cap can
            # complete reasoning without leaving room for the output object.
            "max_output_tokens": 3000,
        }
        try:
            result = self._request(payload)
            text = self._output_text(result)
            data = self._json_output(text)
            web_search_used = False
            web_sources = []
            grounding_status = "disabled"
            grounding_error = None
            grounding_input = " ".join((
                str(data.get("title", "")), str(data.get("description", "")),
                " ".join(str(item) for item in data.get("keywords", [])),
                " ".join(str(item) for item in data.get("topics", [])),
                str(context.get("existingTitle", "")),
                str(context.get("existingDescription", "")),
                str(context.get("transcript", "")),
            ))
            if (self.web_search and self.event_context
                    and EVENT_TERMS.search(grounding_input)):
                try:
                    data, web_search_used, web_sources = self._ground_semantics(data, context)
                    grounding_status = "complete"
                except (VisionError, KeyError, TypeError, ValueError,
                        json.JSONDecodeError) as exc:
                    grounding_status = "failed"
                    grounding_error = str(exc)[:300]
                    self.emit("meta_web_grounding_failed", {"error": grounding_error})
            elif self.web_search and self.event_context:
                grounding_status = "not_relevant"
            title = self._truncate(data["title"], 80)
            description = self._truncate(data["description"], 600)
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
                "source": "poster" if is_image else "video",
                "contextHint": self.event_context or None,
                "webSearchEnabled": self.web_search,
                "webSearchUsed": web_search_used,
                "webSources": web_sources,
                "groundingStatus": grounding_status,
            }
            if grounding_status in ("complete", "not_relevant"):
                output["groundingVersion"] = GROUNDING_VERSION
            elif grounding_error:
                output["groundingError"] = grounding_error
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            self.last_error = f"Meta video understanding response failed: {exc}"
            raise VisionError(self.last_error) from exc
        self.last_error = None
        self.emit("meta_video_described", {
            "model": self.model, "title": output["title"],
            "keywords": len(output["keywords"]), "source": output["source"],
            "web_search_used": output["webSearchUsed"],
        })
        return output
