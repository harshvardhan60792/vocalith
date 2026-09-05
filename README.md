# Vocalith

A free, open-source, **fully local** desktop audio toolkit — text-to-speech, voice
cloning, voice isolation, and dubbing. No subscriptions, no API keys, no accounts,
no cloud. Everything runs on your own machine.

Built as a local alternative to ElevenLabs, using permissively-licensed open models:

| Feature | Model | License |
|---|---|---|
| Text to speech | [Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M) | Apache-2.0 |
| Voice cloning | [Chatterbox](https://github.com/resemble-ai/chatterbox) | MIT |
| Voice isolation | [Demucs](https://github.com/facebookresearch/demucs) | see [docs/LICENSES.md](docs/LICENSES.md) |
| Dubbing | Whisper + Opus-MT/M2M100 + Chatterbox/Kokoro | MIT / Apache-2.0-ish, MIT |

Full license table and an ethics note on voice cloning: [docs/LICENSES.md](docs/LICENSES.md).

## Status

**Released.** [Download the latest release](https://github.com/harshvardhan60792/vocalith/releases/latest) —
one-click installers for Windows, macOS (arm64), and Linux, each built and verified
for real on GitHub Actions' own runners (not just Kaggle spikes). The model pipeline
is proven end-to-end on a real GPU (see [kaggle/results/](kaggle/results/)), and the
app code (`src/vocalith/`) has been GPU-verified running its actual pipelines. See
[IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md)'s "AT A GLANCE" section for exactly
what's done and why each major decision was made — that file is the project's source
of truth and is written so any AI agent or contributor can pick up the work with no
prior context.

## Installing (end users)

Download the archive for your OS from the
[latest release](https://github.com/harshvardhan60792/vocalith/releases/latest),
extract it, and run `Vocalith.exe` (Windows) or `vocalith.sh` (macOS/Linux). No
Python, no terminal, nothing to install first — the archive bundles its own Python
runtime and ffmpeg. macOS is unsigned (Gatekeeper will block it on first launch) —
right-click the app and choose Open to bypass this once; there's no paid Apple
Developer cert behind this project, by design (see "Why local-only" below).

## Running from source (for development — not the end-user path above)

```bash
pip install -e .
python launcher/main.py
```

A browser tab opens automatically. Model weights download on first use of each
feature, with a progress bar — nothing downloads at install time.

## Why local-only

Most "free" TTS/cloning tools online quietly upload your audio to someone else's
server. Vocalith never does — see the hard constraints in
[IMPLEMENTATION_PLAN.md §1](IMPLEMENTATION_PLAN.md#1-what-this-is). This also means it
is not, and will not become, a hosted public web service: voice cloning and dubbing
are too GPU-heavy to serve for free at scale. One local install per user is the
deliberate design, not a limitation.

## Contributing / resuming this project

Read [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) first. It has the repo layout,
every pipeline's exact API, the dubbing timing algorithm, the packaging plan, the risk
register, and a task checklist kept up to date as work lands.
