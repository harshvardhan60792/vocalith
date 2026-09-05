#!/usr/bin/env bash
# macOS portable bundle (arm64): python-build-standalone + site-packages + bundled
# ffmpeg, tarballed as Vocalith-macos-arm64.tar.gz. A .app/.dmg wrapper and code-signing
# are deliberately deferred -- unsigned builds are Gatekeeper-blocked; document the
# right-click -> Open workaround in the README rather than paying for a cert (violates
# the "everything free" constraint). See IMPLEMENTATION_PLAN.md §7.1.
#
# STATUS: run for real on GitHub Actions' macos-14 (arm64) runner via the Release
# workflow, 2026-09-05. First attempt failed in ~0.1s with zero log output -- pipefail
# killed the script on the python-build-standalone URL-resolution line before the
# friendly "could not resolve a URL" check could ever run (see the `|| true` comment
# at that line). Fixed and re-tagged; check this repo's Actions tab for the latest
# release run's actual pass/fail before assuming success from this comment alone.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DIST="$ROOT/dist/macos"
CURL_RETRY="--retry 3 --retry-delay 5 --retry-connrefused"
PY_ASSET_PATTERN="aarch64-apple-darwin-install_only.tar.gz"
# `|| true` on each pipeline: with `pipefail` set, a `grep` that matches nothing exits
# 1, which would abort the script right here via `set -e` -- BEFORE the friendly
# `if [ -z ... ]` check below ever runs. Found for real on GitHub Actions' macos-14
# runner: the job failed in ~0.1s with zero output, because pipefail killed it silently
# on this exact line before any echo could print. `|| true` lets an empty match reach
# the intended graceful error message instead of a silent, unexplained failure.
PY_URL="$(curl -sL $CURL_RETRY https://api.github.com/repos/astral-sh/python-build-standalone/releases/latest \
    | grep -o "https://[^\"]*cpython-3\.11[^\"]*${PY_ASSET_PATTERN}" | head -1 || true)"
if [ -z "$PY_URL" ]; then
    echo "Could not resolve a python-build-standalone download URL for pattern: $PY_ASSET_PATTERN" >&2
    exit 1
fi

rm -rf "$DIST"
mkdir -p "$DIST"

echo "Resolved Python build: $PY_URL"
curl -L $CURL_RETRY "$PY_URL" -o "$DIST/python.tar.gz"
PY_SIZE=$(stat -f%z "$DIST/python.tar.gz" 2>/dev/null || stat -c%s "$DIST/python.tar.gz")
if [ "$PY_SIZE" -lt 1000000 ]; then
    echo "Downloaded Python build is only $PY_SIZE bytes -- not a real tarball. URL: $PY_URL" >&2
    exit 1
fi
tar -xzf "$DIST/python.tar.gz" -C "$DIST"
mv "$DIST/python" "$DIST/pyruntime"
rm "$DIST/python.tar.gz"

"$DIST/pyruntime/bin/python3" -m pip install --quiet \
    torch==2.6.0 torchvision==0.21.0 torchaudio==2.6.0
"$DIST/pyruntime/bin/python3" -m pip install --quiet -e "$ROOT" --no-deps
"$DIST/pyruntime/bin/python3" -m pip install --quiet \
    kokoro==0.9.4 "misaki[en]" chatterbox-tts demucs openai-whisper \
    sentencepiece soundfile librosa "numpy<2.0" platformdirs huggingface_hub "gradio>=4.44"

# macOS ships ffmpeg only via Homebrew, which we can't assume -- bundle a static build
# from evermeet.cx, resolved dynamically via its stable info API (same "don't hardcode
# a version that goes stale" lesson as the python-build-standalone fix above).
#
# LICENSE NOTE, deliberately not glossed over: evermeet.cx's build links x264/x265,
# making it GPL-licensed -- NOT the LGPL "essentials" builds used for Windows/Linux
# (see docs/LICENSES.md). This is an inconsistency worth resolving before a real
# release: either find/build an LGPL-only static macOS ffmpeg (no x264/x265), or
# accept GPL on macOS specifically and update docs/LICENSES.md to say so explicitly
# rather than implying LGPL applies uniformly across all three platforms.
mkdir -p "$DIST/ffmpeg"
FFMPEG_INFO="$(curl -sL $CURL_RETRY https://evermeet.cx/ffmpeg/info/ffmpeg/release)"
FFMPEG_URL="$(echo "$FFMPEG_INFO" | grep -o '"zip":{"url":"[^"]*"' | grep -o 'https://[^"]*' || true)"
if [ -z "$FFMPEG_URL" ]; then
    echo "Could not resolve a macOS ffmpeg download URL from evermeet.cx" >&2
    exit 1
fi
echo "Resolved macOS ffmpeg build: $FFMPEG_URL"
curl -L $CURL_RETRY "$FFMPEG_URL" -o "$DIST/ffmpeg.zip"
FFMPEG_SIZE=$(stat -f%z "$DIST/ffmpeg.zip" 2>/dev/null || stat -c%s "$DIST/ffmpeg.zip")
if [ "$FFMPEG_SIZE" -lt 1000000 ]; then
    echo "Downloaded ffmpeg build is only $FFMPEG_SIZE bytes -- not real. URL: $FFMPEG_URL" >&2
    exit 1
fi
unzip -q -o "$DIST/ffmpeg.zip" -d "$DIST/ffmpeg"
rm "$DIST/ffmpeg.zip"
chmod +x "$DIST/ffmpeg/ffmpeg"

cp -r "$ROOT/src" "$DIST/src"
cp -r "$ROOT/launcher" "$DIST/launcher_src"
cat > "$DIST/vocalith.sh" <<'EOF'
#!/usr/bin/env bash
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export VOCALITH_FFMPEG="$DIR/ffmpeg/ffmpeg"
"$DIR/pyruntime/bin/python3" "$DIR/launcher_src/main.py"
EOF
chmod +x "$DIST/vocalith.sh"

tar -czf "$ROOT/dist/Vocalith-macos-arm64.tar.gz" -C "$DIST" .
echo "Built: $ROOT/dist/Vocalith-macos-arm64.tar.gz"
