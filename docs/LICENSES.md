# Licenses

Vocalith's own code is MIT (see [LICENSE](../LICENSE)). It bundles or downloads the
following third-party models and binaries at runtime. Each keeps its own license and
its own terms apply to that component independently of Vocalith's MIT license.

| Component | License | Commercial use OK? | Notes |
|---|---|---|---|
| Kokoro-82M (TTS) | Apache-2.0 | Yes | hexgrad/Kokoro-82M on HuggingFace |
| Chatterbox (voice cloning) | MIT | Yes | ResembleAI/chatterbox. **Watermarks output by default** (Perth watermarker) — disclosed in the UI, not stripped. |
| Whisper (transcription) | MIT | Yes | openai/whisper |
| Demucs (voice isolation) | **Verify before v1.0 release** | ? | Meta's demucs *code* was relicensed MIT; confirm the `htdemucs` pretrained *weights* carry the same license, separately from the code, before shipping. Blocking item — see IMPLEMENTATION_PLAN.md §9. |
| Helsinki-NLP Opus-MT (translation) | Apache-2.0 / CC-BY-4.0 (varies per language pair) | Yes | Record the exact license per pair actually shipped, at release time |
| facebook/m2m100_418M (translation fallback) | MIT | Yes | Used only for language pairs Opus-MT doesn't cover |
| ffmpeg | LGPL (essentials builds) | Yes, if LGPL build used | Static builds from gyan.dev (Windows) / johnvansickle.com (Linux) are LGPL-licensed shared builds; verify the specific build before release, avoid GPL-only builds |
| **NLLB-200** | CC-BY-NC | **No — not used in this project** | Deliberately excluded; do not add it back without re-checking this table |

## Ethics note

Voice cloning without the speaker's informed consent can cause real harm and is
illegal in a growing number of jurisdictions. Vocalith is built for consenting use:
narrating your own writing, dubbing your own content, cloning your own voice, voice
acting with permission. It ships with no server-side enforcement mechanism (it's a
local, offline app — there is nothing to enforce against) and makes no claim otherwise.
Use it responsibly.
