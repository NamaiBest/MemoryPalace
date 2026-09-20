#!/usr/bin/env python3
"""Run from any working directory; reuses the existing detector without copying it."""
import argparse
import datetime
import json
import os
from pathlib import Path
import sys
import threading
import time

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / "confusion-detector"))

from eegdemo.client import request
from eegdemo.fixture import packet, synthetic_window
from eegdemo.server import Runtime, create_server
from eegdemo.mock_phone import MockPhone


def run_demo(args):
    runtime = Runtime(args.output, recorder=args.recorder, token=args.token)
    server = create_server(runtime, port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_port}"
    phone = MockPhone(url, runtime.output / "mock-phone", args.token).start() if args.recorder == "phone" else None
    start = time.time() * 1000
    try:
        print("SIMULATED EEG + TEST-PATTERN CAMERA. No physical hardware is connected.")
        if phone and not phone.ready.wait(5):
            raise RuntimeError("mock phone did not connect")
        print("Replaying 120 seconds of baseline through the real HTTP EEG endpoint.")
        for i in range(30):
            request(url, "/eeg", packet(synthetic_window(i), start + i * 4000), args.token)
        status = request(url, "/status", token=args.token)
        assert status["eeg"]["phase"] == "ready", status
        request(url, "/recording/start", {}, args.token)
        deadline = time.monotonic() + 30
        while request(url, "/status", token=args.token)["recording"]["state"] == "starting":
            if time.monotonic() > deadline:
                raise RuntimeError("phone did not acknowledge recording start")
            time.sleep(0.1)
        print("Recording a real MP4. Replaying baseline, then sustained high theta/alpha.")
        for i in range(30, 40):
            time.sleep(4 / args.speed)
            request(url, "/eeg", packet(synthetic_window(i, high=i >= 32), start + i * 4000), args.token)
            status = request(url, "/status", token=args.token)
            window = status["eeg"]["last_window"]
            print(f"sample t={window['sample_time_s']:.0f}s z={window['z_score']:+.2f} "
                  f"run={window['run']} recording={status['recording']['state']}")
            if status["recording"]["state"] in ("stopping", "stopped"):
                break
        deadline = time.monotonic() + 15
        while status["recording"]["state"] == "stopping":
            if time.monotonic() > deadline:
                raise RuntimeError("phone did not acknowledge recording stop")
            time.sleep(0.1)
            status = request(url, "/status", token=args.token)
        assert status["recording"]["state"] == "stopped", "EEG did not stop the recording"
        report = {"validated": "synthetic EEG -> HTTP -> existing detector -> actual MP4 stop",
                  "physical_hardware_tested": False, "replay_speed": args.speed,
                  "phone_protocol_tested": phone is not None,
                  "scripted_load_start_s": 128, "trigger_sample_time_s": window["sample_time_s"],
                  "trigger_latency_in_signal_s": window["sample_time_s"] - 128,
                  "status": status}
        (runtime.output / "demo-result.json").write_text(json.dumps(report, indent=2))
        print(f"PASS: recording stopped. Video: {status['recording']['media_path']}")
        print(f"Evidence: {runtime.output / 'demo-result.json'}")
    finally:
        if phone:
            phone.close()
        server.shutdown()
        server.server_close()
        thread.join()
        runtime.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["demo", "serve", "status", "start", "stop", "reset", "mark", "replay", "mock-phone"])
    parser.add_argument("--output", type=Path, default=ROOT / "runs" / datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f"))
    parser.add_argument("--library", type=Path,
                        default=Path(os.environ["MEMORYPALACE_LIBRARY_DIR"])
                        if os.environ.get("MEMORYPALACE_LIBRARY_DIR") else None,
                        help="durable moment/media directory (serve defaults to hardware-demo/library)")
    parser.add_argument("--source", choices=["synthetic", "crown", "playback"], default="crown")
    parser.add_argument("--recorder", choices=["test-video", "phone"], default="test-video")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8771)
    parser.add_argument("--url", default="http://127.0.0.1:8771")
    parser.add_argument("--token", default=os.environ.get("DEMO_TOKEN", ""), help=argparse.SUPPRESS)
    parser.add_argument("--notch", type=int, choices=[0, 50, 60], default=60)
    parser.add_argument("--speed", type=float, default=8, help="demo/replay speed; 1 means real time")
    parser.add_argument("--file", type=Path, help="saved eeg.jsonl for replay")
    parser.add_argument("--label", help="task marker, e.g. hard_start")
    args = parser.parse_args()
    if not 0 < args.speed <= 64:
        parser.error("speed must be in (0,64]")
    if args.command == "demo":
        run_demo(args)
    elif args.command == "serve":
        runtime = Runtime(args.output, args.source, args.recorder, args.token, args.notch,
                          library_dir=args.library or ROOT / "library",
                          legacy_runs=ROOT / "runs")
        server = create_server(runtime, args.host, args.port)
        server.timeout = 0.5
        print(f"Backend: http://{args.host}:{server.server_port} (source={args.source}, recorder={args.recorder})")
        try:
            while True:
                server.handle_request()
                with runtime.lock:
                    runtime.pipeline.watchdog()
                    runtime.recorder.status()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()
            runtime.close()
    elif args.command == "mock-phone":
        phone = MockPhone(args.url, args.output, args.token).start()
        print("SIMULATED PHONE: polling commands and recording an FFmpeg test pattern. Ctrl-C to stop.")
        try:
            while phone.thread.is_alive():
                time.sleep(0.5)
        except KeyboardInterrupt:
            pass
        finally:
            phone.close()
    elif args.command == "replay":
        if not args.file:
            parser.error("replay requires --file path/to/eeg.jsonl")
        previous = None
        with args.file.open() as handle:
            for line in handle:
                body = json.loads(line)["detail"]
                body["source"] = "playback"
                body["stream_id"] = "saved-session-replay"
                timestamp = body["epoch"]["info"]["startTime"]
                if previous is not None:
                    time.sleep(max(0, min(4, (timestamp - previous) / 1000)) / args.speed)
                request(args.url, "/eeg", body, args.token)
                previous = timestamp
        print("Replay finished. Recording remains manually controlled; inspect status.")
    else:
        path = {"status": "/status", "start": "/recording/start", "stop": "/recording/stop",
                "reset": "/calibration/reset", "mark": "/markers"}[args.command]
        body = None if args.command == "status" else ({"label": args.label} if args.command == "mark" else {})
        print(json.dumps(request(args.url, path, body, args.token), indent=2))


if __name__ == "__main__":
    main()
