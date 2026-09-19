#!/usr/bin/env python
"""Run a live confusion-detection session.

    # develop with no hardware at all
    .venv/bin/python run_session.py --board synthetic --calibrate 20 --monitor 60

    # the team's Muse headband
    .venv/bin/python run_session.py --board muse2 --calibrate 60 --monitor 600

    # OpenBCI at HackMIT
    .venv/bin/python run_session.py --board cyton --serial-port /dev/cu.usbserial-XXXX

    # replay a saved session (deterministic demo fallback)
    .venv/bin/python run_session.py --board playback:sessions/LABEL/raw_eeg.npz
"""
import argparse
import sys
from src.config import DEFAULT
from src.eeg_source import make_source
from src.session import Session


def main():
    p = argparse.ArgumentParser(description="Confusion detector - live session")
    p.add_argument("--board", default="synthetic",
                   help="synthetic | muse2 | muses | cyton | ganglion | playback:PATH")
    p.add_argument("--serial-port", default="", help="e.g. /dev/cu.usbserial-XXXX")
    p.add_argument("--mac-address", default="", help="Muse MAC, if discovery fails")
    p.add_argument("--calibrate", type=float, default=None, help="seconds (default 60)")
    p.add_argument("--monitor", type=float, default=300.0, help="seconds")
    p.add_argument("--label", default=None, help="session name")
    p.add_argument("--no-camera", action="store_true")
    p.add_argument("--z", type=float, default=None, help="override z threshold")
    p.add_argument("--k", type=int, default=None, help="override consecutive windows")
    p.add_argument("--cooldown", type=float, default=None)
    p.add_argument("--artifact-uv", type=float, default=None,
                   help="artifact rejection threshold. ~120 for real EEG; the "
                        "synthetic board runs hot, use ~600.")
    p.add_argument("--fast", action="store_true",
                   help="playback only: run as fast as possible")
    a = p.parse_args()

    cfg = DEFAULT
    if a.calibrate is not None:
        cfg.calibration.duration_s = a.calibrate
    if a.z is not None:
        cfg.detector.z_threshold = a.z
    if a.k is not None:
        cfg.detector.k_consecutive = a.k
    if a.cooldown is not None:
        cfg.detector.cooldown_s = a.cooldown
    if a.artifact_uv is not None:
        cfg.signal.artifact_uv = a.artifact_uv
    elif a.board == "synthetic":
        # BrainFlow's generator is ~4x real EEG amplitude; a real-EEG threshold would
        # reject most of it. Only relax this for the fixture, never for real hardware.
        cfg.signal.artifact_uv = 600.0

    print("=" * 66)
    print("  CONFUSION DETECTOR")
    print("  Sustained cognitive load -> bookmark + photo of what you were on")
    print("=" * 66)

    try:
        src = make_source(a.board, serial_port=a.serial_port,
                          mac_address=a.mac_address, realtime=not a.fast)
    except Exception as e:
        print(f"\n  Could not open board {a.board!r}: {e}")
        return 1

    print(f"  board={getattr(src,'board_name',a.board)}  fs={src.fs}Hz  "
          f"channels={src.ch_names}")

    with src:
        s = Session(src, cfg, label=a.label, use_camera=not a.no_camera)
        print(f"  frontal channels in use: {s.frontal_names}")
        try:
            s.calibrate()
        except RuntimeError as e:
            print(f"\n  {e}")
            return 1
        try:
            s.monitor(a.monitor)
        except KeyboardInterrupt:
            print("\n  stopped early")
        out = s.save()

    print(f"\n  {len(s.events)} bookmark(s). Session saved to {out}")
    print(f"  Review it:  .venv/bin/python review.py {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
