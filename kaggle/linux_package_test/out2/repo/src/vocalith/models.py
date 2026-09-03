"""Lazy model download-with-progress layer.

Nothing downloads at install time or app launch. A model downloads the first time a
pipeline that needs it actually runs, with progress wired to the UI so a multi-minute
download never looks like a hung app.
"""
from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from . import paths

ProgressCB = Optional[Callable[[float, str], None]]  # (fraction 0..1, status text)


@dataclass
class ModelSpec:
    key: str
    kind: str  # "hf_repo" | "whisper" | "torch_hub_cache"
    repo_id: str | None = None       # for hf_repo
    whisper_name: str | None = None  # for whisper ("base", "small", ...)
    size_mb: int = 0
    required_for: list[str] = field(default_factory=list)


MODELS: dict[str, ModelSpec] = {
    "kokoro": ModelSpec(
        key="kokoro", kind="hf_repo", repo_id="hexgrad/Kokoro-82M",
        size_mb=350, required_for=["tts", "dub"],
    ),
    "chatterbox": ModelSpec(
        key="chatterbox", kind="hf_repo", repo_id="ResembleAI/chatterbox",
        size_mb=2200, required_for=["clone", "dub"],
    ),
    "demucs": ModelSpec(
        key="demucs", kind="torch_hub_cache", repo_id=None,
        size_mb=320, required_for=["isolate", "dub"],
    ),
    "whisper": ModelSpec(
        key="whisper", kind="whisper", whisper_name="base",
        size_mb=145, required_for=["dub"],
    ),
    "opus_mt": ModelSpec(
        key="opus_mt", kind="hf_repo", repo_id="Helsinki-NLP/opus-mt-{src}-{tgt}",
        size_mb=300, required_for=["dub"],
    ),
}


def _marker_path(key: str) -> Path:
    return paths.models_dir() / f".{key}.done"


def is_downloaded(model_key: str) -> bool:
    return _marker_path(model_key).exists()


def total_download_size(feature: str) -> int:
    return sum(m.size_mb for m in MODELS.values() if feature in m.required_for)


def ensure(model_key: str, progress_cb: ProgressCB = None, lang_pair: tuple[str, str] | None = None) -> Path:
    """Download (if needed) and return the local path/cache location for a model.

    Idempotent: safe to call on every pipeline invocation. huggingface_hub's own
    resume support means a partial download from a killed app picks back up.
    """
    paths.configure_hf_home()
    spec = MODELS[model_key]
    marker = _marker_path(model_key)
    if marker.exists():
        if progress_cb:
            progress_cb(1.0, f"{model_key} ready")
        return _resolve_path(spec, lang_pair)

    if progress_cb:
        progress_cb(0.0, f"Downloading {model_key} (~{spec.size_mb} MB)…")

    if spec.kind == "hf_repo":
        from huggingface_hub import snapshot_download
        repo_id = spec.repo_id
        if lang_pair:
            repo_id = repo_id.format(src=lang_pair[0], tgt=lang_pair[1])
        local_dir = paths.models_dir() / model_key / repo_id.replace("/", "__")
        snapshot_download(repo_id=repo_id, local_dir=str(local_dir))
        if progress_cb:
            progress_cb(1.0, f"{model_key} ready")

    elif spec.kind == "whisper":
        import whisper
        # openai-whisper caches under ~/.cache/whisper by default; redirect into our dir.
        download_root = paths.models_dir() / "whisper"
        whisper.load_model(spec.whisper_name, download_root=str(download_root))
        if progress_cb:
            progress_cb(1.0, "whisper ready")

    elif spec.kind == "torch_hub_cache":
        # demucs pulls its own pretrained weights via torch.hub on first use; just make
        # sure TORCH_HOME points into our dir so it lands somewhere we control/can clean up.
        os.environ.setdefault("TORCH_HOME", str(paths.models_dir() / "torch"))
        if progress_cb:
            progress_cb(1.0, "demucs cache dir ready (weights fetch on first isolate() call)")

    marker.write_text("ok")
    return _resolve_path(spec, lang_pair)


def _resolve_path(spec: ModelSpec, lang_pair: tuple[str, str] | None) -> Path:
    if spec.kind == "hf_repo":
        repo_id = spec.repo_id.format(src=lang_pair[0], tgt=lang_pair[1]) if lang_pair else spec.repo_id
        return paths.models_dir() / spec.key / repo_id.replace("/", "__")
    if spec.kind == "whisper":
        return paths.models_dir() / "whisper"
    return paths.models_dir() / "torch"


def unload_all() -> None:
    """Free resident GPU model weights. Call when switching tabs under tight VRAM."""
    import gc

    import torch
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


def purge_downloaded(model_key: str) -> None:
    """Delete a model's cached weights. Used by a future 'free up disk space' UI action."""
    spec = MODELS[model_key]
    target = _resolve_path(spec, None) if spec.kind != "hf_repo" else paths.models_dir() / model_key
    if target.exists():
        shutil.rmtree(target, ignore_errors=True)
    _marker_path(model_key).unlink(missing_ok=True)
