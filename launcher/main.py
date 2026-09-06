"""Entrypoint for the packaged app. The only thing a non-technical user's double-click runs.

Never shows a terminal in the packaged build (the OS-specific shim in windows/macos/linux
hides the console); this module itself stays console-safe so it also runs fine from source.
"""
from __future__ import annotations

import socket
import sys
import threading
import time
import traceback
import webbrowser

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent / "src"))

from vocalith import paths  # noqa: E402
from vocalith.device import describe_device  # noqa: E402


def _free_port(start: int = 7860) -> int:
    port = start
    while port < start + 20:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
        port += 1
    return start


def _maybe_install_cuda_torch() -> None:
    """First-run only: if an NVIDIA GPU is present but torch is CPU-only, offer the
    CUDA wheels. Keeps the base bundle small (~200MB CPU torch) for the ~60% of users
    without an NVIDIA GPU, per IMPLEMENTATION_PLAN.md §7.2."""
    import subprocess
    marker = paths.cache_dir() / ".cuda_torch_checked"
    if marker.exists():
        return
    marker.write_text("checked")
    try:
        subprocess.run(["nvidia-smi"], capture_output=True, check=True, timeout=5)
    except Exception:
        return  # no NVIDIA GPU, or driver not installed -- stay on CPU torch silently
    import torch
    if torch.cuda.is_available():
        return  # already CUDA-enabled build
    print("NVIDIA GPU detected. Installing CUDA-accelerated PyTorch for faster generation…")
    r = subprocess.run([
        sys.executable, "-m", "pip", "install", "-q",
        "torch==2.6.0", "torchvision==0.21.0", "torchaudio==2.6.0",
        "--index-url", "https://download.pytorch.org/whl/cu124",
    ], capture_output=True, text=True)
    if r.returncode != 0:
        # Not fatal -- CPU torch (already installed) still works, just slower.
        print("CUDA PyTorch install failed, continuing on CPU torch. Details:")
        print(r.stderr[-1500:])


def main():
    print("Starting Vocalith…")
    log_path = paths.logs_dir() / "launcher.log"
    try:
        _maybe_install_cuda_torch()
        info = describe_device()
        print(f"Device: {info['name']} ({'GPU' if info['is_gpu'] else 'CPU mode'})")

        from vocalith.ui.app import launch
        port = _free_port()
        url = f"http://127.0.0.1:{port}"

        def _open_when_ready():
            import urllib.request
            for _ in range(60):
                try:
                    urllib.request.urlopen(url, timeout=1)
                    webbrowser.open(url)
                    return
                except Exception:
                    time.sleep(0.5)
        threading.Thread(target=_open_when_ready, daemon=True).start()

        def _warm_up_tts():
            # Text-to-Speech is the smallest model (~350MB) and the feature most people
            # try first -- loading it in the background while the UI is still rendering
            # means the first real click feels instant instead of paying the "Loading
            # voice model…" cost live. Deliberately NOT warming Chatterbox/Demucs/Whisper
            # too: that would slow launch and hold multiple heavy models in RAM at idle,
            # working against the memory-eviction fix (models.evict_others) elsewhere.
            try:
                from vocalith.pipelines import tts
                tts._get_pipeline("a")
            except Exception:
                pass  # best-effort only -- a real click will just load it then instead
        threading.Thread(target=_warm_up_tts, daemon=True).start()

        launch(server_port=port)
    except Exception:
        tb = traceback.format_exc()
        log_path.write_text(tb)
        print(f"Vocalith failed to start. Details written to: {log_path}")
        print(tb)
        input("Press Enter to close…")
        sys.exit(1)


if __name__ == "__main__":
    main()
