"""Launch-selected LLM boundary for the Memory Guard homepage agent."""
import json
import os
import urllib.error
import urllib.request


PROVIDERS = {
    "meta": {
        "label": "Meta Muse Spark",
        "url": "https://api.meta.ai/v1/responses",
        "model": "muse-spark-1.3",
        "key_env": "MODEL_API_KEY",
    },
    "grok": {
        "label": "Grok",
        "url": "https://api.x.ai/v1/responses",
        "model": "grok-4.6",
        "key_env": "XAI_API_KEY",
    },
}


class AgentError(RuntimeError):
    pass


class MemoryGuard:
    def __init__(self, emit, *, provider=None, api_key=None, url=None, model=None):
        selected = (provider or os.environ.get("MEMORYPALACE_AGENT_PROVIDER", "meta")).lower()
        if selected not in PROVIDERS:
            raise ValueError("MEMORYPALACE_AGENT_PROVIDER must be meta or grok")
        defaults = PROVIDERS[selected]
        self.emit = emit
        self.provider = selected
        self.label = defaults["label"]
        self.url = url or os.environ.get("MEMORYPALACE_AGENT_URL", defaults["url"])
        self.model = model or os.environ.get("MEMORYPALACE_AGENT_MODEL", defaults["model"])
        self.api_key = api_key if api_key is not None else os.environ.get(
            defaults["key_env"], "")
        self.last_error = None

    @property
    def configured(self):
        return bool(self.api_key)

    def status(self):
        return {
            "name": "Memory Guard",
            "provider": self.provider,
            "providerLabel": self.label,
            "model": self.model,
            "configured": self.configured,
            "fallbackAvailable": True,
            "error": self.last_error,
        }

    @staticmethod
    def _output_text(payload):
        if isinstance(payload.get("output_text"), str):
            return payload["output_text"].strip()
        parts = []
        for item in payload.get("output", []):
            for content in item.get("content", []):
                if content.get("type") in ("output_text", "text") and content.get("text"):
                    parts.append(content["text"])
        return "\n".join(parts).strip()

    def answer(self, question, moments, retrieval_engine):
        if not self.configured:
            key = PROVIDERS[self.provider]["key_env"]
            raise AgentError(f"{self.label} is selected but {key} is not set")
        context = []
        for moment in moments[:8]:
            reference = (f"Moment #{int(moment.get('sequence', 0)):03d}: "
                         f"{moment.get('semanticTitle') or 'Captured moment'}")
            context.append({
                "reference": reference,
                "timestamp": moment.get("timestamp"),
                "event": moment.get("eventType"),
                "intensity": moment.get("confidence"),
                "title": moment.get("semanticTitle"),
                "summary": moment.get("summary"),
                "description": moment.get("aiDescription"),
                "transcript": moment.get("transcript", "")[:1600],
            })
        payload = {
            "model": self.model,
            "instructions": (
                "You are Memory Guard, a calm episodic-memory guide. Answer only from the "
                "provided MemoryPalace moments. Cite each human-readable moment reference in "
                "brackets; never expose internal capture IDs. Never diagnose a "
                "medical or emotional condition from EEG; intensity is only a ranking signal. "
                "If evidence is missing, say so plainly."
            ),
            "input": (
                f"Retrieval engine: {retrieval_engine}\n"
                f"Question: {question}\n"
                f"Retrieved moments: {json.dumps(context, allow_nan=False)}"
            ),
        }
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
            with urllib.request.urlopen(request, timeout=90) as response:
                result = json.loads(response.read())
            text = self._output_text(result)
            if not text:
                raise AgentError(f"{self.label} response contained no text")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")[:500]
            self.last_error = f"{self.label} returned HTTP {exc.code}: {detail}"
            raise AgentError(self.last_error) from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            self.last_error = f"{self.label} connection failed: {exc}"
            raise AgentError(self.last_error) from exc
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            self.last_error = f"{self.label} response failed: {exc}"
            raise AgentError(self.last_error) from exc
        self.last_error = None
        self.emit("memory_guard_answered", {
            "provider": self.provider,
            "model": self.model,
            "retrieval_engine": retrieval_engine,
            "moments": len(context),
        })
        return {
            "answer": text,
            "provider": self.provider,
            "providerLabel": self.label,
            "model": self.model,
            "retrievalEngine": retrieval_engine,
            "momentIds": [moment.get("id") for moment in moments[:8]],
        }
