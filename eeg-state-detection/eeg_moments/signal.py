from dataclasses import dataclass

import numpy as np
from scipy.ndimage import maximum_filter1d, uniform_filter1d
from scipy.signal import butter, sosfiltfilt

from .data import CHANNELS, Recording


@dataclass(frozen=True)
class Config:
    sample_rate: float = 128.0
    channels: tuple[str, ...] = CHANNELS
    frontal_channels: tuple[str, ...] = ("Fp1", "Fp2", "F3", "F4")
    bands: tuple[tuple[float, float], ...] = ((4.0, 8.0), (8.0, 13.0), (13.0, 30.0))
    window_s: float = 0.75
    step_s: float = 0.25
    context_offset_s: float = 2.0
    filter_guard_s: float = 2.0
    artifact_amplitude_uv: float = 120.0
    artifact_step_uv: float = 60.0
    flatline_std_uv: float = 0.05
    quality_highpass_hz: float | None = None
    quality_lowpass_hz: float | None = None
    stretch_window_s: float = 2.0
    stretch_z: float = 3.0
    stretch_release_z: float = 1.5
    stretch_min_s: float = 3.0
    gate_radius_s: float = 3.0
    separation_s: float = 2.0
    min_score: float = 0.0

    def __post_init__(self):
        positive = (self.sample_rate, self.window_s, self.step_s, self.context_offset_s,
                    self.filter_guard_s, self.artifact_amplitude_uv, self.artifact_step_uv,
                    self.flatline_std_uv, self.stretch_window_s, self.stretch_min_s,
                    self.gate_radius_s, self.separation_s)
        if any(not np.isfinite(value) or value <= 0 for value in positive):
            raise ValueError("Signal durations, rates, and quality limits must be positive and finite.")
        if (not self.channels or len(set(self.channels)) != len(self.channels)
                or not self.frontal_channels or not set(self.frontal_channels) <= set(self.channels)):
            raise ValueError("Configure unique channels and an explicit frontal subset.")
        if not self.bands or any(not 0 < lo < hi < self.sample_rate / 2 for lo, hi in self.bands):
            raise ValueError("Bands must lie strictly between zero and Nyquist.")
        if self.quality_highpass_hz is not None and not 0 < self.quality_highpass_hz < self.sample_rate / 2:
            raise ValueError("Quality high-pass must lie between zero and Nyquist.")
        if self.quality_lowpass_hz is not None and (self.quality_highpass_hz is None
                or not self.quality_highpass_hz < self.quality_lowpass_hz < self.sample_rate / 2):
            raise ValueError("Quality low-pass requires a valid lower high-pass cutoff.")
        if (round(self.step_s * self.sample_rate) < 1 or round(self.window_s * self.sample_rate) < 3
                or self.context_offset_s <= self.window_s):
            raise ValueError("Window/step is too short or context overlaps the central window.")
        if (not np.isfinite(self.min_score) or not np.isfinite(self.stretch_z)
                or not np.isfinite(self.stretch_release_z) or self.stretch_release_z >= self.stretch_z):
            raise ValueError("Use finite score rules with stretch release below stretch entry.")


@dataclass
class Prepared:
    recording: Recording
    filtered: np.ndarray  # bands x channels x samples
    bad: np.ndarray


@dataclass
class Windows:
    epochs: np.ndarray  # windows x [center,left,right] x bands x channels x samples
    times: np.ndarray
    rejected: int
    total: int


def prepare(recording, config):
    recording.validate()
    if tuple(recording.channels) != tuple(config.channels):
        raise ValueError(f"Channel contract mismatch. Expected {config.channels}; got "
                         f"{recording.channels}. Never silently drop or reorder channels.")
    if recording.sample_rate != config.sample_rate:
        raise ValueError("Sample rate differs from model; resample explicitly before import.")
    raw = recording.samples
    if max(hi for _, hi in config.bands) >= recording.sample_rate / 2:
        raise ValueError("Feature bands must be below Nyquist.")
    quality_samples = raw
    if config.quality_highpass_hz is not None:
        # Raw electrode offsets are not AC artifact amplitudes. This copy is used
        # only for quality assessment; the feature filter below still runs once.
        quality_band = (config.quality_highpass_hz if config.quality_lowpass_hz is None
                        else [config.quality_highpass_hz, config.quality_lowpass_hz])
        quality_samples = sosfiltfilt(butter(4, quality_band,
                                            btype="highpass" if config.quality_lowpass_hz is None else "bandpass",
                                            fs=recording.sample_rate, output="sos"), raw, axis=1)
    bad = np.any(np.abs(quality_samples) > config.artifact_amplitude_uv, axis=0)
    bad |= np.any(np.abs(np.diff(quality_samples, prepend=quality_samples[:, :1], axis=1)) > config.artifact_step_uv, axis=0)
    # Detect flat channels locally, before interpolation/filtering creates false activity.
    size = max(3, round(config.window_s * recording.sample_rate))
    local_variance = uniform_filter1d(quality_samples ** 2, size, axis=1) - uniform_filter1d(quality_samples, size, axis=1) ** 2
    bad |= np.any(local_variance < config.flatline_std_uv ** 2, axis=0)
    good = ~bad
    if good.sum() < 3 * recording.sample_rate:
        raise ValueError("Recording contains too little usable EEG.")
    cleaned = raw.copy()
    if bad.any():
        idx = np.arange(raw.shape[1])
        for ch in range(len(raw)):
            cleaned[ch, bad] = np.interp(idx[bad], idx[good], raw[ch, good])
    guard = round(config.filter_guard_s * recording.sample_rate)
    bad = maximum_filter1d(bad.astype(np.uint8), 2 * guard + 1).astype(bool)
    bad[:guard] = True
    bad[-guard:] = True
    filtered = np.stack([
        sosfiltfilt(butter(4, band, btype="bandpass", fs=recording.sample_rate, output="sos"),
                    cleaned, axis=1)
        for band in config.bands
    ])
    return Prepared(recording, filtered, bad)


def make_windows(prepared, config):
    fs = prepared.recording.sample_rate
    width = round(config.window_s * fs)
    step = round(config.step_s * fs)
    offset = round(config.context_offset_s * fs)
    half = width // 2
    margin = offset + width + round(config.filter_guard_s * fs)
    centers = np.arange(margin, len(prepared.bad) - margin, step)
    examples, times = [], []
    for center in centers:
        starts = [center - half, center - offset - half, center + offset - half]
        if any(prepared.bad[s:s + width].any() for s in starts):
            continue
        examples.append(np.stack([prepared.filtered[:, :, s:s + width] for s in starts]))
        times.append(center / fs)
    shape = (0, 3, len(config.bands), len(config.channels), width)
    epochs = np.stack(examples) if examples else np.empty(shape)
    return Windows(epochs, np.asarray(times), len(centers) - len(times), len(centers))


def stretch_trace(prepared, config):
    fs = prepared.recording.sample_rate
    n = round(config.stretch_window_s * fs)
    frontal = [prepared.recording.channels.index(c) for c in config.frontal_channels]
    # The first configured band is the prespecified stretch band (theta by default).
    power = uniform_filter1d(np.mean(prepared.filtered[0, frontal] ** 2, axis=0), n)
    invalid = maximum_filter1d(prepared.bad.astype(np.uint8), n).astype(bool)
    indices = np.arange(n, len(power) - n, round(config.step_s * fs))
    return indices / fs, np.log(np.maximum(power[indices], 1e-12)), ~invalid[indices]


@dataclass
class StretchReference:
    center: float
    scale: float

    @classmethod
    def fit(cls, prepared_blocks, baseline_intervals, config):
        values = []
        for prepared, intervals in zip(prepared_blocks, baseline_intervals):
            times, logpower, valid = stretch_trace(prepared, config)
            selected = np.zeros(len(times), dtype=bool)
            for start, end in intervals:
                if not 0 <= start < end <= prepared.recording.duration_s:
                    raise ValueError("Invalid baseline interval.")
                # Require the complete centered power window inside calibration baseline.
                selected |= ((times >= start + config.stretch_window_s / 2)
                             & (times <= end - config.stretch_window_s / 2))
            values.extend(logpower[selected & valid])
        if len(values) < 20:
            raise ValueError("Too little clean calibration baseline.")
        center = float(np.median(values))
        scale = max(float(1.4826 * np.median(np.abs(np.asarray(values) - center))), 0.1)
        return cls(center, scale)

    def detect(self, prepared, config):
        times, logpower, valid = stretch_trace(prepared, config)
        z = (logpower - self.center) / self.scale
        stretches, onset, peak, confirmed = [], None, None, None
        for i, time in enumerate(times):
            if onset is None:
                if valid[i] and z[i] >= config.stretch_z:
                    onset, peak = float(time), float(z[i])
            elif not valid[i] or z[i] < config.stretch_release_z:
                if confirmed is not None:
                    stretches.append({"start_s": onset, "confirmed_s": confirmed,
                                      "end_s": float(time), "peak_z": peak})
                onset, peak, confirmed = None, None, None
            else:
                peak = max(peak, float(z[i]))
                if confirmed is None and time - onset >= config.stretch_min_s:
                    confirmed = float(time)
        if confirmed is not None:
            stretches.append({"start_s": onset, "confirmed_s": confirmed,
                              "end_s": float(times[-1]), "peak_z": peak})
        return stretches, times, z, valid


def gate_mask(times, stretches, config, location="onset"):
    mask = np.zeros(len(times), dtype=bool)
    for event in stretches:
        anchor = {"onset": event["start_s"], "midpoint": (event["start_s"] + event["end_s"]) / 2,
                  "end": event["end_s"]}[location]
        mask |= np.abs(times - anchor) <= config.gate_radius_s
    return mask
