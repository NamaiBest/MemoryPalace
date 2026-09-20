# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import *

PAD = 330000
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
os.makedirs(OUT, exist_ok=True)


def block(x, y, w, head, sub, hsz=2250, ssz=1875, hcol=INK, scol=BODY, gap=95000):
    """A bold label with a body line under it. Returns (xml, height)."""
    hh = int(wrapped(head, w, hsz, 1) * hsz / 100.0 * EMU_PT * 1.18)
    sh = int(wrapped(sub, w, ssz, 0) * ssz / 100.0 * EMU_PT * 1.24) if sub else 0
    s = tb(x, y, w, hh, [para([run(head, hsz, 1, hcol)], "l", 118)], "t", head[:40])
    if sub:
        s += tb(x, y + hh + gap, w, sh, [para([run(sub, ssz, 0, scol)], "l", 124)],
                "t", sub[:40])
    return s, hh + (gap + sh if sub else 0)


# ------------------------------------------------------------------ slide 12
def slide12():
    s = []
    s.append(rect(14954250, 381000, 2286000, 1524000, "102F45"))
    s.append(pic("rId3", 15049500, 429292, 2095500, 1389317, "Voloridge"))
    s.append(header("Six public datasets. One question.",
                    "Voloridge • can scalp EEG mark a state change well enough to fire a camera?"))

    items = [
        ("Shin et al. 2018 • dataset A", "28 channels • 5 people • 15 sessions",
         "Task versus rest during n-back. This is the model we ship.", BRASS),
        ("OpenNeuro ds006394", "16 channels • 33 people • 51 recordings",
         "Surprise versus dummy surprise. This chose our hardware.", BRASS),
        ("PhysioNet EEGMMIDB", "64 channels • 109 people • 278 MB",
         "Crown's exact eight channel names, no substitution.", BLUE),
        ("PhysioNet Auditory EEG", "4 channels • 20 people • 476 MB",
         "A real four electrode montage. Split by recording, never at random.", BLUE),
        ("BED", "Restricted access • not downloaded",
         "The only corpus with sessions a week apart. We do not claim it.", CRIT),
        ("Our own Emotiv EPOC X", "14 channels • 192 trials • committed",
         "Three class imagery 65.8%, chance 33.3%, shuffled control 34.8%.", OKG),
    ]

    cols, gapx, gapy = 3, 400050, 380000
    cw = (CW - gapx * (cols - 1)) // cols
    ch = 2700000
    y0 = 3270000
    for i, (name, meta, what, accent) in enumerate(items):
        cx = L + (i % cols) * (cw + gapx)
        cy = y0 + (i // cols) * (ch + gapy)
        s.append(card(cx, cy, cw, ch))
        s.append(rect(cx, cy + 300000, 47625, 600000, accent))
        iw = cw - 2 * PAD
        fits([(name, 2100, 1)], iw, 700000, "s12 name " + name)
        yy = cy + PAD
        b, hgt = block(cx + PAD, yy, iw, name, meta, 2100, 1800, INK, accent)
        s.append(b); yy += hgt + 150000
        hh = int(wrapped(what, iw, 1875, 0) * 1875 / 100.0 * EMU_PT * 1.26)
        if yy + hh > cy + ch - PAD + 60000:
            raise SystemExit("OVERFLOW s12 card %s (%d > %d)" % (name, yy + hh, cy + ch - PAD))
        s.append(tb(cx + PAD, yy, iw, hh,
                    [para([run(what, 1875, 0, BODY)], "l", 126)], "t", what[:40]))

    s.append(footer("167 people, 1.3 GB, labels untouched • public data validates the "
                    "machinery, it never supplies the deployed weights • dataset/README.md"))
    return slide(s)


# ------------------------------------------------------------------ slide 13
def slide13():
    s = []
    s.append(rect(14954250, 381000, 2286000, 1524000, "102F45"))
    s.append(pic("rId3", 15049500, 429292, 2095500, 1389317, "Voloridge"))
    s.append(header("84 numbers. Eight electrodes.",
                    "Voloridge • the simplest model that won, and the smallest montage that keeps it."))

    ly, lh = 3270000, 5900000
    lw = 7315200
    s.append(card(L, ly, lw, lh))
    iw = lw - 2 * PAD
    yy = ly + PAD
    s.append(simple(L + PAD, yy, iw, 500000, "What survived", 2700, 1, BLUE, name="What survived"))
    yy += 540000
    steps = [
        ("28 EEG channels, 200 Hz", "Shin et al. 2018, unmodified labels"),
        ("Regress out the eye channels", "Fit before the task, frozen before scoring"),
        ("Theta / alpha / beta log power", "84 features • 2 s windows, every 0.25 s"),
        ("Logistic regression, then one moving average", "Task versus rest • one smoothing parameter"),
    ]
    for head, sub in steps:
        b, hgt = block(L + PAD, yy, iw, head, sub, 1950, 1725)
        s.append(b); yy += hgt + 130000
    s.append(rule(L + PAD, yy, iw, EDGE)); yy += 180000
    s.append(simple(L + PAD, yy, iw, 460000, "Seven richer alternatives lost or tied",
                    2100, 1, BRASS, name="Seven richer"))
    yy += 430000
    tail = "Riemannian 1,218 features • Fourier 728 • zigzag topology 108 • Bayesian state space"
    th = int(wrapped(tail, iw, 1800, 0) * 1800 / 100.0 * EMU_PT * 1.26)
    s.append(tb(L + PAD, yy, iw, th, [para([run(tail, 1800, 0, BODY)], "l", 126)], "t", "tail"))
    if yy + th > ly + lh - PAD + 80000:
        raise SystemExit("OVERFLOW s13 left %d > %d" % (yy + th, ly + lh - PAD))

    rx = L + lw + 476250
    rw = R - rx
    s.append(card(rx, ly, rw, lh))
    iw2 = rw - 2 * PAD
    yy = ly + PAD
    s.append(simple(rx + PAD, yy, iw2, 500000, "How few electrodes, and where",
                    2700, 1, BLUE, name="How few"))
    yy += 500000
    s.append(simple(rx + PAD, yy, iw2, 380000,
                    "Within-subject AUC on ds006394 • chance 0.50",
                    1725, 0, MUTE, name="axis note"))
    yy += 420000

    bars = [
        ("16 electrodes", "full 16 ch montage", 0.778, MUTE, ""),
        ("8 electrodes", "Crown-like headband", 0.763, BRASS, "WE SHIP THIS · 98% OF 16"),
        ("4 electrodes", "Ganglion • Fz Cz F7 F8", 0.719, BLUE, ""),
        ("2 electrodes", "midline • Fz Cz", 0.719, BLUE, ""),
        ("2 electrodes", "glasses brow • Fp1 Fp2", 0.606, CRIT, ""),
    ]
    lab_w = 2750000
    track_x = rx + PAD + lab_w
    track_w = iw2 - lab_w - 950000
    lo, hi = 0.50, 0.80
    for name, meta, auc, col, tag in bars:
        fits([(meta, 1575, 0)], lab_w - 120000, 300000, "s13 meta " + meta)
        s.append(simple(rx + PAD, yy, lab_w - 120000, 330000, name, 1950, 1, INK, name=name))
        s.append(simple(rx + PAD, yy + 330000, lab_w - 120000, 300000, meta, 1575, 0, MUTE,
                        name=meta[:30]))
        s.append(rect(track_x, yy + 120000, track_w, 300000, "EDE7D9", radius=50000))
        bw = int(track_w * (auc - lo) / (hi - lo))
        s.append(rect(track_x, yy + 120000, bw, 300000, col, radius=50000))
        s.append(simple(track_x + track_w + 90000, yy + 95000, 860000,
                        340000, "%.3f" % auc, 1950, 1, col, name="auc"))
        if tag:
            fits([(tag, 1500, 1)], track_w, 280000, "s13 tag " + tag)
            s.append(simple(rx + PAD, yy + 620000, iw2 - 950000, 280000, tag, 1500, 1, col,
                            name="tag"))
            yy += 920000
        else:
            yy += 640000
    yy += 60000
    s.append(rule(rx + PAD, yy, iw2, EDGE)); yy += 170000
    punch = ("Every one of the top 12 pairs of 120 contains Cz or Fz. One well placed "
             "pair beats four badly placed ones.")
    ph = int(wrapped(punch, iw2, 1875, 0) * 1875 / 100.0 * EMU_PT * 1.26)
    s.append(tb(rx + PAD, yy, iw2, ph, [para([run(punch, 1875, 0, BODY)], "l", 126)], "t", "punch"))
    if yy + ph > ly + lh - PAD + 80000:
        raise SystemExit("OVERFLOW s13 right %d > %d" % (yy + ph, ly + lh - PAD))

    s.append(footer("Not a 128 channel pipeline • 8 dry electrodes hold 98% of the full "
                    "montage • confusion-detector/CHANNELS.md"))
    return slide(s)


# ------------------------------------------------------------------ slide 14
def slide14():
    s = []
    s.append(pic("rId3", 13124685, 619125, 3754380, 1285875, "elastic"))
    s.append(header("Elasticsearch is the memory.",
                    "Sponsor challenge: turn complex, messy data into insights, answers or actions."))

    stages = [
        ("Moment", "10 s clip, 8 channel band powers, IMU and timestamp"),
        ("Elastic Inference", "Jina v5 Omni embeds the video itself, no transcript"),
        ("One index", "1,024 dim cosine vector beside BM25 text"),
        ("Hybrid retrieval", "BM25 and dense kNN fused by RRF"),
        ("Filters", "Confidence band, event type, time range"),
    ]
    n, gapx = len(stages), 300000
    cw = (CW - gapx * (n - 1)) // n
    cy, ch = 3230000, 2420000
    for i, (head, sub) in enumerate(stages):
        cx = L + i * (cw + gapx)
        s.append(card(cx, cy, cw, ch))
        iw = cw - 2 * PAD
        col = BRASS if i in (1, 3) else INK
        s.append(simple(cx + PAD, cy + PAD, iw, 420000, head, 2100, 1, col, name=head))
        sh = int(wrapped(sub, iw, 1725, 0) * 1725 / 100.0 * EMU_PT * 1.3)
        s.append(tb(cx + PAD, cy + PAD + 500000, iw, sh,
                    [para([run(sub, 1725, 0, BODY)], "l", 130)], "t", sub[:30]))
        if PAD + 500000 + sh > ch - PAD + 60000:
            raise SystemExit("OVERFLOW s14 stage %s" % head)
        if i < n - 1:
            s.append(arrow(cx + cw + 60000, cy + ch // 2, gapx - 120000))

    crit = [
        ("Elastic Cloud Serverless", "The whole index runs there. 12 moments live and complete.", "LIVE", OKG),
        ("Jina v5 Omni embeddings", "Video embedded directly. A text fallback is recorded, never hidden.", "LIVE", OKG),
        ("Hybrid semantic search", "A live 'laptop keyboard' query returned the keyboard moment first.", "LIVE", OKG),
        ("Workflows and Agent Builder", "Baseline normalisation and a recall agent. Designed, not yet built.", "NEXT", BRASS),
    ]
    cy2, ch2 = 5830000, 2790000
    s.append(card(L, cy2, CW, ch2, fill=PANEL, shadow=False))
    pitch = (ch2 - 2 * PAD) // 4
    head_x = L + PAD + 1560000
    head_w = 4400000
    sub_x = head_x + head_w + 300000
    sub_w = R - PAD - sub_x
    for i, (head, sub, tag, col) in enumerate(crit):
        ry = cy2 + PAD + i * pitch
        pw = 1400000
        s.append(rect(L + PAD, ry + 20000, pw, 330000, col, radius=50000))
        s.append(tb(L + PAD, ry + 20000, pw, 330000,
                    [para([run(tag, 1425, 1, "FFFFFF")], "ctr", 100)], "ctr", "pill"))
        fits([(head, 1950, 1)], head_w, 330000, "s14 head " + head)
        s.append(simple(head_x, ry, head_w, 380000, head, 1950, 1, INK, name=head))
        fits([(sub, 1800, 0)], sub_w, 360000, "s14 sub " + head)
        s.append(simple(sub_x, ry + 20000, sub_w, 340000, sub, 1800, 0, BODY, name=sub[:30]))
        if i < 3:
            s.append(rule(L + PAD, ry + pitch - 80000, CW - 2 * PAD, EDGE))

    s.append(simple(L, 8760000, CW, 560000,
                    "Semantic and vector indexing is the backbone, not a bolt-on.",
                    3000, 1, INK, name="kicker"))
    s.append(footer("Index memorypalace-multimodal-moments • .jina-embeddings-v5-omni-small "
                    "• eegdemo/elastic_store.py"))
    return slide(s)


# ------------------------------------------------------------------ slide 15
def slide15():
    s = []
    s.append(pic("rId3", 14229292, 666750, 2116667, 1190625, "Meta"))
    s.append(header("Meta sees it, hears you, answers.",
                    "Sponsor challenge: bring people closer together, with AI doing real work."))

    items = [
        ("SEE", "Muse Spark 1.3",
         "Sent as input_video. Returns title, description, keywords, topics.",
         "LIVE", OKG),
        ("GROUND", "Muse Spark web search",
         "Public names verified before indexing. A hint is never proof.",
         "LIVE", OKG),
        ("HEAR", "Muse Voice Transcribe",
         "Push to talk, 24 kHz mono, 30 s. Transcribed, then dropped.",
         "LIVE", OKG),
        ("ANSWER", "Memory Guard, Muse Spark",
         "Reasons over what Elastic returned, and cites the clip to replay.",
         "LIVE", OKG),
        ("CAPTURE", "Wearables Toolkit 0.9",
         "The pairing handoff is real. The phone camera records for now.",
         "DEMO", BLUE),
        ("CONNECT", "Muse Spark",
         "Send a day's highlights to the few people you choose.",
         "SOON", BRASS),
    ]
    cols, gapx, gapy = 3, 400050, 340000
    cw = (CW - gapx * (cols - 1)) // cols
    ch = 2400000
    y0 = 3230000
    for i, (kicker, product, what, tag, col) in enumerate(items):
        cx = L + (i % cols) * (cw + gapx)
        cy = y0 + (i // cols) * (ch + gapy)
        s.append(card(cx, cy, cw, ch))
        iw = cw - 2 * PAD
        yy = cy + PAD
        s.append(simple(cx + PAD, yy, iw - 1900000, 340000, kicker, 1800, 1, col, name=kicker))
        p, pw = pill(cx + cw - PAD - 1750000, cy + PAD - 40000, tag, col, 1425, 120000, 340000)
        s.append(rect(cx + cw - PAD - pw, cy + PAD - 40000, pw, 340000, col, radius=50000))
        s.append(tb(cx + cw - PAD - pw, cy + PAD - 40000, pw, 340000,
                    [para([run(tag, 1425, 1, "FFFFFF")], "ctr", 100)], "ctr", "pill"))
        yy += 400000
        ph = int(wrapped(product, iw, 2100, 1) * 2100 / 100.0 * EMU_PT * 1.18)
        s.append(tb(cx + PAD, yy, iw, ph, [para([run(product, 2100, 1, INK)], "l", 118)], "t", product[:30]))
        yy += ph + 130000
        wh = int(wrapped(what, iw, 1725, 0) * 1725 / 100.0 * EMU_PT * 1.3)
        s.append(tb(cx + PAD, yy, iw, wh, [para([run(what, 1725, 0, BODY)], "l", 130)], "t", what[:30]))
        if yy + wh > cy + ch - PAD + 90000:
            raise SystemExit("OVERFLOW s15 %s (%d > %d)" % (kicker, yy + wh, cy + ch - PAD))

    s.append(simple(L, 8550000, CW, 560000,
                    "A private day, made shareable with the people who matter.",
                    3000, 1, INK, name="kicker"))
    s.append(footer("Responses API and Muse Voice Transcribe are live in the build • the spoken "
                    "answer uses the device speech synthesizer, not a Meta model"))
    return slide(s)


for n, fn in ((12, slide12), (13, slide13), (14, slide14), (15, slide15)):
    open(os.path.join(OUT, "slide%d.xml" % n), "w").write(fn())
    print("wrote slide%d.xml" % n)
