#!/usr/bin/env python3
"""Feed synthetic EEG to an already-running backend.

`run.py demo` is self-contained: it starts its own server and its own mock phone. That
is the wrong shape for testing against a real Android phone, which has to connect to a
long-lived backend started separately. This script fills that gap — it drives a backend
that is already serving, so the phone on the other side is the real one.

    export DEMO_TOKEN=...
    confusion-detector/.venv/bin/python hardware-demo/feed_synthetic.py calibrate
    confusion-detector/.venv/bin/python hardware-demo/feed_synthetic.py trigger

`calibrate` feeds 120 s of baseline and stops, leaving the backend ready. `trigger` also
starts a recording, raises theta/alpha until the detector fires, and verifies the phone
acknowledged the stop. The EEG is synthetic in both cases; nothing here validates a human
signal, a Crown, or real glasses.
"""
import argparse
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent / "confusion-detector"))

from eegdemo.client import request
from eegdemo.fixture import packet, synthetic_window

BASELINE_WINDOWS = 30
LOAD_STARTS_AT = 32


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("mode", choices=["calibrate", "trigger", "stream"])
    parser.add_argument("--url", default=os.environ.get("BACKEND_URL", "http://127.0.0.1:8771"))
    parser.add_argument("--token", default=os.environ.get("DEMO_TOKEN", ""))
    parser.add_argument("--pace", type=float, default=0.5,
                        help="seconds between windows during the load phase")
    parser.add_argument("--wait", type=float, default=0,
                        help="seconds to wait for the phone to appear before giving up")
    args = parser.parse_args()

    def status():
        return request(args.url, "/status", token=args.token)

    s = status()
    print(f"phase={s['eeg']['phase']} recording={s['recording']['state']} "
          f"phone_connected={s['recording']['phone_connected']}")

    if args.mode == "trigger" and not s["recording"]["phone_connected"] and args.wait:
        print(f"waiting up to {args.wait:.0f}s for the phone...")
        deadline = time.monotonic() + args.wait
        while time.monotonic() < deadline:
            s = status()
            if s["recording"]["phone_connected"]:
                print("phone appeared, continuing")
                break
            time.sleep(1)

    if args.mode == "trigger" and not s["recording"]["phone_connected"]:
        sys.exit("phone is not connected: open the app, tap Register, keep it foregrounded")

    # A recorder mid-flight ("starting"/"stopping") refuses recalibration, and it only
    # settles when the phone acknowledges — which a flapping phone may not do promptly.
    if s["recording"]["state"] not in ("idle", "stopped"):
        print(f"recorder is {s['recording']['state']}, waiting for it to settle...")
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            s = status()
            if s["recording"]["state"] in ("idle", "stopped"):
                break
            if s["recording"]["state"] == "error":
                request(args.url, "/recording/stop", {}, args.token)
            time.sleep(1)
        else:
            sys.exit(f"recorder stuck in {s['recording']['state']}: check the phone, then retry")
        print(f"recorder settled: {s['recording']['state']}")

    # The backend drops last_arrival once input goes stale, and /recording/start requires
    # a live source as well as a completed calibration. So always reset and feed straight
    # through into the start call rather than relying on an earlier calibration.
    if s["eeg"]["phase"] == "ready":
        print("resetting stale calibration...")
        request(args.url, "/calibration/reset", {}, args.token)

    start_ms = time.time() * 1000
    print(f"feeding {BASELINE_WINDOWS * 4}s of baseline...")
    for i in range(BASELINE_WINDOWS):
        request(args.url, "/eeg", packet(synthetic_window(i), start_ms + i * 4000), args.token)
    s = status()
    if s["eeg"]["phase"] != "ready":
        sys.exit(f"calibration did not complete: phase={s['eeg']['phase']}")
    print(f"calibrated: {s['eeg']['clean_calibration_windows']} clean windows")

    if args.mode == "calibrate":
        return

    if args.mode == "stream":
        # /recording/start refuses unless EEG arrived recently, so a session driven from
        # the web UI needs a source that keeps running rather than one that stops after
        # calibrating. Baseline windows only: this keeps the backend live without ever
        # tripping the detector, so captures happen when a human asks for them.
        print("streaming baseline EEG; press Ctrl-C to stop")
        index = BASELINE_WINDOWS
        failures = 0
        try:
            while True:
                time.sleep(4.0)
                try:
                    request(args.url, "/eeg",
                            packet(synthetic_window(index), start_ms + index * 4000),
                            args.token)
                    failures = 0
                except Exception as exc:
                    # A single dropped request must not end the session. Losing the feeder
                    # silently is worse than the blip: the signal goes stale within seconds
                    # and every later capture is refused for a reason that points at the
                    # phone rather than at the dead process on this side.
                    failures += 1
                    print(f"  feed error ({failures}): {exc}")
                    if failures >= 15:
                        print("  backend unreachable for ~60s, giving up")
                        return
                    continue
                index += 1
                if index % 15 == 0:
                    try:
                        state = status()
                        print(f"  {index} windows · recorder={state['recording']['state']} "
                              f"· phone={state['recording']['phone_connected']}")
                    except Exception:
                        pass
        except KeyboardInterrupt:
            print("\nstopped streaming")
        return

    print("starting recording on the phone...")
    request(args.url, "/recording/start", {}, args.token)
    deadline = time.monotonic() + 30
    while status()["recording"]["state"] == "starting":
        if time.monotonic() > deadline:
            sys.exit("phone never acknowledged start: is a device connected and preview open?")
        time.sleep(0.2)

    print("raising theta/alpha until the detector fires...")
    window = None
    for i in range(BASELINE_WINDOWS, BASELINE_WINDOWS + 14):
        time.sleep(args.pace)
        request(args.url, "/eeg",
                packet(synthetic_window(i, high=i >= LOAD_STARTS_AT), start_ms + i * 4000),
                args.token)
        s = status()
        window = s["eeg"]["last_window"]
        print(f"  t={window['sample_time_s']:.0f}s z={window['z_score']:+.2f} "
              f"run={window['run']} recording={s['recording']['state']}")
        if s["recording"]["state"] in ("stopping", "stopped"):
            break

    deadline = time.monotonic() + 20
    while s["recording"]["state"] == "stopping":
        if time.monotonic() > deadline:
            sys.exit("phone never acknowledged stop")
        time.sleep(0.2)
        s = status()

    if s["recording"]["state"] != "stopped":
        sys.exit(f"FAILED: final state {s['recording']['state']}")

    print(f"\nPASS: EEG stopped the recording. Media on phone: {s['recording']['media_path']}")
    if window:
        print(f"trigger at t={window['sample_time_s']:.0f}s, "
              f"load scripted from {LOAD_STARTS_AT * 4}s")


if __name__ == "__main__":
    main()
