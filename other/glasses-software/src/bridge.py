"""The seam. ML process posts a SpikeEvent here; this triggers whichever glasses device.

Run this as a separate process from your detector. That separation is deliberate: if
the ML side crashes mid-session, the capture service survives, and vice versa. It also
means the detector can be Python while the capture side could later be anything.

    python -m src.bridge --device mock --port 8770
    curl -X POST localhost:8770/spike -d '{"kind":"cognitive","confidence":0.8,...}'
"""
import argparse
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

from .contract import SpikeEvent, CaptureResult, SpikeKind
from .glasses import make_device


class _Handler(BaseHTTPRequestHandler):
    device = None
    cooldown_s = 20.0
    _last_fire = 0.0
    _lock = threading.Lock()
    log = []

    def _send(self, code, payload):
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            self._send(200, {"ok": True, "device": self.device.name,
                             "connected": self.device.is_connected(),
                             "captures": len(self.log)})
        elif self.path == "/log":
            self._send(200, {"captures": self.log})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/spike":
            return self._send(404, {"error": "not found"})
        try:
            n = int(self.headers.get("Content-Length", 0))
            event = SpikeEvent.from_json(self.rfile.read(n).decode())
        except Exception as e:
            return self._send(400, {"error": f"bad SpikeEvent: {e}"})

        ok, why = event.valid()
        if not ok:
            return self._send(400, {"error": why})

        # Cooldown lives here, not in the detector. One long episode should produce one
        # clip, and the capture service is the only place that knows what it is already
        # busy doing.
        with _Handler._lock:
            since = time.time() - _Handler._last_fire
            if since < self.cooldown_s and event.kind != SpikeKind.MANUAL:
                return self._send(429, {"error": f"cooldown, {self.cooldown_s-since:.1f}s left",
                                        "event_id": event.event_id})
            _Handler._last_fire = time.time()

        res = self.device.capture(event)
        self.log.append({"event": json.loads(event.to_json()),
                         "result": json.loads(res.to_json())})
        print(f"  [{event.kind.value}] conf={event.confidence:.2f} -> "
              f"{'OK' if res.ok else 'FAIL'} {len(res.media_paths)} files "
              f"({res.duration_s:.1f}s)" + (f" {res.error}" if res.error else ""))
        return self._send(200 if res.ok else 500, json.loads(res.to_json()))

    def log_message(self, *a):
        pass          # silence default per-request noise


def serve(device_name="mock", port=8770, cooldown=20.0, **kw):
    dev = make_device(device_name, **kw)
    if not dev.connect():
        print(f"warning: {device_name} did not connect; captures will fail")
    _Handler.device = dev
    _Handler.cooldown_s = cooldown
    srv = HTTPServer(("0.0.0.0", port), _Handler)
    print(f"bridge up on :{port}  device={dev.name}  cooldown={cooldown}s")
    print("  POST /spike   GET /health   GET /log")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nstopping")
    finally:
        dev.disconnect()


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--device", default="mock", choices=["mock", "meta"])
    p.add_argument("--port", type=int, default=8770)
    p.add_argument("--cooldown", type=float, default=20.0)
    p.add_argument("--phone-url", default="http://192.168.1.50:8080")
    a = p.parse_args()
    kw = {"phone_url": a.phone_url} if a.device == "meta" else {}
    serve(a.device, a.port, a.cooldown, **kw)
