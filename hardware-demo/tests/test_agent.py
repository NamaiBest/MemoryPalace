import io
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT.parent / "confusion-detector")]

from eegdemo.agent import MemoryGuard


class Response(io.BytesIO):
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class MemoryGuardTests(unittest.TestCase):
    def test_provider_is_selected_at_launch(self):
        with patch.dict(os.environ, {"MEMORYPALACE_AGENT_PROVIDER": "grok",
                                    "XAI_API_KEY": "secret"}, clear=True):
            guard = MemoryGuard(lambda *_: None)
        self.assertEqual(guard.status()["provider"], "grok")
        self.assertEqual(guard.status()["model"], "grok-4.6")
        self.assertNotIn("secret", json.dumps(guard.status()))

    def test_meta_response_includes_retrieval_provenance(self):
        guard = MemoryGuard(lambda *_: None, provider="meta", api_key="secret")
        response = {"output": [{"content": [{"type": "output_text",
                                               "text": "[Moment #007: Reading nearby] looks relevant."}]}]}
        with patch("eegdemo.agent.urllib.request.urlopen",
                   return_value=Response(json.dumps(response).encode())) as call:
            result = guard.answer("What happened?", [{
                "id": "capture-1", "sequence": 7,
                "semanticTitle": "Reading nearby",
                "timestamp": "2026-09-19T12:00:00Z",
                "eventType": "surprise", "confidence": 0.9,
                "summary": "A surprise", "transcript": "That was unexpected",
            }], "elastic-rrf-jina-v5-omni", [{
                "role": "user", "content": "How was my afternoon?",
            }])
        request_body = json.loads(call.call_args.args[0].data)
        self.assertEqual(request_body["model"], "muse-spark-1.3")
        self.assertIn("That was unexpected", request_body["input"])
        self.assertIn("Moment #007: Reading nearby", request_body["input"])
        self.assertIn("How was my afternoon?", request_body["input"])
        self.assertNotIn("capture-1", request_body["input"])
        # Memory Guard answers from retrieved moments, so it defaults to the cheapest
        # reasoning setting and carries no web_search tool. Both are measured choices
        # rather than incidental: see the comments in MemoryGuard.__init__.
        self.assertEqual(request_body["reasoning"], {"effort": "minimal"})
        self.assertEqual(request_body["max_output_tokens"], 1800)
        self.assertNotIn("tools", request_body)
        self.assertIn("Do not use em dashes", request_body["instructions"])
        self.assertIn("[Moment #005: Title]", request_body["instructions"])
        self.assertIn("immediately after the claim", request_body["instructions"])
        self.assertEqual(result["retrievalEngine"], "elastic-rrf-jina-v5-omni")

    def test_latency_switches_are_opt_in(self):
        """Both speed defaults stay overridable, and the agent's web search is its own
        switch so enabling per-clip grounding does not slow every question down."""
        with patch.dict(os.environ, {"MEMORYPALACE_AGENT_PROVIDER": "meta",
                                     "MODEL_API_KEY": "secret",
                                     "META_WEB_SEARCH": "1"}, clear=True):
            guard = MemoryGuard(lambda *_: None)
        self.assertFalse(guard.web_search)
        self.assertEqual(guard.effort, "minimal")

        with patch.dict(os.environ, {"MEMORYPALACE_AGENT_PROVIDER": "meta",
                                     "MODEL_API_KEY": "secret",
                                     "MEMORYPALACE_AGENT_WEB_SEARCH": "1",
                                     "MEMORYPALACE_AGENT_EFFORT": "low"}, clear=True):
            guard = MemoryGuard(lambda *_: None)
        self.assertTrue(guard.web_search)
        self.assertEqual(guard.effort, "low")
        self.assertEqual(guard.status()["reasoningEffort"], "low")


if __name__ == "__main__":
    unittest.main()
