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
        # Memory Guard answers only from retrieved moments, so the web_search tool sits on
        # the critical path of every question while adding roughly a thousand input tokens
        # of tool schema. Public-event grounding already happens once per clip in vision.py,
        # at indexing time, where latency is invisible. This stays off unless asked for, and
        # is deliberately a separate switch from META_WEB_SEARCH so enabling clip grounding
        # does not silently slow down the conversation.
        self.web_search = (self.provider == "meta" and
                           os.environ.get("MEMORYPALACE_AGENT_WEB_SEARCH", "0").lower()
                           in ("1", "true", "yes", "on"))
        # Muse Spark spends most of a Memory Guard turn on private reasoning. Measured over
        # four questions against eight retrieved moments, "low" ran a 9.5s median and
        # "minimal" 6.0s, with the same facts, the same inline citations and the same shape
        # of answer. Reading back your own day does not need deliberation, so pay for speed.
        self.effort = os.environ.get("MEMORYPALACE_AGENT_EFFORT", "minimal")
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
            "webSearchEnabled": self.web_search,
            "reasoningEffort": self.effort,
            "fallbackAvailable": True,
            "error": self.last_error,
        }

    @staticmethod
    def _output_text(payload):
        if isinstance(payload.get("output_text"), str):
            return payload["output_text"].strip()
        messages = []
        for item in payload.get("output", []):
            parts = []
            for content in item.get("content", []):
                if content.get("type") in ("output_text", "text") and content.get("text"):
                    parts.append(content["text"])
            if parts:
                messages.append("\n".join(parts))
        return messages[-1].strip() if messages else ""

    def share_note(self, moments, recipient=None, sender=None):
        """Write a short personal note about the chosen moments, for someone else to read.

        This is the Meta "bringing people closer together" path. It is the same Muse
        Spark boundary as answer(), with a different job: not answering a question for
        the wearer, but turning a handful of their moments into something a person who
        was not there can actually feel. The grounding rule is stricter, because a note
        that invents a detail gets sent to someone who will believe it.
        """
        if not self.configured:
            key = PROVIDERS[self.provider]["key_env"]
            raise AgentError(f"{self.label} is selected but {key} is not set")
        if not moments:
            raise AgentError("choose at least one moment to share")
        context = []
        for moment in moments[:12]:
            context.append({
                "title": moment.get("semanticTitle") or "Captured moment",
                "time": moment.get("timestamp"),
                "description": moment.get("aiDescription") or moment.get("summary"),
                "note": moment.get("annotation", ""),
                "intensity": moment.get("confidence"),
            })
        who = (recipient or "someone close to me").strip()[:80]
        payload = {
            "model": self.model,
            "instructions": (
                "You are helping someone share the moments that stood out in their day "
                f"with {who}. Write it as that person would write it: first person, warm, "
                "specific, the way you would text someone you love. Two or three short "
                "paragraphs, at most about 140 words total. Open with what the day felt "
                "like, then the moments themselves in the order given, then one closing "
                "line that invites a reply. Describe only what the moments actually "
                "contain. Never invent a place, person, feeling or detail that is not "
                "there, and never state or guess what the person was feeling, because "
                "spike intensity ranks attention, not emotion. Do not mention EEG, "
                "spikes, intensity scores, capture IDs, sensors or this software. Do not "
                "use em dashes or en dashes. Write only the message itself, with no "
                "subject line, no greeting placeholder and no sign-off placeholder."
            ),
            "input": (
                f"Recipient: {who}\n"
                f"Sender: {(sender or 'the person sharing').strip()[:80]}\n"
                f"Moments to share, in order: {json.dumps(context, allow_nan=False)}"
            ),
            "reasoning": {"effort": self.effort},
            "max_output_tokens": 1400,
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
                reason = (result.get("incomplete_details") or {}).get("reason")
                raise AgentError(
                    f"{self.label} response contained no text"
                    + (f" ({reason})" if reason else ""))
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
        self.emit("share_note_composed", {
            "provider": self.provider, "model": self.model, "moments": len(context),
        })
        return {
            "note": text.replace("\u2014", "-").replace("\u2013", "-").strip(),
            "provider": self.provider,
            "providerLabel": self.label,
            "model": self.model,
            "momentIds": [moment.get("id") for moment in moments[:12]],
        }

    def answer(self, question, moments, retrieval_engine, history=None):
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
                "You are Memory Guard, a warm, perceptive companion for someone's day. "
                "Answer only from the provided MemoryPalace moments. Sound natural and "
                "human, not clinical or robotic. Lead with a direct answer, keep it concise, "
                "and use short paragraphs or bullets when they improve clarity. You may use "
                "Markdown bold sparingly. Cite memories inline using their exact bracketed "
                "reference, for example [Moment #005: Title], immediately after the claim "
                "that memory supports. Include at least one citation when retrieved moments "
                "support the answer. Never expose internal capture IDs. Do not use em dashes or en "
                "dashes. Never diagnose a medical or emotional condition from EEG; intensity "
                "is only a ranking signal. If evidence is missing, say so plainly. When web "
                "search is available, use it only to clarify a public event, organization, "
                "place, or object already mentioned in a retrieved moment. Clearly distinguish "
                "public web context from what the person's recording actually shows."
            ),
            "input": (
                f"Retrieval engine: {retrieval_engine}\n"
                f"Conversation so far: {json.dumps(history or [], allow_nan=False)}\n"
                f"Question: {question}\n"
                f"Retrieved moments: {json.dumps(context, allow_nan=False)}"
            ),
            "reasoning": {"effort": self.effort},
            # Muse Spark counts private reasoning against this limit. A 700-token cap can
            # therefore end with status=incomplete before the visible message is emitted,
            # even when the requested answer is short.
            "max_output_tokens": 1800,
        }
        if self.web_search:
            payload["tools"] = [{"type": "web_search"}]
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
                reason = (result.get("incomplete_details") or {}).get("reason")
                suffix = f" ({reason})" if reason else ""
                raise AgentError(f"{self.label} response contained no text{suffix}")
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
            "answer": text.replace("—", "-").replace("–", "-"),
            "provider": self.provider,
            "providerLabel": self.label,
            "model": self.model,
            "retrievalEngine": retrieval_engine,
            "momentIds": [moment.get("id") for moment in moments[:8]],
        }
