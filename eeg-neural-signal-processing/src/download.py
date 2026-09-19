"""Resumable, polite downloader for PhysioNet.

PhysioNet throttles hard on high concurrency. 4 workers is the sweet spot;
16 got us connection-refused across the board.
"""
import sys, os, time, threading, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor

LOCK = threading.Lock()
DONE = [0]


def fetch(url, dest, min_bytes, retries=4):
    """min_bytes is only a sanity floor. Real completeness is checked against the
    server's Content-Length, because file sizes in these datasets vary a lot
    (recordings differ in duration)."""
    tmp = dest + ".part"
    for a in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "hackmit-eeg-research/1.0"})
            with urllib.request.urlopen(req, timeout=180) as r:
                expect = int(r.headers.get("Content-Length", 0))
                if os.path.exists(dest) and expect and os.path.getsize(dest) == expect:
                    return "skip"
                with open(tmp, "wb") as f:
                    while True:
                        chunk = r.read(65536)
                        if not chunk:
                            break
                        f.write(chunk)
            got = os.path.getsize(tmp)
            if got < min_bytes or (expect and got != expect):
                raise IOError(f"short read {got}/{expect}")
            os.replace(tmp, dest)
            return "ok"
        except Exception as e:
            if a == retries - 1:
                return f"FAIL {e}"
            time.sleep(2 * (a + 1))
    return "FAIL"


def run(jobs, workers=4, label=""):
    total = len(jobs)

    def work(j):
        url, dest, mn = j
        st = fetch(url, dest, mn)
        with LOCK:
            DONE[0] += 1
            if DONE[0] % 10 == 0 or st.startswith("FAIL"):
                print(f"[{label}] {DONE[0]}/{total}  {os.path.basename(dest)} {st}", flush=True)
        return st

    with ThreadPoolExecutor(max_workers=workers) as ex:
        res = list(ex.map(work, jobs))
    ok = sum(1 for r in res if r in ("ok", "skip"))
    print(f"[{label}] COMPLETE {ok}/{total} present, {total-ok} failed", flush=True)
    return res


if __name__ == "__main__":
    which = sys.argv[1]
    root = "/Users/namai/Documents/Project/HackMIT/data"
    if which == "auditory":
        d = f"{root}/auditory/filtered"; os.makedirs(d, exist_ok=True)
        exps = ["ex01_s01","ex01_s02","ex01_s03","ex02_s01","ex02_s02","ex02_s03",
                "ex05","ex06","ex07","ex08","ex09","ex10"]
        # condition-major: partial downloads still cover all 20 subjects
        jobs = [(f"https://physionet-open.s3.amazonaws.com/auditory-eeg/1.0.0/Filtered_Data/s{s:02d}_{e}.csv",
                 f"{d}/s{s:02d}_{e}.csv", 200_000)
                for e in exps for s in range(1, 21)]
        DONE[0] = 0; run(jobs, workers=8, label="auditory")
    elif which == "mmidb_mi":
        # R04/R08/R12 = imagined left vs right fist. The classic 2-class motor-imagery
        # problem: volitional command, not just state.
        d = f"{root}/eegmmidb"; os.makedirs(d, exist_ok=True)
        jobs = [(f"https://physionet-open.s3.amazonaws.com/eegmmidb/1.0.0/S{s:03d}/S{s:03d}R{r:02d}.edf",
                 f"{d}/S{s:03d}R{r:02d}.edf", 200_000)
                for r in (4, 8, 12) for s in range(1, 110)]
        DONE[0] = 0; run(jobs, workers=8, label="mmidb_mi")
    elif which == "eegmmidb":
        d = f"{root}/eegmmidb"; os.makedirs(d, exist_ok=True)
        jobs = [(f"https://physionet-open.s3.amazonaws.com/eegmmidb/1.0.0/S{s:03d}/S{s:03d}R{r:02d}.edf",
                 f"{d}/S{s:03d}R{r:02d}.edf", 200_000)
                for s in range(1, 110) for r in (1, 2)]
        DONE[0] = 0; run(jobs, workers=8, label="eegmmidb")
