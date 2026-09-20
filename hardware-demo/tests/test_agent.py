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
            }], "elastic-rrf-jina-v5-omni")
        request_body = json.loads(call.call_args.args[0].data)
        self.assertEqual(request_body["model"], "muse-spark-1.3")
        self.assertIn("That was unexpected", request_body["input"])
        self.assertIn("Moment #007: Reading nearby", request_body["input"])
        self.assertNotIn("capture-1", request_body["input"])
        self.assertEqual(result["retrievalEngine"], "elastic-rrf-jina-v5-omni")


if __name__ == "__main__":
    unittest.main()
