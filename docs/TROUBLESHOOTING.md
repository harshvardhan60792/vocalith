# Troubleshooting

**No GPU detected / "CPU mode" banner on a machine with an NVIDIA GPU**
Vocalith ships CPU-only PyTorch and upgrades to CUDA on first run if it detects
`nvidia-smi`. If that upgrade failed (no internet on first run, corporate proxy,
etc.), delete the marker file in the app's cache dir (see Vocalith's data folder,
`cache/.cuda_torch_checked`) and restart to retry.

**Not enough disk space / C: drive is full**
Models download into your OS's default per-user data folder (`%LOCALAPPDATA%\Vocalith`
on Windows), which usually lives on your C: drive. If that drive is low on space, set
the environment variable `VOCALITH_DATA_DIR` to a folder on a different drive (e.g.
`D:\Vocalith`) before launching, and everything -- models, outputs, cache, logs -- moves
there instead. Voice cloning alone needs ~2.2GB free just for its model.

**Port already in use**
The launcher auto-increments from 7860 up to 7879. If all of those are taken, close
whatever else is using them or restart your machine.

**macOS says the app is damaged / from an unidentified developer**
Builds aren't code-signed (a signing cert costs money; this project is free). Right-click
the app → Open → Open, once. macOS remembers your choice after that.

**Generation is very slow**
Expected on CPU — image/audio generation models are GPU-shaped work. Dubbing a 5-minute
clip on CPU can take 30+ minutes; TTS and short clones are much faster. An NVIDIA GPU
speeds this up roughly 10-20x; Apple Silicon (MPS) is a middle ground.

**Out of memory (CUDA OOM)**
Close other GPU-heavy apps. Vocalith loads models on demand and keeps at most one large
model resident — if you still OOM, your card likely has <6GB VRAM; CPU mode will work
but slowly.

**Dubbing output sounds slightly off-pace from the video**
Some segments may show a "clamped stretch" warning after a run — this means a
translation was too long or short to fit the original timing slot even after
pitch-preserving stretch. It's disclosed, not silently hidden; shorter/simpler source
sentences dub more accurately.

**espeak-ng / Kokoro fails to produce audio**
Kokoro's phonemizer needs espeak-ng. The packaged app bundles it; if you're running
from source and this fails, install espeak-ng for your OS.
