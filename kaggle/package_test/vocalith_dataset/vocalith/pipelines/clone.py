"""Feature 2: voice cloning via Chatterbox (MIT).

API verified working on Kaggle P100, 2026-09-04 spike run (see kaggle/results/).
Note: Chatterbox watermarks its output by default (Resemble AI's Perth watermarker) --
this is disclosed to the user in the UI and in docs/LICENSES.md, not hidden.
"""
from __future__ import annotations
from pathlib import Path
from typing import Callable, Optional

from .. import models, paths
from ..device import pick_device
from .isolate import isolate

ProgressCB = Optional[Callable[[float, str], None]]

MIN_REFERENCE_SECONDS = 6.0
MAX_USEFUL_REFERENCE_SECONDS = 20.0

_model_cache: dict[str, object] = {}


def _get_model(device: str):
    if device not in _model_cache:
        models.ensure("chatterbox")
        from chatterbox.tts import ChatterboxTTS
        _model_cache[device] = ChatterboxTTS.from_pretrained(device=device)
    return _model_cache[device]


def validate_reference(reference_wav: str | Path) -> None:
    from .. import audio as audio_mod
    dur = audio_mod.duration(reference_wav)
    if dur < MIN_REFERENCE_SECONDS:
        raise ValueError(
            f"Your reference clip is {dur:.1f}s. Please upload at least "
            f"{MIN_REFERENCE_SECONDS:.0f}s of clear, single-speaker audio."
        )


def clone(
    text: str,
    reference_wav: str | Path,
    exaggeration: float = 0.5,
    cfg_weight: float = 0.5,
    denoise_reference: bool = True,
    device: str | None = None,
    progress_cb: ProgressCB = None,
    out_path: str | Path | None = None,
) -> Path:
    if not text.strip():
        raise ValueError("No text provided.")
    validate_reference(reference_wav)
    device = device or pick_device()

    ref = Path(reference_wav)
    if denoise_reference:
        if progress_cb:
            progress_cb(0.05, "Cleaning reference audio…")
        try:
            stems = isolate(ref, mode="vocals", device=device)
            ref = stems["vocals"]
        except Exception:
            # denoising is a quality nicety, not a hard requirement -- fall back to raw ref
            pass

    if progress_cb:
        progress_cb(0.2, "Loading Chatterbox…")
    model = _get_model(device)

    if progress_cb:
        progress_cb(0.4, "Generating…")
    wav = model.generate(
        text, audio_prompt_path=str(ref),
        exaggeration=exaggeration, cfg_weight=cfg_weight,
    )

    out_path = Path(out_path) if out_path else paths.outputs_dir() / "clone_output.wav"
    import torchaudio as ta
    ta.save(str(out_path), wav, model.sr)
    if progress_cb:
        progress_cb(1.0, "Done")
    return out_path
