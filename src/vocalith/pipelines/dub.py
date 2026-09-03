"""Feature 4: dubbing -- translate and re-voice a video/audio clip, timed to the original.

Algorithm (see IMPLEMENTATION_PLAN.md §6.4 for the full rationale):
  1. extract audio (if input is video)
  2. Demucs two-stem split -> vocals (speech) + no_vocals (music/ambience bed)
  3. Whisper transcribe vocals with segment timestamps
  4. translate each segment
  5. re-voice each segment (cloned from the original vocals, or a preset Kokoro voice)
  6. pitch-preserving time-stretch each segment to fit its ORIGINAL slot, clamped to
     [0.8, 1.25]x -- outside that range a phase vocoder audibly warbles on speech
  7. place each segment on a silent canvas at its original start time (never
     concatenate end-to-end -- that accumulates drift and desyncs by minute two)
  8. remix with the original background bed, mux back into video if applicable
  9. also emit a .srt of the translated segments

Logic verified end-to-end on Kaggle P100 against a real synthesized video,
2026-09-04 (kaggle/dub_test/ -> kaggle/results/phase0_dub_spike/).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

import numpy as np

from .. import audio as audio_mod
from .. import paths
from ..device import pick_device
from . import isolate as isolate_mod
from . import transcribe as transcribe_mod
from . import translate as translate_mod

ProgressCB = Optional[Callable[[float, str], None]]

BED_GAIN_DEFAULT = 0.8
STRETCH_MIN = 0.8
STRETCH_MAX = 1.25
REFERENCE_CLIP_SECONDS = 8.0

VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".webm", ".avi"}


@dataclass
class DubResult:
    audio_path: Path
    video_path: Path | None
    srt_path: Path
    warnings: list[str] = field(default_factory=list)


def _is_video(path: Path) -> bool:
    return path.suffix.lower() in VIDEO_EXTS


def _srt_timestamp(t: float) -> str:
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h):02d}:{int(m):02d}:{s:06.3f}".replace(".", ",")


def _write_srt(segments: list[dict], out_path: Path) -> None:
    lines = []
    for i, seg in enumerate(segments, 1):
        text = seg.get("translated") or seg["text"]
        lines.append(f"{i}\n{_srt_timestamp(seg['start'])} --> {_srt_timestamp(seg['end'])}\n{text}\n")
    out_path.write_text("\n".join(lines), encoding="utf-8")


def dub(
    input_path: str | Path,
    target_lang: str,
    source_lang: str = "en",
    voice_mode: str = "clone",          # "clone" | "preset"
    preset_voice: str | None = None,     # kokoro voice id, required if voice_mode="preset"
    bed_gain: float = BED_GAIN_DEFAULT,
    device: str | None = None,
    progress_cb: ProgressCB = None,
    out_dir: str | Path | None = None,
) -> DubResult:
    input_path = Path(input_path)
    device = device or pick_device()
    out_dir = Path(out_dir) if out_dir else paths.outputs_dir() / "dub"
    out_dir.mkdir(parents=True, exist_ok=True)
    warnings: list[str] = []

    is_video = _is_video(input_path)

    # 1. extract audio
    if progress_cb:
        progress_cb(0.02, "Extracting audio…")
    src_audio = out_dir / "src_audio.wav"
    if is_video:
        audio_mod.extract_audio(input_path, src_audio)
    else:
        src_audio = input_path

    # 2. demucs split
    if progress_cb:
        progress_cb(0.08, "Separating voice from background…")
    stems = isolate_mod.isolate(src_audio, mode="vocals", device=device, out_dir=out_dir / "demucs")
    vocals_path, bed_path = stems["vocals"], stems["accompaniment"]

    # 3. transcribe
    if progress_cb:
        progress_cb(0.2, "Transcribing…")
    segments = transcribe_mod.transcribe(vocals_path, device=device)
    if not segments:
        raise RuntimeError("No speech detected in this clip.")

    # 4. translate
    if progress_cb:
        progress_cb(0.35, "Translating…")
    segments = translate_mod.translate_segments(
        segments, src=source_lang, tgt=target_lang, device=device,
        progress_cb=lambda f, s: progress_cb and progress_cb(0.35 + f * 0.15, s),
    )

    # 5. re-voice each segment
    if progress_cb:
        progress_cb(0.5, "Re-voicing…")
    generated = _revoice_segments(
        segments, vocals_path, voice_mode, preset_voice, device,
        progress_cb=lambda f, s: progress_cb and progress_cb(0.5 + f * 0.3, s),
    )

    # 6-7. time-stretch + place on original timeline
    if progress_cb:
        progress_cb(0.82, "Aligning timing…")
    dubbed_speech, sr, timing_warnings = _align_to_timeline(generated, bed_path)
    warnings.extend(timing_warnings)

    # 8. remix + mux
    if progress_cb:
        progress_cb(0.9, "Mixing…")
    bed, bed_sr = audio_mod.load(bed_path, sr=sr)
    n = min(len(dubbed_speech), len(bed))
    mixed = dubbed_speech[:n] + bed[:n] * bed_gain
    peak = float(np.abs(mixed).max()) if len(mixed) else 0.0
    if peak > 1.0:
        mixed = mixed / peak

    final_audio = out_dir / "final_audio.wav"
    audio_mod.save(final_audio, mixed, sr)

    final_video = None
    if is_video:
        final_video = out_dir / "dubbed_video.mp4"
        audio_mod.mux_audio(input_path, final_audio, final_video)

    srt_path = out_dir / "dubbed.srt"
    _write_srt(segments, srt_path)

    if progress_cb:
        progress_cb(1.0, "Done")

    return DubResult(audio_path=final_audio, video_path=final_video, srt_path=srt_path, warnings=warnings)


def _revoice_segments(segments, vocals_path, voice_mode, preset_voice, device, progress_cb: ProgressCB):
    from . import clone as clone_mod
    from . import tts as tts_mod

    generated = []
    ref_clip = None
    if voice_mode == "clone":
        ref, sr = audio_mod.load(vocals_path)
        clip_len = min(len(ref), int(sr * REFERENCE_CLIP_SECONDS))
        ref_clip = Path(vocals_path).parent / "clone_ref.wav"
        audio_mod.save(ref_clip, ref[:clip_len], sr)

    for i, seg in enumerate(segments):
        text = seg.get("translated") or seg["text"]
        if not text.strip():
            continue
        seg_path = Path(vocals_path).parent / f"seg_{i:03d}.wav"
        if voice_mode == "clone":
            clone_mod.clone(text, ref_clip, denoise_reference=False, device=device, out_path=seg_path)
            sr = None
        else:
            if not preset_voice:
                raise ValueError("preset_voice is required when voice_mode='preset'.")
            tts_mod.synthesize(text, voice=preset_voice, device=device, out_path=seg_path)
            sr = tts_mod.SAMPLE_RATE
        generated.append({"start": seg["start"], "end": seg["end"], "path": seg_path})
        if progress_cb:
            progress_cb((i + 1) / max(len(segments), 1), f"Re-voicing segment {i+1}/{len(segments)}…")
    return generated


def _align_to_timeline(generated: list[dict], bed_path: Path) -> tuple[np.ndarray, int, list[str]]:
    bed, sr = audio_mod.load(bed_path)
    canvas = np.zeros(len(bed) + sr, dtype=np.float32)  # +1s safety pad
    warnings = []

    for g in generated:
        y, y_sr = audio_mod.load(g["path"], sr=sr)
        target_dur = g["end"] - g["start"]
        actual_dur = len(y) / sr
        factor = actual_dur / max(target_dur, 0.05)
        factor_clamped = min(max(factor, STRETCH_MIN), STRETCH_MAX)
        if abs(factor_clamped - factor) > 0.01:
            warnings.append(
                f"Segment at {g['start']:.1f}s needed {factor:.2f}x stretch, "
                f"clamped to {factor_clamped:.2f}x (translation was too long/short to fit)."
            )
        y = audio_mod.time_stretch(y, sr, factor_clamped)
        start = int(g["start"] * sr)
        end = min(start + len(y), len(canvas))
        canvas[start:end] += y[: end - start]

    return canvas[: len(bed)], sr, warnings
