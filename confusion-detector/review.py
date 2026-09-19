#!/usr/bin/env python
"""End-of-session review: "here are the things that confused you".

Prints a summary and writes a self-contained HTML page with the captured images on a
timeline. The HTML is the demo payoff - a judge should understand it without narration.

    .venv/bin/python review.py sessions/LABEL
"""
import base64
import json
import os
import sys


def load(d):
    with open(os.path.join(d, "session.json")) as f:
        meta = json.load(f)
    trace = []
    tp = os.path.join(d, "trace.json")
    if os.path.exists(tp):
        with open(tp) as f:
            trace = json.load(f)
    return meta, trace


def sparkline(trace, thresh, width=60):
    """ASCII z-score trace, so the terminal output shows the evidence, not just events."""
    zs = [t["z"] for t in trace if t["z"] is not None]
    if not zs:
        return "  (no clean windows)"
    lo, hi = min(zs), max(zs)
    rng = max(hi - lo, 1e-6)
    step = max(1, len(zs) // width)
    blocks = " .:-=+*#%@"
    line = "".join(blocks[min(len(blocks) - 1, int((z - lo) / rng * (len(blocks) - 1)))]
                   for z in zs[::step])
    return (f"  z range {lo:+.2f} to {hi:+.2f}, threshold {thresh:+.2f}\n"
            f"  {line}")


def embed(path):
    """Inline images as data URIs so the HTML is one portable file."""
    try:
        with open(path, "rb") as f:
            return "data:image/jpeg;base64," + base64.b64encode(f.read()).decode()
    except Exception:
        return None


def html(meta, d, out):
    cards = []
    for e in meta["events"]:
        img = None
        if e.get("image"):
            img = embed(os.path.join(d, e["image"]))
        t = e["t_session_s"]
        pic = (f'<img src="{img}" alt="capture {e["n"]}">' if img
               else '<div class="noimg">no photo captured</div>')
        cards.append(f"""
      <article class="card">
        <div class="thumb">{pic}</div>
        <div class="meta">
          <div class="n">#{e['n']}</div>
          <div class="t">{int(t // 60)}m {int(t % 60)}s into session</div>
          <div class="z">sustained load z = {e['z_score']:+.2f}</div>
        </div>
      </article>""")
    if not cards:
        cards = ['<p class="empty">No sustained-load events in this session.</p>']

    cal = meta.get("calibration", {})
    cfg = meta.get("config", {})
    doc = f"""<!doctype html>
<meta charset="utf-8">
<title>What confused you - {meta['label']}</title>
<style>
  :root {{ color-scheme: light dark; --bg:#fff; --fg:#111; --mut:#666; --line:#e3e3e3; --accent:#b23; }}
  @media (prefers-color-scheme: dark) {{
    :root {{ --bg:#151517; --fg:#eee; --mut:#999; --line:#2c2c30; --accent:#f56; }}
  }}
  body {{ margin:0; padding:2.5rem 1.5rem; background:var(--bg); color:var(--fg);
         font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }}
  .wrap {{ max-width: 940px; margin: 0 auto; }}
  h1 {{ font-size:1.7rem; margin:0 0 .3rem; }}
  .sub {{ color:var(--mut); margin-bottom:2rem; }}
  .stats {{ display:flex; gap:2rem; flex-wrap:wrap; padding:1rem 0;
            border-top:1px solid var(--line); border-bottom:1px solid var(--line);
            margin-bottom:2rem; }}
  .stat b {{ display:block; font-size:1.5rem; }}
  .stat span {{ color:var(--mut); font-size:.85rem; }}
  .card {{ display:flex; gap:1.2rem; padding:1rem 0; border-bottom:1px solid var(--line); }}
  .thumb img {{ width:320px; border-radius:8px; display:block; }}
  .noimg {{ width:320px; height:180px; border:1px dashed var(--line); border-radius:8px;
            display:flex; align-items:center; justify-content:center; color:var(--mut); }}
  .n {{ font-size:1.6rem; font-weight:600; color:var(--accent); }}
  .t {{ font-weight:600; margin-top:.2rem; }}
  .z {{ color:var(--mut); font-size:.9rem; margin-top:.35rem; }}
  .empty {{ color:var(--mut); padding:2rem 0; }}
  footer {{ margin-top:2.5rem; color:var(--mut); font-size:.82rem;
            border-top:1px solid var(--line); padding-top:1rem; }}
</style>
<div class="wrap">
  <h1>What confused you</h1>
  <div class="sub">Session {meta['label']} &middot; {meta.get('board','')} &middot;
      channels {', '.join(meta.get('frontal_channels', []))}</div>
  <div class="stats">
    <div class="stat"><b>{len(meta['events'])}</b><span>moments flagged</span></div>
    <div class="stat"><b>{meta.get('n_windows',0)}</b><span>windows analysed</span></div>
    <div class="stat"><b>{cal.get('n_windows',0)}</b><span>calibration windows</span></div>
    <div class="stat"><b>z &ge; {cfg.get('z_threshold','?')}</b><span>threshold</span></div>
    <div class="stat"><b>{cfg.get('k_consecutive','?')} &times; {cfg.get('hop_s','?')}s</b><span>sustained before firing</span></div>
  </div>
  {''.join(cards)}
  <footer>
    Flagged when frontal theta/alpha stayed above this wearer's own calibrated baseline
    for {cfg.get('k_consecutive','?')} consecutive windows. Photo taken on trigger, not
    buffered beforehand. This measures sustained cognitive load, which is not the same
    thing as confusion, and it is not a diagnostic.
  </footer>
</div>"""
    with open(out, "w") as f:
        f.write(doc)
    return out


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    d = sys.argv[1].rstrip("/")
    if not os.path.exists(os.path.join(d, "session.json")):
        print(f"no session.json in {d}")
        return 1
    meta, trace = load(d)
    cfg = meta.get("config", {})

    print("=" * 66)
    print(f"  SESSION {meta['label']}")
    print("=" * 66)
    print(f"  board      {meta.get('board')}   fs {meta.get('fs')}Hz")
    print(f"  channels   {', '.join(meta.get('frontal_channels', []))}")
    cal = meta.get("calibration", {})
    print(f"  baseline   mean={cal.get('mean')} sd={cal.get('std')} "
          f"({cal.get('n_windows')} windows)")
    print(f"  windows    {meta.get('n_windows',0)} analysed")
    print()
    if trace:
        print(sparkline(trace, cfg.get("z_threshold", 1.0)))
        print()

    ev = meta["events"]
    if not ev:
        print("  No sustained-load events. Either it was an easy session, or the")
        print("  threshold is too high - try --z 0.7 or --k 3.")
    else:
        print(f"  {len(ev)} thing(s) that held your attention hardest:\n")
        for e in ev:
            t = e["t_session_s"]
            img = f"  [{e['image']}]" if e.get("image") else "  [no photo]"
            print(f"    #{e['n']}  {int(t//60)}m{int(t%60):02d}s   "
                  f"z={e['z_score']:+.2f}{img}")

    out = html(meta, d, os.path.join(d, "review.html"))
    print(f"\n  Visual review: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
