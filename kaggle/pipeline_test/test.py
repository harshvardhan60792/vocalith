import os, sys, subprocess, time, traceback

OUT = "/kaggle/working"
os.makedirs(OUT, exist_ok=True)

def sh(cmd):
    print(f"$ {cmd}")
    r = subprocess.run(cmd, shell=True)
    if r.returncode != 0:
        print(f"!! command failed rc={r.returncode}: {cmd}")

def stage(name, fn):
    print(f"\n===== STAGE: {name} =====")
    t0 = time.time()
    try:
        fn()
        print(f"===== {name} OK ({time.time()-t0:.1f}s) =====")
    except Exception:
        print(f"===== {name} FAILED ({time.time()-t0:.1f}s) =====")
        traceback.print_exc()

# ---- setup ----
def setup():
    sh("apt-get update -qq && apt-get install -y -qq espeak-ng ffmpeg > /dev/null")
    sh(f"{sys.executable} -m pip install -q kokoro==0.9.4 misaki[en] soundfile")
    sh(f"{sys.executable} -m pip install -q chatterbox-tts")
    sh(f"{sys.executable} -m pip install -q demucs")
    sh(f"{sys.executable} -m pip install -q openai-whisper")
    # chatterbox pins torch==2.6.0, which orphans Kaggle's torchvision 0.25.0 (wants 2.10.0)
    # and breaks every transformers import. Realign the trio to torch 2.6.0's matching set.
    sh(f"{sys.executable} -m pip install -q torch==2.6.0 torchvision==0.21.0 torchaudio==2.6.0")

stage("setup", setup)

def check_imports():
    import torch, torchvision, torchaudio, transformers
    print("torch", torch.__version__, "| torchvision", torchvision.__version__,
          "| torchaudio", torchaudio.__version__, "| transformers", transformers.__version__)
    from torchvision.ops import nms  # canary: fails loudly if the trio is still mismatched
    print("torchvision ops OK")

stage("import_check", check_imports)

import torch
print("CUDA available:", torch.cuda.is_available())
if torch.cuda.is_available():
    print("GPU:", torch.cuda.get_device_name(0))
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# ---- 1. Kokoro TTS ----
def tts_stage():
    from kokoro import KPipeline
    import soundfile as sf
    pipeline = KPipeline(lang_code="a")
    text = "This is a test of the local, open source text to speech engine running on Kaggle."
    audio_chunks = []
    for _, _, audio in pipeline(text, voice="af_heart"):
        audio_chunks.append(audio)
    import numpy as np
    full = np.concatenate(audio_chunks)
    sf.write(f"{OUT}/tts_out.wav", full, 24000)
    print("wrote tts_out.wav, samples:", full.shape)

stage("kokoro_tts", tts_stage)

def ensure_ref(path, fallback_from=None):
    """Stages must not cascade: if an upstream stage failed, synth a stand-in so the
    downstream model still gets exercised and reports its own real error."""
    import os, numpy as np, soundfile as sf
    if os.path.exists(path):
        return path
    if fallback_from and os.path.exists(fallback_from):
        print(f"!! {path} missing, falling back to {fallback_from}")
        return fallback_from
    print(f"!! {path} missing, synthesizing stand-in tone")
    sr = 24000
    t = np.linspace(0, 8, sr * 8, endpoint=False)
    tone = 0.3 * np.sin(2 * np.pi * 180 * t) * (1 + 0.3 * np.sin(2 * np.pi * 3 * t))
    sf.write(path, tone.astype("float32"), sr)
    return path

# ---- 2. Chatterbox voice cloning ----
def clone_stage():
    import torchaudio as ta
    from chatterbox.tts import ChatterboxTTS
    model = ChatterboxTTS.from_pretrained(device=DEVICE)
    ref_wav = ensure_ref(f"{OUT}/tts_out.wav")  # kokoro output as cloning reference
    text = "Voice cloning test. This sentence should sound like the reference speaker."
    wav = model.generate(text, audio_prompt_path=ref_wav)
    ta.save(f"{OUT}/clone_out.wav", wav, model.sr)
    print("wrote clone_out.wav")

stage("chatterbox_clone", clone_stage)

# ---- 3. Demucs voice isolation ----
def demucs_stage():
    import numpy as np, soundfile as sf
    # synth a noisy clip: cloned speech + white noise, so we can prove separation works
    src = ensure_ref(f"{OUT}/clone_out.wav", fallback_from=f"{OUT}/tts_out.wav")
    speech, sr = sf.read(src)
    if speech.ndim > 1:
        speech = speech.mean(axis=1)
    noise = np.random.normal(0, 0.05, speech.shape)
    mix = speech + noise
    sf.write(f"{OUT}/noisy_mix.wav", mix, sr)
    sh(f"{sys.executable} -m demucs --two-stems=vocals -n htdemucs -o {OUT}/demucs_out {OUT}/noisy_mix.wav")

stage("demucs_isolation", demucs_stage)

# ---- 4. Whisper transcription (dubbing backbone) ----
def whisper_stage():
    import whisper
    model = whisper.load_model("base", device=DEVICE)
    result = model.transcribe(ensure_ref(f"{OUT}/clone_out.wav", fallback_from=f"{OUT}/tts_out.wav"))
    print("Whisper transcript:", result["text"])
    with open(f"{OUT}/transcript.txt", "w") as f:
        f.write(result["text"])

stage("whisper_transcribe", whisper_stage)

print("\n\n===== PIPELINE TEST COMPLETE =====")
sh(f"ls -la {OUT}")
sh(f"find {OUT}/demucs_out -type f 2>/dev/null")
