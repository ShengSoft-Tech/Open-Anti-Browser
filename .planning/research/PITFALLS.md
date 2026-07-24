# Pitfalls Research: macOS Packaging & Distribution (Bundled Chromium + PyInstaller + Unsigned DMG)

**Domain:** Desktop app packaging — bundling a Chromium-based browser kernel inside a PyInstaller .app, distributed as an unsigned DMG via GitHub Actions CI
**Researched:** 2026-07-23
**Confidence:** MEDIUM (web search cross-referenced across GitHub issues, Apple Developer Forums, PyInstaller official docs, ungoogled-chromium-macos README; no first-party Apple platform-security spec fetched verbatim, no hands-on repro on this exact repo)

## Critical Pitfalls

### Pitfall 1: Naive zip/upload-artifact silently corrupts the Chromium.app bundle structure

**What goes wrong:**
`zip`/`Expand-Archive`-style tooling and GitHub Actions' `actions/upload-artifact` do not reliably preserve the symlinks that macOS app bundles and frameworks depend on (e.g. `Chromium Framework.framework/Versions/Current` → `Versions/149.0.x.x`, and the top-level `Versions/Current`, `Resources`, `Libraries`, `Helpers` symlinks inside each `.framework`). Reports show `upload-artifact` uploading only the `Contents` folder of a `.app`, symlinks landing as broken links or plain files, and zip losing POSIX permissions entirely (zip has no real permission/symlink model — it emulates it inconsistently across implementations).

**Why it happens:**
Zip's symlink support is an optional, poorly-standardized extension; different zip implementations (Python's `zipfile`, Windows `Expand-Archive`, some CI zip binaries) either drop symlinks, dereference them (duplicating framework payloads and breaking `Versions/Current` indirection), or store them but restore them incorrectly on a different OS/tool. GitHub Actions' `upload-artifact` v4 changed symlink handling between minor versions, so behavior isn't even stable release-to-release.

**How to avoid:**
- Never zip/tar a `.app` with default `zip -r` or `Expand-Archive`. Use `ditto -c -k --keepParent Chromium.app Chromium.zip` (Apple's own tool, correctly preserves symlinks, xattrs, resource forks) or `tar -czf` (bsdtar preserves symlinks by default) for every stage: local build output → GitHub Release asset, and Release asset → CI download → embed in PyInstaller bundle.
- When uploading via `actions/upload-artifact` (e.g. an intermediate CI artifact, not the final release asset), first `ditto`/`tar` the `.app` into a single archive **file** and upload that file, not the raw directory tree. Reverse the same way on download.
- After any extraction step in CI, verify structure with `find Chromium.app -type l -exec test -e {} \; -print` (lists symlinks) or `codesign -dv --verbose=4 Chromium.app` (fails loudly if the framework layout is broken).

**Warning signs:**
- App launches with dyld errors like "Library not loaded" or "no such file" referencing a `.framework/Versions/...` path.
- `codesign --verify --deep --strict Chromium.app` reports "resource missing" or "bundle format unrecognized".
- Extracted bundle size is unexpectedly larger than the original (symlinks got dereferenced/duplicated) or `Versions/Current` is a real directory instead of a symlink.

**Phase to address:**
Phase that builds the macOS CI job (kernel download + `.app` extraction) and the phase that produces the local kernel release asset — both must standardize on `ditto`/`tar`, never plain `zip`.

---

### Pitfall 2: Copying/repackaging the Chromium.app invalidates its code signature → "Killed: 9" on Apple Silicon

**What goes wrong:**
Apple Silicon (arm64) enforces that **every** executable — including ones a user builds locally — carry at least an ad-hoc code signature before the kernel will run it. Any post-build modification (re-zipping with a tool that strips extended attributes, editing a plist inside the bundle, copying with `cp` in a way that drops the signature's covered resources, or the PyInstaller build process touching files inside the embedded `Chromium.app`) invalidates the existing seal. The symptom is stark and unhelpful: the process is silently `SIGKILL`ed, printing only `Killed: 9` with no further diagnostic, at launch time — not at packaging time.

**Why it happens:**
Code signing on macOS covers a bundle's `_CodeSignature/CodeResources` manifest (hashes of all bundled files) plus the Mach-O binary's embedded signature. Since arm64 macOS refuses to `exec()` an unsigned/invalidated Mach-O, any pipeline step that touches bytes inside the signed bundle after it was signed (including some archive tools, some `--add-data` copy steps, and notably PyInstaller potentially re-writing/relinking library paths with `install_name_tool` during binary collection) breaks the seal without any build-time error.

**How to avoid:**
- Treat "sign last, after every mutation" as a hard rule: if the CI pipeline moves, chmods, or otherwise touches files inside `Chromium.app` after it was fetched from the release asset, re-sign it before packaging into the DMG.
- Re-sign inside-out: `find Chromium.app -name "*.framework" -o -name "Helpers" -o -name "*.app"` then sign each nested item first, then the outer bundle last (see Pitfall 5 for the exact ordering). Use `codesign --force -s - <path>` per item — **avoid** `--deep` (Apple has deprecated it; it applies the same options to everything and frequently mis-signs or skips helper apps in complex bundles like Chromium's).
- After signing, verify with `codesign --verify --deep --strict --verbose=2 Chromium.app` and `spctl -a -vv Chromium.app` (the latter simulates Gatekeeper's actual assessment, which is a stricter check than `codesign --verify` alone).
- Because this project already builds the kernel once locally on a Mac and just re-distributes the zip, minimize the number of extraction/repackaging hops between "signed on build machine" and "embedded in DMG" — every hop is a chance to break the seal, especially the CI download-and-embed step.

**Warning signs:**
- The bundled Chromium launches fine on the build Mac (already correctly signed there) but fails silently (`Killed: 9`, exit code 137, or no window at all) on other machines/architectures after CI repackages it.
- `codesign -dv Chromium.app` reports "code object is not signed at all" or a hash mismatch, or `spctl` reports "rejected".
- Failure is architecture-specific: identical pipeline works on Intel x64 (unsigned code can still execute there) but fails on Apple Silicon.

**Phase to address:**
The macOS CI packaging phase (download kernel asset → embed in PyInstaller .app → build DMG) needs an explicit "verify + re-sign if needed" step, tested on an arm64 runner specifically (not just x64).

---

### Pitfall 3: Quarantine + Gatekeeper block the bundled Chromium subprocess even after the user "allows" the outer app

**What goes wrong:**
When a user downloads the DMG from a browser, macOS tags the DMG (and everything extracted from it, including nested app bundles) with the `com.apple.quarantine` extended attribute. Right-clicking the outer PyInstaller `.app` and choosing "Open" (the standard unsigned-app workaround) only clears/approves Gatekeeper's assessment for that top-level bundle launch — it does **not** necessarily clear quarantine on every nested executable. Since this app spawns `Contents/MacOS/Chromium` (or wherever the bundled fingerprint-chromium kernel lives inside `Contents/Resources` or `Contents/Frameworks`) as a **subprocess**, that nested binary can itself independently trip Gatekeeper/quarantine checks the first time it's `exec()`'d, producing a confusing second-order failure that looks like "the app opened, but clicking Launch Profile does nothing" or a Gatekeeper dialog appears with no obvious "open anyway" affordance because it's not a Finder-initiated launch.

**Why it happens:**
`com.apple.quarantine` is propagated recursively by Archive Utility/DMG mount to every file extracted/copied, and Gatekeeper's runtime check (`spctl`) fires per-execution for quarantined, unsigned-or-untrusted binaries — not just once per app. A subprocess launch via Python's `subprocess.Popen` bypasses the Finder "right-click → Open" user-consent flow entirely, so there is no way for the end user to interactively approve the nested Chromium binary the way they approved the outer app.

**Why it happens (secondary — App Translocation):**
If the outer `.app` is launched directly from a mounted, unmoved DMG or from a random unarchived location without ever being copied into `/Applications` via Finder, macOS may run it under **App Translocation** (Gatekeeper Path Randomization): the app executes from a synthetic read-only location, and any code that resolves paths relative to the "real" install location (e.g. writing to a sibling `engines/` directory, or resolving `sys.executable`'s parent for `ENGINES_DIR`) can silently point at the wrong place or fail with permission errors.

**How to avoid:**
- After extracting/building the DMG contents, recursively clear quarantine from **everything embedded**, not just the outer bundle, as part of first-run handling or documented user instructions: `xattr -dr com.apple.quarantine /Applications/Open-Anti-Browser.app` (recursive `-r` covers the bundled Chromium and its helpers). Document this exact command in the release notes as the primary unblock step — it's more reliable for an unsigned bundled subprocess than "right-click → Open", which mainly targets the outer bundle.
- Since re-signing at least ad-hoc (Pitfall 2) makes Gatekeeper's assessment of the nested binary succeed even if quarantined (ad-hoc signed + Gatekeeper still prompts once but allows override), prefer "ad-hoc sign everything" over "rely purely on xattr stripping", since users may re-quarantine by re-downloading or moving the app via Finder.
- Instruct users to drag the app to `/Applications` via Finder (not `mv` in Terminal) before first launch, to sidestep App Translocation; or have the app avoid relying on "path relative to installed location" assumptions that break under translocation (verify `ENGINES_DIR`/`APP_ROOT` resolution works even from a translocated read-only path — on macOS this likely means writable data must go to `~/Library/Application Support/<AppName>` rather than a sibling-to-executable directory, unlike the current Windows LOCALAPPDATA-sibling assumption in `config.py`).

**Warning signs:**
- Users report the app opens but "Launch" does nothing, with no visible error (the Chromium subprocess died to Gatekeeper before any window appeared).
- Console.app / `log show --predicate 'eventMessage contains "Chromium"'` shows Gatekeeper (`com.apple.security.syspolicy`) denial entries around the time of the failed launch.
- Behavior differs between a freshly downloaded DMG (still quarantined) and a rebuilt/copied local `.app` (quarantine already stripped by the developer's own workflow) — a classic "works on my machine" trap since the developer's own Mac won't reproduce it.

**Phase to address:**
The macOS distribution/release-notes phase must document the `xattr -dr` recursive command (not just "right-click Open"), and the packaging phase should ad-hoc sign the whole tree (Pitfall 2) so Gatekeeper's per-binary check has something valid to trust even under quarantine.

---

### Pitfall 4: PyInstaller's onedir-in-.app layout, symlink handling, and LSUIElement interact badly with an embedded Chromium

**What goes wrong:**
Several independent traps stack up when PyInstaller builds a `.app` around a Python backend + PySide6/QWebEngine shell that also carries a bundled Chromium kernel as extra payload:
- PyInstaller ≥6.0 uses symlinks inside onedir builds on **all** POSIX platforms (not just the `.app` bundle step), so the intermediate onedir output must be copied only with symlink-preserving tools (`cp -fR`, not assuming `-fr` preserves them) and must live on a filesystem that supports symlinks (an issue if any CI step stages files through a non-POSIX-preserving mechanism, e.g. a naive `shutil.copytree` without `symlinks=True`, or Docker volume mounts with odd fs semantics).
- `--add-data` used to inject the bundled Chromium kernel into the `.app` does not automatically get the same symlink-aware treatment as PyInstaller's own binary collection — if fed a raw `Chromium.app` tree via `--add-data`, nested framework symlinks can be silently dereferenced/duplicated by PyInstaller's own file-collection step, independent of the CI-download zip issue in Pitfall 1.
- UPX compression (if enabled in the spec for the Python binaries) fails `codesign` validation on macOS and must be disabled (`upx=False`) whenever the output needs any signing (including ad-hoc).
- `LSUIElement`/dock-icon customization in Info.plist can be silently overridden by PyInstaller's bootloader re-parenting the process (a known PyInstaller bootloader quirk), which matters if the roadmap wants any "hide dock icon while backend-only mode runs" behavior analogous to the Windows headless/backend-only mode.

**Why it happens:**
PyInstaller's macOS bundling code treats symlinks as a first-class feature to satisfy Apple's `.app`/framework conventions, but this only reliably applies to files PyInstaller itself discovers and collects via its dependency analysis — arbitrary trees pulled in via `--add-data` (like a whole embedded browser) are copied more literally and are a secondary point where the Pitfall 1 symlink problem can reappear even after a correct `ditto` unzip.

**How to avoid:**
- Prefer embedding the Chromium kernel as a **post-build copy step** in the CI pipeline (copy the already-`ditto`-extracted `Chromium.app` into `Contents/Resources/engines/chrome/` of the PyInstaller output *after* PyInstaller finishes, using `ditto` again) rather than routing it through PyInstaller's `--add-data`/spec-file collection machinery, to keep the two symlink-preservation problems (PyInstaller's and the archive's) independent and each individually verifiable.
- Set `upx=False` in the `.spec` for the macOS build target (mirrors the existing Windows `.spec`, just gated by platform) since this repo will need to sign at least ad-hoc.
- After the full `.app` is assembled (Python backend + Qt + bundled Chromium), run one final `codesign --verify --deep --strict` pass over the **entire** outer bundle as a build-time gate in CI, not just eyeballing that it launches — catches both PyInstaller-introduced and archive-introduced symlink/signature breakage before it reaches users.
- If backend-only / hidden-window behavior is ever added for macOS, test `LSUIElement` behavior specifically against the PyInstaller-built binary (not just a dev-mode `python launch_app.py` run), since the bootloader re-parenting quirk is bootloader-specific.

**Warning signs:**
- `.app` launches in dev-mode testing (`python launch_app.py` directly) but fails when run from the PyInstaller-built bundle, specifically around the embedded Chromium path.
- Bundle size after PyInstaller build is much larger than `du -sh` of the pre-build Chromium.app (indicates framework symlinks got dereferenced during collection).
- `codesign --verify --deep --strict` on the final `.app` fails only at nested paths under the embedded engine directory, not the main executable.

**Phase to address:**
The PyInstaller macOS packaging phase; add a CI verification step (`codesign --verify --deep --strict` + `spctl -a`) as a hard gate before producing the DMG.

---

### Pitfall 5: Chromium's own nested Helper.app bundles need inside-out signing order — `--deep` gets it wrong

**What goes wrong:**
A full Chromium/ungoogled-chromium `.app` is not one signed unit — it contains multiple nested `*.app` bundles (e.g. `Chromium Helper.app`, `Chromium Helper (GPU).app`, `Chromium Helper (Renderer).app`, `Chromium Helper (Plugin).app`, `Chromium Helper (Alerts).app`) plus `.framework` bundles, each independently signed in the original build. If this project's pipeline ever needs to re-sign the kernel (e.g. after Pitfall 1/4 style repackaging broke the seal), naively running `codesign --force --deep -s - Chromium.app` on just the outer bundle is unreliable: Apple has deprecated `--deep` specifically because it applies one signing identity/options blindly to everything nested, frequently signing things in the wrong order or skipping/mis-signing a helper, producing a bundle that passes a shallow `codesign --verify` but fails Gatekeeper's fuller assessment or fails at the exact moment a helper process (GPU/renderer) is spawned at runtime.

**Why it happens:**
Code signing must be applied inside-out — every nested framework and helper app signed first, then the containing bundle signed last — because the outer bundle's signature covers hashes of everything inside it; signing outer-first (or via `--deep`'s non-deterministic-looking traversal) can seal in stale/incorrect nested hashes.

**How to avoid:**
- If re-signing is ever necessary in this pipeline (ideally it isn't, if Pitfall 1/2's "never touch bytes after signing" discipline holds), script it explicitly inside-out: sign every `.framework`, then every nested `Helpers/*.app` / `*.app` inside `Contents/Frameworks/*.framework/Versions/*/Helpers/`, then the outer `Chromium.app` last — never rely on `--deep` for a bundle this complex.
- Prefer to avoid needing to re-sign at all: keep the "sign once at local build time, never mutate bytes afterward" discipline from Pitfall 2, since Chromium's nested-helper signing complexity makes re-signing correctly non-trivial and easy to get subtly wrong in ways that only show up as runtime helper-process crashes (GPU process crash loops, renderer sandbox failures) rather than a clean launch failure.
- If re-signing is unavoidable (e.g. CI must strip+reapply after a repackage step), reference `ungoogled-chromium-macos`'s own build/sign scripts as the concrete inside-out ordering example, since it already solves exactly this problem for the same Chromium codebase family this project forks its fingerprint patches from.

**Warning signs:**
- Main Chromium window opens but tabs are blank/white, or GPU-accelerated content fails, or the renderer process repeatedly crashes — symptomatic of a helper process failing its own Gatekeeper/signature check, not the main binary.
- `codesign --verify` on the outer bundle passes, but `codesign --verify` run explicitly against a nested `Helpers/*.app` path fails.

**Phase to address:**
Only relevant if the macOS CI pipeline includes a re-signing step; document as a hard constraint ("do not re-sign; only re-verify") in the kernel-packaging phase, and as a fallback recipe in the CI troubleshooting notes if re-signing ever becomes unavoidable.

---

### Pitfall 6: fingerprint-chromium launch semantics differ from the Windows `chrome.exe` path assumptions baked into `chrome.py`/`config.py`

**What goes wrong:**
The existing Windows code (`backend/services/chrome.py`, `backend/config.py`) hardcodes `chrome.exe` as the executable filename (`DEFAULT_CHROME_EXECUTABLE = ENGINES_DIR / "chrome" / "chrome.exe"`) and launches it as a plain subprocess with `--user-data-dir`, `--remote-debugging-port`, `--no-first-run`, `--fingerprint=<seed>`, etc. On macOS, the real executable is nested at `Chromium.app/Contents/MacOS/Chromium` (no `.exe` extension, different directory depth), and launching must go **directly at that binary path** via `subprocess.Popen([str(binary_path), *args], ...)` — never via `open -a Chromium.app --args ...`, because `open` hands the launch off to `NSWorkspace`/`launchd`, which (a) does not reliably forward all CLI args (some are silently dropped or altered, especially under sandboxing), (b) detaches stdout/stderr and process-group relationship from the Python parent, breaking this project's psutil-based liveness tracking and the CDP debugging port discovery flow that depends on knowing the exact child PID, and (c) can itself be independently subject to a Gatekeeper/quarantine check on the `.app`, compounding Pitfall 3. Additionally, macOS `--no-first-run` / first-run behaviors and `--user-data-dir` handling have historically had platform-specific quirks in Chromium (e.g. first-run dialogs or default-browser prompts appearing despite the flag, differing from Windows/Linux) that should be explicitly tested rather than assumed to "just work" identically.

**Why it happens:**
The current codebase was written Windows-first and both the path-construction logic (`ENGINES_DIR / "chrome" / "chrome.exe"`) and the process-supervision model (direct `Popen` + psutil PID tracking + CDP over a known port) implicitly assume a flat, single-executable Windows layout. `.app` bundles are directory trees; the platform-idiomatic way to "launch" one (`open`) is specifically the wrong tool for a supervised, arg-passing, PID-tracked automation use case.

**How to avoid:**
- Add a `bundled_engine_executable("chrome")` macOS branch that resolves to `.../engines/chrome/Chromium.app/Contents/MacOS/Chromium` (exact binary name depends on the fork's product name — verify against the actual built `Info.plist`'s `CFBundleExecutable`), not a bare `.exe`-suffixed path.
- Always launch via the direct binary path in `subprocess.Popen`, never `open -a`, to preserve arg-passing fidelity and PID/process-group relationship needed by `runtime_sessions` tracking and the CDP client.
- Verify empirically on macOS (both arm64 and x64 runners/dev machines) that `--user-data-dir`, `--no-first-run`, `--no-default-browser-check`, and `--remote-debugging-port` behave identically to Windows for this specific fork — do not assume upstream Chromium's documented cross-platform flag parity holds for a heavily patched fingerprint fork; regression-test the CDP port actually opening and being reachable (some Chromium versions restrict `--remote-debugging-port` to loopback-only with stricter `Host:` header checks that can behave differently per platform build).
- Audit `runtime_control.py`'s use of Windows-only process-creation flags (`DETACHED_PROCESS`, `CREATE_NEW_PROCESS_GROUP`) — these must be conditionally branched for macOS (e.g. `start_new_session=True` / `os.setsid` equivalents), since the "pure backend mode" detached-process design is part of this same launch pipeline.

**Warning signs:**
- Chrome window never appears despite the process apparently starting (symptomatic of `open -a` detaching from the tracked PID, or of the wrong nested binary path silently no-op'ing).
- CDP WebSocket connection (used by the window synchronizer and geo-resolution self-check) times out only on macOS, never on Windows, for what looks like the same profile config.
- `psutil`-based liveness checks report the profile as "stopped" immediately after launch (because the tracked PID was `open`'s short-lived launcher process, not the actual long-running Chromium process).

**Phase to address:**
The "macOS core functionality" phase (config CRUD, fingerprint launch, proxy, extensions, batch launch on Chrome engine) — this is the central cross-platform adaptation phase and must include explicit macOS launch-path and process-supervision testing, not just "port the Windows code path with an if/else on file extension."

---

### Pitfall 7: Local Chromium build traps (disk space, Xcode/SDK, cross-arch) silently waste hours or produce a subtly broken kernel

**What goes wrong:**
Building ungoogled-chromium (with fingerprint patches) locally on a Mac has several build-time traps distinct from the packaging pitfalls above: Chromium's source checkout + build artifacts commonly require 100–500GB of free disk depending on `is_debug`/`symbol_level` settings (out/Default alone can be 40GB+, and running out of space mid-link produces confusing partial-build errors rather than a clean "disk full" message); Xcode/SDK version mismatches (Chromium's mac build docs pin expected Xcode/SDK versions, and newer/older-than-expected Xcode can fail `gn gen` or produce build errors deep in the toolchain rather than an obvious version-check error); and cross-building x86_64 on an Apple Silicon host, while supported (e.g. ungoogled-chromium-macos's `./build.sh x86_64` pattern, or setting `target_cpu = "x86_64"` in `args.gn`), is a secondary configuration most build docs/scripts don't exercise by default, so it's easy to accidentally produce and ship an arm64-only build for both release assets, or to get a wrong-architecture-labeled but actually-native-arch zip if the build script isn't explicitly parameterized per architecture in this project's local build process.

**Why it happens:**
Chromium's build system (GN + Ninja) is not disk-space-aware and doesn't pre-check available space before starting a multi-hour build; Xcode/SDK requirements shift across Chromium versions and aren't always cross-checked against the locally installed toolchain; and because this project builds both arm64 and x64 kernels from the same source tree on (presumably) a single Apple Silicon dev machine, it's easy to forget to re-set `target_cpu` / re-run `gn gen` with a distinct output directory per architecture, silently overwriting or reusing stale build config between the two builds.

**How to avoid:**
- Confirm free disk space (roughly 150GB+ safety margin) before starting each of the two (arm64, x64) local builds; use separate `out/arm64-Release` and `out/x64-Release` GN output directories so builds don't collide or leave stale cross-arch object files.
- Pin the exact Xcode version this fork's build docs expect (the sibling `../fingerprint-chromium` repo's `flags.macos.gn` / `downloads-macos-arm64.ini` should specify or imply a tested Xcode/SDK combination) before starting a fresh build environment, and install the Metal toolchain component explicitly if using a recent Xcode (`xcodebuild -downloadComponent MetalToolchain`), since some Chromium mac toolchains require it, and skipping it fails obscurely mid-build.
- After each architecture's build completes, verify the produced binary's actual architecture before zipping/uploading (`file Chromium.app/Contents/MacOS/Chromium` should report `arm64` or `x86_64` respectively; `lipo -info` for extra certainty) — do not trust the output directory name alone as proof of which architecture was actually produced, in case a stale `args.gn` from a previous build leaked through.
- Budget wall-clock time generously (multi-hour full builds per architecture are normal for Chromium) and treat the "wipe `build/downloads_cache` for download failures, wipe `build/src` for post-download failures" recovery pattern (used by ungoogled-chromium-macos) as the expected troubleshooting playbook rather than a sign something is fundamentally wrong.

**Warning signs:**
- Build fails partway through linking with vague errors (frequently a disk-space symptom, not the error message's literal claim).
- `gn gen` fails immediately with toolchain-detection errors right after installing/upgrading Xcode.
- The x64 build directory, when inspected with `file`/`lipo`, turns out to actually be arm64 (stale `args.gn` from the previous native build wasn't reset).

**Phase to address:**
The "macOS kernel: build arm64 and x64 from `../fingerprint-chromium`, upload to kernel release" phase — this is entirely pre-CI, local-machine work and should include an explicit architecture-verification step before the zip is uploaded as a release asset, since a wrong-architecture asset will only be caught much later (CI download + app launch failure on the affected architecture) if not checked at the source.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|--------------------|-----------------|------------------|
| Skip re-signing entirely, rely only on `xattr -dr` quarantine stripping | Simpler pipeline, no codesign scripting needed | Breaks specifically on Apple Silicon where an ad-hoc signature is mandatory regardless of quarantine state (Pitfall 2) — will manifest as arm64-only "Killed: 9" bug reports | Never for arm64 target; borderline-acceptable for x64-only if truly never testing/shipping arm64 |
| Route the embedded Chromium through PyInstaller `--add-data` instead of a post-build `ditto` copy | One fewer manual CI step | Re-introduces the symlink-dereference risk inside PyInstaller's own collection logic (Pitfall 4), compounding with Pitfall 1 | Acceptable only if a `codesign --verify --deep --strict` CI gate is added to catch corruption regardless of source |
| Use `codesign --force --deep -s -` as a blanket "just fix signing" step whenever something is broken | Fast, one command, often "seems to work" | Deprecated approach, wrong signing order on nested helpers (Pitfall 5), can mask (not fix) the real corruption from Pitfall 1/4 | Never as a first response; acceptable only as a documented last-resort recipe if inside-out manual signing genuinely isn't feasible |
| Ship only an arm64 dmg first, defer x64 | Faster to ship v0.2, most current Macs are Apple Silicon | Explicitly out of scope per PROJECT.md decision (both required) — but noted here since it's a common shortcut teams take under time pressure | Only if the milestone scope is explicitly renegotiated; PROJECT.md currently requires both |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|-----------------|-------------------|
| GitHub Actions macOS runner + kernel release asset download | Downloading and unzipping the kernel zip with a generic `unzip`/`Expand-Archive`-equivalent step in the workflow YAML | Use `ditto -x -k <zip> <dest>` (or `tar`) explicitly in the workflow, never the default `actions/download-artifact` + implicit unzip if that path is ever used for the `.app` itself |
| PyInstaller `.spec` shared between Windows and macOS | Copy-pasting the Windows `.spec` and adding an `if sys.platform == "darwin"` patch after the fact, missing `upx=False` or the `BUNDLE()` macOS-specific block | Author the macOS `.spec` target explicitly with `BUNDLE(..., info_plist={...})`, `upx=False`, and its own `Info.plist` keys from the start, reviewed independently of the Windows target |
| DMG creation for distribution | Using `hdiutil create` with default UDIF but not verifying the DMG mounts and the app inside still passes `codesign --verify`/`spctl` after DMG round-trip | Build the DMG as the very last step from the fully-signed/verified `.app`, then do one final mount-and-verify pass on the DMG's contents in CI before uploading it as a release asset |
| `backend/_g.py` integrity check at desktop launch | Assuming the macOS build process won't touch `frontend/dist` output in a way that changes hashes (e.g. macOS line-ending normalization via some archive tool, or a different Node/Vite version producing different build output) | Run the exact same `npm run build` toolchain/versions used to generate the locked hashes, and run `_7("runtime")`'s check in CI as a build-gate on macOS too, not just assume it passes because it passes on Windows |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|-----------------|
| Multi-hour local Chromium builds treated as a "just re-run it" step | Local build iteration becomes the bottleneck for every kernel version bump | Cache `build/downloads_cache` across builds; only wipe `build/src` when truly necessary; keep arm64/x64 outputs in separate `out/` dirs so a re-build of one doesn't invalidate the other's ninja cache | Every time a kernel version is bumped, if disk/cache hygiene isn't maintained from the start |
| CI job downloading a large kernel zip (100MB+ typical Chromium build size) on every run without caching | Slow CI, GitHub Actions minutes cost, occasional download flakiness treated as random | Cache the downloaded kernel zip keyed by kernel version/URL in the GH Actions cache, only re-download on version bump | Noticeable once CI runs become frequent (multiple pushes/day) |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Documenting "disable Gatekeeper globally" (`spctl --master-disable`) as the unblock instruction instead of a scoped per-app fix | Trains users to globally weaken macOS security, and the instruction itself may alarm security-conscious users away from the product | Document only the scoped `xattr -dr com.apple.quarantine <path>` and/or right-click-Open for the specific installed app, never global Gatekeeper disable |
| Treating "unsigned but ad-hoc signed" as equivalent to "notarized/Developer-ID signed" in release notes | Understates real risk to users (ad-hoc signing provides no identity verification, just satisfies the arm64 execution requirement) — could create false trust | Be explicit in release notes that the app is unsigned/not notarized and explain exactly why (no Apple Developer Program membership), consistent with the PROJECT.md decision already made |
| Bundling a full Chromium browser inside an unsigned, unnotarized distribution | Users' own security tooling (antivirus, MDM policies) may flag or block the DMG/app more aggressively than a small unsigned utility, since it looks like "unknown browser executable from unverified source" | Ad-hoc sign consistently (Pitfall 2) so at least Gatekeeper's baseline check passes; be prepared for some corporate/MDM-managed Macs to block it entirely regardless, and document that limitation |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|--------------|-------------------|
| Only documenting "right-click → Open" without the recursive `xattr` step | User successfully opens the outer app, then hits a silent failure when clicking "Launch Profile" (Pitfall 3), with no idea why, and no error surfaced in the UI | Document both steps; additionally, have the backend detect a Chromium launch failure that looks like a Gatekeeper kill (process exits near-instantly, exit code pattern) and surface a macOS-specific in-UI hint pointing at the exact `xattr` command |
| Silently disabling window-sync/arrangement features on macOS with no UI indication | Users familiar with the Windows version wonder if the feature is broken vs. intentionally unavailable | Explicit UI messaging ("仅 Windows" as already planned in PROJECT.md) rather than just hiding the buttons with no explanation |
| No feedback while the app is quarantined/blocked and the window simply never appears | User assumes the app is broken/crashed rather than blocked by a one-time OS gate | Where technically feasible, a short first-run helper/README step-through (even just a clear DMG README file with the exact commands) reduces support burden vs. relying on users to search for "app can't be opened mac" |

## "Looks Done But Isn't" Checklist

- [ ] **DMG builds and mounts locally on the CI runner's own Mac:** Often not verified against a *different* Mac (esp. a fresh/clean macOS install without prior dev tooling) — verify on a machine that never had the build toolchain installed, to catch quarantine/Gatekeeper issues the developer's own machine won't reproduce.
- [ ] **Bundled Chromium launches from the CI-produced DMG, not just from the locally-built kernel zip:** Verify by actually mounting the CI-produced DMG artifact end-to-end (download → mount → drag to /Applications → launch → create profile → start Chrome profile), not just confirming the CI job "succeeded" (a green CI check only proves the build/zip steps ran, not that Gatekeeper/quarantine/signature survive the full round trip).
- [ ] **Both arm64 and x64 dmgs tested on their respective native architecture:** Easy to test only on the arm64 dev machine (via Rosetta for the x64 build, which can mask arm64-specific ad-hoc-signature-required failures that wouldn't occur under Rosetta emulation the same way).
- [ ] **CDP-based features (window sync foundation, geo self-check probing) verified over the bundled macOS kernel's actual debugging port behavior:** Not just assumed identical to Windows because the command-line flags look the same.
- [ ] **`backend/_g.py` integrity check passes in the macOS PyInstaller-built app at runtime,** not just in dev-mode — the hash-locked files/build-marker check must be exercised against the actual macOS-built `frontend/dist`.
- [ ] **Uninstall/reinstall path (dragging a new version's .app over an old one in /Applications) doesn't leave stale quarantine-cleared-but-now-newly-quarantined state confusion** for users upgrading between releases.

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|-----------------|------------------|
| Broken symlinks/signature discovered after a release is already published | MEDIUM | Re-run the local build → zip-with-ditto → re-upload kernel release asset → re-run CI packaging job → publish a patch release; no source rebuild needed if only the *packaging* step was at fault, not the Chromium build itself |
| Local Chromium build itself is broken/wrong-architecture | HIGH | Requires a full re-build (hours) of the affected architecture; verify with `file`/`lipo` before re-uploading to avoid a second wasted release cycle |
| Users stuck on Gatekeeper block despite documented instructions | LOW | Provide the exact terminal commands (`xattr -dr com.apple.quarantine /Applications/Open-Anti-Browser.app`) in a pinned release-notes/FAQ section; this is a one-time, low-cost fix per affected user once documented clearly |
| CI job passes but arm64-specific "Killed: 9" reported by users | MEDIUM | Add an explicit arm64 runner smoke-test step (launch the built .app headlessly, verify the Chrome subprocess actually starts and CDP port opens) to CI so this class of regression is caught before release, not after |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|--------------------|----------------|
| Naive zip/upload-artifact corrupts .app (Pitfall 1) | macOS kernel build/upload phase + macOS CI packaging phase | CI step runs `codesign -dv --verbose=4` and a symlink-integrity check on the extracted Chromium.app before proceeding |
| Signature invalidation → Killed: 9 on arm64 (Pitfall 2) | macOS CI packaging phase | CI gate: `codesign --verify --deep --strict` + `spctl -a -vv` on the assembled .app, on an arm64 runner specifically |
| Quarantine/Gatekeeper blocks bundled subprocess (Pitfall 3) | macOS distribution/release-notes phase | Manual smoke test: download DMG fresh on a clean/unrelated Mac, follow only the documented instructions, confirm profile launch succeeds |
| PyInstaller onedir/symlink/LSUIElement traps (Pitfall 4) | PyInstaller macOS packaging phase | CI step: `codesign --verify --deep --strict` on final .app; manual check that embedded kernel directory size matches expected (no dereferenced duplication) |
| Nested Helper.app signing order (Pitfall 5) | Only if re-signing step exists; document in kernel-packaging phase as "do not re-sign" constraint | If re-signing script exists, verify each nested Helper.app independently with `codesign --verify`, not just the outer bundle |
| Windows-assumption launch semantics (chrome.exe, `open -a`, DETACHED_PROCESS) (Pitfall 6) | Backend cross-platform adaptation / "macOS core functionality" phase | Functional test: start a Chrome profile on macOS, confirm psutil liveness tracking, CDP connection, and process termination all behave like the Windows equivalents |
| Local Chromium build traps: disk, Xcode/SDK, cross-arch (Pitfall 7) | macOS kernel build phase (local, pre-CI) | `file`/`lipo -info` check on both produced binaries before uploading as release assets; documented disk-space and Xcode-version prerequisites |

## Sources

- [actions/upload-artifact#38 — permissions not retained](https://github.com/actions/upload-artifact/issues/38)
- [actions/upload-artifact#326 — macOS .app becomes folder](https://github.com/actions/upload-artifact/issues/326)
- [actions/upload-artifact#581 — only Contents of .app uploaded](https://github.com/actions/upload-artifact/issues/581)
- [actions/upload-artifact#590 — symlinks preserved by default (behavior change)](https://github.com/actions/upload-artifact/issues/590)
- [ditto vs zip vs tar on macOS](https://torstencurdt.com/tech/ditto-vs-zip/)
- [macOS distribution — code signing, notarization, quarantine gist](https://gist.github.com/rsms/929c9c2fec231f0cf843a1a746a416f5)
- [Apple Developer Forums — macOS app distributed via ZIP cannot open](https://developer.apple.com/forums/thread/818269)
- ["Killed: 9" getting codesigning to work on Apple Silicon (conda-pack)](https://uwekorn.com/2024/03/11/getting-codesigning-to-work-on-apple-silicon.html)
- [Apple Developer Forums — Killed: 9 for signed binary](https://developer.apple.com/forums/thread/688261)
- [Handling macOS Gatekeeper as an unsigned indie dev — xattr struggle](https://dev.to/hiyoyok/handling-macos-gatekeeper-as-an-unsigned-indie-dev-the-xattr-struggle-1028)
- [Eclectic Light Co — Quarantine and the quarantine flag](https://eclecticlight.co/2020/10/29/quarantine-and-the-quarantine-flag/)
- [Eclectic Light Co — Lost in Translocation](https://eclecticlight.co/2024/05/14/lost-in-translocation/)
- [App Translocation (lapcatsoftware.com)](https://lapcatsoftware.com/articles/app-translocation.html)
- [PyInstaller — Common Issues and Pitfalls (official docs)](https://pyinstaller.org/en/stable/common-issues-and-pitfalls.html)
- [PyInstaller #1917 — doesn't respect LSUIElement=1 on macOS](https://github.com/pyinstaller/pyinstaller/issues/1917)
- [PyInstaller #7191 — improvements to generated macOS app bundles](https://github.com/pyinstaller/pyinstaller/issues/7191)
- [PythonGUIs — Packaging PySide6 apps for macOS with PyInstaller](https://www.pythonguis.com/tutorials/packaging-pyside6-applications-pyinstaller-macos-dmg/)
- [codesign inside-out signing order / --deep deprecated discussion](https://developer.apple.com/forums/thread/661852)
- [electron-builder #8966 — nested code is modified or invalid](https://github.com/electron-userland/electron-builder/issues/8966)
- [ungoogled-chromium-macos README (build/sign/dmg process, cross-arch build.sh)](https://github.com/ungoogled-software/ungoogled-chromium-macos)
- [Chromium docs — Checking out and building Chromium for Mac](https://chromium.googlesource.com/chromium/src/+/main/docs/mac_build_instructions.md)
- [Chromium docs — Chromium for Arm Macs](https://chromium.googlesource.com/chromium/src/+/main/docs/mac_arm64.md)
- Project source read directly: `backend/config.py`, `backend/services/chrome.py` (confirms hardcoded `chrome.exe` path and Windows-style launch args as of this milestone's starting point)

---
*Pitfalls research for: Open-Anti-Browser v0.2 macOS support milestone*
*Researched: 2026-07-23*
