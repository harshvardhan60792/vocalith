"""Translation for the dubbing pipeline.

License note (see docs/LICENSES.md): NLLB-200 is CC-BY-NC and is NOT used here.
Primary: Helsinki-NLP Opus-MT (Apache-2.0 / CC-BY-4.0, per-pair, ~300MB, best quality).
Fallback: M2M100-418M (MIT, one model covers all pairs, lower quality) when no
Opus-MT checkpoint exists for the requested language pair.

Opus-MT API verified against the exact call shape (transformers `pipeline("translation")`)
used in the Kaggle dub-chain spike, 2026-09-04.
"""
from __future__ import annotations
from typing import Callable, Optional

from ..device import pick_device

ProgressCB = Optional[Callable[[float, str], None]]

_translator_cache: dict[str, object] = {}


def _opus_mt_id(src: str, tgt: str) -> str:
    return f"Helsinki-NLP/opus-mt-{src}-{tgt}"


def _load_translator(src: str, tgt: str, device: str):
    key = f"{src}-{tgt}:{device}"
    if key in _translator_cache:
        return _translator_cache[key]

    from transformers import pipeline as hf_pipeline
    from huggingface_hub.utils import HfHubHTTPError

    device_idx = 0 if device == "cuda" else -1
    # transformers requires the explicit "translation_XX_to_YY" task format -- a bare
    # "translation" raises KeyError (confirmed on the exact transformers version pulled
    # by this project's pins, see kaggle/results/README.md's dub-chain spike).
    task = f"translation_{src}_to_{tgt}"
    try:
        translator = hf_pipeline(task, model=_opus_mt_id(src, tgt), device=device_idx)
    except (HfHubHTTPError, OSError, KeyError):
        # no Opus-MT checkpoint for this pair -- fall back to M2M100 (MIT, all pairs)
        translator = hf_pipeline(
            task, model="facebook/m2m100_418M", device=device_idx,
            src_lang=src, tgt_lang=tgt,
        )
    _translator_cache[key] = translator
    return translator


def translate_text(text: str, src: str, tgt: str, device: str | None = None) -> str:
    device = device or pick_device()
    translator = _load_translator(src, tgt, device)
    out = translator(text)[0]
    return out.get("translation_text") or out.get("generated_text", "")


def translate_segments(segments: list[dict], src: str, tgt: str,
                        device: str | None = None, progress_cb: ProgressCB = None) -> list[dict]:
    device = device or pick_device()
    if progress_cb:
        progress_cb(0.05, "Loading translation model…")
    translator = _load_translator(src, tgt, device)
    out = []
    for i, seg in enumerate(segments):
        translated = translator(seg["text"])[0]
        text = translated.get("translation_text") or translated.get("generated_text", "")
        out.append({**seg, "translated": text})
        if progress_cb:
            progress_cb(min(0.95, (i + 1) / max(len(segments), 1)), f"Translating segment {i+1}/{len(segments)}…")
    if progress_cb:
        progress_cb(1.0, "Done")
    return out
