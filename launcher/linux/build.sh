#!/usr/bin/env bash
# Linux portable bundle: python-build-standalone + site-packages + bundled ffmpeg,
# tarballed as Vocalith-linux-x86_64.tar.gz. See IMPLEMENTATION_PLAN.md §7.1.
#
# STATUS: run for real on Kaggle's Linux infra 2026-09-04, and on GitHub Actions'
# ubuntu-latest runner (see this repo's Actions tab). First attempt used a
# hand-guessed release tag ("20250612") that turned out not to exist -- GitHub
# returned a 9-byte error stub instead of a tarball, and `tar` failed with
# "gzip: stdin: not in gzip format". Fixed by resolving the latest release via
# GitHub's API at build time instead of hardcoding a tag that inevitably goes stale
# (python-build-standalone cuts releases roughly weekly). A later real run also hit
# `curl: (28) Failed to connect to johnvansickle.com ... Couldn't connect to server`
# -- a transient outage on that external host, not a code bug -- hence CURL_RETRY
# below on every download.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DIST="$ROOT/dist/linux"
CURL_RETRY="--retry 3 --retry-delay 5 --retry-connrefused"
PY_ASSET_PATTERN="x86_64-unknown-linux-gnu-install_only.tar.gz"
PY_URL="$(curl -sL $CURL_RETRY https://api.github.com/repos/astral-sh/python-build-standalone/releases/latest \
    | grep -o "https://[^\"]*cpython-3\.11[^\"]*${PY_ASSET_PATTERN}" | head -1 || true)"
if [ -z "$PY_URL" ]; then
    echo "Could not resolve a python-build-standalone download URL for pattern: $PY_ASSET_PATTERN" >&2
    exit 1
fi
FFMPEG_URL="https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"

rm -rf "$DIST"
mkdir -p "$DIST"

echo "Resolved Python build: $PY_URL"
curl -L $CURL_RETRY "$PY_URL" -o "$DIST/python.tar.gz"
# Catches exactly the failure this comment block describes above: a bad URL silently
# downloading a tiny error page instead of the real ~40-50MB tarball.
PY_SIZE=$(stat -c%s "$DIST/python.tar.gz" 2>/dev/null || stat -f%z "$DIST/python.tar.gz")
if [ "$PY_SIZE" -lt 1000000 ]; then
    echo "Downloaded Python build is only $PY_SIZE bytes -- not a real tarball. URL: $PY_URL" >&2
    exit 1
fi
tar -xzf "$DIST/python.tar.gz" -C "$DIST"
mv "$DIST/python" "$DIST/pyruntime"
rm "$DIST/python.tar.gz"

"$DIST/pyruntime/bin/python3" -m pip install --quiet \
    torch==2.6.0 torchvision==0.21.0 torchaudio==2.6.0 --index-url https://download.pytorch.org/whl/cpu
"$DIST/pyruntime/bin/python3" -m pip install --quiet -e "$ROOT" --no-deps
"$DIST/pyruntime/bin/python3" -m pip install --quiet \
    kokoro==0.9.4 "misaki[en]" chatterbox-tts demucs openai-whisper \
    sentencepiece soundfile librosa "numpy<2.0" platformdirs huggingface_hub "gradio>=4.44"

curl -L $CURL_RETRY "$FFMPEG_URL" -o "$DIST/ffmpeg.tar.xz"
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
