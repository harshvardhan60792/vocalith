## linux_package_test/ — DONE, Linux packaging (`launcher/linux/build.sh`), 2026-09-04

No Linux machine was directly available this session, but Kaggle kernels *run on*
Linux — genuinely the only real Linux access reachable tonight, and it needed zero
GPU (packaging installs CPU-only torch by design, `enable_gpu: false` on this kernel,
no GPU quota spent). Uploaded a slice of the repo (`src/`, `launcher/`, `pyproject.toml`)
as a dataset and ran `launcher/linux/build.sh` for real, then extracted the resulting
tarball and launched `vocalith.sh` to confirm it actually serves the UI.

**Result (v3): SUCCESS.** Built a 1,003,119,754-byte (1.0 GB) `Vocalith-linux-x86_64.tar.gz`
in 389s, extracted it cleanly, launched `vocalith.sh`, and `curl` got a real `200` from
`http://127.0.0.1:7860` — the packaged app, running from its own bundled Python runtime,
serving the actual UI. Mirrors the Windows result exactly.

Two real bugs found and fixed getting from v1 to v3 (both also pre-emptively fixed in
`launcher/macos/build.sh`, which shares the same code pattern but is still unverified —
no Mac hardware exists in this session's reach):
1. **v1: CRLF line endings.** `set: pipefail: invalid option name` at "line 7" --
   `launcher/linux/build.sh` and `launcher/macos/build.sh` had silently picked up CRLF
   line endings from being edited on this Windows machine (git's `autocrlf`). bash chokes
   on the trailing `\r`. Fixed the files to LF and added `.gitattributes` (`*.sh text
   eol=lf`) so this can't silently recur for anyone else editing on Windows either.
2. **v2: stale hardcoded release tag.** `gzip: stdin: not in gzip format` -- the
   `python-build-standalone` release tag ("20250612") was a never-verified placeholder
   that no longer exists (that project cuts releases roughly weekly); GitHub returned a
   9-byte error stub instead of a tarball. Fixed by resolving the latest release via
   GitHub's API at build time instead of hardcoding a tag, plus a size check (>1MB) on
   the download before extracting, so a bad URL fails with a clear message instead of a
   cryptic `tar` error.

**Practical note for next time:** don't let a packaging-test kernel extract its own
output a second time into `/kaggle/working/` -- the resulting multi-thousand-file output
makes `kaggle kernels output` (which fetches everything the kernel wrote) impractically
slow to download. Use `kaggle kernels output ... --file-pattern ".*\.log$"` to fetch just
the log when you only need to confirm pass/fail, not the built artifact itself.

## phase1_real_package_test/ — DONE, 2026-09-04, kernel v3, Tesla P100

The Phase 0 spikes (`pipeline_test`, `dub_test`) proved the *logic* works by mirroring
it into standalone scripts -- they never imported the actual `src/vocalith/` package.
This closes that gap: uploaded the real package as a Kaggle dataset
(`harshu60792/vocalith-package-src`) and ran its actual `tts.synthesize()`,
`clone.clone()` (including the real Demucs denoise-reference step), `isolate.isolate()`,
and `dub.dub()` functions directly, unmodified, exactly as the shipped app calls them.

**Result: all 4 pass.** Real Spanish output from the real `dub()` function:
*"Esta es la verdadera tubería de doblaje que habla inglés antes de la traducción..."*

Two real bugs found and fixed by this run (not spike-script artifacts -- these were in
the actual shipped code and would have shipped broken):
1. **v1→v2:** the dataset upload flattened the `vocalith/` folder (files landed directly
   at the dataset root, no wrapper folder) -- `import vocalith` failed. Fixed by finding
   the package root via an unambiguous marker file (`paths.py`) and symlinking it to a
   dir literally named `vocalith` before adjusting `sys.path`.
2. **v2→v3:** `dub.dub()` called `clone.clone()` without first checking the source
   clip's voice track was long enough to serve as its own cloning reference -- a short
   clip produced a confusing generic "upload a reference sample" error in a context
   where the user never manually uploaded one. Fixed in `src/vocalith/pipelines/dub.py`
   with a clear, dubbing-specific error message, and verified by lengthening the test
   clip to actually exercise the success path too.

Kaggle dataset source lives at `kaggle/package_test/vocalith_dataset/` (gitignored,
transient -- re-copy from `src/vocalith/` and re-upload via `kaggle datasets version`
if this needs re-running after further changes).

## debug_logs/ — the raw log from every kernel run, not just the passing ones

See [`debug_logs/README.md`](debug_logs/README.md) for an index. Every failed attempt
narrated below and in the phase sections has its actual log text preserved there, not
just this file's summary of it — in case the exact wording ever matters again.

# Kaggle spike results

Saved so nobody has to re-run Kaggle GPU time to see this project's pipeline actually
works. Update this file (don't just add folders) whenever a new spike run lands.

## phase0_spike/ — 2026-09-04, kernel v2, Tesla P100-16GB

`audio-toolkit-pipeline-test` — Kokoro TTS → Chatterbox clone (using Kokoro's own
output as the reference) → Demucs isolation (on a synthetic noisy mix) → Whisper
transcription, chained in one script.

**Result: all 4 stages passed.** Whisper's transcript of the Chatterbox output matched
the intended text exactly, which validates the clone→transcribe round trip.

| Stage | Time | Notes |
|---|---|---|
| setup (pip installs) | 245s | one-time per fresh Kaggle session, not representative of app runtime |
| import_check | 8s | confirms the pinned torch/torchvision/torchaudio/transformers versions import cleanly |
| kokoro_tts | 17s | |
| chatterbox_clone | 50s | |
| demucs_isolation | 8s | |
| whisper_transcribe | 3s | |

**v1 (first attempt, before the fix) failed all 4 model stages** with
`RuntimeError: operator torchvision::nms does not exist` — `chatterbox-tts` pins
`torch==2.6.0`, which orphaned Kaggle's preinstalled `torchvision 0.25.0` (wants
`torch==2.10.0`), breaking every `transformers` import downstream. Fixed by explicitly
reinstalling the matched trio `torch==2.6.0 / torchvision==0.21.0 / torchaudio==2.6.0`
after all pip installs (see `kaggle/pipeline_test/test.py`). **This exact pin is what's
in `pyproject.toml` and every packaging script — do not "helpfully" bump it without
re-running this spike.**

Files: `audio-toolkit-pipeline-test.log` (full run log), `tts_out.wav`, `clone_out.wav`,
`noisy_mix.wav`, `demucs_out/` (separated stems), `transcript.txt`.

## phase0_dub_spike/ — full dubbing chain (P0.8) — DONE, 2026-09-04, kernel v8, Tesla P100

**All 9 stages passed.** Real `dubbed_video.mp4`, correct Spanish translation, correctly
timed `.srt`:

```
Bienvenidos a esta breve demostración.
Hoy estamos probando una tubería de doblaje totalmente local.
Transcribe el discurso, lo traduce y lo revisa en la voz del orador original.
El tiempo debe coincidir con el original lo más cerca posible.
```

Three segments hit the 1.25x stretch cap (wanted 1.6-1.7x) — expected and correctly
handled: Spanish translations run longer than their English source, §6.4's clamp-and-warn
design is exactly what's supposed to happen here, not a bug. It took 8 kernel pushes
(v1-v8) and two distinct real bugs found along the way (both already fixed in the actual
`src/vocalith/pipelines/` code, not just the spike) -- full blow-by-blow kept below because
the debugging path is worth more to a future agent than just the final green run.

### Superseded below: the v6 run (8/9 stages, English-fallback dub) that led here

`kaggle/dub_test/dub_test.py` builds a synthetic video (Kokoro speech over a tone bed),
then runs the complete chain: extract audio → Demucs split → Whisper word-timestamps →
Opus-MT translate (en→es) → Chatterbox re-voice per segment → clamped pitch-preserving
time-stretch → place on original timeline → remix with bed → mux into video → emit
.srt. Its logic is mirrored directly in `src/vocalith/pipelines/dub.py`.

**Result: 8 of 9 stages passed on v6**, producing a real `dubbed_video.mp4` with correct
per-segment timing (one segment needed 1.28x stretch, clamped to the 1.25x cap — exactly
the warning path in §6.4 working as designed) and an aligned `.srt`. The one failure —
`translate` — turned out to be a real bug, not a spike-only issue: **transformers now
requires the explicit `"translation_XX_to_YY"` task string; a bare `"translation"` raises
`KeyError`.** Fixed in both `dub_test.py` and, more importantly, in the actual
`src/vocalith/pipelines/translate.py` — this would have silently broken dubbing's
translation step in the shipped app (Chatterbox's own fallback-to-English logic masked
it well enough in the spike that only 1 of 9 stages showed red). v7 re-runs with the fix;
check this file's status line below for whether it landed.

| Stage | Time (v6) | Notes |
|---|---|---|
| setup | 318s | one-time per session |
| build_input (Kokoro) | 31s | 1.25 GB peak VRAM |
| extract_audio (ffmpeg) | 0.2s | |
| demucs_split | 9s | |
| whisper_transcribe | 11s | 0.49 GB peak VRAM |
| translate | — | failed on v6 — see below |
| chatterbox_revoice | 67s | 3.76 GB peak VRAM (per-segment; 4 segments) |
| align_and_mix | 5s | |
| mux_and_srt | 0.3s | |

**v7 hit a *second*, different translate bug.** The `"translation_XX_to_YY"` task-string
fix was necessary but not sufficient: transformers 5.2.0 turned out to have dropped
`"translation"` from its pipeline task registry entirely (`KeyError: 'translation'`
raised from inside `check_task` itself, not from parsing the task string this time).
**Real fix (v8, passing): stop using `pipeline("translation_...")` at all** — it's just
tokenize → generate → decode underneath, so `translate.py` now calls
`AutoTokenizer`/`AutoModelForSeq2SeqLM` directly, which sidesteps the pipeline registry
entirely and is stable, documented, low-level API regardless of which pipeline task
names a given transformers version supports. Applied to both `dub_test.py` and
`src/vocalith/pipelines/translate.py`. **v8 passed all 9 stages** — see the top of this
section for the actual translated output.

Four earlier attempts (v1–v5) failed before v6 even got translate() itself to run, each
teaching something real, not just
retries of the same thing — worth reading if a similar "works standalone, fails in this
script" symptom shows up again:
1. **v1:** same torch/torchvision mismatch as pipeline_test.py's original bug, in a
   script that was supposed to already have the fix applied — the fix line was correct,
   but nothing had verified it actually ran.
2. **v2:** added an `import_check` diagnostic stage to catch v1's bug faster — the
   diagnostic itself broke the very thing it was checking (details in v3/v4 below).
3. **v3:** tried `--force-reinstall --no-deps` per-package instead of one combined
   install — didn't help, because the real cause was elsewhere.
4. **v4:** added `pip show` + a fresh-subprocess canary for direct evidence. The
   subprocess canary passed every time; the in-process check failed every time.
   That was the actual clue.
5. **Root cause (confirmed before v6):** `stage()`'s own VRAM-tracking helper did
   `import torch` on *every* call — including the very first `stage("setup", setup)`
   call, which ran `import torch` **before** `setup()` had reinstalled the correct
   torch/torchvision pin. That cached the OLD Kaggle-default torch in `sys.modules`;
   every later `import torch` in-process (including torchvision's first-ever import,
   deep inside kokoro's import chain) then registered against that stale module
   instead of the correctly-pinned one now on disk — even though `pip show` and a
   fresh subprocess both correctly showed the pinned versions the entire time. Fixed
   by running `setup()` directly, not through `stage()` — matches
   `kaggle/pipeline_test/test.py`'s original working shape exactly.

**Re-run instructions**, if a future change needs re-verification:

```bash
export KAGGLE_API_TOKEN="<key from kaggle/kaggle.json>"
export PATH="$PATH:$HOME/AppData/Roaming/Python/Python314/Scripts"  # Windows CLI location
kaggle kernels push -p kaggle/dub_test
kaggle kernels status harshu60792/audio-toolkit-dub-test
kaggle kernels output harshu60792/audio-toolkit-dub-test -p kaggle/dub_test/out
```

**Kaggle GPU quota is 30 hrs/week and does not carry over — don't re-run spikes that
already passed.** Check this README before spending GPU time.
