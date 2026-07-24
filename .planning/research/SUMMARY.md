# Project Research Summary

**Project:** Open-Anti-Browser — macOS support (v0.2 milestone)
**Domain:** Cross-platform desktop app retrofit — adding macOS (arm64 + Intel x64) packaging/distribution to a Windows-first PySide6 + FastAPI fingerprint-browser manager, Chrome-engine-only on macOS
**Researched:** 2026-07-23
**Confidence:** MEDIUM-HIGH

## Executive Summary

This milestone ports an existing Windows-only PyInstaller desktop app to macOS, shipping two unsigned dmgs (arm64 + Intel x64) that bundle a pre-built fingerprint-chromium kernel. The Chromium kernel itself is built once, locally, on a Mac (outside this repo's CI, in the sibling `../fingerprint-chromium` repo) and uploaded as a GitHub Release asset; this app's own CI job only downloads, repackages, and signs it. The backend already has one clean seam to exploit — `backend/config.py` is the single source of path truth — so most of the port is a matter of adding platform branches there and in a handful of well-identified files (`browser_manager.py`'s unconditional win32 import, `runtime_control.py`'s Windows-only `creationflags`), not a rewrite. `backend/services/chrome.py` is already portable and needs no changes.

The recommended approach: ship unsigned + ad-hoc-signed (`codesign -s -`) binaries with clear Gatekeeper/quarantine documentation, rather than paying for an Apple Developer account this milestone. Firefox is fully out of scope on macOS (no macOS Firefox kernel exists) and should be hidden, not disabled-with-tooltip. Window sync/arrangement (win32-API-bound) is disabled-with-tooltip since it's a documented, expected Windows feature whose absence should look deliberate, not broken. Packaging uses `hdiutil` (no Finder/AppleScript flakiness) and `ditto` (not `zip`/`Expand-Archive`) at every archive/extract hop, because naive zip tooling silently breaks the nested `Chromium.app`'s framework symlinks and code signature.

The single biggest risk cluster is code-signing/quarantine interaction with a **bundled, subprocess-launched** Chromium kernel: Apple Silicon refuses to exec unsigned code at all ("Killed: 9"), and even after a user approves the outer `.app` via Gatekeeper, the nested Chromium binary — launched via `subprocess.Popen`, never via `open`/Finder — gets no interactive approval moment and can independently fail. Mitigation is disciplined: sign once (inside-out, never `--deep`), never mutate bytes after signing, and document `xattr -dr com.apple.quarantine` (recursive) as the primary unblock instruction, not just "right-click → Open." A secondary, equally important risk is silent Windows-assumption launch semantics baked into `chrome.py`/`config.py` (hardcoded `chrome.exe`, launch-via-path assumptions) that must be branched for macOS's nested `.app` executable layout without touching the Windows code path.

## Key Findings

### Recommended Stack

New macOS-only additions on top of the unchanged Windows stack: GitHub Actions `macos-15` (arm64) and `macos-15-intel` (x64, a wasting asset — GitHub has stated x86_64 macOS runner support ends ~fall 2027) runners; PyInstaller (already used for Windows, same tool/mental model, `>=6.14`); `hdiutil` for dmg creation (zero new dependency, CI-reliable, no Finder/AppleScript flakiness unlike `create-dmg`); `codesign -s -` (ad-hoc signing, mandatory on arm64 independent of Gatekeeper — unsigned arm64 code is refused by the kernel loader outright). The Chromium kernel build chain (Xcode, a pinned Chromium-specific LLVM/clang snapshot — NOT stable LLVM, per the sibling repo's own validated pitfall — `target_cpu` cross-compilation of x64 from an arm64 host) lives entirely in the sibling `../fingerprint-chromium` repo and is out of this repo's CI scope.

**Core technologies:**
- `macos-15` / `macos-15-intel` GitHub-hosted runners — native arch-matched CI packaging jobs, per-architecture matrix
- PyInstaller (existing tool) — freezes `launch_app.py` into a `.app` bundle per architecture; macOS needs its own spec with `BUNDLE()`, `.icns` icon, `upx=False`
- `hdiutil` — builds the release dmg from the `.app`, no new dependency, CI-safe
- `codesign -s -` (ad-hoc) — mandatory arm64 execution requirement, not optional polish
- `requirements.txt` environment markers — `pywin32; sys_platform == "win32"` (hard blocker today: pip install fails outright on macOS without this), `ruyipage` marker optional (ships a pure-Python wheel, won't fail install but is Firefox-only/Windows-scoped)

### Expected Features

**Must have (table stakes) — this is the entire v0.2 MVP:**
- dmg with `.app` + `/Applications` alias (plain layout; custom background is v1.x polish)
- Correct `Info.plist` (`CFBundleName`, `CFBundleIdentifier`, `.icns`) via a macOS-specific PyInstaller `BUNDLE()` — required for menu bar name, Dock icon, working Cmd+Q (none of this works reliably outside a real `.app` bundle / with `--onefile`)
- Chrome kernel (arm64 + x64) bundled inside the dmg, packaged with symlink/signature-preserving tooling (`ditto`, never `zip`)
- `config.py` macOS path branch writing all app data to `~/Library/Application Support/Open-Anti-Browser/`
- Firefox engine **hidden** (not disabled) on macOS — no macOS Firefox kernel exists, so "disabled" is misleading
- Window sync/arrangement **disabled-with-tooltip** ("Windows only") — these are known, documented Windows features; silently hiding them would look broken
- Release notes with step-by-step unsigned-app first-launch instructions: System Settings → Privacy & Security → Open Anyway, PLUS the `xattr -dr com.apple.quarantine` recursive terminal fallback (the recursive flag matters — the bundled kernel binary independently carries its own quarantine flag)
- CI macOS job producing two dmgs (arm64, x64) attached to the same GitHub Release as Windows

**Should have (v1.x follow-up):**
- Custom dmg background/drag-to-Applications graphic (cosmetic only)
- In-app first-run banner surfacing the xattr fix (in addition to release notes)
- Arch-aware download link in any in-app update-check UI

**Defer (v2+, explicitly out of scope this milestone):**
- Apple Developer ID signing + notarization (no budget for $99/yr account this milestone)
- CDP-based cross-platform window sync (technically distinct from the win32 arrangement problem, but deliberately deferred to avoid destabilizing the core "get Chrome-only macOS working" deliverable)
- Universal2 (arm64+x64 fat) binary — explicitly rejected; two separate per-arch dmgs is the permanent approach, not a shortcut
- Sparkle-style auto-updater — requires signing infrastructure as a prerequisite

### Architecture Approach

`backend/config.py`'s existing "single source of path truth" pattern is the primary lever: adding `IS_MACOS`/`IS_WINDOWS` predicates and branching `_writable_root()` (→ `~/Library/Application Support/<App>`) and `DEFAULT_CHROME_EXECUTABLE` (→ nested `Chromium.app/Contents/MacOS/Chromium` instead of `chrome.exe`) fixes almost the entire downstream path tree in one place. `backend/services/chrome.py` is already portable (its `CREATE_NEW_PROCESS_GROUP` already degrades safely via `getattr` fallback) and needs zero changes. The one hard blocker is `browser_manager.py`'s unconditional module-top import of `backend/services/window_manager.py` (`import win32api` etc.) — this crashes the entire backend on import on macOS regardless of function bodies; the fix is a new sibling module `window_manager_macos.py` with matching function signatures/no-op payloads, selected via a conditional import at the single call site, keeping Windows byte-identical. `runtime_control.py` similarly must not pass `creationflags` at all on non-Windows (passing `creationflags=0` explicitly still raises `ValueError` on POSIX). Platform capability gating (Firefox hidden, window sync disabled) should be exposed via a new additive `/api/capabilities` endpoint / `get_platform_capabilities()` method, folded into the existing `bootstrap()` payload — not overloaded onto the existing per-engine `capability_ok` flag, which means something different ("not installed" vs "not supported on this OS").

**Major components:**
1. `backend/config.py` — path/platform predicate branch point (writable root, default executable, kernel zip URL constants)
2. `backend/services/window_manager_macos.py` (new) + conditional import in `browser_manager.py` — keeps win32 code path untouched while unblocking macOS import
3. `backend/main.py` + `browser_manager.py` — new `/api/capabilities` endpoint, consumed by frontend `stores/profile.js`/`App.vue` to hide Firefox tag and window-sync UI
4. `.github/workflows/build-release.yml` — new additive `build-macos` job (matrix arm64/x64) alongside the untouched Windows job, using `ditto`-based fetch, `:`-separated `--add-data`, `hdiutil`/`codesign` packaging instead of Inno Setup

### Critical Pitfalls

1. **Naive zip/`upload-artifact` corrupts the nested `Chromium.app` bundle (symlinks/permissions)** — never use `zip`/`Expand-Archive`; use `ditto` or `tar` at every archive/extract hop (local build → release asset → CI download → embed), and verify with `codesign -dv --verbose=4` after each hop.
2. **Copying/repackaging invalidates the code signature → silent "Killed: 9" on Apple Silicon** — arm64 refuses to exec unsigned/invalidated Mach-O with no diagnostic beyond `Killed: 9`. Sign last, after every mutation; never use deprecated `--deep`; verify with `codesign --verify --deep --strict` + `spctl -a -vv` on an arm64 runner specifically.
3. **Quarantine/Gatekeeper blocks the bundled Chromium subprocess even after the outer app is "allowed"** — `subprocess.Popen`-launched nested binaries get no Finder-mediated approval moment. Document `xattr -dr com.apple.quarantine` (recursive) as the primary fix, not just "right-click → Open"; ad-hoc signing everything makes Gatekeeper's assessment succeed even under quarantine.
4. **PyInstaller onedir symlink handling + `--add-data`-injected Chromium tree interact badly** — route the kernel in via a post-PyInstaller `ditto` copy step, not `--add-data`, to keep the two symlink-preservation problems independently verifiable; set `upx=False`.
5. **Windows-assumption launch semantics baked into `chrome.py`/`config.py`** (hardcoded `chrome.exe`, implicit direct-binary-path launch model) — must launch the nested macOS binary directly via `subprocess.Popen`, never via `open -a` (which detaches PID/stdout, breaking psutil liveness tracking and CDP port discovery).

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Cross-platform backend foundation (unblock import + path resolution)
**Rationale:** Nothing else can be tested or built on macOS until the backend can even start there. This is pure Python-level risk reduction, verifiable locally on a Mac dev machine via `python -m unittest discover` before any CI/packaging work is attempted.
**Delivers:** `requirements.txt` environment markers (`pywin32` marker is a hard install blocker fix); `config.py` `IS_MACOS`/`IS_WINDOWS` predicates + `_writable_root()`/`DEFAULT_CHROME_EXECUTABLE` branches; new `window_manager_macos.py` + conditional import fix in `browser_manager.py`; `runtime_control.py` `creationflags` guard.
**Addresses:** Table-stakes "app runs at all on macOS" prerequisite for every other feature.
**Avoids:** Pitfall 6 (Windows-assumption launch semantics) at the config/path level; the "byte-identical Windows behavior" architecture requirement is satisfied by never editing `window_manager.py` in place.

### Phase 2: macOS-aware Chrome launch + capabilities API
**Rationale:** With paths resolved, the next dependency is making the actual launch (subprocess to a nested `.app` binary, not `open -a`) work, plus exposing what's supported to the frontend before UI work begins.
**Delivers:** `bundled_engine_executable("chrome")` macOS branch resolving to `Chromium.app/Contents/MacOS/Chromium`; verified direct-`Popen` launch (never `open -a`) preserving PID/psutil tracking and CDP reachability; new `GET /api/capabilities` + `get_platform_capabilities()`, folded into `bootstrap()`.
**Uses:** `backend/services/chrome.py` (already portable, no changes needed) plus the config.py branches from Phase 1.
**Implements:** The capabilities-API architecture component (Anti-Pattern 2 avoidance — capabilities is a separate source of truth from per-engine `capability_ok`).

### Phase 3: Frontend platform gating
**Rationale:** Depends on Phase 2's capabilities API existing; purely additive frontend work with low risk to Windows (capabilities always report `true` there).
**Delivers:** Firefox engine tag hidden (not disabled) on macOS with a distinct i18n string; window sync/arrangement controls disabled-with-tooltip ("Windows only"); zh-CN/en-US i18n additions per existing convention.
**Addresses:** FEATURES.md P1 items "hide Firefox engine" and "disable-with-tooltip window sync/arrangement."

### Phase 4: macOS CI packaging job (PyInstaller + codesign + dmg)
**Rationale:** Everything before this is testable via local dev-mode runs on a Mac; this phase is the first that requires an actual macOS CI runner and cannot be verified without one, so it's sequenced last among the "core" phases, after the Python-level logic is already exercised.
**Delivers:** New additive `build-macos` matrix job (arm64, macos-15-intel x64) in the existing workflow file; `ditto`-based kernel fetch (never `zip`/`Expand-Archive`); macOS PyInstaller spec (`BUNDLE()`, `.icns`, `upx=False`, `:`-separated `--add-data`); inside-out ad-hoc codesign of the assembled `.app` (never blanket `--deep`); `hdiutil create -format UDZO` dmg packaging; `codesign --verify --deep --strict` + `spctl -a -vv` as a hard CI gate before upload.
**Addresses:** All P1 packaging/distribution features from FEATURES.md.
**Avoids:** Pitfalls 1, 2, 4, 5 (symlink corruption, signature invalidation, PyInstaller/symlink interaction, wrong signing order) — this phase should be planned with explicit CI verification steps, not just "it built successfully."

### Phase 5: Distribution polish — release notes, Gatekeeper/quarantine documentation, end-to-end verification
**Rationale:** Comes last because it depends on a real, CI-produced dmg existing to actually test against (not just the local build machine, which won't reproduce Gatekeeper/quarantine issues since the developer's own Mac already trusts its own build tooling).
**Delivers:** Release notes with step-by-step System Settings → Open Anyway flow AND the recursive `xattr -dr com.apple.quarantine` fallback; manual smoke test on a clean/unrelated Mac (download → mount → drag to Applications → launch → create profile → start Chrome profile) for both architectures natively (not x64-via-Rosetta-on-arm64, which can mask arm64-specific signature failures).
**Addresses:** FEATURES.md's "Unsigned-app first-launch instructions" and "xattr as backup workaround" table-stakes items.
**Avoids:** Pitfall 3 (quarantine blocks bundled subprocess) and the "Looks Done But Isn't" checklist items around testing only the build machine's own environment.

### Phase Ordering Rationale

- Phases 1-2 front-load the highest "does the backend even start / does launch even work" risk, fully verifiable via local `python -m unittest` runs on a Mac dev machine before any CI investment — this mirrors the architecture research's own suggested build order exactly.
- Phase 3 (frontend) is purely additive and low-risk, sequenced after the capabilities API it depends on, but before CI packaging since it needs no CI runner to build/verify.
- Phase 4 (CI packaging) is deliberately last among "build" phases because it's the only phase that cannot be verified without an actual macOS GitHub Actions runner — deferring it minimizes wasted CI minutes on foundational bugs that should be caught locally first.
- Phase 5 (distribution/docs) depends on Phase 4's actual CI-produced artifact existing, since Gatekeeper/quarantine behavior can only be honestly tested against a freshly-downloaded, previously-untrusted build — not the developer's own already-trusted machine.
- The local Chromium kernel build (arm64 + x64, in the sibling `../fingerprint-chromium` repo) is an out-of-band dependency that must complete before Phase 4 can pull real kernel assets, but is explicitly out of this repo's roadmap/CI scope per PROJECT.md.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 4 (CI packaging):** Needs `--research-phase` — the exact interaction of PyInstaller's `BUNDLE()`/symlink handling with a nested foreign `.app` bundle, and the precise inside-out codesign script for Chromium's multiple nested Helper.app bundles, is MEDIUM confidence and not yet tested against this repo's actual build; plan for an explicit spike/verification step.
- **Phase 2 (Chrome launch):** Needs verification research on whether `--user-data-dir`/`--no-first-run`/`--remote-debugging-port` behave identically to Windows for this specific fingerprint-chromium fork on macOS — PITFALLS.md flags this as unverified, not assumed cross-platform parity.

Phases with standard patterns (skip research-phase):
- **Phase 1 (backend foundation):** Well-documented via direct reading of this repo's own code; pip environment markers and `sys.platform` branching are standard, HIGH-confidence patterns.
- **Phase 3 (frontend gating):** Standard additive API-consumption + i18n pattern already established in this codebase; no new architecture.
- **Phase 5 (distribution docs):** Gatekeeper/quarantine documentation patterns are well-established (cross-checked across multiple sources); primarily a writing/testing task, not a research task.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | MEDIUM-HIGH | Official GitHub Actions/PyInstaller/PyPI-marker docs are HIGH; Chromium mac build specifics cross-checked against the sibling repo's own validated Phase-2 findings (HIGH); some Gatekeeper-behavior sources are community blogs (MEDIUM) |
| Features | MEDIUM | Web-search-derived, cross-checked across multiple independent sources per claim, but no official Apple doc citation for the exact current Gatekeeper flow; competitor analysis includes some vendor-marketing sources (LOW) |
| Architecture | HIGH for backend/CI integration points (read directly from repo code with line numbers); MEDIUM for macOS packaging specifics not yet tested against this repo's actual build |
| Pitfalls | MEDIUM | Cross-referenced across GitHub issues, Apple Developer Forums, PyInstaller official docs, ungoogled-chromium-macos README; no first-party Apple platform-security spec fetched verbatim, no hands-on repro on this exact repo yet |

**Overall confidence:** MEDIUM-HIGH

### Gaps to Address

- **Exact `CFBundleExecutable` name and executable path depth of the fingerprint-chromium macOS build** (referenced as "Chromium.app/Contents/MacOS/Chromium" throughout research, but the actual fork's product name/`Info.plist` should be verified against the real built kernel once the sibling repo's macOS build completes) — verify empirically in Phase 2, don't hardcode from research assumption alone.
- **Whether PyInstaller re-signs or ignores the nested `Chromium.app`'s own binaries during its own `codesign` pass** — architecture research flags this as needing explicit verification during the first macOS CI run (Phase 4); a broken inner signature produces an easily-misattributed Gatekeeper failure.
- **CDP/`--remote-debugging-port` behavior parity with Windows for this specific fork on macOS** — not yet empirically verified; flag as a functional test requirement in Phase 2, not an assumption.
- **Whether one shared workflow file (two jobs) vs. two separate workflow files is preferred for CI** — architecture research recommends one file/two jobs to avoid trigger-logic drift, but this is a judgment call to confirm during Phase 4 planning, not a blocking gap.
- **x64 GitHub-hosted runner longevity (~2027 EOL)** — not a near-term blocker, but the roadmap/CI design should not hard-wire the x64 packaging step to the `macos-15-intel` label forever; note as a known future maintenance item, not something to solve now.

## Sources

### Primary (HIGH confidence)
- [GitHub-hosted runners reference](https://docs.github.com/en/actions/reference/runners/github-hosted-runners)
- [GitHub Actions: macOS 13 runner image is closing down](https://github.blog/changelog/2025-09-19-github-actions-macos-13-runner-image-is-closing-down/)
- [actions/runner-images#13027 — plan for macOS x86_64](https://github.com/actions/runner-images/issues/13027)
- `../fingerprint-chromium/docs/porting-pitfalls.md`, `porting-runbook.md`, `downloads-macos-arm64.ini`, `flags.macos.gn`, `CLAUDE.md` — first-party validated findings from this project's own sibling repo
- [Chromium mac_build_instructions.md](https://chromium.googlesource.com/chromium/src/+/main/docs/mac_build_instructions.md)
- [PyInstaller CHANGES.html / feature-notes.html (official docs)](https://pyinstaller.org/en/stable/CHANGES.html)
- [PyInstaller — Common Issues and Pitfalls (official docs)](https://pyinstaller.org/en/stable/common-issues-and-pitfalls.html)
- Direct reading of this repository: `backend/config.py`, `backend/browser_manager.py`, `backend/runtime_control.py`, `backend/services/chrome.py`, `backend/services/window_manager.py`, `launch_app.py`, `backend/main.py`, `requirements.txt`, `.github/workflows/build-release.yml`, `.planning/PROJECT.md`

### Secondary (MEDIUM confidence)
- [ordonez.tv / OSnews — macOS 15.1 unsigned-app launch regression](https://ordonez.tv/2024/11/04/how-to-run-unsigned-apps-in-macos-15-1/), cross-checked against [OSnews](https://www.osnews.com/story/141055/)
- [Open unsigned applications on macOS Sequoia and newer](https://wiki.hacks.guide/wiki/Open_unsigned_applications_on_macOS_Sequoia_and_newer), [idownloadblog](https://www.idownloadblog.com/2024/08/07/apple-macos-sequoia-gatekeeper-change-install-unsigned-apps-mac/), [Macworld](https://www.macworld.com/article/2457844/)
- ["Killed: 9" getting codesigning to work on Apple Silicon (conda-pack)](https://uwekorn.com/2024/03/11/getting-codesigning-to-work-on-apple-silicon.html)
- [Handling macOS Gatekeeper as an unsigned indie dev](https://dev.to/hiyoyok/handling-macos-gatekeeper-as-an-unsigned-indie-dev-the-xattr-struggle-1028)
- [Eclectic Light Co — Quarantine and the quarantine flag](https://eclecticlight.co/2020/10/29/quarantine-and-the-quarantine-flag/), [Lost in Translocation](https://eclecticlight.co/2024/05/14/lost-in-translocation/)
- [actions/upload-artifact issues #38, #326, #581, #590 — symlink/permission handling](https://github.com/actions/upload-artifact/issues/38)
- [ungoogled-chromium-macos README (build/sign/dmg process)](https://github.com/ungoogled-software/ungoogled-chromium-macos)
- [PySide6 QMenuBar docs / Qt Forum mac app menu discussions](https://doc.qt.io/qtforpython-6/PySide6/QtWidgets/QMenuBar.html)

### Tertiary (LOW confidence)
- [AdsPower — Top 10 Anti Fingerprint Browsers blog](https://www.adspower.com/blog/top-10-anti-fingerprint-browsers-2024) — vendor marketing, not independently verified
- [Multilogin vs AdsPower comparison](https://multilogin.com/compare/multilogin-vs-adspower/) — vendor/affiliate content

---
*Research completed: 2026-07-23*
*Ready for roadmap: yes*
