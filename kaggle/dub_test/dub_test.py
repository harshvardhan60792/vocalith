"""
Phase 0.8 spike: prove the full dubbing chain end-to-end on a real (synthesized) video.
video -> extract audio -> demucs split -> whisper word-timestamps -> translate (Opus-MT,
license-clear) -> chatterbox re-voice per segment -> pitch-preserving time-stretch to fit
original segment timing -> place on original timeline -> remix with background bed ->
mux back into video -> also emit an .srt.

This script's logic becomes src/vocalith/pipelines/dub.py almost verbatim once proven.
Every stage is wrapped so one failure doesn't cascade and hide downstream bugs.
"""
import os, sys, subprocess, time, json, traceback

OUT = "/kaggle/working"
os.makedirs(OUT, exist_ok=True)
TIMINGS = {}
VRAM = {}

def sh(cmd, check=False):
    print(f"$ {cmd}")
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if r.stdout: print(r.stdout[-3000:])
    if r.stderr: print(r.stderr[-3000:])
    if check and r.returncode != 0:
        raise RuntimeError(f"command failed rc={r.returncode}: {cmd}")
    return r

def stage(name, fn):
    print(f"\n===== STAGE: {name} =====")
    t0 = time.time()
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.reset_peak_memory_stats()
        fn()
        if torch.cuda.is_available():
            VRAM[name] = round(torch.cuda.max_memory_allocated() / 1e9, 2)
        TIMINGS[name] = round(time.time() - t0, 1)
        print(f"===== {name} OK ({TIMINGS[name]}s, peak VRAM {VRAM.get(name,'n/a')} GB) =====")
    except Exception:
        TIMINGS[name] = round(time.time() - t0, 1)
        print(f"===== {name} FAILED ({TIMINGS[name]}s) =====")
        traceback.print_exc()

def setup():
    sh("apt-get update -qq && apt-get install -y -qq espeak-ng ffmpeg > /dev/null")
    # Exact match to kaggle/pipeline_test/test.py's WORKING sequence (verified passing,
    # see kaggle/results/phase0_spike/) -- deliberately NOT installing librosa or
    # sentencepiece here. Two dub_test attempts that added those two packages before
    # the torch pin both failed with the same torchvision::nms mismatch that this exact
    # combined-install-last pattern fixed for pipeline_test; isolating that variable
    # before guessing further. librosa/sentencepiece install lazily, right before the
    # stages that actually need them, after torch/torchvision are already locked in.
    sh(f"{sys.executable} -m pip install -q kokoro==0.9.4 misaki[en] soundfile")
    sh(f"{sys.executable} -m pip install -q chatterbox-tts")
    sh(f"{sys.executable} -m pip install -q demucs")
    sh(f"{sys.executable} -m pip install -q openai-whisper")
    sh(f"{sys.executable} -m pip install -q torch==2.6.0 torchvision==0.21.0 torchaudio==2.6.0")

stage("setup", setup)

# NOTE on 3 earlier failed attempts (kaggle/results/README.md has the full story):
# adding an extra diagnostic stage here that imported torch *before* this line -- even
# just to log versions -- reproducibly broke the very torchvision::nms registration this
# was trying to verify, while a check in a brand-new subprocess always passed. Root cause
# not fully isolated (looks like a Kaggle-kernel-specific first-import quirk, not a real
# version mismatch -- `pip show` and the subprocess canary both showed correct versions
# every time). Fix: match kaggle/pipeline_test/test.py's exact proven shape -- the very
# first `import torch` in this process happens right here, immediately after the last
# pip install of the trio, with nothing in between. Do not insert anything above this line.
import torch
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
print("device:", DEVICE)

# ---------- 1. Build a synthetic "video" with speech over a music bed ----------
def build_input():
    from kokoro import KPipeline
    import soundfile as sf, numpy as np
    pipeline = KPipeline(lang_code="a")
    text = (
        "Welcome to this short demonstration. "
        "Today we are testing a fully local dubbing pipeline. "
        "It transcribes speech, translates it, and re-voices it in the original speaker's voice. "
        "The timing should match the original as closely as possible."
    )
    chunks = [audio for _, _, audio in pipeline(text, voice="af_heart")]
    speech = np.concatenate(chunks)
    sr = 24000
    t = np.linspace(0, len(speech) / sr, len(speech), endpoint=False)
    bed = 0.06 * np.sin(2 * np.pi * 110 * t) + 0.04 * np.sin(2 * np.pi * 220 * t)
    mix = speech + bed
    sf.write(f"{OUT}/src_audio.wav", mix, sr)
    sh(f"ffmpeg -y -f lavfi -i color=c=navy:s=320x240:d={len(speech)/sr} "
       f"-i {OUT}/src_audio.wav -c:v libx264 -c:a aac -shortest {OUT}/src_video.mp4", check=True)
    print(f"built src_video.mp4, duration {len(speech)/sr:.1f}s")

stage("build_input", build_input)

# ---------- 2. Extract audio from video ----------
def extract_audio():
    sh(f"ffmpeg -y -i {OUT}/src_video.mp4 -vn -acodec pcm_s16le -ar 24000 -ac 1 {OUT}/extracted.wav", check=True)

stage("extract_audio", extract_audio)

# ---------- 3. Demucs: split vocals from bed ----------
def demucs_split():
    sh(f"{sys.executable} -m demucs --two-stems=vocals -n htdemucs -o {OUT}/demucs_out {OUT}/extracted.wav", check=True)
    import glob
    vocals = glob.glob(f"{OUT}/demucs_out/htdemucs/*/vocals.wav")[0]
    bed = glob.glob(f"{OUT}/demucs_out/htdemucs/*/no_vocals.wav")[0]
    sh(f"cp '{vocals}' {OUT}/vocals.wav")
    sh(f"cp '{bed}' {OUT}/bed.wav")

stage("demucs_split", demucs_split)

# ---------- 4. Whisper: transcribe with word/segment timestamps ----------
SEGMENTS = []
def transcribe():
    import whisper
    model = whisper.load_model("base", device=DEVICE)
    result = model.transcribe(f"{OUT}/vocals.wav", word_timestamps=True)
    for seg in result["segments"]:
        SEGMENTS.append({"start": seg["start"], "end": seg["end"], "text": seg["text"].strip()})
    print(json.dumps(SEGMENTS, indent=2))
    with open(f"{OUT}/segments_original.json", "w") as f:
        json.dump(SEGMENTS, f, indent=2)

stage("whisper_transcribe", transcribe)

# ---------- 5. Translate each segment (Opus-MT, Apache-2.0 / CC-BY-4.0) ----------
TRANSLATED = []
def translate():
    sh(f"{sys.executable} -m pip install -q sentencepiece")
    from transformers import pipeline as hf_pipeline
    translator = hf_pipeline("translation", model="Helsinki-NLP/opus-mt-en-es",
                              device=0 if DEVICE == "cuda" else -1)
    for seg in SEGMENTS:
        out = translator(seg["text"])[0]["translation_text"]
        TRANSLATED.append({**seg, "translated": out})
        print(f"[{seg['start']:.1f}-{seg['end']:.1f}] {seg['text']!r} -> {out!r}")
    with open(f"{OUT}/segments_translated.json", "w") as f:
        json.dump(TRANSLATED, f, indent=2)

stage("translate", translate)

# ---------- 6. Chatterbox: re-voice each translated segment, cloned from vocals.wav ----------
GENERATED = []  # list of (start, end, np.array, sr)
def revoice():
    import torchaudio as ta, soundfile as sf, numpy as np
    from chatterbox.tts import ChatterboxTTS
    model = ChatterboxTTS.from_pretrained(device=DEVICE)
    # use a clean early slice of the original voice as the cloning reference
    ref, sr = sf.read(f"{OUT}/vocals.wav")
    ref_slice = ref[: int(sr * min(8, len(ref) / sr))]
    sf.write(f"{OUT}/clone_ref.wav", ref_slice, sr)
    for i, seg in enumerate(TRANSLATED if TRANSLATED else SEGMENTS):
        text = seg.get("translated") or seg["text"]
        if not text.strip():
            continue
        wav = model.generate(text, audio_prompt_path=f"{OUT}/clone_ref.wav")
        path = f"{OUT}/seg_{i:02d}.wav"
        ta.save(path, wav, model.sr)
        GENERATED.append({"start": seg["start"], "end": seg["end"], "path": path, "sr": model.sr})
        print(f"generated seg {i}: {path}")

stage("chatterbox_revoice", revoice)

# ---------- 7. Time-stretch each segment to fit + place on original timeline ----------
def align_and_mix():
    sh(f"{sys.executable} -m pip install -q librosa")
    import soundfile as sf, numpy as np, librosa
    bed, bed_sr = sf.read(f"{OUT}/bed.wav")
    if bed.ndim > 1:
        bed = bed.mean(axis=1)
    total_dur = len(bed) / bed_sr
    canvas = np.zeros(int(total_dur * bed_sr) + bed_sr, dtype=np.float32)  # +1s safety pad

    warnings = []
    for g in GENERATED:
        y, sr = sf.read(g["path"])
        if y.ndim > 1:
            y = y.mean(axis=1)
        if sr != bed_sr:
            y = librosa.resample(y, orig_sr=sr, target_sr=bed_sr)
            sr = bed_sr
        target_dur = g["end"] - g["start"]
        actual_dur = len(y) / sr
        factor = actual_dur / max(target_dur, 0.05)
        factor_clamped = min(max(factor, 0.8), 1.25)
        if abs(factor_clamped - factor) > 0.01:
            warnings.append(f"seg@{g['start']:.1f}s: wanted stretch {factor:.2f}x, clamped to {factor_clamped:.2f}x")
        if abs(factor_clamped - 1.0) > 0.02:
            y = librosa.effects.time_stretch(y.astype(np.float32), rate=factor_clamped)
        start_sample = int(g["start"] * bed_sr)
        end_sample = min(start_sample + len(y), len(canvas))
        canvas[start_sample:end_sample] += y[: end_sample - start_sample]

    canvas = canvas[: len(bed)]
    mixed = canvas + bed.astype(np.float32) * 0.8
    peak = np.abs(mixed).max()
    if peak > 1.0:
        mixed = mixed / peak
    sf.write(f"{OUT}/final_audio.wav", mixed, bed_sr)
    with open(f"{OUT}/timing_warnings.txt", "w") as f:
        f.write("\n".join(warnings) if warnings else "none")
    print("wrote final_audio.wav; timing warnings:", warnings or "none")

stage("align_and_mix", align_and_mix)

# ---------- 8. Mux dubbed audio back into the video; write .srt ----------
def mux_and_srt():
    sh(f"ffmpeg -y -i {OUT}/src_video.mp4 -i {OUT}/final_audio.wav "
       f"-map 0:v -map 1:a -c:v copy -c:a aac -shortest {OUT}/dubbed_video.mp4", check=True)

    def ts(t):
        h, r = divmod(t, 3600); m, s = divmod(r, 60)
        return f"{int(h):02d}:{int(m):02d}:{s:06.3f}".replace(".", ",")

    lines = []
    src = TRANSLATED if TRANSLATED else SEGMENTS
    for i, seg in enumerate(src, 1):
        text = seg.get("translated") or seg["text"]
        lines.append(f"{i}\n{ts(seg['start'])} --> {ts(seg['end'])}\n{text}\n")
    with open(f"{OUT}/dubbed.srt", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("wrote dubbed_video.mp4 and dubbed.srt")

stage("mux_and_srt", mux_and_srt)

print("\n\n===== DUB PIPELINE TEST COMPLETE =====")
print("TIMINGS:", json.dumps(TIMINGS, indent=2))
print("VRAM_GB:", json.dumps(VRAM, indent=2))
with open(f"{OUT}/perf_summary.json", "w") as f:
    json.dump({"timings_sec": TIMINGS, "peak_vram_gb": VRAM, "device": DEVICE}, f, indent=2)
sh(f"ls -la {OUT}")
