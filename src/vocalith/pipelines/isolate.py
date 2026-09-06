"""Feature 3: voice isolation via Demucs (htdemucs, two-stem mode).

API verified working on Kaggle P100, 2026-09-04 spike run (see kaggle/results/).
Demucs is invoked as a subprocess (its own CLI) rather than imported, matching how
the spike proved it out -- keeps its dependency surface isolated from the rest of
the app's process.
"""
from __future__ import annotations

import glob
import subprocess
import sys
from pathlib import Path
from typing import Callable, Optional

from .. import models, paths
from ..device import pick_device

ProgressCB = Optional[Callable[[float, str], None]]


def isolate(
    input_path: str | Path,
    mode: str = "vocals",
    device: str | None = None,
    progress_cb: ProgressCB = None,
    out_dir: str | Path | None = None,
) -> dict[str, Path]:
    """mode='vocals' -> {'vocals': ..., 'accompaniment': ...} (fast, two-stem).
    mode='all' -> {'vocals','drums','bass','other': ...} (four-stem, slower).
    """
    device = device or pick_device()
    models.ensure("demucs")
    if progress_cb:
        progress_cb(0.05, "Loading separation model (first run downloads ~320 MB)…")

    out_dir = Path(out_dir) if out_dir else paths.outputs_dir() / "demucs"
    out_dir.mkdir(parents=True, exist_ok=True)

    cmd = [sys.executable, "-m", "demucs", "-n", "htdemucs", "-d", device, "-o", str(out_dir)]
    if mode == "vocals":
        cmd += ["--two-stems=vocals"]
    cmd += [str(input_path)]

    if progress_cb:
        progress_cb(0.2, "Separating audio…")
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        # Demucs' progress bars alone can run past 2000 chars, burying the actual error
        # under download-progress noise -- found for real debugging a run that looked
        # broken but was just truncated before the real traceback. Full output goes to
        # a log file; only a short, actually-useful tail is shown inline.
        log_path = paths.logs_dir() / "demucs_error.log"
        log_path.write_text(f"STDOUT:\n{r.stdout}\n\nSTDERR:\n{r.stderr}", encoding="utf-8")
        raise RuntimeError(
            f"Voice separation failed:\n{r.stderr[-500:]}\n\nFull details: {log_path}"
        )

    stem_dir_matches = glob.glob(str(out_dir / "htdemucs" / "*"))
    if not stem_dir_matches:
        raise RuntimeError("Demucs produced no output stems.")
    stem_dir = Path(stem_dir_matches[-1])

    result: dict[str, Path] = {}
    if mode == "vocals":
        result["vocals"] = stem_dir / "vocals.wav"
        result["accompaniment"] = stem_dir / "no_vocals.wav"
    else:
        for stem in ("vocals", "drums", "bass", "other"):
            p = stem_dir / f"{stem}.wav"
            if p.exists():
                result[stem] = p

    if progress_cb:
        progress_cb(1.0, "Done")
    return result
