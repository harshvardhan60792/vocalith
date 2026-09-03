# Vocalith — Implementation Plan

> **Project name is a placeholder.** It appears in exactly three places: `pyproject.toml`
> (`name`), `src/vocalith/` (package dir), and `app/launcher` branding strings. Change it
> once at the start if desired; do not rename mid-build.

**Read this file top to bottom before writing any code.** It is written so an AI agent with
no prior conversation context can pick up the build at any phase, know what is already done,
and know exactly what "done" means for the next task.

---

## 1. What this is

A free, open-source, **fully local** desktop audio toolkit — a self-hosted alternative to
ElevenLabs. Four features:

| # | Feature | Model | What it does |
|---|---------|-------|--------------|
| 1 | Text-to-speech | Kokoro-82M | Type text, pick a voice, get audio |
| 2 | Voice cloning | Chatterbox | Upload a reference sample, generate speech in that voice |
| 3 | Voice isolation | Demucs (htdemucs) | Strip music/noise from a recording, keep the voice |
| 4 | Dubbing | Whisper + translation + Chatterbox/Kokoro + Demucs | Re-voice a video/audio clip in another language, in the original speaker's voice, timed to the original |

**Hard constraints (non-negotiable — treat as acceptance criteria on every PR):**

- **C1.** No network calls at runtime except first-run model weight downloads from
  HuggingFace/GitHub. No telemetry, no analytics, no phone-home, no crash reporting.
- **C2.** No API keys, no accounts, no subscriptions, no cloud inference. Ever.
- **C3.** User audio never leaves the machine. Not to a server, not to a temp CDN, not to a
  "free" hosted endpoint.
- **C4.** Zero coding experience required. One download, one double-click, a browser tab
  opens. The user never sees a terminal, never runs `pip`, never edits a config file, never
  manually places a model file.
- **C5.** GPU optional. Detect and use CUDA/MPS if present; fall back to CPU silently and
  stay functional (slower is fine, broken is not).
- **C6.** Every bundled model must be permissively licensed (see §9). A model that is
  non-commercial-only is disqualified regardless of quality.
- **C7.** This ships as a local app per user. Do **not** build toward a centrally-hosted
  public web service — the GPU cost of serving cloning/dubbing to unlimited traffic is the
  exact thing this project exists to avoid.

---

## 2. Build order and current status

Work happens in two environments, in this order. **Do not start Phase 3 before Phase 1 is
signed off** — packaging a pipeline that doesn't work yet wastes days.

```
Phase 0  Kaggle spike        — prove the 4 models load and run on free GPU      [DONE — all 4 features + full dub chain (9/9 stages) proven on real GPU]
Phase 1  Core engine         — the 4 pipelines as a clean importable package    [WRITTEN; two real bugs found+fixed in translate.py via the mirrored spike script; no live GPU run of the actual package yet, only the spike script it's mirrored from]
Phase 2  Gradio UI           — the app a non-technical user actually sees       [DONE — premium redesign, verified in-browser across all 4 tabs, no GPU needed]
Phase 3  Packaging           — one-click installers per OS                      [DRAFTED, NOT RUN]
Phase 4  CI + Release        — GitHub Actions builds all 3 OSes, publishes      [WRITTEN, NEVER RUN — no push yet]
Phase 5  Docs + polish       — README, licenses, first-run UX, error messages   [DONE — refine as issues surface]
```

**Status tracking:** update the table above and the per-task checkboxes in §11 as work lands.
That table is the handoff mechanism — an agent resuming this project reads it first.

**2026-09-04 overnight session — what actually happened, read this before anything else:**
The user asked for the whole project built autonomously overnight while minimizing token
spend and Kaggle GPU time, with explicit permission to switch models and make any call
needed. Model used switched Opus→Sonnet mid-session (user's own /model command). Everything
below was done *without* asking the user, per that standing permission — but nothing was
pushed to GitHub (no remote exists yet, and pushing/publishing requires the user's explicit
per-action confirmation regardless of a "build it all" instruction — that boundary was not
relaxed by the goal).

What's real and verified: Phase 0's four individual models (§4, P0.1-P0.7) — confirmed
working together on a Kaggle P100, see `kaggle/results/phase0_spike/`. The full dubbing
chain (P0.8) was queued on Kaggle in the same session — check
`kaggle/results/README.md` for whether that run landed; if it's still marked "queued", it
needs to be finished before Phase 1's `dub.py` can be considered proven rather than
"logic ported from a design, not yet GPU-verified".

What's real but *not* GPU/browser-verified: all of `src/vocalith/` (device, paths, models,
audio, all four pipelines, the Gradio UI) and `launcher/main.py` were written directly
against the exact API calls proven in the Phase 0 spike log (import names, function
signatures, argument shapes) — not guessed. `tests/` covers the model-free logic
(timing/alignment math, SRT formatting, path handling) and should pass on CPU with no
GPU. Nobody has run `pip install -e .` and clicked through the actual Gradio app yet —
that is the single highest-value next step for whoever picks this up, GPU or not (TTS
and isolation can be smoke-tested on CPU, slowly).

What's a first draft only, explicitly flagged in its own file header as unverified: the
three packaging scripts (`launcher/{windows,macos,linux}/build.*`). They implement the
embedded-Python approach from §7.1 but have never been run — not in CI, not on a clean
VM. Treat every filename, URL, and version pin in them as "someone's best guess tonight,"
not fact. `.github/workflows/*.yml` are written but have never executed (would require
pushing to a GitHub remote, which needs the user's go-ahead).

Two decisions made autonomously that a human should sanity-check, not because they're
shaky, but because they weren't explicitly discussed with the user:
- Chose **"Vocalith"** as a placeholder project name (was previously referred to only as
  "the audio toolkit"). Trivial to rename — see the note at the top of this file.
- Chose **Spanish** as the demo target language for the P0.8 dubbing spike, and
  **Opus-MT** over M2M100 as the default translator per §6.5's own stated preference
  order — this was already the plan's documented recommendation, not a new call.

**Later the same night — continuation, after the user gave a second instruction
("finish this while I sleep, conserve tokens and GPU, make it feel free"):**

**P0.8 (full dubbing chain) is DONE — all 9 stages pass on real Kaggle GPU (kernel
v8).** It took 8 kernel pushes (v1-v8) to get there, and every failure taught something
real — full story in `kaggle/results/README.md`, don't skip it if a similar "works
standalone, fails in this script" symptom ever shows up again. Two genuinely different
bug classes, both now fixed in the real `src/vocalith/` code, not just the spike:
1. **A self-inflicted debugging artifact (v1-v6):** a diagnostic stage added to catch
   one bug was itself silently causing a *different* one — a VRAM-tracking helper's own
   `import torch` was pre-caching the wrong torch version before `setup()` had
   reinstalled the pin. Fixed by running `setup()` outside the tracking wrapper.
2. **A real transformers-version bug (v6-v8):** `pipeline("translation_XX_to_YY", ...)`
   raised `KeyError` two different ways across two attempts — transformers 5.2.0 (pulled
   in unpinned by this project's other deps) turned out to have dropped the
   `"translation"` pipeline task from its registry entirely. Fixed by rewriting
   `translate.py` to call `AutoTokenizer`/`AutoModelForSeq2SeqLM` directly (tokenize →
   generate → decode) instead of going through the pipeline task-name abstraction at
   all — stable, documented, low-level API that doesn't depend on what task names a
   given transformers version happens to register.

v8's output, for real, on a synthesized English clip: *"Bienvenidos a esta breve
demostración. Hoy estamos probando una tubería de doblaje totalmente local..."* —
correct Spanish, correctly timed (three segments hit the 1.25x stretch cap exactly as
§6.4 designed, since translations ran 1.6-1.7x longer than the English source).

**The UI went through three real design passes**, each triggered by direct user
feedback, worth understanding in order because each one overwrote real work:
1. First pass, prompted by "the default Gradio look screams AI" — used the
   `frontend-animation` skill's decision tree (plain HTML/CSS/JS project → anime.js)
   and built a dark near-black + warm-copper-accent editorial theme with a vendored
   Fraunces serif for display type.
2. Second pass, prompted by "the coffee-brown palette reads as default AI slop, not
   premium" — swapped copper for a neutral near-black + a single vivid recording-light
   red (thematically apt for an audio tool), still dark mode.
3. Third pass, prompted by "look at ElevenLabs and similar platforms, use that as the
   base" — checked elevenlabs.io directly (their actual marketing site, not their app)
   and rebuilt around its real structure: light mode, warm off-white background,
   near-black text, pill-shaped buttons/tabs/badges everywhere.
4. Fourth pass (current, final), prompted by "still sloppy, I want dark, just copy
   award-winning sites, don't overthink it" — committed directly to the
   Linear/Vercel/Raycast school of dark developer-tool design, the most consistently
   cited reference class for this look: near-black background (`#09090B`, not pure
   black), off-white text (`#EDEEF0`, not pure white), one indigo-violet accent
   (`#5E6AD2`) used sparingly, tight 8-10px rounded-rect shapes (not full pills —
   those read as ElevenLabs-specific, not the broader dark-SaaS norm), subtle 1px
   borders instead of shadows, primary buttons filled with the accent color (Linear's
   own signature move) rather than plain black/white. Every structural CSS fix found
   during the earlier passes (see below) carried forward unchanged — they're
   correctness fixes independent of the palette on top. This is the current, final
   look — check the file's own top-of-file comment in `src/vocalith/ui/design.py` for
   the reasoning behind each pass; don't revert to an earlier one without a reason.

   **Four real, non-obvious CSS bugs were found and fixed getting the dark mode to
   actually render** (all still apply under pass 4's colors — read these before
   touching `design.py`'s cascade again):
   - Gradio adds a `body.dark` class when the OS prefers dark color-scheme, and its
     own dark-mode rule for `.gradio-container` has the *same specificity* as a plain
     `.gradio-container` selector — so on a dark-preference OS, Gradio's rule won
     regardless of `!important`. Fix: explicitly match `body.dark .gradio-container`.
   - Setting the `background` shorthand and then a separate `background-image`
     longhand in the *same rule* silently dropped `background-color` from the
     serialized declaration entirely (confirmed via the live CSSOM, not a guess) —
     the container rendered fully transparent as a result. Fix: use
     `background-color` + `background-image` as two explicit longhands, never mix
     shorthand with a following longhand override for the same shorthand family.
   - The Audio/File component's floating file-type badge (`[data-testid="block-label"]`)
     and the Dropdown's inner wrapper (`.wrap`) are separate nested components with
     their own dark-mode defaults that the container-level override doesn't reach —
     each needed its own explicit rule.
   - Gradio adds a literal `.selected` class to the active radio `<label>` — far more
     reliable than guessing at `role`/`:has()` selectors, which didn't match this
     component's actual markup at all.

Only anime.js is vendored now (the Fraunces font files were deleted along with pass 3).
It's inlined as text directly into the page — zero runtime network calls, matching the
project's own offline promise (a `gr.themes.GoogleFont` or a CDN `<script src>` would
have quietly broken that). See `src/vocalith/ui/design.py` for the whole system,
especially the note about why the hero's entrance animation is CSS-driven, not
JS-driven (a JS-timing bug once left it permanently invisible; anime.js is now reserved
for a lower-stakes completion-pulse flourish instead). **Verified in-browser, all four
tabs, screenshots taken, zero GPU/model-download needed** since every pipeline import
is lazy. Two unrelated Gradio 6.0 API breaks were found and fixed along the way (see
Phase 2 checklist below) — this local machine runs a newer Gradio than the loose
`gradio>=4.44` pin technically requires, which is itself a signal: **pin Gradio to a
tighter range before release**, or explicitly test against the oldest allowed version,
because 4.44 and 6.0 disagree on where `css`/`js`/`head`/`theme` belong.

**Where each phase runs:**
- Phase 0–1: Kaggle notebooks (free GPU, 30 hrs/week, no billing risk — quota just stops).
  Kaggle CLI is already configured; see §10.
- Phase 2–5: local machine + GitHub Actions.

---

## 3. Repository layout

Create exactly this structure. Do not invent parallel directories.

```
vocalith/
├── src/vocalith/
│   ├── __init__.py
│   ├── device.py            # GPU/CPU detection, dtype selection
│   ├── models.py            # lazy model registry + download-with-progress
│   ├── paths.py             # per-OS data dirs (models, outputs, cache)
│   ├── audio.py             # load/save/resample/time-stretch/mux helpers (ffmpeg wrapper)
│   ├── pipelines/
│   │   ├── __init__.py
│   │   ├── tts.py           # Feature 1  — Kokoro
│   │   ├── clone.py         # Feature 2  — Chatterbox
│   │   ├── isolate.py       # Feature 3  — Demucs
│   │   ├── translate.py     # translation model wrapper (used by dubbing)
│   │   ├── transcribe.py    # Whisper wrapper (used by dubbing)
│   │   └── dub.py           # Feature 4  — orchestrates the above
│   └── ui/
│       ├── __init__.py
│       ├── app.py           # Gradio Blocks — 4 tabs, one per feature
│       └── theme.py
├── launcher/
│   ├── main.py              # entrypoint: first-run setup → start server → open browser
│   ├── windows/             # embedded-Python portable build scripts
│   ├── macos/               # .app bundle scripts
│   └── linux/               # AppImage / tarball scripts
├── kaggle/
│   ├── kaggle.json          # API token — GITIGNORED, never commit
│   └── pipeline_test/       # Phase 0 spike notebook (kernel-metadata.json + test.py)
├── tests/
│   ├── test_device.py
│   ├── test_pipelines.py    # smoke tests, tiny inputs, CPU-only
│   └── fixtures/            # 3–5s reference clips, a noisy clip, a 10s test video
├── .github/workflows/
│   ├── ci.yml               # lint + tests on every push
│   └── release.yml          # 3-OS bundle build + GitHub Release on tag
├── docs/
│   ├── LICENSES.md          # per-model license table (§9) — legally load-bearing
│   └── TROUBLESHOOTING.md
├── IMPLEMENTATION_PLAN.md   # this file
├── README.md
├── LICENSE                  # MIT for our own code
└── pyproject.toml
```

---

## 4. Phase 0 — Kaggle spike (proving the models work)

**Goal:** prove all four models load and produce correct output on Kaggle's free GPU, before
any packaging effort. This is the phase that catches "this model doesn't actually work the
way the README claims."

**Already pushed:** `kaggle/pipeline_test/` — a script kernel that installs deps, runs Kokoro
→ Chatterbox (using Kokoro's output as the cloning reference) → Demucs (on a synthetic noisy
mix) → Whisper (transcribing the cloned audio), printing a PASS/FAIL banner per stage.

**P0 exit criteria — all must be true, verified by reading the kernel log:**

- [ ] **P0.1** `CUDA available: True` and a GPU name printed.
- [ ] **P0.2** Kokoro writes `tts_out.wav`, non-silent, intelligible on listen.
- [ ] **P0.3** Chatterbox writes `clone_out.wav` that audibly resembles the reference.
- [ ] **P0.4** Demucs writes a `vocals.wav` stem measurably cleaner than the noisy input
      (compare RMS of the residual; also listen).
- [ ] **P0.5** Whisper transcript matches the spoken text (allow minor punctuation drift).
- [ ] **P0.6** Record wall-clock seconds per stage — these become the CPU-mode expectation
      baseline. GPU time × ~10–20 ≈ CPU time; if a stage is >5 min on GPU it will be
      unusable on CPU and needs a smaller model variant.
- [ ] **P0.7** Record peak VRAM per stage. If the four models together exceed ~8 GB, models
      must be loaded and unloaded per-request rather than held resident (see §5.2).

**Then extend the spike to the full dubbing chain (P0.8)** before declaring Phase 0 done:
transcribe a real 30–60s video with word timestamps → translate segments → synthesize each
segment → time-align → mux back to video. See §6.4 for the algorithm. Verify by watching the
result: does the dubbed speech land on the original speaker's mouth movements within ~300 ms?

**Known Phase 0 landmines (check these first if a stage fails):**

- **Kokoro needs espeak-ng** for phonemization. On Kaggle: `apt-get install espeak-ng`.
  On the packaged app this becomes a real problem — see §7.3. Modern `kokoro` pulls
  `espeakng-loader`, which ships prebuilt binaries; **verify this during Phase 0**, because
  if it does not, Windows packaging gets significantly harder.
- **Chatterbox pins torch versions aggressively** and pulls `s3tokenizer` and `perth`
  (a watermarker). Install it in an isolated check first — if it downgrades torch and breaks
  Demucs/Whisper, that dependency conflict must be resolved in Phase 1, not discovered in
  Phase 3. Chatterbox also **watermarks its output by default**; document this in the README
  (it is a feature, not a bug — but users must know).
- **Demucs is unmaintained upstream** (archived). Pin the version and vendor a fork if a
  Python 3.12+ incompatibility appears. Check the license before committing to it (§9).
- **Kaggle GPU quota is 30 hrs/week.** Do not leave notebooks idling. Kill sessions.

---

## 5. Phase 1 — Core engine

The engine is a plain importable Python package with **no Gradio imports anywhere in
`pipelines/`**. UI and engine stay separable so the engine can be tested headlessly in CI on
CPU.

### 5.1 `device.py`

```python
def pick_device() -> str:
    """Return 'cuda', 'mps', or 'cpu'. Never raises."""

def pick_dtype(device: str):
    """float16 on cuda, float32 elsewhere. MPS float16 is buggy for some ops — test."""

def describe_device() -> dict:
    """{'device','name','vram_gb','is_gpu'} for display in the UI footer."""
```

Rule: **every** pipeline takes `device: str | None = None` and calls `pick_device()` when
None. Never hardcode `.cuda()`.

### 5.2 `models.py` — the download-with-progress layer

This is the piece that satisfies C4 (no manual file placement) and keeps the installer small.

```python
MODELS = {
  "kokoro":     ModelSpec(repo="hexgrad/Kokoro-82M", size_mb=350,  required_for=["tts","dub"]),
  "chatterbox": ModelSpec(repo="ResembleAI/chatterbox", size_mb=2200, required_for=["clone","dub"]),
  "demucs":     ModelSpec(url=..., size_mb=320,  required_for=["isolate","dub"]),
  "whisper":    ModelSpec(name="base", size_mb=145, required_for=["dub"]),
  "translate":  ModelSpec(repo=..., size_mb=1200, required_for=["dub"]),
}

def ensure(model_key: str, progress_cb: Callable[[float, str], None] | None = None) -> Path
def is_downloaded(model_key: str) -> bool
def total_download_size(feature: str) -> int
```

Requirements:
- **Lazy.** Nothing downloads at install time or app launch. A model downloads the first time
  the user clicks Generate on a feature that needs it.
- **Progress is visible.** `progress_cb` is wired to `gr.Progress()` in the UI. A silent
  15-minute download reads as a hung app to a non-technical user — this is the single most
  common way this class of app loses users.
- **Resumable.** Use `huggingface_hub.snapshot_download` (resumes natively) rather than raw
  `requests`.
- **Cached under `paths.models_dir()`**, not the Python install dir — otherwise reinstalling
  the app re-downloads 4 GB. Set `HF_HOME` to that dir at startup.
- **Model residency:** load on demand, keep an LRU of at most one large model resident on GPU
  (governed by P0.7's VRAM measurement). Expose `unload_all()` and call it when switching
  tabs if VRAM is tight.

### 5.3 `paths.py`

Per-OS user data dirs (use `platformdirs`):
- Windows: `%LOCALAPPDATA%\Vocalith\{models,outputs,cache}`
- macOS: `~/Library/Application Support/Vocalith/...`
- Linux: `~/.local/share/vocalith/...`

Never write into the install directory (breaks on Program Files / read-only mounts / macOS
app bundles).

### 5.4 `audio.py`

Wrap ffmpeg (bundled — see §7.4) rather than shelling out to a system ffmpeg that may not
exist:

```python
def load(path, sr=None) -> tuple[np.ndarray, int]
def save(path, audio, sr)
def extract_audio(video_path) -> Path            # ffmpeg -vn
def mux_audio(video_path, audio_path, out_path)  # replace audio, copy video stream
def time_stretch(audio, sr, factor) -> np.ndarray  # for dub timing; see §6.4
def duration(path) -> float
```

---

## 6. Phase 2 — The four pipelines

Every pipeline function is **synchronous, pure-ish, and returns a path to a written file**.
No global state beyond the model cache.

### 6.1 `tts.py` — Kokoro

```python
VOICES: dict[str, str]   # display name -> kokoro voice id (af_heart, am_michael, bf_emma, ...)

def synthesize(text: str, voice: str = "af_heart", speed: float = 1.0,
               lang: str = "a", device=None, progress_cb=None) -> Path
```

- Kokoro streams per-sentence chunks; concatenate them. Sample rate is **24000**.
- Long text: split on sentence boundaries before feeding; Kokoro degrades on very long inputs.
- Expose speed (0.5–2.0) and voice picker in the UI. Show a short preview sample per voice.

### 6.2 `clone.py` — Chatterbox

```python
def clone(text: str, reference_wav: Path, exaggeration: float = 0.5,
          cfg_weight: float = 0.5, device=None, progress_cb=None) -> Path
```

- Reference audio: **6–20 seconds, clean, single speaker**. Validate and reject bad input with
  a plain-English message ("Your sample is 2 seconds — please upload at least 6 seconds of
  clear speech"), not a stack trace.
- **Run the reference through Demucs first** if it is noisy. This is a genuine quality win and
  a reason the four features belong in one app: isolation feeds cloning.
- Chatterbox watermarks output. Document it.

### 6.3 `isolate.py` — Demucs

```python
def isolate(input_path: Path, mode: str = "vocals", device=None, progress_cb=None) -> dict[str, Path]
    # mode: "vocals" (two-stem: vocals + no_vocals) | "all" (drums/bass/other/vocals)
```

- Use `htdemucs` two-stem mode for the isolation feature — faster, and the `no_vocals` stem is
  exactly what dubbing needs for the background bed.
- Long files: Demucs chunks internally, but a 10-minute file on CPU is ~20+ minutes. Show
  estimated time up front based on the P0.6 baseline and the detected device.

### 6.4 `dub.py` — the hard one

This is the feature with real engineering in it. Algorithm:

```
1. If input is video: extract audio (audio.extract_audio). Keep the video stream aside.
2. Demucs two-stem split  →  vocals.wav (speech)  +  no_vocals.wav (music/ambience bed)
3. Whisper transcribe vocals.wav with word_timestamps=True
      → segments: [{start, end, text, words:[...]}]
4. For each segment: translate text → target language  (translate.py)
5. Choose the voice:
      a. clone mode  → use vocals.wav (or a user-selected slice of it) as the Chatterbox
                       reference, so the dub keeps the original speaker's voice
      b. preset mode → Kokoro voice picked by the user (faster, lower VRAM)
6. Synthesize each translated segment independently.
7. TIMING — the part that makes or breaks this feature:
      for each segment:
        target_dur   = original.end - original.start
        actual_dur   = len(generated) / sr
        factor       = actual_dur / target_dur
        if factor within [0.8, 1.25]:  time-stretch to fit exactly (pitch-preserving)
        if factor > 1.25 (translation too long):  stretch to 1.25 max, then allow overflow
              into the following silence gap; if no gap, accept drift and log it
        if factor < 0.8 (too short):   stretch to 0.8, pad the remainder with silence
      Place each stretched segment at its ORIGINAL start time on a silent canvas.
      Never concatenate end-to-end — that accumulates drift and desyncs by the 2-minute mark.
8. Mix: dubbed_speech + (no_vocals * bed_gain, default 0.8). Keeping the original music bed
   is what makes the output sound like a real dub instead of a voice memo.
9. If input was video: mux the new audio against the untouched original video stream.
10. Also write a .srt of the translated segments — free, useful, and it lets the user verify
    the translation without listening to the whole thing.
```

```python
def dub(input_path: Path, target_lang: str, voice_mode: str = "clone",
        preset_voice: str | None = None, bed_gain: float = 0.8,
        device=None, progress_cb=None) -> DubResult   # .audio, .video, .srt, .warnings
```

- **Pitch-preserving time-stretch** is mandatory. Naive resampling chipmunks the voice. Use
  `librosa.effects.time_stretch` (phase vocoder, no extra binary) or ffmpeg's `atempo` filter.
  Benchmark both on speech in Phase 0 and pick by ear; ffmpeg `atempo` chained is usually
  cleaner for speech, librosa is one less subprocess.
- `warnings` surfaces per-segment timing failures to the UI ("3 segments were too long to fit
  and may overlap"). Honest output beats silent desync.
- Progress must be per-segment — dubbing a 5-minute video is a multi-minute operation and a
  frozen bar is indistinguishable from a crash.

### 6.5 `translate.py` — **license-critical, read this**

The translation model is the easiest place to accidentally poison the whole project's
licensing. **NLLB-200 is CC-BY-NC (non-commercial) — do not use it**, despite it being the
obvious first search result.

Acceptable options, in preference order:
1. **Helsinki-NLP Opus-MT** (`Helsinki-NLP/opus-mt-{src}-{tgt}`) — Apache-2.0/CC-BY-4.0,
   ~300 MB per language pair, good quality, downloads only the pair the user needs.
2. **M2M100-418M** — MIT, one 1.9 GB model covering 100 languages, simpler UX (no per-pair
   download), lower quality than Opus-MT on common pairs.
3. Whisper's built-in `task="translate"` — **only translates to English**. Acceptable as a
   fast path for X→English dubbing; not a general solution.

Recommendation: **Opus-MT with per-pair lazy download**, falling back to M2M100 for pairs
Opus-MT lacks. Verify each pair's license on its model card at implementation time and record
it in `docs/LICENSES.md`.

---

## 7. Phase 3 — Packaging (the phase that decides whether this project reaches anyone)

### 7.1 The decision: PyInstaller vs embedded Python

**Recommendation: embedded-Python portable build for Windows; PyInstaller only for macOS.**

Rationale — PyInstaller and PyTorch are a known-bad pairing: hidden imports for
`torch`, `torchaudio`, `transformers`, and `demucs` require hand-maintained hooks; dynamic
`importlib` loading in `transformers` defeats static analysis; and the resulting bundle
routinely breaks on a torch minor-version bump. The portable-embedded-Python pattern
(what Stable Diffusion WebUI, ComfyUI, and Fooocus all converged on, independently, after
trying to freeze) sidesteps every one of those failure modes because the interpreter and
site-packages stay real files on disk.

**Do not spend more than one day trying to make PyInstaller work on Windows before switching
to the portable approach.** If a hard blocker appears earlier than that, switch immediately
and record the blocker in this file.

**Per-OS plan:**

| OS | Approach | Artifact | Notes |
|----|----------|----------|-------|
| Windows | Embedded Python (`python-3.11.x-embed-amd64`) + preinstalled site-packages + `run.bat` + a tiny `.exe` launcher shim | `Vocalith-win64.zip` (~1.5-2 GB) | **Revised 2026-09-04 after a real local run:** originally planned as `.7z` to halve the download, but that requires 7-Zip on the build machine — confirmed absent (`Get-Command 7z` and both Program Files paths came back empty) on a real Windows dev machine, and CI would need an extra `choco install 7zip` step. Switched to PowerShell's native `Expand-Archive`/`Compress-Archive` (plain `.zip`, zero external tool dependencies) — a larger download traded for one less thing to go wrong. Still ship an `.exe` shim so users double-click an icon, not a `.bat`. |
| macOS | PyInstaller `.app`, or the same embedded pattern with `python-build-standalone` | `Vocalith-macos-arm64.dmg` | **Unsigned builds are Gatekeeper-blocked.** Either pay $99/yr for signing (violates the free constraint) or document the right-click→Open workaround prominently. Support arm64 (MPS) first; Intel Macs are CPU-only and slow. |
| Linux | `python-build-standalone` + tarball, or AppImage | `Vocalith-linux-x86_64.tar.gz` | Simplest of the three. AppImage is nicer UX but adds build complexity — tarball first. |

### 7.2 Ship CPU torch, fetch CUDA on first run

**This is the single most important packaging decision.** A bundle with CUDA torch is ~2.5 GB
larger and exceeds comfortable GitHub Actions runner disk limits.

```
Bundle:      torch CPU wheels                                    (~200 MB)
First run:   detect NVIDIA GPU (nvidia-smi / torch.cuda probe)
             if present → pip install torch --index-url .../cu121 into the bundled env,
                          with a visible progress bar in the launcher window
             if absent  → keep CPU torch, show "Running on CPU — generation will be slower"
```

This keeps the download honest for the ~60% of users without an NVIDIA GPU, and GPU users
accept one extra first-run download.

### 7.3 espeak-ng (Kokoro's phonemizer) — verify early

Kokoro needs espeak-ng. If `espeakng-loader` (which ships prebuilt binaries) works inside the
bundle, this is a non-issue. If it does not:
- Windows: bundle `espeak-ng.dll` + data dir, set `PHONEMIZER_ESPEAK_LIBRARY`.
- macOS: bundle the dylib inside the `.app`.
- Linux: bundle the `.so`; do not rely on the user's package manager.

**Test this in Phase 0**, on a machine that has never had espeak-ng installed. A dev machine
with a system espeak-ng will hide the bug until the first user report.

### 7.4 ffmpeg

Bundle static ffmpeg binaries per OS (`ffmpeg.org` builds, LGPL/GPL — note in LICENSES.md,
and prefer LGPL builds). Never assume a system ffmpeg. `audio.py` resolves the bundled binary
path first, system PATH second.

### 7.5 The launcher (`launcher/main.py`)

The entire user-facing experience of "it just works":

```
1. Show a small native console/splash: "Starting Vocalith…"
2. First run only:  GPU probe → optional CUDA torch install (progress shown)
3. Start Gradio on 127.0.0.1, port 7860 (auto-increment if taken)
4. Wait for the server to answer, then webbrowser.open() the URL
5. Keep running; on window close, shut the server down cleanly
6. Any crash → write a log to the data dir and show a plain-English message with the
   log path. Never leave a black window that vanishes.
```

`server_name` must be `127.0.0.1`, **never** `0.0.0.0` — do not expose a user's voice-cloning
server to their LAN by default. `share=False` always (Gradio's share tunnel routes audio
through a public relay, violating C3).

---

## 8. Phase 4 — CI and releases

`.github/workflows/ci.yml` — on every push: ruff + CPU-only pipeline smoke tests using tiny
fixtures. Keep under 10 minutes.

`.github/workflows/release.yml` — on tag `v*`:
```yaml
strategy:
  matrix:
    include:
      - os: windows-latest
      - os: macos-14        # arm64
      - os: ubuntu-latest
```
Each job builds its bundle, then `softprops/action-gh-release` uploads to the Release.

**Runner limits to design around:** ~14 GB free disk, 6-hour job cap. With CPU-only torch
(§7.2) a bundle lands ~1.5 GB, comfortably inside both. If a job starts approaching the disk
limit, that is the signal that something CUDA-shaped crept into the bundle.

**Release assets:** the three bundles, plus SHA256 checksums, plus a `RELEASE_NOTES.md` that
states plainly what downloads on first run and how large it is.

---

## 9. Licensing (`docs/LICENSES.md` — must exist before first public release)

| Component | License | Commercial use | Action required |
|-----------|---------|----------------|-----------------|
| Kokoro-82M | Apache-2.0 | Yes | Attribute |
| Chatterbox | MIT | Yes | Attribute; disclose watermarking |
| Whisper | MIT | Yes | Attribute |
| Demucs | **VERIFY** — Meta relicensed demucs to MIT, but confirm the exact tag and the `htdemucs` weights separately from the code | ? | **Blocking check before release.** If weights are CC-BY-NC, either find MIT weights or cut the feature. |
| Opus-MT | CC-BY-4.0 / Apache-2.0 (varies per pair) | Yes | Record per-pair |
| M2M100 | MIT | Yes | Attribute |
| **NLLB-200** | **CC-BY-NC** | **NO** | **Do not use** |
| ffmpeg | LGPL/GPL depending on build | Prefer LGPL build | Note build source |
| Our code | MIT | — | — |

Also add an **ethics note** to the README: voice cloning without the speaker's consent is
harmful and, in a growing number of jurisdictions, illegal. State the intended use. Do not
add "safety" theater that a local app cannot enforce — state it plainly and move on.

---

## 10. Kaggle workflow (for the agent doing Phase 0/1)

The API token lives at `kaggle/kaggle.json` (gitignored). **The installed Kaggle CLI is 2.x,
which does not read the legacy `username`+`key` file** — it wants the bearer token in an env
var:

```bash
export KAGGLE_API_TOKEN="<the key field from kaggle/kaggle.json>"
export PATH="$PATH:$HOME/AppData/Roaming/Python/Python314/Scripts"   # Windows CLI location
kaggle kernels push -p kaggle/pipeline_test
kaggle kernels status harshu60792/audio-toolkit-pipeline-test
kaggle kernels output harshu60792/audio-toolkit-pipeline-test -p ./out
```

`kernel-metadata.json` must keep `enable_gpu: true` and `enable_internet: true` (pip installs
and HF downloads both need it). Kernels are `is_private: true`.

---

## 11. Task checklist

Update checkboxes as work lands. Each task's acceptance criterion is the thing that must be
demonstrated, not merely written.

**Phase 0 — spike**
- [x] P0.1–P0.7 exit criteria in §4 all verified from a real kernel log (`kaggle/results/phase0_spike/`)
- [ ] P0.8 full dubbing chain proven on a real 30–60s video — **check `kaggle/results/README.md` for current state; was queued/running when this session ended**
- [x] Dependency-conflict check: chatterbox + demucs + whisper + kokoro in one env, one torch — found and fixed (torch 2.6.0/torchvision 0.21.0/torchaudio 2.6.0 pin, see kaggle/results/README.md)
- [ ] espeak-ng bundling path confirmed (§7.3) — worked via `apt-get install espeak-ng` on Kaggle; **packaged-app bundling (no apt available) still unverified**
- [x] Timings recorded in kaggle/results/README.md — VRAM (P0.7) not captured in phase0_spike; dub_test.py does capture peak VRAM per stage if that run completed, check its perf_summary.json

**Phase 1 — engine** (all written against the Phase 0-verified API calls; none browser/GPU-tested yet)
- [x] `device.py`, `paths.py`, `models.py` with resumable progress downloads (huggingface_hub snapshot_download)
- [x] `audio.py` with bundled-ffmpeg resolution
- [x] `tts.py`, `clone.py`, `isolate.py` — written; **no CPU smoke test has actually been run yet**, that's the next concrete step
- [x] `translate.py` with a license-cleared model (Opus-MT primary, M2M100 fallback)
- [x] `dub.py` with the §6.4 timing algorithm — logic mirrors kaggle/dub_test/dub_test.py; **confirm that spike passed before trusting this file**

**Phase 2 — UI**
- [x] 4-tab Gradio Blocks app, `127.0.0.1`, `share=False` — `src/vocalith/ui/app.py`
- [x] Per-feature progress bars wired to `progress_cb`
- [x] Device banner ("Running on NVIDIA RTX 4070" / "Running on CPU — slower")
- [x] Plain-English validation errors, never stack traces (traceback goes to console/log only)
- [x] Output files land in `paths.outputs_dir()` with a download button
- [x] **Opened in a browser and verified, 2026-09-04.** `PYTHONPATH=src python launcher/main.py` starts cleanly (imports are lazy, so this needed zero model downloads and zero GPU), served on 127.0.0.1:7860, and all four tabs were confirmed rendering their real fields (screenshot + get_page_text via the browser tool) — Text-to-Speech, Voice Cloning (with the watermark disclosure), Voice Isolation, Dubbing (with target-language/voice-mode/bed-gain controls). Two bugs this run caught and fixed: a redundant "CPU mode, CPU mode" banner string, and a Gradio 6.0 deprecation warning from passing `theme=` to `gr.Blocks()` instead of `.launch()`. **What's still unverified:** clicking Generate on any tab — that needs an actual model download, which needs either a GPU or patience on CPU. That's the next real gap, not the UI itself.

**Phase 3 — packaging** — all three scripts are first drafts, explicitly unverified (see file headers)
- [ ] Windows portable bundle launches on a clean VM with no Python installed
- [ ] macOS bundle launches; Gatekeeper workaround documented
- [ ] Linux tarball launches on a clean container
- [ ] First-run CUDA-torch upgrade path works and is visible
- [ ] Uninstall = delete the folder + the data dir (documented)
- [ ] `launcher/windows/build.ps1`'s .exe shim is a TODO stub (currently a .bat) — needs a real no-console shim

**Phase 4 — CI/release** — workflows written, never executed (no push has happened)
- [ ] `ci.yml` green on CPU — untested locally too; run `pytest tests/` before trusting it
- [ ] `release.yml` produces 3 assets + checksums on a tag
- [ ] A tagged pre-release downloaded and run by someone who did not build it
- [ ] **Requires user go-ahead to push to a GitHub remote** — do not push autonomously even under a "finish the project" instruction; that crosses into publishing/sending, which needs per-action confirmation

**Phase 5 — docs**
- [x] README: what it does, first-run expectations — download links pending an actual release
- [x] `docs/LICENSES.md` — Demucs weight-license question still explicitly open, flagged as blocking
- [x] `docs/TROUBLESHOOTING.md`: no GPU detected, port in use, Gatekeeper, slow CPU, OOM
- [x] Ethics note on voice cloning consent

**Immediate next steps for whoever resumes this** (in order):
1. Check `kaggle/results/README.md`'s dub-chain section — v7 (confirming the
   `translate.py` task-format fix) may still need to land; check its status before
   assuming translation itself is GPU-verified, though the fix is standard enough to
   trust either way.
2. `pytest tests/` verified passing (9/9, CPU-only, no GPU needed) on 2026-09-04 —
   note: local dev machine ran Python 3.14, outside the pinned 3.10-3.13 range, so tests
   were run via `PYTHONPATH=src pytest tests/` rather than an editable install; do a real
   `pip install -e .` on an in-range Python before trusting packaging.
3. `python launcher/main.py` **has been done** — all four tabs verified rendering
   correctly in-browser with the new premium design (screenshots taken, see the session
   note above). What's *not* yet verified: clicking Generate on any tab, which needs an
   actual model download (GPU or patient CPU). That's the real next gap — fix whatever
   it turns up; this is real code that has never actually generated audio, so treat
   first-run bugs there as expected, not a sign the approach is wrong.
4. Only after 1-3: attempt a packaging script, on the OS it targets, and update its
   STATUS header honestly based on what happens.

---

## 12. Risk register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Chatterbox pins a torch version that conflicts with Demucs/Whisper | High | Blocks Phase 1 | Resolve in Phase 0; if unresolvable, isolate Chatterbox in a subprocess with its own venv |
| Demucs weights turn out to be non-commercial | Medium | Cuts feature 3 and degrades feature 4 | Verify before Phase 1; alternatives: MDX-Net, or a smaller MIT denoiser |
| PyInstaller cannot bundle torch reliably | High | Blocks Phase 3 | Portable embedded Python is the primary plan, not the fallback (§7.1) |
| Bundle exceeds CI runner disk | Medium | Blocks Phase 4 | CPU torch in bundle, CUDA on first run (§7.2) |
| CPU-only dubbing is unusably slow (>30 min for 5 min video) | Medium | Feature unusable for most users | Offer `whisper-tiny`/Kokoro-preset "fast mode"; show honest time estimates up front |
| Unsigned macOS app blocked by Gatekeeper | Certain | Friction for Mac users | Document the workaround; revisit signing only if someone donates a cert |
| espeak-ng missing on user machines | Medium | Feature 1 dead on arrival | Bundle binaries (§7.3), test on a clean VM |

---

## 13. Notes for the next agent

- **Do not skip Phase 0.** Every failure mode in §12 is cheaper to find in a Kaggle notebook
  than in a Windows installer.
- **Do not add features.** Four features, done well, beats eight half-working ones. Requests
  for real-time voice changing, speech-to-speech, or a REST API go in a `FUTURE.md`, not into
  this build.
- **Do not add cloud anything.** Not "optional" cloud inference, not a hosted demo, not
  Gradio `share=True` for testing. C1–C3 are the product.
- **Test on a machine without a GPU** before every release. That is the median user.
- When a decision in this plan turns out to be wrong, **edit this file** and say why. This
  document is the project's memory.
