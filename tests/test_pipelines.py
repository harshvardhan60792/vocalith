"""CPU-only, model-free smoke tests: the pure logic that must be right regardless of
which model backs each pipeline (timing math, SRT formatting, path handling). Tests
that require actual model weights (Kokoro/Chatterbox/Demucs/Whisper) are proven
against real Kaggle GPU runs instead -- see kaggle/results/ -- rather than run here,
so CI stays fast and doesn't need a GPU.
"""
import numpy as np

from vocalith import audio as audio_mod
from vocalith.pipelines.dub import STRETCH_MAX, _align_to_timeline, _srt_timestamp, _write_srt


def test_srt_timestamp_format():
    assert _srt_timestamp(0.0) == "00:00:00,000"
    assert _srt_timestamp(65.5) == "00:01:05,500"
    assert _srt_timestamp(3661.25) == "01:01:01,250"


def test_write_srt(tmp_path):
    segments = [{"start": 0.0, "end": 1.5, "text": "hello", "translated": "hola"}]
    out = tmp_path / "out.srt"
    _write_srt(segments, out)
    content = out.read_text(encoding="utf-8")
    assert "1\n00:00:00,000 --> 00:00:01,500\nhola" in content


def test_align_to_timeline_places_segments_at_original_start(tmp_path):
    sr = 8000
    bed = np.zeros(sr * 4, dtype=np.float32)
    bed_path = tmp_path / "bed.wav"
    audio_mod.save(bed_path, bed, sr)

    seg_audio = np.ones(sr, dtype=np.float32) * 0.1  # 1s of signal
    seg_path = tmp_path / "seg.wav"
    audio_mod.save(seg_path, seg_audio, sr)

    generated = [{"start": 1.0, "end": 2.0, "path": seg_path}]
    canvas, out_sr, warnings = _align_to_timeline(generated, bed_path)

    assert out_sr == sr
    assert len(canvas) == len(bed)
    # region before 1s should be ~silent, region [1s,2s) should carry the signal
    assert np.abs(canvas[: sr - 100]).max() < 1e-6
    assert np.abs(canvas[sr + 100 : 2 * sr - 100]).mean() > 0.05
    assert warnings == []


def test_align_to_timeline_clamps_extreme_stretch(tmp_path):
    sr = 8000
    bed = np.zeros(sr * 10, dtype=np.float32)
    bed_path = tmp_path / "bed.wav"
    audio_mod.save(bed_path, bed, sr)

    # 5s of generated audio squeezed into a 1s original slot -> factor way outside clamp
    seg_audio = np.ones(sr * 5, dtype=np.float32) * 0.1
    seg_path = tmp_path / "seg.wav"
    audio_mod.save(seg_path, seg_audio, sr)

    generated = [{"start": 0.0, "end": 1.0, "path": seg_path}]
    _, _, warnings = _align_to_timeline(generated, bed_path)
    assert len(warnings) == 1
    assert "clamped" in warnings[0]


def test_time_stretch_identity_for_factor_near_one():
    y = np.random.RandomState(0).randn(4000).astype(np.float32)
    out = audio_mod.time_stretch(y, 8000, 1.005)
    assert np.array_equal(out, y)  # short-circuits, no librosa call, no artifact risk


def test_time_stretch_changes_length_outside_identity_band():
    y = np.random.RandomState(0).randn(8000).astype(np.float32) * 0.1
    out = audio_mod.time_stretch(y, 8000, STRETCH_MAX)
    assert len(out) < len(y)  # sped up -> shorter
