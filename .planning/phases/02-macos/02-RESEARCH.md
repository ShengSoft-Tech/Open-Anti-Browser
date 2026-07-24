# Phase 2: macOS 内核构建与发布 - Research

**Researched:** 2026-07-24
**Domain:** macOS release engineering (ditto packaging, code-signature/arch verification, GitHub Releases upload, Python config constants) — NOT Chromium build/compile engineering (that stays in `../fingerprint-chromium`)
**Confidence:** HIGH

## Summary

This phase is narrow by design: two shell/CLI concerns (verify-and-upload the kernel zips; backfill `backend/config.py` URLs) rather than any Chromium build work. Everything needed is already installed and verified working on this machine: `ditto`, `file`, `lipo`, `codesign`, `arch` (Rosetta 2 confirmed installed), and an authenticated `gh` CLI with `repo` scope pointed at `ShengSoft-Tech/Open-Anti-Browser`. The target release `kernel-149.0.7827.114` already exists and currently holds only the four Windows `-1.1`/`-1.2` assets — no macOS assets yet, confirming this phase's upload is additive, not a re-run.

The sibling repo's arm64 build (`../fingerprint-chromium/build/src/out/Default/Chromium.app`) is real, ad-hoc/linker-signed, and version-matches 149.0.7827.114 today — but it is the **pre-D-02** build (LOG(INFO) calibration line not yet stripped per the 07-01-SUMMARY hand-off note). No x64 build exists yet — `downloads-macos-x64.ini` is absent from the sibling repo and `build/src/out/Release/` contains only GN tooling, not a Chromium build. This confirms the cross-repo blocker recorded in STATE.md is still open as of this research date: **KERNEL-02 cannot be closed until the sibling repo produces the x64 zip**, and KERNEL-01's zip is not yet the final artifact this repo should upload (needs the D-02 rebuild first).

A critical, non-obvious technical detail this research surfaces: the Chromium `.app` bundle contains **two separate Mach-O binaries whose architecture must each be verified independently** — the thin launcher stub at `Contents/MacOS/Chromium` (52KB) and the actual compiled engine at `Contents/Frameworks/Chromium Framework.framework/Versions/149.0.7827.114/Chromium Framework` (the real payload, reached via a **real symlink** `Versions/Current -> 149.0.7827.114`). A verify script that only checks the top-level launcher and ignores the Framework binary — or that uses a plain `unzip`/`cp -R` instead of `ditto` and silently dereferences/breaks that symlink — can pass a shallow check while shipping a corrupted or wrong-architecture bundle.

**Primary recommendation:** Build one idempotent bash script (`scripts/release/verify_and_upload_macos_kernel.sh` or similar) that: (1) `ditto -x -k` extracts each input zip to a scratch dir (never plain `unzip`, to preserve the Framework symlink and PKZip-format extended attributes), (2) runs `file` + `lipo -archs` against BOTH `Contents/MacOS/Chromium` and the Framework binary and asserts the expected single architecture on each, (3) runs `codesign -dv` and asserts `adhoc,linker-signed` flags survived the round-trip, (4) for x64 only, launches the binary under `arch -x86_64` with a temp `--user-data-dir` and `--remote-debugging-port`, polls `http://127.0.0.1:<port>/json/version` for a valid CDP response with a generous Rosetta-cold-start timeout, then kills it, (5) uploads via `gh release upload kernel-149.0.7827.114 <zip> --clobber` for idempotency, and (6) separately, edit `backend/config.py` to add `_CHROME_KERNEL_BASE`-relative macOS arm64/x64 URL constants following the exact `CHROME_ENGINE_ZIP_URL` pattern already established for Windows, extending `tests/test_config_platform.py` with matching assertions.

## Architectural Responsibility Map

This phase has no browser/frontend/API/CDN/DB tiers in the usual web-app sense — it is release tooling + a config constants module. Mapped onto the project's actual architecture:

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Extract + verify ditto zips (file/lipo/codesign) | Release tooling (new `scripts/` script, this repo) | — | Pure CLI verification, no app runtime involved |
| Rosetta launch smoke test (x64) | Release tooling (same script) | — | One-off process spawn + CDP HTTP poll, not part of `browser_manager.py` runtime |
| Upload to kernel release | Release tooling (same script) | External: GitHub Releases (asset host, consumed later by CI + runtime installer) | `gh release upload` hits GitHub's API directly; this repo does not run its own CDN |
| macOS URL backfill | Backend config (`backend/config.py`) | Consumed by: CI (`build-release.yml`, future macOS job in Phase 5) + runtime installer download path | Single source of truth pattern already established for Windows (`CHROME_ENGINE_ZIP_URL`) |

## Package Legitimacy Audit

**Not applicable.** This phase installs zero new Python, npm, or other package-manager dependencies. All tooling used (`ditto`, `file`, `lipo`, `codesign`, `arch`, `gh`) is either a macOS system utility (`/usr/bin/*`) or the already-installed `gh` CLI (verified authenticated: `gh auth status` → logged in as `bfwg` with `repo` scope). No `npm install` / `pip install` / `cargo add` occurs in this phase's scope.

## Standard Stack

### Core (all pre-existing on the target machine — verified this session)

| Tool | Version/Path | Purpose | Why Standard |
|------|------|---------|---------------|
| `ditto` | `/usr/bin/ditto` (macOS built-in) | Create AND extract the kernel zips | Only tool that reliably preserves symlinks (Framework `Versions/Current`), resource forks, and extended attributes through a zip round-trip; `unzip`/`zip` can silently mangle bundle symlinks. Already locked in by D-06/KERNEL-01 as the packaging tool. [VERIFIED: local `ditto --help` this session] |
| `file` | `/usr/bin/file` (macOS built-in) | Architecture identification per binary | Standard, always available, output format stable (`Mach-O 64-bit executable arm64`) [VERIFIED: ran against sibling repo's actual build this session] |
| `lipo -archs` | `/usr/bin/lipo` (macOS built-in) | Confirms single-architecture thin binary (not accidentally fat/universal) | Standard Apple tool for architecture-slice inspection [VERIFIED: present at `/usr/bin/lipo`] |
| `codesign -dv` | `/usr/bin/codesign` (macOS built-in) | Confirms ad-hoc signature (`adhoc,linker-signed`) survived the ditto round-trip | Standard Apple signing tool; sibling repo's build shows `flags=0x20002(adhoc,linker-signed)` today [VERIFIED: ran `codesign -dv` against the actual `.app` this session] |
| `arch -x86_64` | `/usr/bin/arch` (macOS built-in) | Forces Rosetta 2 translation to run the x64 binary on this arm64 Mac | Standard Apple mechanism for explicit-architecture process launch; Rosetta 2 confirmed installed (`pkgutil --pkg-info com.apple.pkg.RosettaUpdateAuto` returns a valid record) [VERIFIED: ran this session, exit 0] |
| `gh release upload` | `gh` CLI, authenticated | Upload zip assets to the existing `kernel-149.0.7827.114` release | Already the established mechanism in this repo (canonical_refs D-05); `--clobber` flag makes re-uploads idempotent [VERIFIED: `gh release upload --help` this session confirms `--clobber` semantics] |
| `python3` (stdlib only) | repo's existing interpreter | Edit `backend/config.py` constants | No new dependency; follows exact existing `_CHROME_KERNEL_BASE`/`CHROME_ENGINE_ZIP_URL` pattern |

### Supporting

| Tool | Purpose | When to Use |
|------|---------|-------------|
| `curl` (or `curl.exe` pattern seen in `build-release.yml`) | Poll `http://127.0.0.1:<port>/json/version` for the Rosetta CDP smoke test | Confirms the process is not just alive but actually serving CDP — matches this repo's existing CDP-centric convention (`services/synchronizer.py` uses CDP WebSocket for Chrome) |
| `xattr -p com.apple.quarantine` | Diagnostic check on downloaded zips | Not required for THIS phase (quarantine is set by browser/Finder downloads, not by `gh`/`curl` fetches) — but useful if debugging a "why won't this launch" report later |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `ditto -x -k` for extraction | `unzip` | `unzip` does not reliably preserve the `Versions/Current -> 149.0.7827.114` symlink inside `Chromium Framework.framework`; risks dereferencing it into a duplicate real directory, breaking the bundle and silently passing a naive top-level-only architecture check |
| `gh release upload --clobber` | Manual `gh api` delete-then-upload | `gh release upload --clobber` is a single atomic-enough CLI call already documented by `gh` itself; manual delete+upload is more failure-prone (partial-delete leaves a broken release) — `gh` docs even warn `--clobber` deletes-then-uploads, so a script should treat upload failure as needing a retry, not assume the original is safe |
| CDP `/json/version` poll for smoke test | Just check process didn't exit within N seconds | Process-alive-only is a much weaker signal (a hung/crashed-but-zombie process could pass); CDP response proves the browser actually initialized far enough to serve its debug protocol — matches KERNEL-03's "启动冒烟测试" intent and this repo's existing CDP-based session-tracking convention in `browser_manager.py` |

**Installation:** None required — all tools are already present on the target machine.

**Version verification:** Not applicable (system tools + already-authenticated `gh`, no package versions to pin).

## Architecture Patterns

### System Architecture Diagram

```
../fingerprint-chromium (sibling repo, out of scope)
  │
  │  produces (arm64 today; x64 blocked on downloads-macos-x64.ini)
  ▼
ditto-packaged zip(s) on local disk
  (ungoogled-chromium_149.0.7827.114-1.3_macos_{arm64,x64}.zip)
  │
  ▼
[THIS REPO] scripts/release/verify_and_upload_macos_kernel.sh <zip> <arch>
  │
  ├─► 1. ditto -x -k  → scratch extraction dir
  │        │
  │        ▼
  ├─► 2. file + lipo -archs on:
  │        - Contents/MacOS/Chromium (launcher stub)
  │        - Contents/Frameworks/Chromium Framework.framework/Versions/Current/Chromium Framework (real symlink target)
  │        assert single arch == expected arch, FAIL otherwise
  │        │
  │        ▼
  ├─► 3. codesign -dv --verbose  → assert "adhoc,linker-signed" flags intact
  │        │
  │        ▼
  ├─► 4. [x64 only] arch -x86_64 Contents/MacOS/Chromium \
  │        --user-data-dir=<tmp> --remote-debugging-port=<port> &
  │        curl --retry (generous timeout, Rosetta cold-start) http://127.0.0.1:<port>/json/version
  │        assert JSON contains "Browser": "Chrome/149.0.7827.114"
  │        kill process, assert no zombie
  │        │
  │        ▼
  └─► 5. gh release upload kernel-149.0.7827.114 <zip> --clobber
           │
           ▼
       GitHub Release asset (public download URL)
           │
           ▼
[THIS REPO] backend/config.py — macOS arm64/x64 URL constants
  (mirrors existing _CHROME_KERNEL_BASE + CHROME_ENGINE_ZIP_URL pattern)
           │
           ├─► consumed by: Phase 5 CI macOS job (future, downloads kernel into .app bundle)
           └─► consumed by: runtime installer download path (future macOS install flow)
```

### Recommended Project Structure

```
scripts/
└── release/
    └── verify_and_upload_macos_kernel.sh   # D-10/D-11: verify + upload,入仓
backend/
└── config.py                                # macOS arm64/x64 URL constants added near line 117-119
tests/
└── test_config_platform.py                  # extend with macOS URL assertions
```

**Note on D-11's gitignore distinction:** CLAUDE.md's "打包脚本已 gitignore" convention (`build_installer.ps1`, dmg scripts) refers specifically to **application installer packaging** scripts. This new script is a **kernel release publishing tool** — a different category per D-11 — and should be committed normally. Do not add it to `.gitignore`.

### Pattern 1: ditto round-trip preserves symlinks and signatures
**What:** Always pair `ditto -c -k --keepParent --sequesterRsrc src dst.zip` (creation, done in sibling repo) with `ditto -x -k src.zip dst_dir` (extraction, done here) — never mix with `zip`/`unzip`.
**When to use:** Any time a `.app` bundle containing Framework symlinks needs to move through a zip.
**Example:**
```bash
# Source: verified this session against ../fingerprint-chromium's actual build —
# Contents/Frameworks/Chromium Framework.framework/Versions/Current is a REAL symlink
# (lrwxr-xr-x ... Current -> 149.0.7827.114), confirmed via `ls -la` and `file`.
extract_dir="$(mktemp -d)"
ditto -x -k "$zip_path" "$extract_dir"
app_path="$(find "$extract_dir" -maxdepth 1 -name '*.app')"
```

### Pattern 2: Verify architecture on BOTH the launcher stub and the Framework binary
**What:** `file`/`lipo -archs` against only `Contents/MacOS/Chromium` is insufficient — that binary is a 52KB thin launcher stub. The actual compiled Chromium engine lives in the Framework bundle, reached through the `Versions/Current` symlink.
**When to use:** Every architecture-verification step in this phase (KERNEL-03).
**Example:**
```bash
# Source: verified this session —
# file .../Contents/MacOS/Chromium            -> "Mach-O 64-bit executable arm64"
# file .../Frameworks/.../Versions/Current/Chromium Framework -> "Mach-O 64-bit dynamically linked shared library arm64"
app="$1"; expected_arch="$2"   # e.g. arm64 or x86_64
launcher="$app/Contents/MacOS/Chromium"
fw_dir="$app/Contents/Frameworks/Chromium Framework.framework/Versions/Current"
framework_bin="$fw_dir/Chromium Framework"

for bin in "$launcher" "$framework_bin"; do
  arch_found="$(lipo -archs "$bin")"
  if [[ "$arch_found" != "$expected_arch" ]]; then
    echo "ARCH MISMATCH: $bin is [$arch_found], expected [$expected_arch]" >&2
    exit 1
  fi
done
```

### Pattern 3: Idempotent asset upload
**What:** `gh release upload <tag> <file> --clobber` deletes any existing same-named asset before re-uploading, making the script safely re-runnable (D-10's explicit requirement).
**When to use:** Every `gh release upload` call in the script.
**Example:**
```bash
# Source: gh release upload --help, verified this session
gh release upload kernel-149.0.7827.114 \
  "ungoogled-chromium_149.0.7827.114-1.3_macos_${arch_label}.zip" \
  --clobber \
  --repo ShengSoft-Tech/Open-Anti-Browser
```

### Pattern 4: CDP-based Rosetta smoke test with cold-start-aware timeout
**What:** Launch the x64 binary under `arch -x86_64`, then poll the CDP HTTP endpoint rather than merely checking the process didn't exit.
**When to use:** KERNEL-03's x64 smoke test (D-04: Rosetta is acceptable, real Intel hardware deferred to Phase 6).
**Example:**
```bash
# Source: pattern matches this repo's existing CDP convention (services/synchronizer.py CdpPageClient);
# --remote-debugging-port + /json/version is the standard Chromium CDP handshake endpoint.
port=9333
tmp_profile="$(mktemp -d)"
arch -x86_64 "$launcher" \
  --user-data-dir="$tmp_profile" \
  --remote-debugging-port="$port" \
  --headless=new --no-first-run &
pid=$!
# Rosetta first-run AOT translation on a large Chromium binary can take noticeably
# longer than a native launch — use a generous retry budget, not a short fixed sleep.
for i in $(seq 1 30); do
  if curl -s -f "http://127.0.0.1:${port}/json/version" | grep -q "149.0.7827.114"; then
    echo "CDP smoke test PASS"; break
  fi
  sleep 2
done
kill "$pid" 2>/dev/null; wait "$pid" 2>/dev/null
```

### Pattern 5: config.py macOS URL backfill mirrors the Windows pattern exactly
**What:** Add macOS arm64/x64 constants next to the existing `_CHROME_KERNEL_BASE`/`CHROME_ENGINE_ZIP_URL` block, following identical naming conventions, so future CI/installer code reads them the same way.
**When to use:** After both zips are verified and uploaded.
**Example:**
```python
# Source: pattern extends backend/config.py:110-119 (read this session)
CHROME_ENGINE_ZIP_URL_MACOS_ARM64 = (
    f"{_CHROME_KERNEL_BASE}/ungoogled-chromium_149.0.7827.114-1.3_macos_arm64.zip"
)
CHROME_ENGINE_ZIP_URL_MACOS_X64 = (
    f"{_CHROME_KERNEL_BASE}/ungoogled-chromium_149.0.7827.114-1.3_macos_x64.zip"
)
```
(Exact platform-branch structure — e.g. whether this becomes a single `CHROME_ENGINE_ZIP_URL` that resolves per-platform-and-arch, vs. separate named constants consumed later by Phase 5's CI — is Claude's Discretion per CONTEXT.md; the planner should pick whichever reads most naturally alongside the existing Windows constant given Phase 5 isn't planned yet.)

### Anti-Patterns to Avoid
- **Using `unzip` anywhere in this pipeline:** breaks Framework symlinks and can corrupt the ad-hoc signature's expected resource layout. Always `ditto`.
- **Checking only `Contents/MacOS/Chromium`'s architecture:** misses a mismatched Framework binary, which is where 99% of the compiled code (and thus the actual fingerprinting patches) lives.
- **Treating this phase's `codesign -dv` check as the PKG-03 hard gate:** Phase 5's `codesign --verify --deep --strict` (full CI re-sign gate) is a stricter, later-phase concern on the FINAL packaged `.app`. This phase's check is a lighter sanity check that the ad-hoc signature survived the ditto zip round-trip intact — do not conflate the two or over-engineer this phase's check to Phase 5's rigor.
- **Hardcoding the kernel revision/version anywhere except `backend/config.py`:** matches the existing single-source-of-truth convention already enforced for Windows (`build-release.yml:62` reads it from `backend.config`, not from a hardcoded string).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Symlink/resource-fork-safe zip extraction | Custom Python zipfile symlink-restoration logic | `ditto -x -k` | Apple's own tool handles PKZip-format extended attributes and symlinks correctly; reimplementing this in Python's `zipfile` module requires manually restoring `st_mode` symlink bits from the zip's external attributes — error-prone and unnecessary when `ditto` exists |
| Idempotent GitHub release asset upload | Manual `gh api` calls to list/delete/upload assets | `gh release upload --clobber` | `gh` CLI already implements exactly this delete-then-upload sequence atomically enough for this use case; hand-rolling it duplicates already-tested logic for no benefit |
| Process-liveness + protocol-readiness check | Fixed `sleep N` then assume success | CDP `/json/version` HTTP poll with retry loop | A fixed sleep either wastes time (native-speed case) or false-fails (Rosetta cold-start case, D-04); a poll-with-timeout is standard and self-adjusting |

**Key insight:** Every piece of this phase already has a first-party Apple or GitHub CLI tool that does exactly the needed job — the risk in this phase is not "which library" but "using the wrong flag on the right tool" (e.g., `unzip` instead of `ditto`, missing `--clobber`, checking the wrong binary inside the bundle).

## Common Pitfalls

### Pitfall 1: Verifying only the launcher stub, missing the Framework binary
**What goes wrong:** A script checks `file Contents/MacOS/Chromium`, sees the correct architecture, and reports PASS — while the Framework binary (the actual ~99% of compiled code, containing the entropy-gate fingerprint patches) is the wrong architecture or corrupted.
**Why it happens:** The launcher stub is the obvious, top-level, easy-to-find binary; the Framework binary is nested three directories deep behind a symlink (`Versions/Current`).
**How to avoid:** Always verify both `Contents/MacOS/Chromium` AND `Contents/Frameworks/Chromium Framework.framework/Versions/Current/Chromium Framework`.
**Warning signs:** A "PASS" verify result that only ever printed one `file`/`lipo` line, not two.

### Pitfall 2: Extracting with `unzip` breaks the Framework symlink
**What goes wrong:** `unzip` (or a naive `zipfile.extractall()`/`cp -R` after some other extraction) can dereference `Versions/Current -> 149.0.7827.114` into a duplicated real directory, or drop the symlink's target reference entirely, corrupting the bundle so it fails to launch.
**Why it happens:** Not all zip formats/extractors handle symlink entries identically; `ditto`'s PKZip format used to CREATE the zip is specifically chosen (D-06) because it round-trips correctly with `ditto` on extraction — mixing extractors breaks that guarantee.
**How to avoid:** Extraction must always use `ditto -x -k`, matching the `ditto -c -k` used to create it.
**Warning signs:** `Versions/Current` shows up as a real directory (not `lrwxr-xr-x`) after extraction, or the app fails to launch with a "file not found" for the Framework binary.

### Pitfall 3: `gh release upload` fails non-idempotently without `--clobber`
**What goes wrong:** Re-running the script (e.g., after fixing a bug, or for a future revision bump) fails with a 422/"asset already exists" error instead of replacing the asset.
**Why it happens:** `gh release upload`'s default behavior is upload-only, no overwrite — by design, to prevent accidental clobbering.
**How to avoid:** Always pass `--clobber` in this script's context (D-10 explicitly wants a repeatable, re-runnable script) — but be aware `gh`'s own docs warn: "If the upload fails, the original assets will be lost" (delete happens before re-upload), so the script should treat any upload failure as needing investigation/retry, not assume the previous asset is still safe.
**Warning signs:** Script exits non-zero on a second run with no code changes; or (worse) a failed re-upload leaves the release with a missing asset.

### Pitfall 4: Rosetta cold-start false-negative on smoke test
**What goes wrong:** The x64 binary under `arch -x86_64` takes noticeably longer to start on first launch (Rosetta ahead-of-time translation of a large Chromium binary) than a fixed short timeout allows, causing the smoke test to report FAIL on a kernel that actually works.
**Why it happens:** Rosetta 2 performs AOT translation and caches it; the very first launch of a multi-hundred-MB binary is the slowest case.
**How to avoid:** Use a retry-poll loop with a generous total budget (e.g., 60s+) rather than a single short `sleep` + check, per Pattern 4 above.
**Warning signs:** Smoke test intermittently fails on first run of a session but passes on retry of the identical binary.

### Pitfall 5: Conflating this phase's signature check with Phase 5's hard gate
**What goes wrong:** Over-engineering this phase's `codesign` check to match Phase 5's `codesign --verify --deep --strict` CI gate (PKG-03), which applies to the FINAL re-signed application bundle, not the standalone kernel zip.
**Why it happens:** Both phases use `codesign`, inviting confusion about which check belongs where.
**How to avoid:** This phase only needs to confirm the ad-hoc signature survived the ditto round-trip (`codesign -dv` reports `adhoc,linker-signed`, matching the pre-zip state) — not a strict `--deep --strict` verify, which may behave differently on a standalone kernel `.app` not yet embedded/re-signed inside the final Open-Anti-Browser `.app`.
**Warning signs:** Verify script fails on `--deep --strict` checks that have nothing to do with this phase's actual acceptance criteria (KERNEL-03 only requires file/lipo arch match + smoke test, not a strict codesign gate).

### Pitfall 6: The 021 LOG(INFO) calibration line is a cross-repo handoff risk
**What goes wrong:** If the sibling repo's D-02 (removing/DLOG-guarding the `LOG(INFO)` calibration diagnostic) is not actually done before the zip handed to this repo is produced, the shipped kernel will spam per-frame canvas calibration info to stderr for every user running with any logging enabled — a quality/perf regression, not a fingerprinting regression.
**Why it happens:** This is entirely a sibling-repo build step (D-02); this repo's verify script has no automated way to detect it purely from the zip contents (the log line only fires at runtime under `--enable-logging=stderr`, and only on the gate-skip code path).
**How to avoid:** Treat this as a manual handoff checklist item, not something the automated verify script enforces: before running the verify+upload script, confirm with the sibling repo that D-02's rebuild has landed (e.g., checking `../fingerprint-chromium`'s git log / `07-01-SUMMARY.md`'s "Phase-8 hand-off" note, or simply re-running the smoke test with `--enable-logging=stderr` and confirming no `entropy gate skipped noise` LOG line appears on a low-entropy canvas draw).
**Warning signs:** Verbose per-frame log output when a user runs the app with logging enabled — sibling-repo's own smoke test harness (`regression-cdp.js --mode calibrate`) is the authoritative way to check for this, not something this repo's zip-verification script should attempt to replicate.

## Code Examples

Verified patterns from this session's direct inspection of the actual build artifact and CLI tools (no official docs URL applicable — these are macOS system tool behaviors confirmed by running them):

### Confirm current release state before uploading (avoid accidental duplicate)
```bash
# Source: ran this session — gh release view kernel-149.0.7827.114 --json assets
gh release view kernel-149.0.7827.114 --json assets --jq '.assets[].name'
# Currently returns only 4 Windows assets (-1.1 and -1.2 installer+zip) — no macOS
# assets exist yet, confirming this phase's upload is purely additive.
```

### Full architecture + signature verification snippet
```bash
# Source: verified against ../fingerprint-chromium/build/src/out/Default/Chromium.app this session
app="$1"           # path to extracted .app
expected_arch="$2" # "arm64" or "x86_64"

launcher="$app/Contents/MacOS/Chromium"
framework="$app/Contents/Frameworks/Chromium Framework.framework/Versions/Current/Chromium Framework"

for bin in "$launcher" "$framework"; do
  [[ -f "$bin" ]] || { echo "MISSING: $bin" >&2; exit 1; }
  got="$(lipo -archs "$bin" 2>&1)"
  [[ "$got" == "$expected_arch" ]] || { echo "ARCH FAIL: $bin -> $got (want $expected_arch)" >&2; exit 1; }
done

codesign -dv "$app" 2>&1 | grep -q 'flags=0x20002(adhoc,linker-signed)' \
  || { echo "SIGNATURE FAIL: expected adhoc,linker-signed" >&2; exit 1; }

echo "Verified OK: $app ($expected_arch, adhoc-signed)"
```

## State of the Art

| Old Approach (this repo, Windows-only) | Current Approach (this phase, macOS) | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Single-platform, single-arch `CHROME_ENGINE_ZIP_URL` in `backend/config.py` | Platform+arch-aware macOS constants added alongside, following identical naming/URL-construction pattern | This phase | CI and installer code gain a stable place to read macOS URLs from without hardcoding; sets the precedent Phase 5's CI macOS job will consume |
| No macOS kernel release assets exist | Two new ditto zips (`-macos_arm64`, `-macos_x64`) added to the existing `kernel-149.0.7827.114` release | This phase | First macOS-capable kernel assets in the project; unblocks Phase 3 (needs at least one local kernel for launch integration) |

**Deprecated/outdated:** None — this is greenfield macOS tooling, nothing being replaced.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The exact macOS `Contents/Frameworks/Chromium Framework.framework/Versions/Current` symlink structure observed in the CURRENT arm64 build will be identical in the future D-02-rebuilt zip and the not-yet-built x64 zip | Architecture Patterns, Pitfalls 1-2 | Low — this is standard Chromium `.app` bundle layout (Apple-mandated `Framework.framework/Versions/` convention), extremely unlikely to change between an incremental rebuild or a cross-compiled arch of the same Chromium version. [Confidence: HIGH — verified directly against the actual build this session, and this layout is Chromium/macOS-standard across versions] |
| A2 | CDP `/json/version` HTTP polling is an acceptable "启动冒烟测试" per D-04's "能拉起进程 / 能响应 CDP 端口等" discretion language | Pattern 4, Standard Stack | Low — CONTEXT.md explicitly lists "能响应 CDP 端口" as one of two acceptable granularities; this is directly supported by the user's own words, not an external assumption |
| A3 | The `--headless=new` flag works identically on this fingerprint-patched Chromium build as on stock Chromium 149 (used in the Rosetta smoke test example) | Pattern 4 | Medium — if the fingerprint patches alter headless-mode behavior in any way, the smoke test flags may need adjustment; the planner/executor should confirm this against the sibling repo's actual launch flags (`services/chrome.py` in THIS repo already has the canonical flag set used for real launches and should be consulted/reused rather than inventing new flags) |

## Open Questions (RESOLVED)

*All three open questions had recommendations the Phase 2 plans act on; each is closed by a specific plan/task below (resolved 2026-07-24 during plan-phase).*

1. **Has the sibling repo's D-02 rebuild (removing the LOG(INFO) calibration line) landed yet?**
   - What we know: 07-01-SUMMARY.md explicitly flags this as a "Phase-8 hand-off: must be removed or DLOG-guarded before Windows packaging" — and CONTEXT.md's D-02 says the same applies to the Mac zip this repo will receive.
   - What's unclear: This research found the CURRENT arm64 build (`Framework` binary mtime 2026-07-22) predates any visible confirmation that the diagnostic-removal rebuild has run. The zip handed to this repo for upload needs to be the POST-D-02 rebuild, not today's build.
   - Recommendation: Planner should make the first task a check/checkpoint: confirm with the sibling repo (or re-run the calibration diagnostic check) that the LOG(INFO) line is gone/guarded BEFORE running the verify+upload script against the "final" arm64 zip — do not assume today's `build/src/out/Default/Chromium.app` is already the artifact to upload.
   - **Resolved:** 02-03 Task 1 is a `checkpoint:human-verify` (gate=blocking) that confirms the sibling repo's post-D-02 rebuild landed (LOG(INFO) removed/DLOG-guarded) and captures the final arm64 zip path before 02-03 Task 2 uploads. The dry-run tracer (02-01 Task 1) runs against today's pre-D-02 build only to exercise script logic, never as the upload target.

2. **Has the x64 cross-compile happened yet?**
   - What we know: `downloads-macos-x64.ini` does not exist in `../fingerprint-chromium` as of this research (confirmed via `find`); `build/src/out/Release/` contains only GN tooling, no Chromium build.
   - What's unclear: Timeline for the sibling repo's cross-compile completion is outside this repo's control (STATE.md blocker).
   - Recommendation: Planner should structure the plan so the arm64 upload+config-backfill work (KERNEL-01, half of KERNEL-03) can proceed and be verified independently of x64 readiness, with the x64 leg (KERNEL-02, other half of KERNEL-03) either gated behind a `checkpoint:human-verify` / blocked-task marker, or split into a separate plan/wave that starts once the sibling repo signals the x64 zip is ready. Do not block the entire phase on x64 if arm64 can ship first.
   - **Resolved:** arm64 (02-03) and x64 (02-04) are split into separate wave-2 plans, each `autonomous: false` with its own blocking handoff checkpoint. arm64 ships and is verified independently; x64 stays blocked on the sibling repo's cross-compile without blocking arm64.

3. **Exact naming/structure of the macOS URL constants in `config.py`**
   - What we know: CONTEXT.md explicitly marks "config.py 里 macOS URL 的平台分支写法...常量命名" as Claude's Discretion.
   - What's unclear: Whether Phase 5's CI (not yet planned) will want a single dynamic `CHROME_ENGINE_ZIP_URL` that resolves per-`platform.machine()`, or explicit separate constants (`CHROME_ENGINE_ZIP_URL_MACOS_ARM64` / `_X64`) that a future CI matrix job selects by job name.
   - Recommendation: Favor explicit separate named constants (as shown in Pattern 5) — simpler to reason about, no runtime branching logic needed in `config.py` itself, and trivially greppable/testable. The planner can revise this when Phase 5 is actually planned if a different shape turns out to be more ergonomic for the CI matrix.
   - **Resolved:** 02-02 Task 1 adds explicit module-level `CHROME_ENGINE_ZIP_URL_MACOS_ARM64` / `CHROME_ENGINE_ZIP_URL_MACOS_X64` constants (no `platform.machine()` runtime branch), covered by 02-02 Task 2's `test_macos_arm64_kernel_url` / `test_macos_x64_kernel_url`.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `ditto` | zip create/extract (D-06, verify script) | ✓ | macOS built-in | — |
| `file` | arch identification | ✓ | macOS built-in | — |
| `lipo` | arch identification (`-archs`) | ✓ | `/usr/bin/lipo` | — |
| `codesign` | signature sanity check | ✓ | `/usr/bin/codesign` | — |
| `arch` (Rosetta 2) | x64 smoke test on this arm64 Mac (D-04) | ✓ | Rosetta 2 installed (`com.apple.pkg.RosettaUpdateAuto` present) | Intel-native smoke test deferred to Phase 6 per D-04 if Rosetta were ever unavailable |
| `gh` CLI | release upload | ✓ | authenticated as `bfwg`, `repo` scope, targets `ShengSoft-Tech/Open-Anti-Browser` | — |
| `curl` | CDP `/json/version` poll | ✓ | macOS built-in | — |
| Sibling repo arm64 zip (D-02-rebuilt, post LOG(INFO) removal) | KERNEL-01 upload | ✗ (pre-D-02 build exists; post-D-02 rebuild not yet confirmed) | — | See Open Question 1 — block the upload step, not the whole phase, on this |
| Sibling repo x64 zip | KERNEL-02 upload | ✗ (downloads-macos-x64.ini not yet created; no x64 build tree exists) | — | See Open Question 2 — structure plan so arm64 can ship independently |

**Missing dependencies with no fallback:**
- The actual kernel zips (post-D-02 arm64, and x64) — these are cross-repo build outputs this repo cannot produce itself. The verify+upload SCRIPT can be built and tested (e.g. self-tested against the current arm64 build for the file/lipo/codesign logic, even if it's not the final upload target) even while blocked on the final artifacts.

**Missing dependencies with fallback:**
- None — the tooling fallbacks (Intel-native smoke test) are already deferred to Phase 6 by explicit user decision (D-04), not something this phase needs to work around.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Python `unittest` (existing repo convention, no pytest config) |
| Config file | none — `python -m unittest discover -s tests -v` |
| Quick run command | `python -m unittest tests.test_config_platform -v` |
| Full suite command | `python -m unittest discover -s tests -v` |

**Important scoping note:** Only the `backend/config.py` URL-backfill portion of this phase is meaningfully unit-testable in this repo's existing `unittest` convention (mirroring `tests/test_config_platform.py`'s `importlib.reload(config)` + `patch.object(sys, "platform", ...)` pattern). The shell script's `ditto`/`lipo`/`codesign`/`gh`/Rosetta-launch logic operates on real binaries and a live GitHub release — this is **not** practically unit-testable without either (a) shipping fixture `.app` bundles into the test suite (heavyweight, and the whole point is testing against the REAL sibling-repo artifact) or (b) mocking every `subprocess.run` call (low signal — would just test that the script calls the right CLI args, not that the actual verification logic is correct). Treat the script's correctness as **manually verified via a `--dry-run`/self-test invocation against the already-available arm64 build**, gated by a `checkpoint:human-verify` task before the real upload runs, rather than forcing it into the automated unit-test suite.

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| KERNEL-01 | macOS arm64 URL constant present, correctly formed, follows `_CHROME_KERNEL_BASE` pattern | unit | `python -m unittest tests.test_config_platform.ConfigPlatformTests.test_macos_arm64_kernel_url -v` | ❌ Wave 0 — new test method to add |
| KERNEL-02 | macOS x64 URL constant present, correctly formed | unit | `python -m unittest tests.test_config_platform.ConfigPlatformTests.test_macos_x64_kernel_url -v` | ❌ Wave 0 — new test method to add |
| KERNEL-03 (arch verify) | file/lipo arch match logic in the verify script | manual / script self-test | `bash scripts/release/verify_and_upload_macos_kernel.sh --dry-run --arch arm64 ../fingerprint-chromium/build/src/out/Default/Chromium.app` (self-test against currently-available build; not a `unittest`) | ❌ Wave 0 — script + a `--dry-run`/verify-only mode need to be written |
| KERNEL-03 (smoke test) | Rosetta CDP launch smoke test | manual / e2e, human-gated | run script's smoke-test function standalone once an x64 build exists; `checkpoint:human-verify` before real upload | ❌ Blocked on sibling repo x64 build (Open Question 2) |
| KERNEL-01/02 (upload) | `gh release upload --clobber` idempotency | manual verification via `gh release view --json assets` before/after | not automatable as a `unittest` (hits live GitHub API) | ❌ Wave 0 — treat as a `checkpoint:human-verify` gate, not a unit test |

### Sampling Rate
- **Per task commit:** `python -m unittest tests.test_config_platform -v` (fast, config.py changes only)
- **Per wave merge:** `python -m unittest discover -s tests -v` (full suite, confirm zero regression on the other 71 existing tests)
- **Phase gate:** Full suite green before `/gsd-verify-work`; PLUS a human-gated checkpoint confirming the actual upload (`gh release view kernel-149.0.7827.114 --json assets`) shows the two new macOS assets with correct names, since that part is inherently outside `unittest`'s reach.

### Wave 0 Gaps
- [ ] `tests/test_config_platform.py` — add `test_macos_arm64_kernel_url` / `test_macos_x64_kernel_url` (or equivalent) covering KERNEL-01/KERNEL-02's config.py constants
- [ ] `scripts/release/verify_and_upload_macos_kernel.sh` — does not exist yet; needs to be authored with a `--dry-run`/self-test mode so its file/lipo/codesign logic can be manually exercised against the currently-available arm64 build even before the D-02 rebuild / x64 build land
- [ ] No new test framework install needed — `unittest` already covers everything this phase can automate

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | N/A — this phase touches no user-facing auth |
| V3 Session Management | No | N/A |
| V4 Access Control | No | N/A — `gh` CLI's existing token scope (`repo`) already gates who can upload; no new access-control surface introduced |
| V5 Input Validation | Yes (narrow) | Verify script must validate its own CLI args (zip path exists, `--arch` is one of `arm64`/`x86_64`) before running `ditto`/`gh` — standard shell-script defensive argument checking (`set -euo pipefail` + explicit `[[ -f "$1" ]] || exit 1` style checks), not a library concern |
| V6 Cryptography | No (adjacent) | This phase does not implement any cryptography itself — `codesign`'s ad-hoc signature is a pre-existing artifact property being *verified*, not generated, by this phase's script. No custom crypto to hand-roll or review here. |

### Known Threat Patterns for this phase's stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Uploading a wrong-architecture or corrupted zip to a public release, silently shipped to end users | Tampering (unintentional, via broken verification rather than malicious) | The file/lipo dual-binary check (Pattern 2) + `--clobber` idempotent re-upload IS the mitigation — a bad upload can be caught and corrected by re-running the same script once the bug is found, without a manual delete-first dance |
| `gh` CLI token/credential exposure in a committed script | Information Disclosure | Script must NEVER embed a token; rely on the already-authenticated `gh auth login` session (as this session already has) — do not add `GH_TOKEN=...` literals to the script or to any committed file |
| Malicious/tampered zip substituted between sibling-repo build and this repo's upload (supply-chain risk, since it's a manual cross-repo local-disk handoff, not a signed channel) | Tampering / Spoofing | Out of scope for this phase per D-03/D-05 (that trust boundary is accepted as-is — both repos are controlled by the same developer on the same local machine); worth noting as a residual risk if the project ever grows to multiple contributors, but not something KERNEL-01/02/03 asks this phase to solve |

## Project Constraints (from CLAUDE.md)

- **Commit messages in English, short sentences** (e.g. `Fix Firefox geo timezone resolution` style) — applies to any commits this phase's tasks produce.
- **API error messages / user-visible text in Chinese** — not directly applicable (this phase has no user-facing UI text), but any comments the script/config.py changes add should follow the repo's existing bilingual convention (Chinese comments for rationale, as seen in `config.py`'s existing macOS block).
- **`backend/config.py` is the single source of truth for all path/URL constants** — "所有路径常量从这里导入,不要在别处拼路径" — the macOS URL backfill MUST go into `config.py`, not hardcoded elsewhere (e.g., not inline in a future CI workflow file).
- **打包脚本 gitignore 约定** — `build_installer.ps1`-style APPLICATION installer scripts are gitignored; per CONTEXT.md D-11 this new KERNEL RELEASE script is a different category and should be committed, not gitignored. Executor must not accidentally add it to `.gitignore` by pattern-matching the existing convention too broadly.
- **`backend/_g.py` integrity check** — this phase does not touch `frontend/src/lib/openSourceNotice.js` or `frontend/src/App.vue`, so no hash updates needed; confirmed via CONTEXT.md canonical_refs ("本 phase 不碰...无哈希更新需求").
- **Version numbers live in two places (`frontend/package.json` + `backend/main.py`)** — not applicable to this phase (no version bump), but if any future task in this phase accidentally touches versioning, both must be updated together.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| KERNEL-01 | macOS arm64 指纹内核可从 kernel release 下载(ditto 打包保留符号链接,含 ad-hoc 签名) | Pattern 1/2/5, Code Examples, Pitfall 1/2 — verify script + config.py URL backfill; NOTE: current arm64 build is pre-D-02, see Open Question 1 |
| KERNEL-02 | macOS Intel x64 指纹内核可从 kernel release 下载(先在兄弟项目补 downloads-macos-x64.ini,arm64 Mac 交叉编译) | Environment Availability confirms x64 build does not exist yet (blocker, out of this repo's control per D-03); this repo's responsibility is limited to verify+upload+config.py once the sibling repo delivers the zip (Open Question 2) |
| KERNEL-03 | 内核资产上传前通过架构验证(file/lipo)与本机启动冒烟测试,文件名含明确架构标识 | Pattern 2 (dual-binary arch check), Pattern 4 (CDP smoke test via Rosetta for x64), Pitfall 1/4, Validation Architecture (script self-test + human-gated checkpoint since not unittest-automatable) |
</phase_requirements>

## Sources

### Primary (HIGH confidence)
- Direct filesystem/CLI inspection this session: `../fingerprint-chromium/build/src/out/Default/Chromium.app` (file, lipo, codesign, ls -la on Framework symlink), `backend/config.py` (full read), `.github/workflows/build-release.yml` (full read), `tests/test_config_platform.py` (full read), `gh release view kernel-149.0.7827.114 --json assets` (live release state), `gh auth status`, `gh release upload --help`, tool presence checks (`which ditto file lipo codesign arch`), Rosetta install check (`pkgutil --pkg-info com.apple.pkg.RosettaUpdateAuto`, `arch -x86_64 /usr/bin/true`)
- `.planning/phases/02-macos/02-CONTEXT.md` — user-locked decisions D-01 through D-11
- `../fingerprint-chromium/.planning/phases/07-021-mac-oab/07-01-SUMMARY.md` and `07-02-SUMMARY.md` — full read, confirms D-01/D-02 provenance (021 patch, LOG(INFO) hand-off note, kMaxDistinctColors=32 lock)

### Secondary (MEDIUM confidence)
- None — this phase's research relied entirely on direct verification against the actual local environment and repos rather than external web sources, since the domain is macOS system tooling behavior (stable, well-documented Apple tools) rather than a fast-moving library ecosystem.

### Tertiary (LOW confidence)
- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — every tool verified present and working on this exact machine this session, no version-drift risk since these are macOS system utilities
- Architecture: HIGH — the Framework symlink structure and dual-binary verification need were discovered by direct inspection of the actual sibling-repo build artifact, not assumed
- Pitfalls: HIGH — every pitfall (except #6, the cross-repo LOG(INFO) handoff, which is inherently a coordination risk rather than a technical one) is grounded in something directly observed this session (the real symlink, the real ad-hoc signature flags, the real `gh` CLI `--clobber` semantics)

**Research date:** 2026-07-24
**Valid until:** Stable for ~90 days — this phase depends on macOS system tools (`ditto`/`lipo`/`file`/`codesign`) that change on OS-release timescales, not package-ecosystem timescales. The one time-sensitive element is the cross-repo blocker status (Open Questions 1-2), which should be re-checked at plan/execute time rather than trusted from this research snapshot.

---
*Phase: 2-macOS 内核构建与发布*
*Research completed: 2026-07-24*
