"""Scripted EEG fixture. NEVER label these samples as a human recording."""
import numpy as np
from .pipeline import CROWN_CHANNELS


def synthetic_window(number, high=False, fs=256):
    rng = np.random.default_rng(1042 + number)
    t = np.arange(fs * 4) / fs
    theta = 7 * (1 + 0.15 * np.sin(number * 1.7))
    alpha = 14 * (1 + 0.12 * np.cos(number * 1.3))
    if high:
        theta *= 2.2
        alpha *= 0.4
    return np.array([
        theta * np.sin(2 * np.pi * 6 * t + c * 0.4)
        + alpha * np.sin(2 * np.pi * 10.5 * t + c * 0.7)
        + rng.normal(0, 3, len(t)) for c in range(8)])


def packet(data, start_ms, stream_id="synthetic-demo", source="synthetic"):
    return {"source": source, "stream_id": stream_id,
            "epoch": {"data": data.tolist(), "info": {"channelNames": list(CROWN_CHANNELS),
                       "samplingRate": 256, "startTime": start_ms}}}
