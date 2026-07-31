# Phase 6: 发布文档与端到端验证 - Pattern Map

**Mapped:** 2026-07-30
**Files analyzed:** 12
**Analogs found:** 12 / 12

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|-----------------|----------------|
| `.github/RELEASE_NOTES_TEMPLATE.md` (NEW) | config/doc | request-response (static content rendered into GitHub Release body via `body_path`) | `frontend/src/lib/macosGatekeeperNotice.js` (same content, different surface) + `.github/workflows/build-release.yml` release job | role-match (new file type, but content is a rewrite of the existing gatekeeper text, and its CI wiring mirrors an existing `body_path`-less step) |
| `.github/workflows/build-release.yml` § `release` job | config | request-response (CI step config) | itself, `build-macos` job's `create-dmg` step (existing `with:`-style config additions) | exact (modifying an existing job in the same file) |
| `launch_app.py::build_quarantine_failure_message` | utility | transform (string formatting) | itself (`quarantine_command_target`, same file) | exact |
| `frontend/src/lib/macosGatekeeperNotice.js` | utility/component-logic | transform (builds HTML string from i18n keys) | itself | exact |
| `frontend/src/lib/macosGatekeeperNotice.test.js` | test | request-response (assertion) | itself | exact |
| `frontend/src/i18n/zh-CN.js` § `gatekeeper` | config (i18n) | transform | `frontend/src/i18n/en-US.js` § `gatekeeper` (mirror locale) | exact |
| `frontend/src/i18n/en-US.js` § `gatekeeper` | config (i18n) | transform | `frontend/src/i18n/zh-CN.js` § `gatekeeper` (mirror locale) | exact |
| `README.md` § 下载 | doc | request-response | `README_EN.md` § Download (mirror locale) | exact |
| `README_EN.md` § Download | doc | request-response | `README.md` § 下载 (mirror locale) | exact |
| `tests/test_macos_desktop_runtime.py` § `BuildQuarantineFailureMessageTests` | test | request-response (assertion) | itself | exact |
| new D-12 cross-file consistency test (Python or node:test, planner's choice) | test | request-response (assertion) | `tests/test_macos_desktop_runtime.py::BuildQuarantineFailureMessageTests.test_translocated_scenario_matches_frontend_constant` (05-02 precedent) | exact |
| `assets/dmg-background.png` / `@2x` (regenerated) | asset (non-code) | file-I/O (headless screenshot → PNG) | `.planning/phases/05-ci/05-01-SUMMARY.md`'s documented generation process (script itself was never committed) | role-match (process documented, not a file to diff against) |
| `.planning/ROADMAP.md` § Phase 6 SC1-SC3, `.planning/REQUIREMENTS.md` § DOCS-01/02 | doc | transform | themselves (existing prose to rewrite in place) | exact |

## Pattern Assignments

### `.github/RELEASE_NOTES_TEMPLATE.md` (NEW, doc)

**Analog A — content source:** `frontend/src/i18n/zh-CN.js` / `en-US.js` § `gatekeeper` (current, stale — must be rewritten first, then template mirrors the rewrite) and `frontend/src/lib/macosGatekeeperNotice.js`'s `GATEKEEPER_XATTR_COMMAND` constant (source of truth for the quoted command literal, per D-04/D-12).

**Analog B — CI wiring:** `.github/workflows/build-release.yml` lines 815-820, the existing `Create GitHub Release` step:
```yaml
      - name: Create GitHub Release
        uses: softprops/action-gh-release@v2
        with:
          files: release-assets/*
          generate_release_notes: true
          name: "Open-Anti-Browser ${{ github.ref_name }}"
```
Add `body_path: .github/RELEASE_NOTES_TEMPLATE.md` to the `with:` block, keep `generate_release_notes: true` (D-09: it appends the auto-changelog after the template body).

**Bilingual structure (D-10) — mirror the existing bilingual-doc pattern already used in `README_EN.md` line 9** (a single fork-notice paragraph that exists only in the EN file, no cross-reference needed) — but D-10 wants both languages **in one file**, so instead mirror the progressive-disclosure Markdown shape from RESEARCH.md's Pattern 2 example (headers `## 首次打开被拦截？` then `## First Launch Blocked?`, or Chinese section followed by an English section, each internally structured as: primary step visible, `<details>` block for steps 2-3).

**xattr command literal (must be byte-identical to the other two surfaces, D-04/D-12):**
```
xattr -dr com.apple.quarantine "/Applications/Open-Anti-Browser.app"
```

**spctl caveat (Pitfall 4, must be stated plainly, not apologetically):** base wording on CONTEXT.md's Specific Ideas bullet — "应用能跑是因为不再被隔离，不是因为被 Gatekeeper 信任" — do not use phrasing like "once approved" or "after Gatekeeper trusts the app".

**Prerequisite checklist (D-05/D-06):** GUI-first self-check ("苹果菜单 → 关于本机 → 芯片显示 Apple M×" / "系统版本 ≥ 15"), followed by the terminal fallback `uname -m && sw_vers -productVersion`. State macOS 15.0 as the floor (Pitfall 2 — do not cite 12.0 or 13.0, both superseded).

---

### `.github/workflows/build-release.yml` § `release` job (config, request-response)

**Analog:** the job itself, lines 785-821 (already read in full above).

**Core pattern — adding a `body_path` input to an already-verified `softprops/action-gh-release@v2` step:**
```yaml
      - name: Create GitHub Release
        uses: softprops/action-gh-release@v2
        with:
          files: release-assets/*
          body_path: .github/RELEASE_NOTES_TEMPLATE.md
          generate_release_notes: true
          name: "Open-Anti-Browser ${{ github.ref_name }}"
```
No other lines in the `release` job (needs/if guard/download-artifact/verify-assets steps) should change — this is a single-line addition per D-09.

---

### `launch_app.py::build_quarantine_failure_message` (utility, transform)

**Analog:** itself and its sibling `quarantine_command_target`, lines 113-130 (already fully read above).

**Current (unquoted, WR-01 defect):**
```python
def build_quarantine_failure_message(bundle) -> str:
    target = quarantine_command_target(bundle)
    command = f"xattr -dr {QUARANTINE_ATTRIBUTE} {target}"
    return (
        "首次打开 Open-Anti-Browser 时出现这个提示是正常现象，不代表应用损坏或出错。\n\n"
        "macOS 会给刚安装的应用加上一次性的隔离标记，需要手动清除一次才能正常启动内置的浏览器内核。"
        "请打开“终端”（Terminal），完整复制粘贴以下命令并回车：\n\n"
        f"{command}\n\n"
        "若你把应用安装在了别的位置，请把命令末尾的路径换成实际安装位置。"
    )
```

**D-04 fix — wrap target in a fixed double-quote literal (NOT `shlex.quote`, see RESEARCH.md Pitfall 3 — `shlex.quote` is a documented no-op for this path and uses single quotes, not double):**
```python
    command = f'xattr -dr {QUARANTINE_ATTRIBUTE} "{target}"'
```

**Error handling / guard pattern to preserve unchanged** (three-tier guard in `maybe_strip_quarantine`, lines 133-143): non-darwin / non-frozen / unresolvable-bundle all short-circuit before touching `subprocess`. Do not alter this control flow — only the string-formatting line inside `build_quarantine_failure_message` changes.

---

### `frontend/src/lib/macosGatekeeperNotice.js` (utility/component-logic, transform)

**Analog:** itself, line 11 (`GATEKEEPER_XATTR_COMMAND`) and lines 37-49 (`buildGatekeeperNoticeHtml`, already fully read above).

**Current:**
```javascript
export const GATEKEEPER_XATTR_COMMAND = 'xattr -dr com.apple.quarantine /Applications/Open-Anti-Browser.app'
```

**D-04 fix:**
```javascript
export const GATEKEEPER_XATTR_COMMAND = 'xattr -dr com.apple.quarantine "/Applications/Open-Anti-Browser.app"'
```

**HTML-building pattern to preserve (lines 37-49)** — four `<li>` entries pulling from i18n keys `gatekeeper.step1`-`step4`. Per RESEARCH.md Open Question 2, content parity with the template's progressive-disclosure steps is required (D-02), but the DOM structure (flat `<ol>`) does not need to become a `<details>` clone — only the *content* of `step1`-`step4` needs rewriting to describe "double-click again" as the primary step, with `step1` carrying that content and remaining steps as the documented fallback chain.

---

### `frontend/src/lib/macosGatekeeperNotice.test.js` (test)

**Analog:** itself, lines 111-116 (already fully read above).

**Current assertion (must be updated for the new quoted format):**
```javascript
test('GATEKEEPER_XATTR_COMMAND targets a single .app bundle without sudo or spctl', () => {
  assert.ok(GATEKEEPER_XATTR_COMMAND.startsWith('xattr -dr com.apple.quarantine '))
  const targetPath = GATEKEEPER_XATTR_COMMAND.replace('xattr -dr com.apple.quarantine ', '')
  assert.ok(targetPath.endsWith('.app'))
  assert.ok(!GATEKEEPER_XATTR_COMMAND.includes('spctl'))
  assert.ok(!GATEKEEPER_XATTR_COMMAND.includes('sudo'))
```
**Fix pattern:** strip the wrapping double-quotes before the `.endsWith('.app')` check, e.g. `targetPath.replace(/^"|"$/g, '').endsWith('.app')`, or switch to `targetPath === '"/Applications/Open-Anti-Browser.app"'` for an exact-literal assertion. Keep the `spctl`/`sudo` forbidden-fragment checks unchanged (Security Domain requirement, must persist).

---

### `frontend/src/i18n/{zh-CN,en-US}.js` § `gatekeeper` (i18n config, transform)

**Analog:** the sibling locale file (each is the analog for the other — this project's established i18n-parity pattern per CLAUDE.md: "新增用户可见文案必须同时更新 `i18n/zh-CN.js` 和 `i18n/en-US.js`").

**Current zh-CN block (lines 351-363, already fully read above)** — four flat, equally-weighted steps describing the stale System-Settings-first flow. **Current en-US block (lines 351-363 of en-US.js)** mirrors it 1:1, same key structure.

**Rewrite pattern:** keep the exact key set (`title`, `intro`, `stepsTitle`, `step1`-`step4`, `commandTitle`, `commandHint`, `settingsHint`, `confirm` — required by `i18n-parity.test.js`'s 24-key gatekeeper list per RESEARCH.md), only change the *prose* inside `step1`-`step4` to describe: step1 = "再次双击打开即可" (primary, D-01/D-03), step2-3 = System Settings fallback, and fold the `xattr` fallback into `commandHint`/`commandTitle` area consistent with the current structure (command already rendered separately by `macosGatekeeperNotice.js` via `GATEKEEPER_XATTR_COMMAND`). Must update both locale files in the same commit — this is the exact pattern CLAUDE.md and the existing `i18n-parity.test.js` already enforce.

---

### `README.md` / `README_EN.md` § 下载/Download (doc, request-response)

**Analog:** the sibling-language README (mirror-locale pattern, same as i18n files). Current state (lines 70-74 of README.md, already read above):
```markdown
## 下载

- 安装包发布页（本 fork）: [Releases](https://github.com/ShengSoft-Tech/Open-Anti-Browser/releases)
- 本 fork 源码: [ShengSoft-Tech/Open-Anti-Browser](https://github.com/ShengSoft-Tech/Open-Anti-Browser)
- 原始项目: [Wtcity22/Open-Anti-Browser](https://github.com/Wtcity22/Open-Anti-Browser)
```

**D-11 addition pattern — exactly 2 lines of prerequisite + link, no step duplication:**
```markdown
## 下载

- **下载前请确认：** Apple Silicon (M 系列) 芯片 + macOS 15 或更新版本（Windows 用户无需关注此项）
- 首次打开需要按 Release 页面说明放行一次，详见 [Releases](https://github.com/ShengSoft-Tech/Open-Anti-Browser/releases) 页面里对应版本的说明
- 安装包发布页（本 fork）: [Releases](https://github.com/ShengSoft-Tech/Open-Anti-Browser/releases)
- 本 fork 源码: [ShengSoft-Tech/Open-Anti-Browser](https://github.com/ShengSoft-Tech/Open-Anti-Browser)
- 原始项目: [Wtcity22/Open-Anti-Browser](https://github.com/Wtcity22/Open-Anti-Browser)
```
(exact wording at planner/implementer's discretion; the pattern to copy is "2 short bullets above the existing 3 links, no walkthrough duplicated here" per D-11). Apply the equivalent English rewrite to `README_EN.md`'s parallel section.

---

### `tests/test_macos_desktop_runtime.py` § `BuildQuarantineFailureMessageTests` (test)

**Analog:** itself, lines 116-141 (already fully read above) — this class IS the 05-02 cross-language consistency precedent that D-12 must extend.

**Existing pattern to update (regex against JS constant, then exact literal assertion):**
```python
class BuildQuarantineFailureMessageTests(unittest.TestCase):
    """D-12a: 兜底提示是预期主路径的措辞，且命令与前端常量逐字一致。"""

    def test_translocated_scenario_matches_frontend_constant(self) -> None:
        message = launch_app.build_quarantine_failure_message(None)
        js_source = GATEKEEPER_NOTICE_JS.read_text(encoding="utf-8")
        match = re.search(
            r"GATEKEEPER_XATTR_COMMAND\s*=\s*'([^']+)'", js_source
        )
        self.assertIsNotNone(match, "未能在 macosGatekeeperNotice.js 中找到 GATEKEEPER_XATTR_COMMAND")
        expected_command = match.group(1)
        self.assertIn(expected_command, message)
        self.assertEqual(
            expected_command,
            "xattr -dr com.apple.quarantine /Applications/Open-Anti-Browser.app",
        )

    def test_non_translocated_bundle_message_points_to_its_own_path(self) -> None:
        bundle = Path("/Applications/Open-Anti-Browser.app")
        message = launch_app.build_quarantine_failure_message(bundle)
        self.assertIn(f"xattr -dr com.apple.quarantine {bundle}", message)
```
**Update needed:** both hardcoded literal expectations (`"xattr -dr com.apple.quarantine /Applications/Open-Anti-Browser.app"` and `f"xattr -dr com.apple.quarantine {bundle}"`) must gain the double-quote wrap to match D-04's fix, e.g. `f'xattr -dr com.apple.quarantine "{bundle}"'`. `test_message_contains_no_dangerous_command_fragments` (line 133) needs no change — its forbidden-fragment list (`sudo`, `spctl`, `--master-disable`, `~/Downloads`) is orthogonal to the quoting fix.

---

### New D-12 cross-file consistency test (planner's choice: extend Python class above, or new `node:test` file)

**Analog:** the exact same `test_translocated_scenario_matches_frontend_constant` shown above — this is the 05-02 precedent to literally copy and extend from 2-way to 3-way comparison.

**Pattern to extend:**
```python
# Read the fixed command out of the JS constant (regex, as above)
# Read/regex the same literal out of .github/RELEASE_NOTES_TEMPLATE.md
# Read the Python-rendered message via launch_app.build_quarantine_failure_message(None)
# Assert all three equal after D-04's quoting change:
#   'xattr -dr com.apple.quarantine "/Applications/Open-Anti-Browser.app"'
```
Both `GATEKEEPER_NOTICE_JS` (an existing `Path` constant already imported at the top of `tests/test_macos_desktop_runtime.py`, confirm exact name via `grep -n "GATEKEEPER_NOTICE_JS" tests/test_macos_desktop_runtime.py`) and a new `RELEASE_NOTES_TEMPLATE = Path(...) / ".github" / "RELEASE_NOTES_TEMPLATE.md"` constant should follow the same `Path.read_text(encoding="utf-8")` + `re.search` pattern already established.

---

### `assets/dmg-background.png` / `@2x` (asset, file-I/O)

**Analog:** the documented (not committed) generation process from `.planning/phases/05-ci/05-01-SUMMARY.md` lines 121-123, already read above — no source HTML file exists in the repo to diff against (05-01 intentionally never committed it), so this is a **process pattern**, not a code analog.

**Process to replicate exactly:**
```
1. Write a scratch HTML file (session scratchpad only, never committed) with CSS absolute
   positioning matching create-dmg's parameters (600×400 window, 128px icon size,
   app-icon alias at (150,190), Applications alias at (450,190)).
2. Screenshot via the repo's vendored headless Chromium:
   engines/chrome/Chromium.app/Contents/MacOS/Chromium
     --headless=new --disable-gpu --no-sandbox --hide-scrollbars
     --window-size=600,400 --force-device-scale-factor=1
     --screenshot=<out>.png
   → assets/dmg-background.png (600×400)
   Same command with --force-device-scale-factor=2 → assets/dmg-background@2x.png (1200×800)
3. Verify with: sips -g pixelWidth -g pixelHeight <file>.png
4. Only commit the final PNGs; delete scratch HTML and intermediate screenshots.
```
**Content change required (D-02):** footer/instructional text in the scratch HTML must be rewritten from "右键点图标 →「打开」" to describe the measured D-01/D-03 flow ("首次打开若被拦截，请再双击一次"), and must pass the same forbidden-phrase audit 05-01 already established (`spctl`, `sudo`, `--master-disable`, wide-directory recursion — per Security Domain table above).

---

## Shared Patterns

### Cross-file verbatim consistency lock (D-12, extends 05-02 precedent to 3 surfaces)
**Source:** `tests/test_macos_desktop_runtime.py::BuildQuarantineFailureMessageTests.test_translocated_scenario_matches_frontend_constant` (lines 119-131)
**Apply to:** `launch_app.py::build_quarantine_failure_message`, `frontend/src/lib/macosGatekeeperNotice.js::GATEKEEPER_XATTR_COMMAND`, `.github/RELEASE_NOTES_TEMPLATE.md`'s embedded command — all three must render `xattr -dr com.apple.quarantine "/Applications/Open-Anti-Browser.app"` byte-identical.
```python
match = re.search(r"GATEKEEPER_XATTR_COMMAND\s*=\s*'([^']+)'", js_source)
expected_command = match.group(1)
self.assertIn(expected_command, message)
self.assertEqual(expected_command, "xattr -dr com.apple.quarantine \"/Applications/Open-Anti-Browser.app\"")
```

### i18n bilingual parity
**Source:** `frontend/src/i18n/zh-CN.js` / `en-US.js` § `gatekeeper` (mirror key sets, both required by `i18n-parity.test.js`)
**Apply to:** any change to `gatekeeper.step1`-`step4` — CLAUDE.md mandates both locale files updated in the same change.

### "Measured, not inferred" prose discipline (Pitfall 1, Pitfall 4)
**Source:** `.planning/phases/05-ci/05-06-SUMMARY.md` Group B (B1-B8) real-hardware evidence
**Apply to:** every prose surface in this phase (`RELEASE_NOTES_TEMPLATE.md`, README sections, i18n `gatekeeper.*`, dmg background text, ROADMAP/REQUIREMENTS rewrites) — never restate the pre-Phase-5 assumption ("System Settings first", "app becomes trusted") that Phase 5's real hardware testing falsified.

### Progressive disclosure ordering (D-03, RESEARCH.md Pattern 2)
**Source:** RESEARCH.md's example `<details>` block (lines 256-274 of 06-RESEARCH.md)
**Apply to:** `RELEASE_NOTES_TEMPLATE.md` primarily; content-parity requirement extends to `gatekeeper.step1`-`step4` (step1 = primary path, steps 2-4 = fallback chain) though the in-app modal need not literally use `<details>`.

## No Analog Found

None — every file in scope has at least a role-match analog already in the repo (the `.github/RELEASE_NOTES_TEMPLATE.md` file itself is new, but its content, wiring, and consistency-test patterns are all directly copyable from existing files as detailed above).

## Metadata

**Analog search scope:** `launch_app.py`, `frontend/src/lib/macosGatekeeperNotice.js` (+ test), `frontend/src/i18n/{zh-CN,en-US}.js`, `README.md`/`README_EN.md`, `.github/workflows/build-release.yml`, `tests/test_macos_desktop_runtime.py`, `.planning/phases/05-ci/05-01-SUMMARY.md`
**Files scanned:** 9 direct reads + 2 grep sweeps
**Pattern extraction date:** 2026-07-30
