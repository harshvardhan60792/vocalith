# Licenses

Vocalith's own code is MIT (see [LICENSE](../LICENSE)). It bundles or downloads the
following third-party models and binaries at runtime. Each keeps its own license and
its own terms apply to that component independently of Vocalith's MIT license.

| Component | License | Commercial use OK? | Notes |
|---|---|---|---|
| Kokoro-82M (TTS) | Apache-2.0 | Yes | hexgrad/Kokoro-82M on HuggingFace |
| Chatterbox (voice cloning) | MIT | Yes | ResembleAI/chatterbox. **Watermarks output by default** (Perth watermarker) — disclosed in the UI, not stripped. |
| Whisper (transcription) | MIT | Yes | openai/whisper |
| Demucs (voice isolation) | MIT | Yes | facebookresearch/demucs. Confirmed 2026-09-04 by reading the repo directly: its README states plainly "Demucs is released under the MIT license," with no carve-out for the pretrained `htdemucs` weights vs. the code — the project's own official position covers both. (The training data, MusDB18 + an extra 800 songs, is separately-licensed commercial music, same as virtually every audio/speech model in this table including Whisper and Kokoro — that's a training-data-provenance question, not a redistribution-license one, and isn't specific to Demucs.) |
| Helsinki-NLP Opus-MT (translation) | Apache-2.0 / CC-BY-4.0 (varies per language pair) | Yes | Record the exact license per pair actually shipped, at release time |
| facebook/m2m100_418M (translation fallback) | MIT | Yes | Used only for language pairs Opus-MT doesn't cover |
| ffmpeg (Windows/Linux) | LGPL (essentials builds) | Yes | Static builds from gyan.dev (Windows) / johnvansickle.com (Linux) are LGPL-licensed shared builds |
| ffmpeg (macOS) | **GPL** — inconsistent with Windows/Linux, open item | Yes, but copyleft terms differ | `launcher/macos/build.sh` bundles evermeet.cx's static build, which links x264/x265 and is therefore GPL, not LGPL. **Not yet resolved:** either find/build an LGPL-only static macOS ffmpeg (drop x264/x265), or explicitly accept GPL on macOS specifically and document why that's fine for this project's distribution model. Don't let this sit unresolved into a real release. |
| **NLLB-200** | CC-BY-NC | **No — not used in this project** | Deliberately excluded; do not add it back without re-checking this table |

## Ethics note

Voice cloning without the speaker's informed consent can cause real harm and is
illegal in a growing number of jurisdictions. Vocalith is built for consenting use:
narrating your own writing, dubbing your own content, cloning your own voice, voice
acting with permission. It ships with no server-side enforcement mechanism (it's a
local, offline app — there is nothing to enforce against) and makes no claim otherwise.
Use it responsibly.
