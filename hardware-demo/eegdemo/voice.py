"""Meta Muse Voice input for conversational Memory Guard turns."""
import json
import os
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.request
import uuid
from pathlib import Path


DEFAULT_URL = "https://api.meta.ai/v1/asr/transcribe"
DEFAULT_MODEL = "muse-voice-transcribe-1.0"
MAX_AUDIO_BYTES = 8 * 1024 * 1024


class VoiceError(RuntimeError):
    pass


class MetaVoiceTranscriber:
    def __init__(self, emit, *, api_key=None, url=None, model=None):
        self.emit = emit
        self.api_key = api_key if api_key is not None else os.environ.get(
            "MODEL_API_KEY", "")
        self.url = url or os.environ.get("META_VOICE_URL", DEFAULT_URL)
        self.model = model or os.environ.get("META_VOICE_MODEL", DEFAULT_MODEL)
        self.last_error = None

    @property
    def configured(self):
        return bool(self.api_key)

    def status(self):
        return {
            "provider": "meta",
            "model": self.model,
            "configured": self.configured,
            "mode": "push-to-talk",
            "output": "device-speech-synthesis",
            "error": self.last_error,
        }

    @staticmethod
    def _suffix(content_type):
        mime = content_type.split(";", 1)[0].strip().lower()
        return {
            "audio/webm": ".webm",
            "audio/ogg": ".ogg",
            "audio/mp4": ".m4a",
            "audio/x-m4a": ".m4a",
            "audio/wav": ".wav",
            "audio/wave": ".wav",
        }.get(mime, ".webm")

    def _wav(self, audio, content_type):
        if not shutil.which("ffmpeg"):
            raise VoiceError("ffmpeg is required for Meta voice input")
        with tempfile.TemporaryDirectory(prefix="memorypalace-voice-") as temp:
            source = Path(temp) / ("input" + self._suffix(content_type))
            target = Path(temp) / "voice.wav"
            source.write_bytes(audio)
            try:
                subprocess.run(
                    ["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i",
                     str(source), "-ac", "1", "-ar", "24000", "-c:a", "pcm_s16le",
                     "-map_metadata", "-1", str(target)],
                    check=True, timeout=30, stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                )
            except subprocess.CalledProcessError as exc:
                detail = exc.stderr.decode(errors="replace")[:300]
                raise VoiceError(f"could not decode voice recording: {detail}") from exc
            except (OSError, subprocess.TimeoutExpired) as exc:
                raise VoiceError(f"could not prepare voice recording: {exc}") from exc
            return target.read_bytes()

    @staticmethod
    def _multipart(settings, wav):
        boundary = "memorypalace-" + uuid.uuid4().hex
        pieces = []

        def add(value):
            pieces.append(value.encode() if isinstance(value, str) else value)

        add(f"--{boundary}\r\n")
        add('Content-Disposition: form-data; name="request"\r\n')
        add("Content-Type: application/json\r\n\r\n")
        add(json.dumps(settings, allow_nan=False))
        add("\r\n")
        add(f"--{boundary}\r\n")
        add('Content-Disposition: form-data; name="audio"; filename="voice.wav"\r\n')
        add("Content-Type: audio/wav\r\n\r\n")
        add(wav)
        add("\r\n")
        add(f"--{boundary}--\r\n")
        return boundary, b"".join(pieces)

    def transcribe(self, audio, content_type):
        if not self.configured:
            raise VoiceError("set MODEL_API_KEY")
        if not audio:
            raise VoiceError("voice recording was empty")
        if len(audio) > MAX_AUDIO_BYTES:
            raise VoiceError(f"voice recording exceeds {MAX_AUDIO_BYTES} bytes")
        wav = self._wav(audio, content_type)
        boundary, body = self._multipart({
            "model": self.model,
            "audioEncoding": "WAV",
            "mode": "PUSH_TO_TALK",
            "languageBias": ["English"],
            "keywords": ["MemoryPalace", "HackMIT", "Meta", "Elastic"],
        }, wav)
        request = urllib.request.Request(
            self.url, data=body, method="POST",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Accept": "application/json",
                "Content-Type": f"multipart/form-data; boundary={boundary}",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                result = json.loads(response.read())
            transcript = str(result.get("transcript", "")).strip()
            if not transcript:
                raise VoiceError("Meta did not detect speech in that recording")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")[:500]
            self.last_error = f"Meta Muse Voice returned HTTP {exc.code}: {detail}"
            raise VoiceError(self.last_error) from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            self.last_error = f"Meta Muse Voice connection failed: {exc}"
            raise VoiceError(self.last_error) from exc
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            self.last_error = f"Meta Muse Voice response failed: {exc}"
            raise VoiceError(self.last_error) from exc
        self.last_error = None
        self.emit("meta_voice_transcribed", {
            "model": self.model,
            "audio_bytes": len(audio),
            "wav_bytes": len(wav),
            "characters": len(transcript),
        })
        return transcript
