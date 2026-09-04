# Raw kernel logs — every attempt, not just the final passing ones

The main [`kaggle/results/README.md`](../README.md) narrates *why* each attempt failed
and what fixed it. This folder is the receipts: the actual raw log text from every
kernel run referenced there, in case the narration ever needs double-checking or a
similar failure pattern shows up again and the exact wording matters.

| File | What it is |
|---|---|
| `dub_test_v3.log` – `v5.log` | Dub-chain spike attempts before the torch/torchvision root cause (the `stage()` VRAM-tracking helper pre-caching torch) was found. v1/v2's raw logs weren't saved before this archival habit started — their content is narrated in the main README instead. |
| `dub_test_v6.log` | 8/9 stages passing; `translate` failing on the `"translation_XX_to_YY"` task-format issue. |
| `dub_test_v7.log` | `translate` still failing — the *second*, different transformers bug (`"translation"` dropped from the pipeline task registry entirely). |
| `dub_test_v8.log` | All 9 stages passing. Full output already archived separately in `../phase0_dub_spike/`. |
| `package_test_v1.log` | Real-package test: dataset-flattening bug (`import vocalith` failed). |
| `package_test_v2.log` | Real-package test: 3/4 pipelines pass; `dub()` fails on the missing reference-length check. |
| (v3 not here) | All 4 pipelines pass. Full output archived in `../phase1_real_package_test/`. |
| `linux_package_test_v1.log` | CRLF line endings break bash (`set: pipefail: invalid option name`). |
| `linux_package_test_v2.log` | CRLF fixed; stale `python-build-standalone` release tag fails (`gzip: stdin: not in gzip format`). |
| `linux_package_test_v3.log` | Both fixed — full build, extract, launch, HTTP 200. This is the *only* copy of this success log; it was never copied elsewhere because the Linux packaging test doesn't have its own dedicated results folder (the build artifact itself is a 1GB tarball, not worth archiving — the log is the evidence that matters). |
