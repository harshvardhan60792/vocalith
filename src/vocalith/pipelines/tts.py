"""Feature 1: text-to-speech via Kokoro-82M (Apache-2.0).

API verified working on Kaggle P100, 2026-09-04 spike run (see kaggle/results/).
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

import numpy as np

from .. import models, paths
from ..device import pick_device

ProgressCB = Optional[Callable[[float, str], None]]

# display name -> kokoro voice id. Extend as more voices are validated.
VOICES: dict[str, str] = {
    "Heart (US, female)": "af_heart",
    "Michael (US, male)": "am_michael",
    "Emma (UK, female)": "bf_emma",
}

SAMPLE_RATE = 24000

_pipeline_cache: dict[str, object] = {}

models.register_unloader("tts", _pipeline_cache.clear)


def _get_pipeline(lang_code: str = "a"):
    if lang_code not in _pipeline_cache:
        models.evict_others(keep="tts")
        models.ensure("kokoro")
        from kokoro import KPipeline
        _pipeline_cache[lang_code] = KPipeline(lang_code=lang_code)
    return _pipeline_cache[lang_code]


def synthesize(
    text: str,
    voice: str = "af_heart",
    speed: float = 1.0,
    lang: str = "a",
    device: str | None = None,
    progress_cb: ProgressCB = None,
    out_path: str | Path | None = None,
) -> Path:
    if not text.strip():
        raise ValueError("No text provided.")
    device = device or pick_device()
    if progress_cb:
        progress_cb(0.0, "Loading voice model…")
    pipeline = _get_pipeline(lang)

    chunks = []
    # Kokoro streams per-sentence; concatenating is correct and degrades gracefully
    # on very long inputs (each sentence synthesized independently).
    gen = pipeline(text, voice=voice, speed=speed)
    for i, (_, _, audio) in enumerate(gen):
        chunks.append(audio)
        if progress_cb:
            progress_cb(min(0.9, 0.1 + i * 0.05), "Synthesizing…")

    if not chunks:
        raise RuntimeError("Kokoro produced no audio for this input.")
    full = np.concatenate(chunks)

    out_path = Path(out_path) if out_path else paths.outputs_dir() / "tts_output.wav"
    import soundfile as sf
    sf.write(str(out_path), full, SAMPLE_RATE)
    if progress_cb:
        progress_cb(1.0, "Done")
    return out_path
