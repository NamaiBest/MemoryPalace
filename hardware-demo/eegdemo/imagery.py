"""Meta Muse Image: a keepsake illustration for a moment worth keeping.

Deliberately illustrative, never photoreal. The point of this image is to be a memento
of a moment, and a photoreal render of something the camera did not see would be a
fabricated memory sitting next to a real one in the same gallery. The style instruction
is part of the safety of the feature, not decoration.
"""
import base64
import json
import os
import urllib.error
import urllib.request


DEFAULT_URL = "https://api.meta.ai/v1/images/generations"
DEFAULT_MODEL = "muse-image-1.0"
MAX_PROMPT = 1200


class ImageryError(RuntimeError):
    pass


class MetaKeepsakeArtist:
    def __init__(self, emit, *, api_key=None, url=None, model=None):
        self.emit = emit
        self.api_key = api_key if api_key is not None else os.environ.get("MODEL_API_KEY", "")
        self.url = url or os.environ.get("META_IMAGE_URL", DEFAULT_URL)
        self.model = model or os.environ.get("META_IMAGE_MODEL", DEFAULT_MODEL)
        self.last_error = None

    @property
    def configured(self):
        return bool(self.api_key)

    def status(self):
        return {"provider": "meta", "model": self.model,
                "configured": self.configured, "error": self.last_error}

    @staticmethod
    def prompt_for(moment):
        """Build the prompt from what the camera actually saw, and nothing else."""
        title = (moment.get("semanticTitle") or "").strip()
        description = (moment.get("aiDescription") or moment.get("summary") or "").strip()
        keywords = ", ".join(moment.get("keywords", [])[:6])
        scene = ". ".join(part for part in (title, description) if part)[:700]
        return (
            "A quiet editorial illustration of this remembered scene, in the style of a "
            "keepsake: soft ink linework with muted watercolour washes, warm ivory paper, "
            "brass and slate accents, generous negative space, calm and unhurried. "
            "Clearly an illustration and never a photograph. No text, no captions, no "
            "watermark, no logos, and no recognisable faces.\n\n"
            f"The scene: {scene}\n"
            + (f"Details present: {keywords}" if keywords else "")
        )[:MAX_PROMPT]

    def keepsake(self, moment):
        if not self.configured:
            raise ImageryError("set MODEL_API_KEY")
        payload = {"model": self.model, "prompt": self.prompt_for(moment)}
        request = urllib.request.Request(
            self.url,
            data=json.dumps(payload, allow_nan=False).encode(),
            method="POST",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=180) as response:
                result = json.loads(response.read())
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")[:400]
            self.last_error = f"Muse Image returned HTTP {exc.code}: {detail}"
            raise ImageryError(self.last_error) from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            self.last_error = f"Muse Image connection failed: {exc}"
            raise ImageryError(self.last_error) from exc
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            self.last_error = f"Muse Image response failed: {exc}"
            raise ImageryError(self.last_error) from exc

        items = result.get("data") or []
        encoded = items[0].get("b64_json") if items and isinstance(items[0], dict) else None
        if not encoded:
            self.last_error = "Muse Image response contained no image"
            raise ImageryError(self.last_error)
        self.last_error = None
        fmt = (result.get("output_format") or "webp").lower()
        self.emit("keepsake_generated", {"moment": moment.get("id"), "model": self.model,
                                         "format": fmt})
        return base64.b64decode(encoded), fmt
