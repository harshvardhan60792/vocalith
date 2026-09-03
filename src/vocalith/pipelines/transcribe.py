"""Whisper transcription wrapper (MIT) -- the dubbing backbone.

API verified working on Kaggle P100, 2026-09-04 spike run (see kaggle/results/).
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional, TypedDict

from .. import models
from ..device import pick_device

ProgressCB = Optional[Callable[[float, str], None]]


class Segment(TypedDict):
    start: float
    end: float
    text: str


_model_cache: dict[str, object] = {}


def _get_model(name: str, device: str):
    key = f"{name}:{device}"
    if key not in _model_cache:
        models.ensure("whisper")
        import whisper

        from .. import paths
        _model_cache[key] = whisper.load_model(
            name, device=device, download_root=str(paths.models_dir() / "whisper")
        )
    return _model_cache[key]


def transcribe(
    audio_path: str | Path,
    model_name: str = "base",
    device: str | None = None,
    progress_cb: ProgressCB = None,
) -> list[Segment]:
    device = device or pick_device()
    if progress_cb:
        progress_cb(0.1, "Loading Whisper…")
    model = _get_model(model_name, device)
    if progress_cb:
        progress_cb(0.3, "Transcribing…")
    result = model.transcribe(str(audio_path), word_timestamps=True)
    segments: list[Segment] = [
        {"start": s["start"], "end": s["end"], "text": s["text"].strip()}
        for s in result["segments"]
    ]
    if progress_cb:
        progress_cb(1.0, "Done")
    return segments
