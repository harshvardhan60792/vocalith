"""
Test launcher/linux/build.sh for real on actual Linux (Kaggle kernels run Ubuntu) --
the one packaging target this session had no direct hardware access to otherwise.
No GPU needed (build.sh installs CPU-only torch by design, see IMPLEMENTATION_PLAN.md
§7.2), so this kernel runs with enable_gpu:false -- zero GPU-quota cost.
"""
import glob
import os
import subprocess
import sys
import time

def sh(cmd, cwd=None, timeout=1800):
    print(f"$ {cmd}")
    r = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    if r.stdout:
        print(r.stdout[-4000:])
    if r.stderr:
        print(r.stderr[-4000:])
    print(f"  (exit code {r.returncode})")
    return r

# Locate the uploaded repo slice (learned tonight: Kaggle dataset uploads can flatten
# folder nesting, so find it by an unambiguous marker file rather than a guessed path).
_candidates = glob.glob("/kaggle/input/**/pyproject.toml", recursive=True)
if not _candidates:
    sh("find /kaggle/input -maxdepth 6")
    raise RuntimeError("Could not locate the repo slice under /kaggle/input")
_repo_src = os.path.dirname(_candidates[0])
print(f"Found repo slice at: {_repo_src}")

# Reconstruct the expected layout in a writable location, exactly as build.sh expects
# (it computes $ROOT as two directories up from its own script path).
REPO = "/kaggle/working/repo"
sh(f"mkdir -p {REPO}")
sh(f"cp -r {_repo_src}/src {_repo_src}/launcher {_repo_src}/pyproject.toml {REPO}/")
sh(f"chmod +x {REPO}/launcher/linux/build.sh")
sh(f"ls -la {REPO}")

print("\n===== Running launcher/linux/build.sh =====")
t0 = time.time()
r = sh("bash launcher/linux/build.sh", cwd=REPO, timeout=1800)
print(f"build.sh finished in {time.time()-t0:.0f}s, exit code {r.returncode}")

dist_tar = f"{REPO}/dist/Vocalith-linux-x86_64.tar.gz"
if r.returncode != 0 or not os.path.exists(dist_tar):
    print("BUILD FAILED or did not produce the expected tarball.")
    sh(f"find {REPO}/dist -maxdepth 3 2>/dev/null || echo 'no dist dir'")
    sys.exit(1)

print(f"\n===== Build succeeded: {dist_tar} =====")
sh(f"ls -la {dist_tar}")

# Verify the tarball is real and extracts cleanly, then launch it for real.
extract_dir = "/kaggle/working/extracted"
sh(f"mkdir -p {extract_dir}")
sh(f"tar -xzf {dist_tar} -C {extract_dir}", timeout=300)
sh(f"ls -la {extract_dir}")

print("\n===== Launching the packaged app for real =====")
launch = subprocess.Popen(
    ["bash", "vocalith.sh"], cwd=extract_dir,
    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
)
time.sleep(25)
poll = launch.poll()
if poll is not None:
    print(f"Launcher process exited early with code {poll} -- FAILED")
    print(launch.stdout.read()[-4000:])
    sys.exit(1)

check = sh("curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:7860", timeout=15)
print("HTTP status from packaged app:", check.stdout.strip())
launch.terminate()

if check.stdout.strip() == "200":
    print("\n===== LINUX PACKAGE TEST: SUCCESS =====")
else:
    print("\n===== LINUX PACKAGE TEST: FAILED (app did not serve 200) =====")
    sys.exit(1)
