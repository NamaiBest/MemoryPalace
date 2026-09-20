import argparse
import json
from pathlib import Path

import joblib

from .data import Recording, write_json
from .model import train
from .signal import Config
from .synthetic import simulate


def main():
    parser = argparse.ArgumentParser(description="Offline EEG candidate experiment. Synthetic != physiological evidence.")
    commands = parser.add_subparsers(dest="command", required=True)
    demo = commands.add_parser("demo", help="Train both models and run the held-out synthetic benchmark")
    demo.add_argument("--out", type=Path, default=Path("outputs/eeg_demo"))
    demo.add_argument("--session-seed", type=int, default=19)
    real = commands.add_parser("real", help="Run the fixed within-session Shin n-back real EEG benchmark")
    real.add_argument("--data", type=Path, default=Path("data/shin2018/VP001"))
    real.add_argument("--out", type=Path, default=Path("outputs/real_vp001"))
    workload = commands.add_parser("workload", help="Fit labeled workload scorers and test fresh VP002 holdout blocks")
    workload.add_argument("--data", type=Path, default=Path("data/shin2018/VP002"))
    workload.add_argument("--out", type=Path, default=Path("outputs/workload_vp002"))
    volatility = commands.add_parser("volatility", help="Compare power and lagged EWMA features on fresh VP003")
    volatility.add_argument("--data", type=Path, default=Path("data/shin2018/VP003"))
    volatility.add_argument("--out", type=Path, default=Path("outputs/volatility_vp003"))
    fourier = commands.add_parser("fourier", help="Compare band power and sliding Fourier spectra on fresh VP004")
    fourier.add_argument("--data", type=Path, default=Path("data/shin2018/VP004"))
    fourier.add_argument("--out", type=Path, default=Path("outputs/fourier_vp004"))
    combined = commands.add_parser("combined", help="Replay both EEG branches on known VP002 excerpts; integration only")
    combined.add_argument("--data", type=Path, default=Path("data/shin2018/VP002"))
    combined.add_argument("--stretch-kind", choices=["power_ema", "power"], default="power_ema",
                          help="power_ema: selected smoothed wrappers (session*.power_ema.joblib); power: original unsmoothed classifiers")
    combined.add_argument("--workload-models", type=Path, default=None,
                          help="Directory with the stretch models and their standalone event exports; by default outputs/smoothing_vp002 for power_ema or outputs/workload_vp002 for power")
    combined.add_argument("--reference-bursts", type=Path, default=None,
                          help="Earlier combined output directory; verify burst candidates are identical apart from stretch links")
    combined.add_argument("--out", type=Path, default=Path("outputs/combined_vp002_smoothed"))
    combined.add_argument("--top-k", type=int, default=5, help="Burst budget per excerpt; all confirmed stretches remain")
    dynamic = commands.add_parser("dynamic-tda", help="Compare Bayesian workload inference and zigzag ERP features on fresh VP005")
    dynamic.add_argument("--data", type=Path, default=Path("data/shin2018/VP005"))
    dynamic.add_argument("--out", type=Path, default=Path("outputs/dynamic_tda_vp005"))
    smoothing = commands.add_parser("smoothing", help="Compare smoothing of the original saved VP002 power classifiers")
    smoothing.add_argument("--data", type=Path, default=Path("data/shin2018/VP002"))
    smoothing.add_argument("--models", type=Path, default=Path("outputs/workload_vp002"))
    smoothing.add_argument("--out", type=Path, default=Path("outputs/smoothing_vp002"))
    background = commands.add_parser("background", help="Fresh-participant burst comparison with calibration-only background negatives, plus chosen-stretch validation")
    background.add_argument("--data", type=Path, default=Path("data/shin2018/VP006"))
    background.add_argument("--out", type=Path, default=Path("outputs/background_vp006"))
    background.add_argument("--draws", type=int, default=2000, help="Random-flag draws for the null distributions")
    backtest = commands.add_parser("backtest", help="Walk-forward figures and circular time-shift null for the saved state detectors; fits nothing")
    backtest.add_argument("--data-root", type=Path, default=Path("data/shin2018"))
    backtest.add_argument("--out", type=Path, default=Path("outputs/backtest_state"))
    backtest.add_argument("--draws", type=int, default=2000)
    channel = commands.add_parser("channel-check", help="Aligned target AUROC by channel set on inspected participants; fits subsets on calibration blocks only")
    channel.add_argument("--data-root", type=Path, default=Path("data/shin2018"))
    channel.add_argument("--out", type=Path, default=Path("outputs/channel_check_dev"))
    channel.add_argument("--participants", nargs="+", default=["VP001", "VP002", "VP005", "VP006"])
    channel.add_argument("--erp-highpass", type=float, default=1.0, help="Lower edge of the ERP analysis band in Hz; quality checks stay at 1-30 Hz")
    burst_diag = commands.add_parser("burst-diagnostic", help="Place existing continuous burst flags relative to markers on inspected participants; fits nothing")
    burst_diag.add_argument("--data-root", type=Path, default=Path("data/shin2018"))
    burst_diag.add_argument("--out", type=Path, default=Path("outputs/burst_diagnostic_dev"))
    burst_diag.add_argument("--draws", type=int, default=2000, help="Random-flag draws per participant for the null distributions")
    simulation = commands.add_parser("simulate", help="Create a 180-second virtual-session block and separate truth")
    simulation.add_argument("--out", type=Path, required=True)
    simulation.add_argument("--seed", type=int, default=3000)
    simulation.add_argument("--session-seed", type=int, default=19)
    simulation.add_argument("--scenario", choices=["mixed", "independent", "negative", "baseline"], default="mixed")
    training = commands.add_parser("train", help="Train from a JSON manifest of independent calibration blocks")
    training.add_argument("--manifest", type=Path, required=True)
    training.add_argument("--kind", choices=["power", "tangent"], default="tangent")
    training.add_argument("--out", type=Path, required=True)
    detection = commands.add_parser("detect", help="Read samples + fitted model; output timestamped flags")
    detection.add_argument("--recording", type=Path, required=True)
    detection.add_argument("--model", type=Path, required=True)
    detection.add_argument("--out", type=Path, required=True)
    detection.add_argument("--scope", choices=["onset", "all"], default="all", help="Burst search scope; stretches are always detected independently")
    detection.add_argument("--top-k", type=int, default=5, help="Maximum burst events; all confirmed stretches are also exported")
    detection.add_argument("--offset-s", type=float, default=0)
    detection.add_argument("--session-id", default=None, help="Output work-session ID; does not bypass EEG calibration checks")
    args = parser.parse_args()
    if args.command == "demo":
        from .benchmark import run_demo
        run_demo(args.out, args.session_seed)
        print((args.out / "RESULTS.md").read_text())
    elif args.command == "real":
        from .real_benchmark import run_real_benchmark
        run_real_benchmark(args.data, args.out)
        print((args.out / "RESULTS.md").read_text())
    elif args.command == "workload":
        from .workload_benchmark import run_workload_benchmark
        run_workload_benchmark(args.data, args.out)
        print((args.out / "RESULTS.md").read_text())
    elif args.command == "volatility":
        from .volatility_benchmark import run_volatility_benchmark
        run_volatility_benchmark(args.data, args.out)
        print((args.out / "RESULTS.md").read_text())
    elif args.command == "fourier":
        from .fourier_benchmark import run_fourier_benchmark
        run_fourier_benchmark(args.data, args.out)
        print((args.out / "RESULTS.md").read_text())
    elif args.command == "simulate":
        rec, truth = simulate(args.seed, args.session_seed, args.scenario)
        args.out.mkdir(parents=True, exist_ok=True)
        rec.save(args.out / "recording.npz")
        write_json(args.out / "truth.json", truth)
        print(args.out / "recording.npz")
    elif args.command == "combined":
        from .combined_replay import DEFAULT_MODEL_DIRECTORIES, run_combined_replay
        models = args.workload_models or Path(DEFAULT_MODEL_DIRECTORIES[args.stretch_kind])
        run_combined_replay(args.data, models, args.out, args.top_k, args.stretch_kind, args.reference_bursts)
        print((args.out / "RESULTS.md").read_text())
    elif args.command == "train":
        rows = json.loads(args.manifest.read_text())
        pairs = [(Recording.load(args.manifest.parent / row["recording"]),
                  json.loads((args.manifest.parent / row["labels"]).read_text())) for row in rows]
        # New sensor sets may be supplied explicitly through the Python Config API.
        model = train(pairs, kind=args.kind, config=Config())
        args.out.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(model, args.out)
        write_json(args.out.with_suffix(".model_card.json"), model.model_card)
        print(args.out)
    elif args.command == "dynamic-tda":
        from .dynamic_tda_benchmark import run_dynamic_tda_benchmark
        run_dynamic_tda_benchmark(args.data, args.out)
        print((args.out / "RESULTS.md").read_text())
    elif args.command == "background":
        from .background_benchmark import run_background_benchmark
        run_background_benchmark(args.data, args.out, args.draws)
        print((args.out / "RESULTS.md").read_text())
    elif args.command == "backtest":
        from .backtest import run_backtest
        run_backtest(args.data_root, args.out, args.draws)
        print((args.out / "RESULTS.md").read_text())
    elif args.command == "channel-check":
        from .channel_check import run_channel_check
        run_channel_check(args.data_root, args.out, tuple(args.participants), args.erp_highpass)
        print((args.out / "RESULTS.md").read_text())
    elif args.command == "burst-diagnostic":
        from .burst_diagnostic import run_burst_diagnostic
        run_burst_diagnostic(args.data_root, args.out, args.draws)
        print((args.out / "RESULTS.md").read_text())
    elif args.command == "smoothing":
        from .smoothing_benchmark import run_smoothing_benchmark
        run_smoothing_benchmark(args.data, args.models, args.out)
        print((args.out / "RESULTS.md").read_text())
    else:
        rec = Recording.load(args.recording)
        model = joblib.load(args.model)
        events, scan = model.detect(rec, args.top_k, args.scope, args.offset_s, args.session_id)
        counts = {kind: sum(e["signal_type"] == kind for e in events) for kind in ("burst", "stretch")}
        write_json(args.out, events)
        write_json(args.out.with_suffix(".diagnostics.json"), {
            "source": rec.source, "scope": args.scope, "offset_s": args.offset_s,
            "stretches_eeg_time": scan["stretches"], "rejected_windows": scan["rejected_windows"],
            "total_windows": scan["total_windows"], "returned_events": len(events), "event_counts": counts})
        print(f"Saved {counts['stretch']} stretches and {counts['burst']} bursts to {args.out}")
