import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
import urllib.error
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from eegdemo.vision import MetaVideoDescriber, VisionError


class Response(io.BytesIO):
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class MetaVideoDescriberTests(unittest.TestCase):
    def test_structured_video_description(self):
        events = []
        client = MetaVideoDescriber(
            lambda kind, detail: events.append((kind, detail)), api_key="secret")
        described = {"title": "Connecting EEG wires at a conference", "description": (
            "A person arranges red EEG leads on a desk beside an auditorium stage."),
            "keywords": ["EEG", "wires", "desk"], "topics": ["conference setup"]}
        api_response = {"output": [{"content": [{
            "type": "output_text", "text": json.dumps(described),
        }]}]}
        with tempfile.TemporaryDirectory() as temp:
            video = Path(temp) / "moment.mp4"
            video.write_bytes(b"short-video")
            with patch("eegdemo.vision.urllib.request.urlopen",
                       side_effect=lambda *_args, **_kwargs: Response(
                           json.dumps(api_response).encode())) as call:
                result = client.describe(video)
        requests = call.call_args_list
        body = json.loads(requests[0].args[0].data)
        content = body["input"][0]["content"]
        self.assertEqual(content[1]["type"], "input_video")
        self.assertTrue(content[1]["video_url"].startswith("data:video/mp4;base64,"))
        self.assertEqual(body["text"]["format"]["type"], "json_schema")
        grounding_body = json.loads(requests[1].args[0].data)
        self.assertEqual(grounding_body["tools"], [{"type": "web_search"}])
        self.assertEqual(grounding_body["tool_choice"], "auto")
        self.assertIn("HackMIT 2026 at MIT", grounding_body["input"])
        self.assertEqual(result["title"], "Connecting EEG wires at a conference")
        self.assertEqual(result["provider"], "meta")
        self.assertNotIn("secret", json.dumps(client.status()))
        self.assertEqual(events[0][0], "meta_video_described")

    def test_only_old_event_like_moments_need_context_upgrade(self):
        client = MetaVideoDescriber(lambda *_: None, api_key="secret")
        self.assertTrue(client.needs_grounding({
            "semanticTitle": "Laptop in an auditorium",
            "vision": {"status": "complete"},
        }))
        self.assertFalse(client.needs_grounding({
            "semanticTitle": "Red bottle on a desk",
            "vision": {"status": "complete"},
        }))
        self.assertFalse(client.needs_grounding({
            "semanticTitle": "HackMIT sponsor presentation",
            "vision": {"status": "complete", "groundingVersion": "meta-web-v1"},
        }))

    def test_poster_frame_uses_image_understanding(self):
        client = MetaVideoDescriber(lambda *_: None, api_key="secret")
        described = {"title": "Laptop on a desk", "description": "An open laptop.",
                     "keywords": ["laptop"], "topics": ["work"]}
        api_response = {"output": [{"content": [{
            "type": "output_text", "text": json.dumps(described),
        }]}]}
        with tempfile.TemporaryDirectory() as temp:
            poster = Path(temp) / "moment.jpg"
            poster.write_bytes(b"image")
            with patch("eegdemo.vision.urllib.request.urlopen",
                       side_effect=lambda *_args, **_kwargs: Response(
                           json.dumps(api_response).encode())) as call:
                result = client.describe(poster)
        content = json.loads(call.call_args_list[0].args[0].data)["input"][0]["content"]
        self.assertEqual(content[1]["type"], "input_image")
        self.assertTrue(content[1]["image_url"].startswith("data:image/jpeg;base64,"))
        self.assertEqual(result["source"], "poster")

    def test_billing_failure_opens_circuit_breaker(self):
        client = MetaVideoDescriber(lambda *_: None, api_key="secret")
        error = urllib.error.HTTPError(client.url, 402, "Payment Required", {},
                                      io.BytesIO(b'{"error":"billing"}'))
        with tempfile.TemporaryDirectory() as temp:
            video = Path(temp) / "moment.mp4"
            video.write_bytes(b"short-video")
            with patch("eegdemo.vision.urllib.request.urlopen", side_effect=error):
                with self.assertRaises(VisionError):
                    client.describe(video)
        self.assertFalse(client.enabled)
        self.assertIn("HTTP 402", client.status()["error"])


if __name__ == "__main__":
    unittest.main()
