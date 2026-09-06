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


def _check_disk_space(spec: ModelSpec) -> None:
    """Fail with a clear, actionable message before downloading, instead of letting
    a too-full drive silently corrupt the download and surface as a confusing crash
    much later (e.g. a torch import error, or a subprocess failing with no useful
    message). Found for real: huggingface_hub only *warns* on low disk space and
    proceeds anyway -- on a drive with less free space than the file being fetched,
    that produces a truncated/corrupt download whose failure shows up somewhere
    completely unrelated downstream, not here where the actual cause is."""
    free_mb = shutil.disk_usage(paths.models_dir()).free / (1024 * 1024)
    # 1.3x headroom: downloads need temp space alongside the final file during
    # extraction/hashing, not just room for the finished artifact.
    needed_mb = spec.size_mb * 1.3
    if free_mb < needed_mb:
        raise RuntimeError(
            f"Not enough disk space to download this feature's model "
            f"(~{spec.size_mb} MB needed, only {free_mb:.0f} MB free on this drive). "
            f"Free up some space and try again."
        )


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

    _check_disk_space(spec)

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


_unload_hooks: dict[str, Callable[[], None]] = {}


def register_unloader(name: str, unload_fn: Callable[[], None]) -> None:
    """Each pipeline module with an in-process model cache (tts, clone, transcribe,
    translate) registers a callback that clears its own cache dict. Lets
    evict_others() actually free memory instead of only running a no-op gc pass."""
    _unload_hooks[name] = unload_fn


def evict_others(keep: str) -> None:
    """Drop every cached model except `keep`'s before loading a new heavy model.

    Real bug this fixes: each pipeline's model cache lives for the process's whole
    lifetime, so using TTS, then Clone, then Dub in one session leaves Kokoro,
    Chatterbox, Whisper, and the translation model all resident in RAM at once.
    On a 16GB machine with normal desktop usage that's enough to trigger a
    MemoryError / OOM kill mid-request -- confirmed for real: a second heavy
    process alongside a live server hit `MemoryError` loading a few-KB JSON file,
    which only happens when available memory is already critically low. Capping
    residency to one feature's model at a time (repeat use of the *same* feature
    stays fast; switching features pays one reload, not a growing pile) is the
    fix that doesn't require touching each pipeline's own logic.
    """
    for name, fn in _unload_hooks.items():
        if name != keep:
            fn()
    unload_all()


def unload_all() -> None:
    """Free resident GPU model weights and run a GC pass. Safe to call any time;
    only actually frees CPU-resident weights for caches cleared via evict_others()
    first, since Python can't reclaim memory still referenced by a live cache dict."""
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
