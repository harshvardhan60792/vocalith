"""ffmpeg-backed audio/video helpers. Resolves a bundled ffmpeg binary first, falls
back to system PATH -- never assume the user has ffmpeg installed (most don't)."""
from __future__ import annotations
import os
import shutil
import subprocess
from pathlib import Path

import numpy as np
import soundfile as sf


def _ffmpeg_bin() -> str:
    """Prefer a bundled ffmpeg (set by the launcher via VOCALITH_FFMPEG) over PATH."""
    bundled = os.environ.get("VOCALITH_FFMPEG")
    if bundled and Path(bundled).exists():
        return bundled
    found = shutil.which("ffmpeg")
    if found:
        return found
    raise RuntimeError(
        "ffmpeg not found. This should never happen in the packaged app (ffmpeg is "
        "bundled) -- if you're running from source, install ffmpeg or set VOCALITH_FFMPEG."
    )


def _run(args: list[str]) -> None:
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {' '.join(args)}\n{r.stderr[-2000:]}")


def load(path: str | Path, sr: int | None = None) -> tuple[np.ndarray, int]:
    audio, file_sr = sf.read(str(path), always_2d=False)
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    if sr and sr != file_sr:
        import librosa
        audio = librosa.resample(audio.astype(np.float32), orig_sr=file_sr, target_sr=sr)
        file_sr = sr
    return audio.astype(np.float32), file_sr


def save(path: str | Path, audio: np.ndarray, sr: int) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(path), audio, sr)


def extract_audio(video_path: str | Path, out_path: str | Path, sr: int = 24000) -> Path:
    ffmpeg = _ffmpeg_bin()
    out_path = Path(out_path)
    _run([ffmpeg, "-y", "-i", str(video_path), "-vn", "-acodec", "pcm_s16le",
          "-ar", str(sr), "-ac", "1", str(out_path)])
    return out_path


def mux_audio(video_path: str | Path, audio_path: str | Path, out_path: str | Path) -> Path:
    """Replace a video's audio track with a new one; the video stream is copied untouched."""
    ffmpeg = _ffmpeg_bin()
    out_path = Path(out_path)
    _run([ffmpeg, "-y", "-i", str(video_path), "-i", str(audio_path),
          "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac",
          "-shortest", str(out_path)])
    return out_path


def duration(path: str | Path) -> float:
    ffmpeg = _ffmpeg_bin()
    ffprobe = ffmpeg.replace("ffmpeg", "ffprobe")
    if Path(ffprobe).exists() or shutil.which("ffprobe"):
        r = subprocess.run(
            [ffprobe if shutil.which("ffprobe") else ffprobe, "-v", "error",
             "-show_entries", "format=duration", "-of",
             "default=noprint_wrappers=1:nokey=1", str(path)],
            capture_output=True, text=True,
        )
        try:
            return float(r.stdout.strip())
        except ValueError:
            pass
    audio, sr = load(path)
    return len(audio) / sr


def time_stretch(audio: np.ndarray, sr: int, factor: float) -> np.ndarray:
    """Pitch-preserving time-stretch. factor > 1 speeds up (shortens); < 1 slows down.

    Clamped to [0.8, 1.25] by callers (see pipelines/dub.py) -- outside that range a
    phase vocoder audibly warbles on speech.
    """
    import librosa
    if abs(factor - 1.0) < 0.02:
        return audio
    return librosa.effects.time_stretch(audio.astype(np.float32), rate=factor)
