#!/usr/bin/env python
"""End-to-end demo: spike detected -> glasses record 30 s -> clip on disk.

Runs with no hardware of any kind. Proves the whole chain works before HackMIT.

    python demo_end_to_end.py                  # in-process, fastest
    python demo_end_to_end.py --via-bridge     # over HTTP, the real topology
"""
import argparse
import json
import time
import urllib.request

from src.contract import SpikeEvent, SpikeKind
from src.glasses import make_device


def direct(capture_s):
    print("=" * 70)
    print("  DIRECT (ML calls the device in-process)")
    print("=" * 70)
    with make_device("mock", out_dir="captures", fps=1.0) as dev:
        for kind, conf, src in [
            (SpikeKind.SEMANTIC, 0.82, "eeg:crown"),
            (SpikeKind.LOAD,     0.71, "eeg:crown"),
        ]:
            ev = SpikeEvent(kind=kind, confidence=conf, source=src,
                            capture_seconds=capture_s,
                            detail={"note": "demo"})
            print(f"\n  spike: {kind.value} (conf {conf}) from {src}")
            t0 = time.time()
            res = dev.capture(ev)
            print(f"    -> ok={res.ok}  {len(res.media_paths)} files  "
                  f"{time.time()-t0:.1f}s  dir=captures/{ev.event_id}")


def via_bridge(capture_s, port):
    print("=" * 70)
    print(f"  VIA BRIDGE (ML posts HTTP to :{port} - the real topology)")
    print("=" * 70)
    try:
        with urllib.request.urlopen(f"http://localhost:{port}/health", timeout=3) as r:
            print("  bridge health:", json.loads(r.read().decode()))
    except Exception as e:
        print(f"  bridge not running. Start it first:\n"
              f"    python -m src.bridge --device mock --port {port}\n  ({e})")
        return

    ev = SpikeEvent(kind=SpikeKind.SEMANTIC, confidence=0.77,
                    source="eeg:crown", capture_seconds=capture_s)
    req = urllib.request.Request(f"http://localhost:{port}/spike",
                                 data=ev.to_json().encode(),
                                 headers={"Content-Type": "application/json"},
                                 method="POST")
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            print(f"  -> {json.loads(r.read().decode())}  ({time.time()-t0:.1f}s)")
    except urllib.error.HTTPError as e:
        print(f"  -> HTTP {e.code}: {e.read().decode()}")

    # second spike immediately: should be refused by cooldown
    ev2 = SpikeEvent(kind=SpikeKind.SEMANTIC, confidence=0.9,
                     source="eeg:crown", capture_seconds=capture_s)
    req2 = urllib.request.Request(f"http://localhost:{port}/spike",
                                  data=ev2.to_json().encode(),
                                  headers={"Content-Type": "application/json"},
                                  method="POST")
    try:
        with urllib.request.urlopen(req2, timeout=10) as r:
            print("  second spike -> ", json.loads(r.read().decode()))
    except urllib.error.HTTPError as e:
        print(f"  second spike -> HTTP {e.code} (expected: cooldown) "
              f"{e.read().decode()}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--via-bridge", action="store_true")
    p.add_argument("--port", type=int, default=8770)
    p.add_argument("--seconds", type=float, default=5.0,
                   help="capture length; 30 in production, 5 keeps the demo short")
    a = p.parse_args()
    if a.via_bridge:
        via_bridge(a.seconds, a.port)
    else:
        direct(a.seconds)
