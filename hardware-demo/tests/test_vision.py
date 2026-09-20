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
        described = {"title": "Connecting EEG wires", "description": (
            "A person arranges red EEG leads on a desk beside a headset."),
            "keywords": ["EEG", "wires", "desk"], "topics": ["hardware setup"]}
        api_response = {"output": [{"content": [{
            "type": "output_text", "text": json.dumps(described),
        }]}]}
        with tempfile.TemporaryDirectory() as temp:
            video = Path(temp) / "moment.mp4"
            video.write_bytes(b"short-video")
            with patch("eegdemo.vision.urllib.request.urlopen",
                       return_value=Response(json.dumps(api_response).encode())) as call:
                result = client.describe(video)
        request = call.call_args.args[0]
        body = json.loads(request.data)
        content = body["input"][0]["content"]
        self.assertEqual(content[1]["type"], "input_video")
        self.assertTrue(content[1]["video_url"].startswith("data:video/mp4;base64,"))
        self.assertEqual(body["text"]["format"]["type"], "json_schema")
        self.assertEqual(result["title"], "Connecting EEG wires")
        self.assertEqual(result["provider"], "meta")
        self.assertNotIn("secret", json.dumps(client.status()))
        self.assertEqual(events[0][0], "meta_video_described")

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
