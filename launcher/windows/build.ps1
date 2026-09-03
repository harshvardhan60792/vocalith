# Windows portable bundle: embedded Python + site-packages + bundled ffmpeg, zipped as
# Vocalith-win64.zip. See IMPLEMENTATION_PLAN.md §7.1 for why embedded-Python was chosen
# over PyInstaller (torch + PyInstaller is a known-bad pairing).
#
# STATUS: run locally 2026-09-04 on a real Windows machine (not yet on a clean VM or in
# CI). First real run found a real gap: the original draft used `7z` for both the
# ffmpeg extraction and the final archive -- but 7-Zip isn't installed on a typical dev
# machine (confirmed: `Get-Command 7z` and both Program Files paths came back empty on
# this machine). Switched to PowerShell's native Expand-Archive/Compress-Archive and an
# ffmpeg .zip build instead of .7z, so this script has zero external tool dependencies.
# Trade-off: zip compresses worse than 7z, so the final download is somewhat larger --
# accepted deliberately in exchange for not requiring users (or CI, without an extra
# `choco install 7zip` step) to have 7-Zip present. Before fully trusting this script:
# run it end to end, then launch Vocalith.exe on a VM with no Python and no Visual C++
# redistributables preinstalled -- that is the actual bar for "works".
$ErrorActionPreference = "Stop"

$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$dist = Join-Path $root "dist\windows"
$pyVersion = "3.11.9"
$embedUrl = "https://www.python.org/ftp/python/$pyVersion/python-$pyVersion-embed-amd64.zip"
$ffmpegUrl = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"  # LGPL build, .zip not .7z

Remove-Item -Recurse -Force $dist -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $dist | Out-Null

# 1. embedded Python
Invoke-WebRequest $embedUrl -OutFile "$dist\python-embed.zip"
Expand-Archive "$dist\python-embed.zip" -DestinationPath "$dist\python"

# enable site-packages in the embeddable build (disabled by default)
$pthFile = Get-ChildItem "$dist\python\python*._pth" | Select-Object -First 1
(Get-Content $pthFile.FullName) -replace '#import site', 'import site' | Set-Content $pthFile.FullName

# bootstrap pip
Invoke-WebRequest "https://bootstrap.pypa.io/get-pip.py" -OutFile "$dist\get-pip.py"
& "$dist\python\python.exe" "$dist\get-pip.py" --no-warn-script-location

# 2. install our package + deps (CPU torch -- CUDA fetched on first run, see §7.2)
& "$dist\python\python.exe" -m pip install --no-warn-script-location `
    "torch==2.6.0" "torchvision==0.21.0" "torchaudio==2.6.0" `
    --index-url https://download.pytorch.org/whl/cpu
& "$dist\python\python.exe" -m pip install --no-warn-script-location -e "$root" --no-deps
& "$dist\python\python.exe" -m pip install --no-warn-script-location `
    kokoro==0.9.4 "misaki[en]" chatterbox-tts demucs openai-whisper `
    sentencepiece soundfile librosa "numpy<2.0" platformdirs huggingface_hub "gradio>=4.44"

# 3. bundled ffmpeg (LGPL build; note in docs/LICENSES.md)
Invoke-WebRequest $ffmpegUrl -OutFile "$dist\ffmpeg.zip"
Expand-Archive "$dist\ffmpeg.zip" -DestinationPath "$dist\ffmpeg_tmp"
$ffmpegExe = Get-ChildItem -Recurse "$dist\ffmpeg_tmp" -Filter "ffmpeg.exe" | Select-Object -First 1
New-Item -ItemType Directory -Force -Path "$dist\ffmpeg" | Out-Null
Copy-Item $ffmpegExe.FullName "$dist\ffmpeg\ffmpeg.exe"
Remove-Item -Recurse -Force "$dist\ffmpeg_tmp", "$dist\ffmpeg.zip"

# 4. launcher entrypoint + a double-clickable .exe shim (requires a tiny C launcher or
#    a tool like `pyinstaller --onefile launcher_shim.py` just for the shim -- NOT for
#    bundling torch, only for a clean icon/no-console entrypoint). TODO: build the shim.
Copy-Item -Recurse "$root\src" "$dist\src"
Copy-Item -Recurse "$root\launcher" "$dist\launcher_src"
@"
@echo off
set VOCALITH_FFMPEG=%~dp0ffmpeg\ffmpeg.exe
"%~dp0python\python.exe" "%~dp0launcher_src\main.py"
"@ | Set-Content "$dist\Vocalith.bat"

# 5. archive
Compress-Archive -Path "$dist\*" -DestinationPath "$root\dist\Vocalith-win64.zip" -Force

Write-Host "Built: $root\dist\Vocalith-win64.zip"
