#!/usr/bin/env bash
# macOS portable bundle (arm64): python-build-standalone + site-packages + bundled
# ffmpeg, tarballed as Vocalith-macos-arm64.tar.gz. A .app/.dmg wrapper and code-signing
# are deliberately deferred -- unsigned builds are Gatekeeper-blocked; document the
# right-click -> Open workaround in the README rather than paying for a cert (violates
# the "everything free" constraint). See IMPLEMENTATION_PLAN.md §7.1.
#
# STATUS: first draft, written 2026-09-04, NOT YET RUN. Test on a clean Mac account.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DIST="$ROOT/dist/macos"
PY_TAG="20250612"
PY_URL="https://github.com/astral-sh/python-build-standalone/releases/download/${PY_TAG}/cpython-3.11.9+${PY_TAG}-aarch64-apple-darwin-install_only.tar.gz"

rm -rf "$DIST"
mkdir -p "$DIST"

curl -L "$PY_URL" -o "$DIST/python.tar.gz"
tar -xzf "$DIST/python.tar.gz" -C "$DIST"
mv "$DIST/python" "$DIST/pyruntime"
rm "$DIST/python.tar.gz"

"$DIST/pyruntime/bin/python3" -m pip install --quiet \
    torch==2.6.0 torchvision==0.21.0 torchaudio==2.6.0
"$DIST/pyruntime/bin/python3" -m pip install --quiet -e "$ROOT" --no-deps
"$DIST/pyruntime/bin/python3" -m pip install --quiet \
    kokoro==0.9.4 "misaki[en]" chatterbox-tts demucs openai-whisper \
    sentencepiece soundfile librosa "numpy<2.0" platformdirs huggingface_hub "gradio>=4.44"

# macOS ships ffmpeg only via Homebrew, which we can't assume -- bundle a static build.
# TODO: pin a specific evermeet.cx/osxexperts.net release URL + checksum before first release.
mkdir -p "$DIST/ffmpeg"
echo "TODO: download a static macOS ffmpeg binary into $DIST/ffmpeg/ffmpeg"

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
