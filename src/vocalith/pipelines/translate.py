"""Translation for the dubbing pipeline.

License note (see docs/LICENSES.md): NLLB-200 is CC-BY-NC and is NOT used here.
Primary: Helsinki-NLP Opus-MT (Apache-2.0 / CC-BY-4.0, per-pair, ~300MB, best quality).
Fallback: M2M100-418M (MIT, one model covers all pairs, lower quality) when no
Opus-MT checkpoint exists for the requested language pair.

Uses AutoTokenizer + AutoModelForSeq2SeqLM directly rather than transformers'
`pipeline("translation_XX_to_YY")` wrapper. The wrapper turned out to be a moving
target: transformers 5.2.0 (pulled in by this project's other pins on the Kaggle
dub-chain spike, 2026-09-04) raises `KeyError: 'translation'` because that pipeline
task was removed from its registry -- the wrapper's job is just tokenize -> generate
-> decode, which is stable, documented, low-level API across transformers versions.
See kaggle/results/README.md for the two failed pipeline()-based attempts this replaced.
"""
from __future__ import annotations

from typing import Callable, Optional

from ..device import pick_device

ProgressCB = Optional[Callable[[float, str], None]]

_translator_cache: dict[str, tuple] = {}  # key -> (tokenizer, model, is_m2m100: bool)


def _opus_mt_id(src: str, tgt: str) -> str:
    return f"Helsinki-NLP/opus-mt-{src}-{tgt}"


def _load_translator(src: str, tgt: str, device: str) -> tuple:
    key = f"{src}-{tgt}:{device}"
    if key in _translator_cache:
        return _translator_cache[key]

    from huggingface_hub.utils import HfHubHTTPError
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

    try:
        tokenizer = AutoTokenizer.from_pretrained(_opus_mt_id(src, tgt))
        model = AutoModelForSeq2SeqLM.from_pretrained(_opus_mt_id(src, tgt))
        is_m2m100 = False
    except (HfHubHTTPError, OSError):
        # no Opus-MT checkpoint for this pair -- fall back to M2M100 (MIT, all pairs)
        tokenizer = AutoTokenizer.from_pretrained("facebook/m2m100_418M")
        model = AutoModelForSeq2SeqLM.from_pretrained("facebook/m2m100_418M")
        tokenizer.src_lang = src
        is_m2m100 = True

    model = model.to(device).eval()
    result = (tokenizer, model, is_m2m100)
    _translator_cache[key] = result
    return result


def _generate(texts: list[str], tokenizer, model, tgt: str, is_m2m100: bool, device: str) -> list[str]:
    import torch
    if not texts:
        return []
    inputs = tokenizer(texts, return_tensors="pt", padding=True, truncation=True).to(device)
    gen_kwargs = {}
    if is_m2m100:
        gen_kwargs["forced_bos_token_id"] = tokenizer.get_lang_id(tgt)
    with torch.no_grad():
        out_ids = model.generate(**inputs, **gen_kwargs)
    return tokenizer.batch_decode(out_ids, skip_special_tokens=True)


def translate_text(text: str, src: str, tgt: str, device: str | None = None) -> str:
    device = device or pick_device()
    tokenizer, model, is_m2m100 = _load_translator(src, tgt, device)
    return _generate([text], tokenizer, model, tgt, is_m2m100, device)[0]


def translate_segments(segments: list[dict], src: str, tgt: str,
                        device: str | None = None, progress_cb: ProgressCB = None) -> list[dict]:
    device = device or pick_device()
    if progress_cb:
        progress_cb(0.05, "Loading translation model…")
    tokenizer, model, is_m2m100 = _load_translator(src, tgt, device)

    if progress_cb:
        progress_cb(0.2, f"Translating {len(segments)} segment(s)…")
    texts = [seg["text"] for seg in segments]
    translated = _generate(texts, tokenizer, model, tgt, is_m2m100, device)

    out = [{**seg, "translated": t} for seg, t in zip(segments, translated)]
    if progress_cb:
        progress_cb(1.0, "Done")
    return out
