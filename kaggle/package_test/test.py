"""
Verify the REAL, shipped src/vocalith/ package -- not a mirrored spike script --
actually works end to end on GPU. Closes the gap flagged after the Phase 0 spike:
dub.py's logic was proven via kaggle/dub_test/dub_test.py, but nobody had run the
actual importable package itself. This does.

Tests, in order: device detection -> TTS -> voice cloning -> voice isolation ->
full dubbing (video in, translated+re-voiced video out). Uses the exact installed
package from src/vocalith/, uploaded as a Kaggle dataset (harshu60792/vocalith-package-src).
"""
import glob
import os
import subprocess
import sys
import time
import traceback

OUT = "/kaggle/working"
os.makedirs(OUT, exist_ok=True)

def sh(cmd, check=False):
    print(f"$ {cmd}")
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if r.stdout:
        print(r.stdout[-2000:])
    if r.stderr:
        print(r.stderr[-2000:])
    if check and r.returncode != 0:
        raise RuntimeError(f"command failed rc={r.returncode}: {cmd}")
    return r

def stage(name, fn):
    # NOTE: deliberately no `import torch` or any GPU/VRAM instrumentation in this
    # wrapper. That exact pattern cost 7 failed Kaggle runs earlier this session
    # (kaggle/results/README.md has the story) -- importing torch inside a wrapper
    # that also runs BEFORE setup() reinstalls the pin caches the wrong version in
    # memory for the rest of the process. Keep this wrapper inert.
    print(f"\n===== STAGE: {name} =====")
    t0 = time.time()
    try:
        fn()
        print(f"===== {name} OK ({time.time()-t0:.1f}s) =====")
        return True
    except Exception:
        print(f"===== {name} FAILED ({time.time()-t0:.1f}s) =====")
        traceback.print_exc()
        return False

def setup():
    sh("apt-get update -qq && apt-get install -y -qq espeak-ng ffmpeg > /dev/null")
    sh(f"{sys.executable} -m pip install -q kokoro==0.9.4 misaki[en] soundfile")
    sh(f"{sys.executable} -m pip install -q chatterbox-tts")
    sh(f"{sys.executable} -m pip install -q demucs")
    sh(f"{sys.executable} -m pip install -q openai-whisper")
    sh(f"{sys.executable} -m pip install -q sentencepiece librosa platformdirs huggingface_hub")
    # combined, LAST, one command -- the exact pattern proven to correctly resolve
    # the cu124 build for all three packages together (see kaggle/results/README.md).
    sh(f"{sys.executable} -m pip install -q torch==2.6.0 torchvision==0.21.0 torchaudio==2.6.0")

print("\n===== STAGE: setup =====")
_t0 = time.time()
try:
    setup()
    print(f"===== setup OK ({time.time()-_t0:.1f}s) =====")
except Exception:
    print(f"===== setup FAILED ({time.time()-_t0:.1f}s) =====")
    traceback.print_exc()

# Locate the uploaded package. v1 assumed Kaggle would preserve the "vocalith/" folder
# name in the dataset -- it didn't: `kaggle datasets create -r zip` flattened it, so
# paths.py/device.py/pipelines/ etc. sit directly at the dataset root with no
# "vocalith" wrapper folder at all. Find the root by an unambiguous marker file
# instead of guessing a folder name, then symlink it to a dir literally named
# "vocalith" so `import vocalith` resolves regardless of how the upload was flattened.
_candidates = glob.glob("/kaggle/input/**/paths.py", recursive=True)
if not _candidates:
    sh("find /kaggle/input -maxdepth 6")
    raise RuntimeError("Could not locate the vocalith package under /kaggle/input")
_pkg_root = os.path.dirname(_candidates[0])
_stage = "/kaggle/working/pkg_stage"
os.makedirs(_stage, exist_ok=True)
_link = os.path.join(_stage, "vocalith")
if not os.path.exists(_link):
    os.symlink(_pkg_root, _link)
sys.path.insert(0, _stage)
print(f"Package root found at: {_pkg_root}, symlinked to: {_link}")

import torch  # first import in the process, strictly after setup() finished -- see stage() note
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
print("device:", DEVICE, "|", torch.cuda.get_device_name(0) if DEVICE == "cuda" else "CPU")

from vocalith import paths
from vocalith.device import describe_device
print("describe_device():", describe_device())

RESULTS = {}

# ---------- 1. TTS (real pipelines/tts.py) ----------
def test_tts():
    from vocalith.pipelines import tts as tts_mod
    path = tts_mod.synthesize(
        "Welcome to this short demonstration. Today we are testing the real, "
        "shipped Vocalith package end to end, not a mirrored spike script.",
        voice="af_heart", device=DEVICE,
        out_path=f"{OUT}/tts_out.wav",
    )
    assert path.exists() and path.stat().st_size > 1000, "tts output missing or empty"
    RESULTS["tts_path"] = path
    print("tts output:", path, path.stat().st_size, "bytes")

ok_tts = stage("tts_synthesize", test_tts)

# ---------- 2. Voice cloning (real pipelines/clone.py, incl. Demucs pre-clean) ----------
def test_clone():
    from vocalith.pipelines import clone as clone_mod
    ref = RESULTS.get("tts_path", f"{OUT}/tts_out.wav")
    path = clone_mod.clone(
        "Voice cloning test using the real clone pipeline, including its "
        "denoise-reference-with-Demucs step.",
        reference_wav=ref, denoise_reference=True, device=DEVICE,
        out_path=f"{OUT}/clone_out.wav",
    )
    assert path.exists() and path.stat().st_size > 1000, "clone output missing or empty"
    RESULTS["clone_path"] = path
    print("clone output:", path, path.stat().st_size, "bytes")

ok_clone = stage("clone_with_denoise", test_clone)

# ---------- 3. Voice isolation (real pipelines/isolate.py, subprocess demucs -d flag) ----------
def test_isolate():
    from vocalith.pipelines import isolate as isolate_mod
    from vocalith import audio as audio_mod
    import numpy as np
    src = RESULTS.get("clone_path", f"{OUT}/tts_out.wav")
    y, sr = audio_mod.load(src)
    noisy = y + np.random.RandomState(0).normal(0, 0.05, y.shape).astype(np.float32)
    audio_mod.save(f"{OUT}/noisy_mix.wav", noisy, sr)
    stems = isolate_mod.isolate(f"{OUT}/noisy_mix.wav", mode="vocals", device=DEVICE,
                                 out_dir=f"{OUT}/isolate_out")
    assert stems["vocals"].exists(), "isolate produced no vocals stem"
    RESULTS["vocals_path"] = stems["vocals"]
    print("isolate stems:", stems)

ok_isolate = stage("isolate_real_pipeline", test_isolate)

# ---------- 4. Full dubbing (real pipelines/dub.py, video in -> dubbed video out) ----------
def test_dub():
    from vocalith.pipelines import tts as tts_mod
    from vocalith.pipelines import dub as dub_mod
    from vocalith import audio as audio_mod
    import numpy as np

    # Build a real input video: speech + a tone bed, muxed with ffmpeg (same
    # construction as kaggle/dub_test/dub_test.py's proven build_input()).
    speech_path = tts_mod.synthesize(
        "This is the real dubbing pipeline speaking English before translation.",
        voice="af_heart", device=DEVICE, out_path=f"{OUT}/dub_src_speech.wav",
    )
    speech, sr = audio_mod.load(speech_path)
    t = np.linspace(0, len(speech) / sr, len(speech), endpoint=False)
    bed = 0.05 * np.sin(2 * np.pi * 110 * t)
    audio_mod.save(f"{OUT}/dub_src_audio.wav", speech + bed, sr)
    sh(f"ffmpeg -y -f lavfi -i color=c=navy:s=320x240:d={len(speech)/sr} "
       f"-i {OUT}/dub_src_audio.wav -c:v libx264 -c:a aac -shortest {OUT}/dub_src_video.mp4",
       check=True)

    result = dub_mod.dub(
        f"{OUT}/dub_src_video.mp4", target_lang="es", source_lang="en",
        voice_mode="clone", device=DEVICE, out_dir=f"{OUT}/dub_out",
        progress_cb=lambda f, s: print(f"  [{f*100:.0f}%] {s}"),
    )
    assert result.video_path and result.video_path.exists(), "dub produced no video"
    assert result.srt_path.exists(), "dub produced no srt"
    print("dub result:", result)
    print("SRT contents:\n", result.srt_path.read_text(encoding="utf-8"))
    if result.warnings:
        print("warnings:", result.warnings)

ok_dub = stage("full_dub_pipeline", test_dub)

print("\n\n===== REAL PACKAGE TEST COMPLETE =====")
summary = {"tts": ok_tts, "clone": ok_clone, "isolate": ok_isolate, "dub": ok_dub}
print("SUMMARY:", summary)
import json
with open(f"{OUT}/summary.json", "w") as f:
    json.dump(summary, f, indent=2)
sh(f"find {OUT} -maxdepth 2 -type f")
