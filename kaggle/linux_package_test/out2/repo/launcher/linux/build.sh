#!/usr/bin/env bash
# Linux portable bundle: python-build-standalone + site-packages + bundled ffmpeg,
# tarballed as Vocalith-linux-x86_64.tar.gz. See IMPLEMENTATION_PLAN.md §7.1.
#
# STATUS: first draft, written 2026-09-04, NOT YET RUN. Test on a container with no
# system Python before trusting it.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DIST="$ROOT/dist/linux"
PY_TAG="20250612"  # python-build-standalone release tag -- pin and bump deliberately
PY_URL="https://github.com/astral-sh/python-build-standalone/releases/download/${PY_TAG}/cpython-3.11.9+${PY_TAG}-x86_64-unknown-linux-gnu-install_only.tar.gz"
FFMPEG_URL="https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"

rm -rf "$DIST"
mkdir -p "$DIST"

curl -L "$PY_URL" -o "$DIST/python.tar.gz"
tar -xzf "$DIST/python.tar.gz" -C "$DIST"
mv "$DIST/python" "$DIST/pyruntime"
rm "$DIST/python.tar.gz"

"$DIST/pyruntime/bin/python3" -m pip install --quiet \
    torch==2.6.0 torchvision==0.21.0 torchaudio==2.6.0 --index-url https://download.pytorch.org/whl/cpu
"$DIST/pyruntime/bin/python3" -m pip install --quiet -e "$ROOT" --no-deps
"$DIST/pyruntime/bin/python3" -m pip install --quiet \
    kokoro==0.9.4 "misaki[en]" chatterbox-tts demucs openai-whisper \
    sentencepiece soundfile librosa "numpy<2.0" platformdirs huggingface_hub "gradio>=4.44"

curl -L "$FFMPEG_URL" -o "$DIST/ffmpeg.tar.xz"
mkdir -p "$DIST/ffmpeg_tmp"
tar -xf "$DIST/ffmpeg.tar.xz" -C "$DIST/ffmpeg_tmp"
mkdir -p "$DIST/ffmpeg"
find "$DIST/ffmpeg_tmp" -name ffmpeg -type f -exec cp {} "$DIST/ffmpeg/ffmpeg" \;
chmod +x "$DIST/ffmpeg/ffmpeg"
rm -rf "$DIST/ffmpeg_tmp" "$DIST/ffmpeg.tar.xz"

cp -r "$ROOT/src" "$DIST/src"
cp -r "$ROOT/launcher" "$DIST/launcher_src"
cat > "$DIST/vocalith.sh" <<'EOF'
#!/usr/bin/env bash
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export VOCALITH_FFMPEG="$DIR/ffmpeg/ffmpeg"
"$DIR/pyruntime/bin/python3" "$DIR/launcher_src/main.py"
EOF
chmod +x "$DIST/vocalith.sh"

tar -czf "$ROOT/dist/Vocalith-linux-x86_64.tar.gz" -C "$DIST" .
echo "Built: $ROOT/dist/Vocalith-linux-x86_64.tar.gz"
