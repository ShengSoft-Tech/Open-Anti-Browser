# Stack Research

**Domain:** Desktop app packaging/distribution — adding macOS (arm64 + Intel x64) build, package, and release to an existing Windows-first PyInstaller + GitHub Actions pipeline
**Researched:** 2026-07-23
**Confidence:** MEDIUM-HIGH (official docs for GitHub Actions/PyInstaller/PyPI markers = HIGH; Chromium mac build specifics cross-checked against the sibling `../fingerprint-chromium` repo's own validated Phase-2 findings = HIGH; a few community/blog sources on Gatekeeper behavior = MEDIUM, flagged below)

This file covers only the **additions** needed for macOS support. Everything already working on Windows (FastAPI backend, Vue frontend, profile/proxy/extension logic, PyInstaller onedir + Inno Setup on `windows-latest`) is unchanged and out of scope here.

## Recommended Stack

### Core Technologies (new, macOS-only)

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| GitHub Actions `macos-15` runner | current arm64 GA image | CI job that packages the arm64 dmg | Native Apple Silicon (M-series), 7GB RAM/14GB disk on standard runner; matches the arm64 kernel produced by the local Mac build. Do not use `macos-14` — it carries a deprecation notice as of the 15-series GA. |
| GitHub Actions `macos-15-intel` runner | current x64 GA image | CI job that packages the x64 dmg | The **only** GitHub-hosted label that is still x86_64 once `macos-13`/`macos-13-intel` fully retire (deprecation began Sept 2025, cut off ~Dec 2025). GitHub has stated x86_64 macOS runners end after the macOS-15 image retires (~fall 2027) — treat Intel CI as a wasting asset, not a long-term bet. |
| PyInstaller | >=6.14 (already pinned in `requirements.txt`; verify against 6.21.x if bumping) | Freezes `launch_app.py` into a `.app` bundle per architecture | Already the project's chosen freezer for Windows; using the same tool on macOS keeps one build tool, one spec/CLI surface, one mental model across platforms. Actively maintained, current stable is 6.21.0 (2026-06). |
| `hdiutil` (macOS built-in) | ships with macOS | Creates the release `.dmg` from the `.app` bundle | Zero new dependency (no Node, no extra Python package), 100% reliable in headless CI (no AppleScript/Finder automation to flake), and sufficient for a "drag `.app` into `/Applications`" installer — which is all this milestone needs. |
| `codesign` (macOS built-in, Xcode Command Line Tools) | ships with macOS | Ad-hoc signs (`codesign -s -`) the frozen `.app` and all embedded Mach-O binaries | **Mandatory**, not optional, for arm64: unsigned arm64 code is refused by the kernel loader outright (`Killed: 9`), independent of Gatekeeper. Ad-hoc signing (no Apple Developer account, no cert) is enough to satisfy the loader. |

### Supporting / Build-Chain Tools (Chromium kernel — built once, locally, NOT in CI)

The milestone context is explicit: the Chromium kernel is built on a local Mac and uploaded as a release asset; GitHub Actions only downloads and packages it. These are documented here because they determine what URL/artifact shape `backend/config.py`'s `CHROME_ENGINE_ZIP_URL`-style constants need to point at for macOS, and because the app-level roadmap should not schedule a "build Chromium in CI" phase.

| Tool | Version | Purpose | Notes |
|------|---------|---------|-------|
| Xcode | Whatever Xcode version ships the SDK pinned by Chromium 149's `build/config/mac/mac_sdk.gni` (official Chromium bots build against a specific SDK; newer SDKs "usually" work, older reliably don't). In practice: latest Xcode available for the macOS version on the build Mac. | Provides the macOS SDK, `ld64.lld` linker support tooling, and the Metal Toolchain component. | The sibling `../fingerprint-chromium` repo does **not** use Xcode's bundled clang for the actual compile — it downloads a pinned upstream clang instead (see next row) because Chromium 149 requires flags stable Xcode/LLVM clang doesn't support. Xcode is still required for the macOS SDK headers/frameworks and for `xcodebuild -downloadComponent MetalToolchain`. |
| Chromium-pinned LLVM/clang | `llvmorg-23-init-10931-g20b6ec66-8` (clang 23 dev snapshot) + matching `dsymutil` | Actual compiler used for the mac build | **Do not use stable LLVM 22.1.0** — confirmed by the sibling repo's own Phase-2 validation: it rejects `-fdiagnostics-show-inlining-chain` and equivalent flags Chromium 149's build scripts pass. `downloads-macos-arm64.ini` in `../fingerprint-chromium` already pins the correct clang/dsymutil/rust/node tarballs with sha512 checksums — reuse it as-is, don't re-derive versions. |
| `llvm-otool` shim | n/a (symlink) | Chromium's mac build invokes `llvm-otool`, which Google's clang tarball does not ship | `ln -s /usr/bin/otool third_party/llvm-build/Release+Asserts/bin/llvm-otool` — already documented as pitfall B-09 in `../fingerprint-chromium/docs/porting-pitfalls.md`. |
| GN `target_cpu` | `"arm64"` or `"x64"` in `args.gn` | Selects which architecture Chromium builds | Chromium's mac toolchain supports cross-compiling **x64 output from an arm64 host** by setting `target_cpu="x64"` — an Intel Mac is not required to produce the x64 kernel. This lets the entire kernel build (both architectures) happen on a single Apple Silicon Mac, matching the "built locally on a Mac" constraint. `flags.macos.gn` in the sibling repo currently hardcodes `target_cpu="arm64"`; producing the x64 kernel needs a second args.gn pass with `target_cpu="x64"` and (per the milestone context) a new `downloads-macos-x64.ini` toolchain manifest analogous to the arm64 one. |
| Disk / RAM / time budget | ~15GB source + 10-20GB build output (validated by the sibling repo's own Phase-2 cheap-build); full official-build output with symbols is typically larger — budget 60-100GB free disk for a real (non-cheap) release build including both arch outputs and intermediate artifacts. RAM: build under 32GB risks V8-builtins OOM (pitfall B-07) — use `-j4` on lower-memory machines. | Sizing guidance for the local Mac doing the kernel build | This is why the milestone correctly keeps this off GitHub Actions — the standard GitHub-hosted mac runner (14GB disk, 7GB RAM) cannot fit a real Chromium build at all, cheap or otherwise. |
| `downloads-macos-*.ini` pattern | project-specific `utils/downloads.py` config format (ungoogled-chromium tooling) | Declares pinned toolchain tarball URLs + sha512 + install path, consumed via `utils/downloads.py retrieve/unpack -i <file>` | This is **not** a generic ungoogled-chromium standard filename — it's this project's own convention (parallel to the existing `downloads.ini`). `downloads-macos-arm64.ini` exists; per the milestone's Active requirements, an equivalent `downloads-macos-x64.ini` (same clang/dsymutil key, `Mac_x64`-flavored rust/node tarballs) needs to be authored before the x64 kernel can be built. This is kernel-repo work, not app-repo work — flag it as a dependency/blocker for the "macOS 内核" requirement, not something this app's CI needs to solve. |

### Packaging Command Additions (app repo, new macOS CI job)

| Step | Tool | Command shape | Why |
|------|------|----------------|-----|
| Freeze | PyInstaller | `pyinstaller --noconfirm --windowed --name "Open-Anti-Browser" --icon assets/app.icns --add-data "frontend/dist:frontend/dist" --add-data "assets:assets" --add-data "engines:engines" --hidden-import websockets ... launch_app.py` | Same flags as Windows job, mac-specific changes: `--icon` needs an `.icns` (not `.ico`), `--add-data` separator is `:` not `;` on POSIX, and drop `--hidden-import ruyipage` / firefox engine bundling since Firefox is out of scope on macOS. `--windowed` on macOS automatically produces **both** a onedir POSIX folder and a `.app` bundle (via the spec file's `COLLECT` + `BUNDLE` targets) — no separate "bundle mode" flag is needed; the `.app` is the packaging target to ship. |
| Ad-hoc sign | `codesign` | `codesign --force --deep --sign - "dist/Open-Anti-Browser.app"` | PyInstaller already ad-hoc (re)signs the individual collected Mach-O binaries and the main executable by default on macOS as part of the freeze step, but re-signing the whole `.app` bundle after adding the (non-PyInstaller-managed) `engines/chrome` kernel binaries into it is the safe belt-and-suspenders step — anything added into the bundle after PyInstaller ran (the downloaded Chromium kernel) needs its own ad-hoc signature or the outer bundle seal breaks. Do this with `--deep` since the kernel bundle contains nested frameworks/helpers (`*.app/Contents/Frameworks/*.framework`, helper apps) that each need a valid signature for arm64 to launch them. |
| Package | `hdiutil` | `hdiutil create -volname "Open-Anti-Browser" -srcfolder dist/Open-Anti-Browser.app -ov -format UDZO "Open-Anti-Browser-<version>-<arch>.dmg"` | Simplest reliable path; produces a compressed read-only dmg containing just the `.app` (user drags it to Applications manually, or add a `-Applications` symlink into the srcfolder for a slightly nicer drop target). No AppleScript/Finder window-layout step — those are what make `create-dmg`-style tools flaky on headless CI runners. |

### What NOT to Add

| Avoid | Why | Use Instead |
|-------|-----|--------------|
| Building Chromium inside GitHub Actions | GitHub-hosted mac runners cap out at 14GB disk / 7GB RAM (standard tier) — nowhere near the ~60-100GB and 32GB+ RAM budget a real Chromium build needs, and would run far past Actions' job time limits | Local Mac build → upload to `kernel-149.0.7827.114`-style GitHub release, exactly as the milestone context specifies |
| `create-dmg` (npm, sindresorhus) or `create-dmg` (shell script, andreyvit/create-dmg) for the dmg step in this milestone | Both drive Finder/AppleScript to lay out icon positions and background images — a known source of CI flakiness on headless macOS runners (timing-dependent Finder registration). Adds either a Node dependency or a new shell tool for a feature (pretty drag-to-Applications window) this milestone doesn't need | Plain `hdiutil create -format UDZO`; revisit `create-dmg`/`dmgbuild` later only if UX polish becomes a requirement |
| `dmgbuild` (Python, pip-installable) — for *this* milestone | Not wrong, just unnecessary scope: it exists specifically to avoid the Finder/AppleScript flakiness of `create-dmg` while still giving background-image/icon-position control, but that control isn't a stated requirement here | Note as the natural next step if a later milestone wants a polished dmg, since it's pure Python and fits this project's existing tooling better than a Node-based alternative |
| Universal2 (`lipo`-combined) PyInstaller build | Project's own Key Decision already rules this out for the Chromium kernel; keeping the Python app as a single arch-per-dmg build (not universal2) matches that decision and avoids bundling both a large arm64 and x64 kernel inside one dmg | Two separate PyInstaller invocations, one on each runner arch, each pulling only its matching kernel zip |
| `--osx-bundle-identifier` / `--codesign-identity <real cert>` / `--osx-entitlements-file` with hardened runtime | Requires an Apple Developer account (already explicitly out of scope per Key Decisions) and, worse, hardened-runtime signing of `QtWebEngineProcess` without the right entitlements (`com.apple.security.cs.allow-jit`, `disable-library-validation`, `allow-unsigned-executable-memory`) is a known way to make the embedded browser silently fail to launch | Plain ad-hoc signing (`codesign -s -`, no `--options runtime`) — hardened-runtime restrictions that block JIT/unsigned memory only activate when hardened runtime is explicitly turned on, so a plain ad-hoc signature avoids the whole QtWebEngine-JIT-entitlements problem entirely |
| `spctl --master-disable` / disabling Gatekeeper globally in release instructions | Requires admin + a multi-step System Settings dance, and was actually *broken* on macOS 15.1 (regression, fixed in 15.2) — documenting a workaround for a bug that no longer reproduces is bad advice | Document the two normal per-app bypasses instead (see Pitfalls file): right-click → Open (prompts an explicit "Open" confirmation for ad-hoc/unidentified-developer apps), or `xattr -dr com.apple.quarantine /Applications/Open-Anti-Browser.app` as the terminal fallback |

## Python Dependency Handling (`requirements.txt`)

| Change | Before | After | Why |
|--------|--------|-------|-----|
| `pywin32` | `pywin32>=308` (unconditional) | `pywin32>=308; sys_platform == "win32"` | `pywin32` only ships Windows wheels (`win32`/`win_amd64` platform tags) — `pip install -r requirements.txt` **fails outright** on macOS without this marker, since pip has no fallback sdist path for it. This is the literal blocker referenced in the Active requirement "pywin32 条件依赖". |
| `ruyipage` | `ruyipage>=1.0.0` (unconditional) | Leave unconditional, OR mark `; sys_platform == "win32"` if you want to keep it fully out of the macOS environment | `ruyipage` ships a pure-Python `py3-none-any` wheel, so unlike pywin32 it **will install fine on macOS** without a marker — no hard blocker here. The marker is a scope/cleanliness choice (Firefox is out of scope on macOS this milestone), not a build-breaking requirement. If left unconditional, just don't add `--hidden-import ruyipage` to the macOS PyInstaller invocation. |
| `curl_cffi` | `curl_cffi>=0.14.0` | unchanged | Ships prebuilt wheels for macOS arm64 and x86_64 (confirmed on PyPI, e.g. `cp3xx-macosx_11_0_arm64` wheels published through 2026) — no marker or platform-specific handling needed. |
| `PySide6` | `PySide6>=6.9.0` | unchanged | Ships a single `universal2` wheel (`macosx_12_0_universal2`) covering both arm64 and Intel from one `pip install` — no per-arch pip logic needed; PyInstaller will thin it to the target arch when freezing on each runner. Minimum supported macOS is 12.0 (Monterey), well below anything the target runners run. |
| New macOS-only deps | — | None required for the features in scope (profile CRUD, launch, proxy, extensions, batch launch) | No `pyobjc` or other mac-specific packages are needed since window arrangement/sync (the only pieces that would plausibly need native mac APIs) are explicitly disabled on macOS this milestone. Revisit only if a later milestone adds a macOS window-sync equivalent. |

## Installation

```bash
# Unchanged core (same as Windows)
pip install -r requirements.txt   # requirements.txt updated with the sys_platform marker above

# macOS CI job additionally needs (all preinstalled on GitHub-hosted mac runners — nothing to pip/brew install):
#   Xcode Command Line Tools (codesign, hdiutil) — present by default on macos-15 / macos-15-intel images
# No new Python packages, no Homebrew formulas, no Node packages needed for dmg/codesign.
```

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|--------------------------|
| `hdiutil` for dmg creation | `dmgbuild` (Python) | If a later milestone wants a custom background image / icon-position drag-to-Applications layout without Finder/AppleScript flakiness — it's pure Python (fits this repo's stack) and CI-safe, unlike `create-dmg`. |
| `hdiutil` for dmg creation | `create-dmg` (npm or shell script) | Only if the team is fine debugging occasional CI flakiness from its Finder/AppleScript dependency, in exchange for its more turnkey "fancy dmg" templating. Not recommended for this milestone. |
| Ad-hoc `codesign -s -` | Apple Developer ID cert + notarization | Once (if ever) an Apple Developer account ($99/yr) is added — explicitly out of scope per PROJECT.md's Key Decisions this milestone. |
| Cross-building x64 from an arm64 Mac (`target_cpu="x64"`) | Building on a real Intel Mac | Cross-build is simpler (one machine, one Xcode install) and is what Chromium's own toolchain supports; a real Intel Mac would only matter if the cross-built x64 binary showed a runtime issue that only reproduces on native Intel hardware (rare, and testable in a GitHub Actions `macos-15-intel` runner instead of owning Intel hardware). |
| Two arch-specific PyInstaller app builds (one per dmg) | Single universal2 PyInstaller app | Universal2 would shrink CI job count from 2 to 1 for the Python-app-freeze step, but conflicts with the project's own Key Decision to avoid universal binaries, and would still need per-arch kernel bundling logic anyway (the kernel is never universal) — no net simplification. |

## Stack Patterns by Variant

**If a later milestone adds notarization:**
- Add `xcrun notarytool submit` + `xcrun stapler staple` steps after the dmg is created, gated behind an Apple Developer ID being available as a GitHub Actions secret.
- Because notarization requires a real Developer ID certificate for signing (ad-hoc signatures cannot be notarized) — this is a distinct, larger scope change than this milestone's ad-hoc approach.

**If the x64 GitHub-hosted runner disappears (post ~2027) before an Intel dmg is retired:**
- Fall back to cross-building the x64 `.app`/dmg on the arm64 runner using PyInstaller's `--target-arch x86_64` against a universal2 (or x86_64) CPython/PySide6, and code-sign/dmg it the same way.
- Because GitHub has stated x86_64 macOS support ends after the macos-15 image retires — plan the Intel packaging step to not be hard-wired to an Intel runner label forever.

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|------------------|-------|
| PyInstaller >=6.14 | Python 3.11 (this project's pinned interpreter, per `build-release.yml`) | No known incompatibility; PyInstaller 6.x fully supports 3.11 on macOS (arm64 + x64) as of 6.21.0. |
| PySide6 >=6.9.0 (`universal2`) | macOS 12.0+ | Both `macos-15` (arm64) and `macos-15-intel` (x64) runners run far newer OS versions than this floor. |
| Chromium 149 kernel build | Pinned clang `llvmorg-23-init-10931-g20b6ec66-8`, NOT stable LLVM 22.1.0 | Confirmed incompatibility by the sibling repo's own Phase-2 validation (pitfall B-01) — do not "upgrade" to a newer stable LLVM without re-verifying against Chromium's `tools/clang/scripts/update.py` `CLANG_REVISION`. |
| `codesign -s -` (ad-hoc) | arm64 + x64 Mach-O binaries | Ad-hoc signing satisfies the kernel-level "must be signed" requirement introduced for arm64; it does **not** satisfy Gatekeeper's "identified developer" check, which is why the first-launch bypass instructions in PITFALLS.md are still required even after signing. |

## Sources

- [GitHub-hosted runners reference](https://docs.github.com/en/actions/reference/runners/github-hosted-runners) — HIGH confidence, official docs; runner label → architecture table
- [GitHub Actions: macOS 13 runner image is closing down](https://github.blog/changelog/2025-09-19-github-actions-macos-13-runner-image-is-closing-down/) — HIGH confidence, official changelog
- [actions/runner-images#13027 — What's the plan for macOS x86_64?](https://github.com/actions/runner-images/issues/13027) — HIGH confidence, official GitHub Actions team statement on x64 mac EOL (~fall 2027)
- `../fingerprint-chromium/docs/porting-pitfalls.md` (B-01, B-07, B-08, B-09) and `../fingerprint-chromium/docs/porting-runbook.md` (步骤 8-9) — HIGH confidence, first-party validated findings from this project's own sibling repo's Phase-2 macOS cheap-build
- `../fingerprint-chromium/downloads-macos-arm64.ini`, `flags.macos.gn`, `CLAUDE.md` — HIGH confidence, primary source, read directly
- [Chromium mac_build_instructions.md](https://chromium.googlesource.com/chromium/src/+/main/docs/mac_build_instructions.md) — HIGH confidence, official Chromium docs (general SDK/Xcode guidance; does not give exact disk/RAM numbers)
- [PyInstaller CHANGES.html (stable/6.21.0)](https://pyinstaller.org/en/stable/CHANGES.html) and [feature-notes.html](https://pyinstaller.org/en/stable/feature-notes.html) — HIGH confidence, official docs; ad-hoc signing default behavior, arm64/universal2 support, argv_emulation, QtWebEngine qt.conf generation
- [How to Package PySide6 Apps for macOS with PyInstaller (.app & .dmg)](https://www.pythonguis.com/tutorials/packaging-pyside6-applications-pyinstaller-macos-dmg/) — MEDIUM confidence, third-party tutorial, used for `--windowed` COLLECT+BUNDLE behavior confirmation
- [QtWebEngine signing issues (Qt Forum)](https://forum.qt.io/topic/102212/qtwebengine-signing-issues) and [codesign — Unable to sign QtWebEngineProcess with --options runtime](https://forum.qt.io/topic/151688/codesign-unable-to-sign-qtwebengineprocess-with-options-runtime) — MEDIUM confidence, community forum, cross-checked against each other; only relevant if hardened runtime is ever turned on (not needed for ad-hoc signing)
- [pypi.org/project/curl-cffi](https://pypi.org/project/curl-cffi/) — HIGH confidence, official package index, confirms macOS arm64/x64 wheel availability
- [ordonez.tv — How to run unsigned apps in macOS 15.1](https://ordonez.tv/2024/11/04/how-to-run-unsigned-apps-in-macos-15-1/) and [OSnews — Bug or intentional? macOS 15.1 completely removes ability to launch unsigned applications](https://www.osnews.com/story/141055/bug-or-intentional-macos-15-1-completely-removes-ability-to-launch-unsigned-applications/) — MEDIUM confidence, community-sourced; cross-checked, confirms this was a 15.1 regression fixed in 15.2, not the current permanent behavior
- pip / PEP 508 environment markers (`sys_platform == "win32"` / `"darwin"`) — HIGH confidence, standard documented pip behavior

---
*Stack research for: macOS (arm64 + Intel x64) packaging/distribution addition to Open-Anti-Browser*
*Researched: 2026-07-23*
