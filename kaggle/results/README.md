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

## phase0_dub_spike/ — full dubbing chain (P0.8)

Status: **queued/running as of 2026-09-04 night** — see IMPLEMENTATION_PLAN.md task
checklist for current state. `kaggle/dub_test/dub_test.py` builds a synthetic video
(Kokoro speech over a tone bed), then runs the complete chain: extract audio → Demucs
split → Whisper word-timestamps → Opus-MT translate (en→es) → Chatterbox re-voice per
segment → clamped pitch-preserving time-stretch → place on original timeline → remix
with bed → mux into video → emit .srt. Its logic is mirrored directly in
`src/vocalith/pipelines/dub.py`.

**If this folder is empty or this section still says "queued" when you pick up this
project: the run either didn't finish or wasn't downloaded yet.** Re-run it with:

```bash
export KAGGLE_API_TOKEN="<key from kaggle/kaggle.json>"
export PATH="$PATH:$HOME/AppData/Roaming/Python/Python314/Scripts"  # Windows CLI location
kaggle kernels status harshu60792/audio-toolkit-dub-test
kaggle kernels output harshu60792/audio-toolkit-dub-test -p kaggle/dub_test/out
```

If it's not yet pushed at all: `kaggle kernels push -p kaggle/dub_test`.

**Kaggle GPU quota is 30 hrs/week and does not carry over — don't re-run spikes that
already passed.** Check this README before spending GPU time.
