# Phase 2: macOS 内核构建与发布 - Pattern Map

**Mapped:** 2026-07-24
**Files analyzed:** 3
**Analogs found:** 3 / 3 (2 exact-file edits + 1 new-file pattern-composite)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|-----------------|---------------|
| `backend/config.py` (add macOS arm64/x64 kernel URL constants) | config | request-response (constant lookup, consumed by CI/installer) | `backend/config.py:105-124` (existing `_CHROME_KERNEL_BASE`/`CHROME_ENGINE_ZIP_URL` block, same file) | exact |
| `tests/test_config_platform.py` (add macOS URL assertions) | test | transform (reload+assert) | `tests/test_config_platform.py` (same file, existing darwin-branch test methods) | exact |
| `scripts/release/verify_and_upload_macos_kernel.sh` (new) | utility (release tooling script) | file-I/O + batch (extract → verify → upload) | No existing shell script in repo; closest structural analog is `.github/workflows/build-release.yml`'s "Prepare browser engines" PowerShell step (fetch → extract → verify → place) | role-match (cross-language, no direct shell analog exists) |

## Pattern Assignments

### `backend/config.py` (config, request-response)

**Analog:** same file, existing block at lines 105-124 (Windows Chrome kernel URL constants — this is literally the pattern to extend, not a different file).

**Existing pattern to copy** (`backend/config.py:105-124`):
```python
# Chrome kernel engine assets. Single source of truth for BOTH the runtime installer
# download AND the CI engine-bundle fetch — .github/workflows/build-release.yml reads
# CHROME_ENGINE_ZIP_URL from here instead of hardcoding a kernel URL. The -1.2 revision
# adds patch 020 (speech-synthesis Google voices / browser_name "Chrome" fix); assets
# live on the kernel-149.0.7827.114 release.
_CHROME_KERNEL_BASE = (
    "https://github.com/ShengSoft-Tech/Open-Anti-Browser/releases/download/"
    "kernel-149.0.7827.114"
)
CHROME_INSTALLER_URL = (
    f"{_CHROME_KERNEL_BASE}/ungoogled-chromium_149.0.7827.114-1.2_installer_x64.exe"
)
CHROME_ENGINE_ZIP_URL = (
    f"{_CHROME_KERNEL_BASE}/ungoogled-chromium_149.0.7827.114-1.2_windows_x64.zip"
)
```

**How to extend (per RESEARCH.md Pattern 5 / D-07/D-08):** add two new module-level constants immediately after `CHROME_ENGINE_ZIP_URL`, reusing `_CHROME_KERNEL_BASE` (same base, same release tag `kernel-149.0.7827.114`) and the `-1.3` revision (021 baseline, per D-08):
```python
CHROME_ENGINE_ZIP_URL_MACOS_ARM64 = (
    f"{_CHROME_KERNEL_BASE}/ungoogled-chromium_149.0.7827.114-1.3_macos_arm64.zip"
)
CHROME_ENGINE_ZIP_URL_MACOS_X64 = (
    f"{_CHROME_KERNEL_BASE}/ungoogled-chromium_149.0.7827.114-1.3_macos_x64.zip"
)
```
Naming convention observed: `CHROME_<ASSET>_URL[_<PLATFORM>_<ARCH>]`, all caps, `_CHROME_KERNEL_BASE` always reused via f-string — never hardcode the base URL string a second time.

**darwin-branch placement precedent** (`backend/config.py:88-99`, the existing `if sys.platform == "darwin":` block for executables) shows the established style for platform-conditional constants in this file — Chinese comments explaining rationale, `# D-0x` style references are NOT used inline (those live in CONTEXT.md), but explanatory comments in Chinese immediately above the block are the house style:
```python
if sys.platform == "darwin":
    # 系统级已安装浏览器检测路径（辅助能力，非 XPLAT-03 验收锁定值）。
    # 具体位置属 Claude's Discretion，Phase 2/3 结合内核打包形态校准。
    SYSTEM_CHROME_EXECUTABLE = Path("/Applications/Chromium.app/Contents/MacOS/Chromium")
    ...
```
Per RESEARCH.md's Open Question 3 recommendation (Claude's Discretion, CONTEXT.md confirms), prefer explicit separate named constants (`_MACOS_ARM64` / `_MACOS_X64`) over runtime `platform.machine()` branching logic inside `config.py` — matches this file's existing convention of static, greppable constants rather than functions for URLs.

---

### `tests/test_config_platform.py` (test, transform)

**Analog:** same file — existing test methods `test_macos_engine_metadata_contains_chrome_and_firefox` and `test_windows_system_and_default_executable_values_unchanged` show the exact reload+assert pattern to follow for the new URL constants.

**Reload/patch pattern** (`tests/test_config_platform.py:53-62`):
```python
def test_macos_engine_metadata_contains_chrome_and_firefox(self) -> None:
    with patch.object(sys, "platform", "darwin"), patch.object(
        sys, "frozen", True, create=True
    ):
        importlib.reload(config)
        self.assertIn("chrome", config.ENGINE_METADATA)
        ...
```

**tearDown always reloads real platform** (`tests/test_config_platform.py:14-17`):
```python
def tearDown(self) -> None:
    # 无论用例是否用了 mock，末尾都强制回到真实平台重新求值一次，避免污染其他测试文件。
    importlib.reload(config)
```

**How to extend:** add `test_macos_arm64_kernel_url` / `test_macos_x64_kernel_url` (as flagged in RESEARCH.md's Wave 0 Gaps) that assert the new constants:
1. Contain `_macos_arm64` / `_macos_x64` in the filename,
2. Are prefixed by `_CHROME_KERNEL_BASE` (string `.startswith` check, mirroring how `test_windows_system_and_default_executable_values_unchanged` asserts exact `Path`/string equality against `config.ENGINES_DIR`-derived paths),
3. Carry revision `-1.3` (distinct from Windows' `-1.2`, per D-08) — this class of assertion doesn't need `patch.object(sys, "platform", ...)` since the constants are platform-independent (no `if sys.platform` branch wraps them), unlike `SYSTEM_CHROME_EXECUTABLE` which does. No mock needed for this pair of tests, just direct `self.assertEqual`/`assertTrue` against `config.CHROME_ENGINE_ZIP_URL_MACOS_ARM64` after a fresh (non-reloaded, or reloaded — doesn't matter, they're static strings) import.

**No new test framework needed:** `python -m unittest tests.test_config_platform -v` is the existing quick-run command (confirmed working, 71 existing tests pass per RESEARCH.md Validation Architecture section).

---

### `scripts/release/verify_and_upload_macos_kernel.sh` (utility, file-I/O + batch)

**No direct shell-script analog exists in this repo** — this is the first `scripts/` directory and first `.sh` file. Closest structural analog is the "Prepare browser engines" step in `.github/workflows/build-release.yml` (PowerShell, not bash, but same *shape*: fetch → extract → verify → place), which is itself explicitly documented as reading `CHROME_ENGINE_ZIP_URL` from `backend.config` rather than hardcoding it.

**Cross-tool structural pattern to mirror** (`.github/workflows/build-release.yml:37-60`):
```powershell
function Fetch-Engine($url, $zip, $exeName, $dest) {
  Write-Host "Downloading $url"
  curl.exe -L --fail -o $zip $url
  if ($LASTEXITCODE -ne 0) { throw "download failed: $url" }
  $extract = Join-Path $env:RUNNER_TEMP ("extract_" + [IO.Path]::GetFileNameWithoutExtension($zip))
  if (Test-Path $extract) { Remove-Item $extract -Recurse -Force }
  Expand-Archive -Path $zip -DestinationPath $extract -Force
  $exe = Get-ChildItem -Path $extract -Recurse -Filter $exeName | Select-Object -First 1
  if (-not $exe) { throw "$exeName not found inside $zip" }
  ...
}
# Chrome kernel URL comes from backend/config.py (single source of truth) — no hardcoded kernel version here.
$chromeZipUrl = (python -c "from backend.config import CHROME_ENGINE_ZIP_URL; print(CHROME_ENGINE_ZIP_URL)").Trim()
if (-not $chromeZipUrl) { throw "CHROME_ENGINE_ZIP_URL is empty from backend.config" }
```
**Transferable conventions from this analog:**
- Fail-fast on every external command (`$LASTEXITCODE -ne 0` in PS ⇒ bash equivalent is `set -euo pipefail` + explicit `|| { echo ...; exit 1; }` after each `ditto`/`lipo`/`codesign`/`gh` call, exactly as RESEARCH.md's Code Examples section already drafts).
- Never hardcode the kernel version/URL — always resolve through `backend.config` via `python3 -c "from backend.config import ...; print(...)"` (mirrors the PowerShell `python -c` invocation pattern) rather than duplicating the `-1.3_macos_arm64.zip` filename string inside the shell script if it can instead be derived from (or cross-checked against) the config.py constant.
- Verbose `Write-Host`-style progress echoing before/after each step — bash equivalent: plain `echo` statements bracketing each verification stage, matching this repo's existing preference for readable CI logs over silent operation.

**Concrete extraction/verification/upload logic to use as the actual script body** — RESEARCH.md already contains fully-formed, session-verified bash snippets (Patterns 1-4 and the "Full architecture + signature verification snippet" in Code Examples, `.planning/phases/02-macos/02-RESEARCH.md:126-297`); the planner/executor should treat those as the primary source for this new file's body since no in-repo bash precedent exists to copy from instead. Key elements to combine:
- `ditto -x -k "$zip_path" "$extract_dir"` (never `unzip`) — RESEARCH.md Pattern 1.
- Dual-binary arch check against BOTH `Contents/MacOS/Chromium` AND `Contents/Frameworks/Chromium Framework.framework/Versions/Current/Chromium Framework` — RESEARCH.md Pattern 2 / Pitfall 1.
- `codesign -dv` checked for `adhoc,linker-signed` — RESEARCH.md Code Examples.
- `arch -x86_64` + CDP `/json/version` poll loop (x64 only) — RESEARCH.md Pattern 4.
- `gh release upload kernel-149.0.7827.114 <zip> --clobber --repo ShengSoft-Tech/Open-Anti-Browser` — RESEARCH.md Pattern 3.

**Argument validation convention** (per RESEARCH.md's Security Domain V5 note): `set -euo pipefail` at top of script + explicit `[[ -f "$1" ]] || exit 1`-style checks on CLI args before touching `ditto`/`gh`, matching the general shell defensive-scripting expectation called out in RESEARCH.md (no in-repo bash precedent to cite; this is a new convention this script establishes for the repo).

---

## Shared Patterns

### Single source of truth for kernel URLs
**Source:** `backend/config.py:105-119` (`_CHROME_KERNEL_BASE` + `CHROME_ENGINE_ZIP_URL`)
**Apply to:** `backend/config.py` (new macOS constants), and indirectly `scripts/release/verify_and_upload_macos_kernel.sh` (should read/cross-check against config.py rather than hardcode filenames independently), matching the existing rule "所有路径常量从这里导入,不要在别处拼路径" (CLAUDE.md).

### Platform-conditional reload testing
**Source:** `tests/test_config_platform.py:14-17` (`tearDown` reload) and lines 19-51 (darwin `patch.object(sys, "platform", "darwin")` + `importlib.reload(config)` pattern)
**Apply to:** any new test methods added to `tests/test_config_platform.py` for the macOS URL constants — though note the new URL constants are NOT inside an `if sys.platform` branch, so most new tests for them will not need the platform patch/reload dance at all, only a direct attribute-equality assertion.

### Fail-fast external-command wrapping
**Source:** `.github/workflows/build-release.yml:34-60` (`$ErrorActionPreference = 'Stop'` + explicit `if ($LASTEXITCODE -ne 0) { throw ... }` after every external call)
**Apply to:** `scripts/release/verify_and_upload_macos_kernel.sh` — bash equivalent `set -euo pipefail` plus explicit exit-code/output checks after every `ditto`/`file`/`lipo`/`codesign`/`arch`/`curl`/`gh` invocation, so failures surface immediately rather than silently continuing to the upload step.

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `scripts/release/verify_and_upload_macos_kernel.sh` | utility | file-I/O + batch | First shell script and first `scripts/` directory in this repo; no bash precedent exists to copy from directly. Planner should treat RESEARCH.md's Code Examples section (fully-formed, session-verified bash snippets) as the primary source instead of an in-repo analog — see Pattern Assignments section above for the specific snippets and how they compose into the final script. |

## Metadata

**Analog search scope:** `backend/config.py`, `tests/test_config_platform.py`, `.github/workflows/build-release.yml`, repo root for any `scripts/`/`.sh` precedent (none found), CLAUDE.md conventions
**Files scanned:** `backend/config.py` (full read), `tests/test_config_platform.py` (full read), `.github/workflows/build-release.yml` (lines 1-120)
**Pattern extraction date:** 2026-07-24
</content>
</invoke>
