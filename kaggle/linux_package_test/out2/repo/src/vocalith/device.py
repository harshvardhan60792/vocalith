"""GPU/CPU detection. Every pipeline calls pick_device() instead of hardcoding .cuda()."""
from __future__ import annotations

import torch


def pick_device() -> str:
    """Return 'cuda', 'mps', or 'cpu'. Never raises."""
    try:
        if torch.cuda.is_available():
            return "cuda"
    except Exception:
        pass
    try:
        if torch.backends.mps.is_available():
            return "mps"
    except Exception:
        pass
    return "cpu"


def pick_dtype(device: str):
    """float16 on cuda, float32 elsewhere.

    MPS float16 has known op-coverage gaps in torch <2.4 for some audio ops;
    keep MPS on float32 until that's verified fixed for the pinned torch version.
    """
    if device == "cuda":
        return torch.float16
    return torch.float32


def describe_device() -> dict:
    """Summary for the UI footer / first-run banner."""
    device = pick_device()
    info = {"device": device, "is_gpu": device != "cpu", "name": "CPU", "vram_gb": None}
    if device == "cuda":
        info["name"] = torch.cuda.get_device_name(0)
        props = torch.cuda.get_device_properties(0)
        info["vram_gb"] = round(props.total_memory / 1e9, 1)
    elif device == "mps":
        info["name"] = "Apple GPU (MPS)"
    return info
