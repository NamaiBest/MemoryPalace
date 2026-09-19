"""Download the surprise EEG dataset (OpenNeuro ds006394) from the S3 mirror.

openneuro.org's web endpoint is slow; the S3 bucket serves the same files ~10x faster.
Only EEG files are fetched (.set/.fdt/events/channels) - behavioural and code are not
needed for this analysis.
"""
import json, os, sys, threading, urllib.request
from concurrent.futures import ThreadPoolExecutor

BASE = "https://s3.amazonaws.com/openneuro.org/"
OUT = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "ds006394")
LOCK = threading.Lock()
DONE = [0]


def fetch(key, total):
    dest = os.path.join(OUT, key.replace("ds006394/", "", 1))
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        st = "skip"
    else:
        tmp = dest + ".part"
        try:
            with urllib.request.urlopen(BASE + key, timeout=180) as r, open(tmp, "wb") as f:
                while True:
                    c = r.read(1 << 16)
                    if not c:
                        break
                    f.write(c)
            os.replace(tmp, dest)
            st = "ok"
        except Exception as e:
            st = f"FAIL {e}"
    with LOCK:
        DONE[0] += 1
        if DONE[0] % 20 == 0 or st.startswith("FAIL"):
            print(f"[{DONE[0]}/{total}] {os.path.basename(dest)} {st}", flush=True)
    return st


if __name__ == "__main__":
    keys = json.load(open(sys.argv[1] if len(sys.argv) > 1 else "/tmp/ds006394_files.json"))
    with ThreadPoolExecutor(max_workers=8) as ex:
        res = list(ex.map(lambda k: fetch(k, len(keys)), keys))
    bad = [r for r in res if r.startswith("FAIL")]
    print(f"COMPLETE {len(res)-len(bad)}/{len(res)} ok, {len(bad)} failed")
