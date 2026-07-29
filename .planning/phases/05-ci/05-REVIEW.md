---
phase: 05-ci
reviewed: 2026-07-29T19:31:33Z
depth: standard
files_reviewed: 5
files_reviewed_list:
  - .github/workflows/build-release.yml
  - launch_app.py
  - scripts/release/check_version_consistency.py
  - tests/test_macos_desktop_runtime.py
  - tests/test_version_consistency.py
findings:
  critical: 0
  warning: 7
  info: 4
  total: 11
status: issues_found
---

# Phase 05-ci: Code Review Report

**Reviewed:** 2026-07-29T19:31:33Z
**Depth:** standard
**Files Reviewed:** 5
**Status:** issues_found

## Summary

This phase's headline defects — the `installEventFilter` SIGSEGV and the Cmd+Q infinite-quit-loop
— are already fixed, pinned by two AST structural-guard test classes
(`QApplicationEventFilterGuardTests`, `MacQuitEventLoopConvergenceTests`), and independently
proven on both real CI runs and real hardware (per `05-02-GAP-FIX-SUMMARY.md`,
`05-02-GAP-FIX-2-SUMMARY.md`, `05-06-SUMMARY.md`). I re-traced `DesktopApplication.event()`,
`DesktopMainWindow.force_exit()`/`closeEvent()`/`shutdown()`, and the quarantine self-strip path
end to end and did not find a new instance of that same defect shape (event-swallowing,
re-entrancy, or override-changes-delivery-semantics). No Critical findings.

I did find a cluster of lower-severity but real issues, mostly outside the areas that got
real-hardware attention: an unquoted/unescaped shell command handed to users in the D-12a fallback
message, a blocking `subprocess.run()` call with no timeout on the app's synchronous startup path,
an overly broad `permissions: contents: write` grant that all three CI jobs inherit even though
only `release` needs it, a version-regex in `check_version_consistency.py` that isn't anchored to
a word boundary, and a silent fail-open on a malformed `is_tag` CLI argument in the same script.
None of these are "must fix before ship" on their own, but several sit exactly in the two areas
the task flagged for extra scrutiny (the quarantine subprocess/message path, and CI gate
robustness), so I'm reporting all of them as Warnings rather than downgrading to Info.

## Warnings

### WR-01: D-12a fallback command is not shell-quoted — breaks on install paths with spaces

**File:** `launch_app.py:121-130` (message text), `launch_app.py:113-118` (`quarantine_command_target`)
**Issue:** `build_quarantine_failure_message()` builds the copy-pasteable Terminal command as:
```python
command = f"xattr -dr {QUARANTINE_ATTRIBUTE} {target}"
```
`target` is either the hardcoded `CANONICAL_INSTALL_BUNDLE` (no spaces, safe today) or
`str(bundle)` — the actual resolved `.app` path — for a non-translocated custom install location
(`quarantine_command_target`, line 118). If a user installs to any path containing a space or
shell metacharacter (e.g. `/Users/John Doe/Applications/Open-Anti-Browser.app`, or any folder a
user renames), the command shown in the dialog and copy-pasted into Terminal by the user silently
breaks (`xattr` gets `John` and `Doe/Applications/Open-Anti-Browser.app` as two separate
arguments, "no such file" for both). This is exactly the "wrong path shown as a shell command" risk
class called out for this feature — the tool's own guidance disclaims this ("若你把应用安装在了别的
位置，请把命令末尾的路径换成实际安装位置") but doesn't fix the primary rendered command.
**Fix:**
```python
import shlex
command = f"xattr -dr {QUARANTINE_ATTRIBUTE} {shlex.quote(str(target))}"
```
`tests/test_macos_desktop_runtime.py::BuildQuarantineFailureMessageTests` currently asserts the
*unquoted* literal string (`"xattr -dr com.apple.quarantine /Applications/Open-Anti-Browser.app"`)
— for the canonical path `shlex.quote` is a no-op, so the existing assertions keep passing after
this fix; add a case with a space in the path to lock in the new behavior.

### WR-02: Translocated-path fallback command targets a location the app hasn't been installed to yet

**File:** `launch_app.py:113-130`
**Issue:** When `is_translocated_path(bundle)` is true, `quarantine_command_target` returns
`CANONICAL_INSTALL_BUNDLE` ("/Applications/Open-Anti-Browser.app") — but a translocated app is, by
definition, *not yet* at that path (translocation is triggered precisely by running the app from
somewhere other than a stable, user-drag-installed location, e.g. straight off a mounted dmg or
`~/Downloads`). The message tells the user to run `xattr -dr … /Applications/Open-Anti-Browser.app`
without ever saying "first drag/copy the app into /Applications" — if the app genuinely isn't there
yet, the command will just fail with "No such file or directory" and the user is left stuck with no
actionable next step. (05-06's real-hardware checkpoint found this path is not actually triggered by
a normal Finder drag-install — Assumption A1 was falsified — so this is a low-probability edge case
today, but the code path and message still exist and are exercised directly by
`BuildQuarantineFailureMessageTests::test_translocated_scenario_matches_frontend_constant`.)
**Fix:** Either add one sentence to `build_quarantine_failure_message` covering "if the command
reports 'No such file', first move/copy the app into /Applications, then try again," or make the
canonical-path substitution explicit about that precondition rather than implicit.

### WR-03: `strip_quarantine_from_bundle` runs `subprocess.run` with no timeout on the app's synchronous startup path

**File:** `launch_app.py:102-110`, called from `maybe_strip_quarantine()` (`launch_app.py:133-143`),
called from `run_desktop()` before the window is shown (`launch_app.py:448`)
**Issue:** `xattr -dr` recurses over the entire `.app` bundle (hundreds of files across the Qt
frameworks, WebEngine process, and the embedded Chromium kernel — per `05-02-GAP-FIX-SUMMARY.md`'s
own comment, "只剥主二进制不够，framework dylib 与 helper 也带 quarantine"). This call has no
`timeout=` and runs synchronously on the Qt main thread *before* `find_available_port`/
`build_server`/`window.show()` — i.e., before any window or feedback is visible to the user. If the
filesystem is slow (network volume, iCloud file provider throttling an external drive, antivirus
hooking `xattr` syscalls), the entire app hangs indefinitely at launch with zero UI and no way for
the user to tell whether it's starting or frozen.
**Fix:**
```python
result = subprocess.run(
    ["xattr", "-dr", QUARANTINE_ATTRIBUTE, str(bundle)],
    capture_output=True,
    text=True,
    timeout=30,
)
```
and treat `subprocess.TimeoutExpired` as a failure path (returns the same fallback message rather
than propagating an uncaught exception that would crash `run_desktop()` before any window exists).

### WR-04: Workflow-level `permissions: contents: write` is inherited by `build` and `build-macos`, which don't need it

**File:** `.github/workflows/build-release.yml:9-10`
**Issue:** The top-level `permissions: contents: write` block applies to every job in the workflow
by default. Only the `release` job actually needs write access (`softprops/action-gh-release`
creates a GitHub Release and uploads assets). `build` and `build-macos` only run
`pip install`/`npm install`/PyInstaller/codesign/`actions/upload-artifact` — none of which need
`contents: write`, and `actions/upload-artifact` doesn't use the `contents` scope at all. This
violates least-privilege: if a supply-chain step in either build job is ever compromised (a
malicious npm/pip dependency, a tampered engine `.zip` download over `curl`), the compromised step
currently has a live `GITHUB_TOKEN` with repo write access it has no legitimate use for.
**Fix:** Move the permission to the job that needs it and default the others to read-only:
```yaml
permissions:
  contents: read

jobs:
  build:
    runs-on: windows-latest
    # no permissions override needed — inherits contents: read
  build-macos:
    runs-on: macos-15
    # no permissions override needed — inherits contents: read
  release:
    needs: [build, build-macos]
    if: startsWith(github.ref, 'refs/tags/')
    runs-on: ubuntu-latest
    permissions:
      contents: write
```

### WR-05: `check_version_consistency.py`'s semver regex isn't anchored to a word boundary

**File:** `scripts/release/check_version_consistency.py:39-41`
**Issue:**
```python
_SEMVER_VERSION_RE = re.compile(
    r'version\s*=\s*"(\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?)"'
)
```
This matches any substring `...version="X.Y.Z"` in `backend/main.py`, not just a standalone
`version=` keyword-argument — there's no `\b` or non-word-character lookbehind. Today
`backend/main.py` only contains the two intended `FastAPI(..., version="0.1.16")` occurrences, so
the check passes cleanly. But the module's own docstring explains the *purpose* of the regex is
specifically to "避免 backend/main.py 里任何其他 version="..." 字面量把校验误伤成不一致" — i.e., it's
already anticipating drift, just not fully closing the gap. If a future edit adds any other
`..._version="1.2.3"`-shaped literal to `backend/main.py` (e.g. `api_version="1.0.0"` for an
unrelated sub-router, or a docstring example containing the exact substring), the release gate
would either (a) start requiring a spurious third value to match, breaking a legitimate release, or
(b) in the unlucky case where it coincidentally matches the real version, silently do nothing —
either way it stops meaning what its own comment says it means.
**Fix:** Anchor with a word boundary or non-identifier lookbehind:
```python
_SEMVER_VERSION_RE = re.compile(
    r'(?<![\w.])version\s*=\s*"(\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?)"'
)
```

### WR-06: `check_version_consistency.py` silently downgrades to the lenient non-tag mode on any malformed `is_tag` argument

**File:** `scripts/release/check_version_consistency.py:121-122`
**Issue:**
```python
ref_name, is_tag_raw = args
is_tag = is_tag_raw.strip().lower() == "true"
```
Any value other than a case-insensitive `"true"` (a typo, an empty string, `"1"`, a shell-quoting
mistake in a future workflow edit) silently resolves to `is_tag=False` — the *less strict* mode,
which skips the tag-vs-package.json-vs-main.py comparison entirely and only checks
package.json == main.py. For a script whose entire job is to be the release version gate, failing
open on malformed input is the wrong default. Currently the calling workflow step always passes a
literal `"true"`/`"false"` string it computed itself, so this isn't exploitable today, but it's a
latent trap for the next person who edits the `Resolve version` step.
**Fix:** Validate explicitly and fail closed on anything unexpected:
```python
normalized = is_tag_raw.strip().lower()
if normalized not in {"true", "false"}:
    print(f"错误: is_tag 参数必须是 true/false, 实际收到: {is_tag_raw!r}", file=sys.stderr)
    return 1
is_tag = normalized == "true"
```

### WR-07: `check_version_consistency.py` doesn't catch malformed-input exceptions (`JSONDecodeError`, `KeyError`, `OSError`)

**File:** `scripts/release/check_version_consistency.py:48-59`, `112-132`
**Issue:** `read_package_version()` does `data["version"]` with no `.get()`/try-except — a
`package.json` missing the `version` key raises an uncaught `KeyError`; a syntactically broken
`package.json` raises `json.JSONDecodeError`; a missing/unreadable file raises `FileNotFoundError`/
`OSError`. `main()`'s `try/except VersionMismatch` only catches the one exception type this module
itself raises, so any of these surfaces as a raw Python traceback in CI output instead of the
module's own `错误: ...` convention, and returns Python's default nonzero exit code (1, same
effective result, but a much worse diagnostic experience for whoever is debugging a broken release).
**Fix:** Wrap the read helpers or the `main()` call site in a broader `except Exception as exc`
that still prints a clear `错误:` message and returns 1, e.g.:
```python
try:
    version = check_version_consistency(ref_name, is_tag)
except VersionMismatch as exc:
    print(f"错误: {exc}", file=sys.stderr)
    return 1
except Exception as exc:  # malformed package.json / unreadable main.py / etc.
    print(f"错误: 版本校验时发生意外错误: {exc}", file=sys.stderr)
    return 1
```

## Info

### IN-01: `handle_macos_quit_request`'s return value is now dead — signature invites re-introducing the fixed early-return bug

**File:** `launch_app.py:76-80`, consumer at `launch_app.py:416-419`
**Issue:** `handle_macos_quit_request(window) -> bool` still declares and returns `True`, a holdover
from before `05-02-GAP-FIX-2` removed the `if handle_macos_quit_request(...): return True` gating
pattern that caused the Cmd+Q infinite-loop defect. The current caller ignores the return value
entirely:
```python
def event(self, e) -> bool:
    if e.type() == QEvent.Type.Quit and self.target_window is not None:
        handle_macos_quit_request(self.target_window)
    return super().event(e)
```
The function signature and the still-passing test
(`test_handle_macos_quit_request_calls_force_exit_once_and_returns_true`) both keep alive the shape
of the exact anti-pattern the AST guard in `MacQuitEventLoopConvergenceTests` was written to
prevent from returning — a future edit that "helpfully" starts using the return value again
(`if handle_macos_quit_request(...): return True`) would silently reintroduce the fixed bug, and
the AST guard only checks the shape of `event()`'s body, not whether some other call site does this.
**Fix:** Change the signature to `-> None` and drop the `return True`, or add a code comment at the
call site making explicit that the return value must never be used to gate a `return` in `event()`.

### IN-02: Windows `build` job has its own independent, un-synced version derivation — D-08's gate only covers `build-macos`

**File:** `.github/workflows/build-release.yml:98-99` (Windows, pre-existing) vs.
`.github/workflows/build-release.yml:144-171` (macOS, new in this phase)
**Issue:** The new `check_version_consistency.py` gate (D-08) is wired into `build-macos`'s
`Resolve version` step only. The pre-existing Windows `build` job still derives its installer
version independently and more leniently:
```powershell
$v = "${{ github.ref_name }}" -replace '^v', ''
if (-not ($v -match '^\d+(\.\d+)+')) { $v = '0.0.0' }
```
This never checks `package.json`/`main.py` at all, and silently falls back to `0.0.0` rather than
failing on a malformed tag. In the current three-job topology this is harmless in practice — the
`release` job's `needs: [build, build-macos]` means a `build-macos` version-consistency failure
still blocks the GitHub Release regardless of what the Windows job did — but it means D-08's
guarantee ("三方必须全等") is asymmetric across platforms and only incidentally protects Windows via
the other job's `needs` dependency, not by its own logic. Flagging as Info (not Warning) since the
Windows job is explicitly out of scope for this phase's edits and the overall pipeline is still
correctly gated end-to-end.
**Fix (future phase):** If the Windows job is ever revisited, route it through the same
`check_version_consistency.py` script for a single source of truth, rather than relying on
`needs:` topology to transitively protect it.

### IN-03: Placeholder file (`engines/chrome/.placeholder`) ends up shipped inside the macOS `.app` bundle

**File:** `.github/workflows/build-release.yml:213-215`, `263-290`
**Issue:** The "Prepare browser engine (macOS arm64)" step writes
`engines/chrome/.placeholder` into the repo-tree `engines/` directory (so PyInstaller's
`--add-data "engines:engines"` produces the right directory *shape* without copying the real
400MB kernel). The later "Inject Chrome kernel into .app" step only `rm -rf`s the
`Chromium.app` subdirectory before `ditto`-ing the real kernel in — it never removes
`.placeholder` itself, so that inert marker file rides along inside every shipped `.app` at
`Contents/Resources/engines/chrome/.placeholder`. Harmless (a few bytes, no functional effect,
and `find ... -not -path "*/engines/*"` in the signing/enumeration steps already excludes it from
mattering), but it's shipped debris in a production artifact.
**Fix:** `rm -f "$APP/Contents/Resources/engines/chrome/.placeholder"` alongside the existing
`rm -rf "$DEST"` in the "Inject Chrome kernel into .app" step, or just don't write the placeholder
file at that exact path (use a differently-named/located marker that PyInstaller doesn't include).

### IN-04: Workflow file name is stale — no longer just "Windows Installer"

**File:** `.github/workflows/build-release.yml:1`
**Issue:** `name: Build & Release Windows Installer` predates this phase; the workflow now also
builds a macOS arm64 `.app`/dmg and creates a combined cross-platform GitHub Release. The name is
misleading in the Actions UI (a maintainer scanning workflow runs would not expect a "Windows
Installer" workflow to also gate/publish the macOS build).
**Fix:** Rename to something like `Build & Release (Windows + macOS)`.

---

_Reviewed: 2026-07-29T19:31:33Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
