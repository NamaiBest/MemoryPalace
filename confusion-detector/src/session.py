"""Session orchestration: calibrate, monitor, capture, save.

Flow:
    1. CALIBRATE  - ~60 s of the wearer reading something easy, to learn their baseline
    2. MONITOR    - sliding windows; each produces a load index, z-scored vs baseline
    3. TRIGGER    - k consecutive elevated windows fires a bookmark and takes a photo
    4. SAVE       - events + raw EEG to disk, so the session can be reviewed and replayed
"""
import os
import json
import time
import datetime
import numpy as np

from .cognitive_load import LoadExtractor, RingBuffer
from .detector import Calibrator, PersistenceDetector
from .capture import Camera, NullCamera


class Session:
    def __init__(self, source, cfg, label=None, use_camera=True, on_event=None):
        self.src = source
        self.cfg = cfg
        self.label = label or datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        self.dir = os.path.join(cfg.session_dir, self.label)
        os.makedirs(self.dir, exist_ok=True)

        self.fs = source.fs
        self.frontal = source.frontal_indices(cfg.preferred_frontal)
        self.frontal_names = [source.ch_names[i] for i in self.frontal]

        self.extractor = LoadExtractor(self.fs, cfg)
        self.calibrator = Calibrator(cfg)
        self.detector = PersistenceDetector(cfg)
        self.camera = Camera(cfg) if use_camera else NullCamera(cfg)
        self.on_event = on_event

        self.events = []
        self.trace = []
        self._raw = []
        self._buf = RingBuffer(len(self.frontal), int(cfg.signal.window_s * self.fs))

    # ---------- internals ----------

    def _clock(self, t0):
        """Elapsed seconds. Follows the data for playback, the wall for live capture."""
        if hasattr(self.src, "data_time"):
            return self.src.data_time() - t0
        return time.time() - t0

    def _clock_start(self):
        return self.src.data_time() if hasattr(self.src, "data_time") else time.time()

    def _pump(self):
        """Pull whatever EEG is available and push the frontal channels into the ring."""
        chunk = self.src.read()
        if chunk.shape[1]:
            self._raw.append(chunk)
            self._buf.push(chunk[self.frontal, :])
        return chunk.shape[1]

    def _measure(self):
        """One window -> (load_index, artifact_fraction, warming_up).

        A not-yet-full ring buffer is warmup, not a dirty signal. Conflating the two
        makes it look like the electrodes are bad during the first few seconds.
        """
        if not self._buf.ready():
            return None, 0.0, True
        idx, frac = self.extractor.load_index(self._buf.window())
        return idx, frac, False

    # ---------- phases ----------

    def calibrate(self, verbose=True):
        dur = self.cfg.calibration.duration_s
        if verbose:
            print(f"\n  Calibrating for {dur:.0f}s using {self.frontal_names}.")
            print("  Read something comfortable. Try not to blink more than usual.\n")
        t0 = self._clock_start()
        next_hop = self.cfg.signal.hop_s
        dirty = 0
        while self._clock(t0) < dur:
            if hasattr(self.src, "exhausted") and self.src.exhausted():
                break
            self._pump()
            el = self._clock(t0)
            if el >= next_hop:
                next_hop += self.cfg.signal.hop_s
                idx, frac, warming = self._measure()
                if idx is not None:
                    self.calibrator.add(idx)
                elif not warming:
                    dirty += 1
                if verbose:
                    bar = "#" * int(20 * el / dur)
                    tag = "warmup" if warming else f"dirty={dirty:3d}"
                    print(f"\r  [{bar:<20}] {el:4.0f}/{dur:.0f}s  "
                          f"clean={self.calibrator.n():3d} {tag}   ", end="")
            time.sleep(0.05)
        if verbose:
            print()
        mean, std = self.calibrator.finish()
        if verbose:
            print(f"  Baseline: mean={mean:.3f} sd={std:.3f} "
                  f"({self.calibrator.n()} clean windows, {dirty} rejected)\n")
        return mean, std

    def monitor(self, duration_s, verbose=True):
        d = self.cfg.detector
        if verbose:
            print(f"  Monitoring for {duration_s:.0f}s. Fires after "
                  f"{d.k_consecutive} consecutive windows at z>={d.z_threshold} "
                  f"(~{d.k_consecutive * self.cfg.signal.hop_s:.0f}s sustained).\n")
        t0 = self._clock_start()
        next_hop = self.cfg.signal.hop_s
        while True:
            now = self._clock(t0)
            if now >= duration_s:
                break
            if hasattr(self.src, "exhausted") and self.src.exhausted():
                break
            self._pump()
            if now >= next_hop:
                next_hop += self.cfg.signal.hop_s
                idx, frac, warming = self._measure()
                z = self.calibrator.z(idx)
                fired = self.detector.update(z, now)
                self.trace.append({
                    "t": round(now, 2),
                    "load": None if idx is None else round(idx, 4),
                    "z": None if z is None else round(z, 3),
                    "artifact_frac": round(frac, 3),
                    "run": self.detector.run,
                })
                if verbose:
                    zs = "  --  " if z is None else f"{z:+5.2f}"
                    mark = "!" if fired else ("*" if (z or 0) >= d.z_threshold else " ")
                    print(f"\r  t={now:6.1f}s  z={zs} {mark}  run={self.detector.run} "
                          f"  events={len(self.events)}   ", end="")
                if fired:
                    self._fire(now, idx, z, verbose)
            time.sleep(0.05)
        if verbose:
            print()
        return self.events

    def _fire(self, t, idx, z, verbose=True):
        n = len(self.events) + 1
        img = os.path.join(self.dir, "captures", f"event_{n:03d}.jpg")
        got = self.camera.grab(img)
        ev = {
            "n": n,
            "t_session_s": round(t, 2),
            "wall_clock": datetime.datetime.now().isoformat(timespec="seconds"),
            "load_index": None if idx is None else round(idx, 4),
            "z_score": None if z is None else round(z, 3),
            "image": os.path.relpath(got, self.dir) if got else None,
            "note": None,
        }
        self.events.append(ev)
        if verbose:
            print(f"\n  >> BOOKMARK {n} at t={t:.1f}s (z={z:+.2f})"
                  f"{' - photo saved' if got else ' - no photo'}")
        if self.on_event:
            self.on_event(ev)

    # ---------- persistence ----------

    def save(self):
        meta = {
            "label": self.label,
            "board": getattr(self.src, "board_name", "unknown"),
            "fs": self.fs,
            "frontal_channels": self.frontal_names,
            "config": {
                "window_s": self.cfg.signal.window_s,
                "hop_s": self.cfg.signal.hop_s,
                "z_threshold": self.cfg.detector.z_threshold,
                "k_consecutive": self.cfg.detector.k_consecutive,
                "cooldown_s": self.cfg.detector.cooldown_s,
                "artifact_uv": self.cfg.signal.artifact_uv,
            },
            "calibration": self.calibrator.to_dict(),
            "events": self.events,
            "n_windows": len(self.trace),
        }
        with open(os.path.join(self.dir, "session.json"), "w") as f:
            json.dump(meta, f, indent=2)
        with open(os.path.join(self.dir, "trace.json"), "w") as f:
            json.dump(self.trace, f, indent=2)
        if self._raw:
            raw = np.concatenate(self._raw, axis=1)
            np.savez_compressed(
                os.path.join(self.dir, "raw_eeg.npz"),
                eeg=raw, fs=self.fs,
                ch_names=np.array(self.src.ch_names, dtype=object),
            )
        return self.dir
