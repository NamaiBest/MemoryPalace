import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from eegdemo.voice import MAX_AUDIO_BYTES, MetaVoiceTranscriber, VoiceError


class Response(io.BytesIO):
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class MetaVoiceTranscriberTests(unittest.TestCase):
    def test_transcribes_ephemeral_audio_with_muse_voice(self):
        events = []
        client = MetaVoiceTranscriber(
            lambda kind, detail: events.append((kind, detail)), api_key="secret")
        response = {"sessionId": "voice-test", "transcript": "How was my day?",
                    "audioDurationMs": 1800, "turns": []}
        with patch.object(client, "_wav", return_value=b"prepared-wav"), \
                patch("eegdemo.voice.urllib.request.urlopen",
                      return_value=Response(json.dumps(response).encode())) as call:
            transcript = client.transcribe(b"browser-audio", "audio/webm;codecs=opus")
        request = call.call_args.args[0]
        self.assertIn(b"muse-voice-transcribe-1.0", request.data)
        self.assertIn(b"prepared-wav", request.data)
        self.assertEqual(transcript, "How was my day?")
        self.assertEqual(events[0][0], "meta_voice_transcribed")
        self.assertNotIn("secret", json.dumps(client.status()))

    def test_rejects_oversized_voice_turn(self):
        client = MetaVoiceTranscriber(lambda *_: None, api_key="secret")
        with self.assertRaises(VoiceError):
            client.transcribe(b"x" * (MAX_AUDIO_BYTES + 1), "audio/webm")


if __name__ == "__main__":
    unittest.main()
