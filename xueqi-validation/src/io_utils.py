"""Shared helpers: directories, logging skipped files, JSON I/O."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import numpy as np

from . import config as C


def setup_logging(name: str) -> logging.Logger:
    C.LOGS_DIR.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    logger.addHandler(sh)
    fh = logging.FileHandler(C.LOGS_DIR / "pipeline.log")
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    return logger


def ensure_dirs() -> None:
    for d in (C.RESULTS_DIR, C.FIGURES_DIR, C.LOGS_DIR, C.CACHE_DIR):
        d.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=_json_default))


def read_json(path: Path) -> Any:
    return json.loads(path.read_text())


def _json_default(o: Any) -> Any:
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, Path):
        return str(o)
    raise TypeError(type(o))


def skipped_log_path() -> Path:
    return C.LOGS_DIR / "skipped.json"


def load_skipped() -> list[dict]:
    p = skipped_log_path()
    if p.exists():
        return read_json(p)
    return []


def log_skip(record: dict) -> None:
    """Append a skip record. Never silent."""
    rows = load_skipped()
    rows.append(record)
    write_json(skipped_log_path(), rows)


def reset_skipped() -> None:
    write_json(skipped_log_path(), [])
