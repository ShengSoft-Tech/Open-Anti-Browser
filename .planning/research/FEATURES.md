# Feature Research

**Domain:** macOS port/distribution of a Windows-first desktop fingerprint-browser manager (PySide6 + FastAPI, Chrome-engine-only on macOS)
**Researched:** 2026-07-23
**Confidence:** MEDIUM (web-search-derived, cross-checked across multiple independent sources per claim; no official Apple doc citation for Gatekeeper flow but consistent across Macworld/idownloadblog/OSnews/Apple Community for Sequoia+Tahoe behavior)

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist for *any* macOS desktop app distribution. Missing these makes the app look broken or amateurish, independent of whether it's a fingerprint browser or any other tool.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| dmg with drag-to-Applications layout (.app + `/Applications` alias) | Universal macOS install convention since OS X; users literally don't know another way to install a non-App-Store app | LOW | Standard tooling: `hdiutil` scripting or `create-dmg` npm/brew tool. Custom background image is optional polish, the Applications alias is the part users actually need — without it they may run the app directly from the mounted dmg (breaks auto-update paths, orphans user data on eject). |
| Correct app identity in menu bar / Dock (app name, not "Python" or script name) | Any properly bundled macOS app shows its real name top-left and in Dock; a Python app run outside a `.app` bundle shows "Python" and behaves like a foreground terminal process | LOW–MEDIUM | Controlled by `CFBundleName`/`CFBundleDisplayName` in `Info.plist` inside the PyInstaller `.app`, not by Qt/PySide6 code. Must set `bundle_identifier` and a custom `Info.plist` in the PyInstaller spec's `BUNDLE()` call. This project already runs via PyInstaller for Windows; macOS spec needs its own `BUNDLE()` block. |
| Cmd+Q quits the app; Cmd+W closes window; standard app menu | Baseline macOS keyboard/menu convention; every native and Electron/Qt app on the platform has this | LOW | Comes largely for free from Qt/Cocoa integration **when the app runs as a real `.app` bundle** — it does NOT work correctly if launched as a bare onefile binary or raw script outside a bundle (no proper NSApplication delegate, quit behaves inconsistently). This is a strong argument for `--onedir` `.app` bundle, not `--onefile`, on macOS. |
| Dock icon (proper `.icns`, not a generic gear/terminal icon) | Any polished desktop app has a real icon in the Dock and Finder | LOW | Needs an `.icns` asset (already likely have a Windows `.ico`; convert via `iconutil`/`sips`). Set via PyInstaller `icon=` param, and `CFBundleIconFile` in Info.plist. |
| Unsigned-app first-launch instructions in release notes | Modern macOS (Sequoia 15.x, Tahoe 26) actively blocks unsigned/unnotarized apps with a "Not Opened" / "is damaged" dialog with no obvious bypass; users unfamiliar with dev tooling will not find System Settings > Privacy & Security > "Open Anyway" on their own | LOW (docs) but user-facing risk is HIGH if skipped | Verified: Sequoia (15.0) removed the old Control-click → Open Gatekeeper bypass entirely. Correct flow now is: launch once (blocked) → System Settings → Privacy & Security → scroll to bottom → "Open Anyway" (requires password/Touch ID) → relaunch from Finder → a second "Open Anyway" confirmation appears. The button only appears **after a failed launch attempt** and must be used within roughly an hour of that attempt, or the user must repeat the failed-launch step. Must be documented step-by-step with screenshots in the GitHub release body, not just prose — this is a recurring support-ticket generator for every unsigned indie Mac tool. |
| `xattr -d com.apple.quarantine` as an alternative/backup workaround | Terminal-comfortable users (a meaningful fraction of this tool's target audience — automation/API users) prefer a one-line fix over GUI clicking, and it also fixes cases where the GUI flow gets stuck (e.g. the "is damaged and can't be opened" variant, which is really an untrusted-quarantine issue, not corruption) | LOW (docs) | Document `xattr -dr com.apple.quarantine /Applications/Open-Anti-Browser.app` as the terminal alternative in the same release notes / README section. `-r` (recursive) matters because the bundled Chrome kernel binary inside the `.app`/support dir also carries the quarantine flag and can independently trigger a second Gatekeeper block when the app tries to spawn it. |
| Per-profile isolated data directories under `~/Library/Application Support/<AppName>/` | This is the macOS equivalent of the existing Windows `data/`/`browser-data/` convention; every well-behaved macOS app writes app-writable state under `~/Library/Application Support`, never inside the read-only `.app` bundle itself (bundle is often re-verified/resigned-checked and is not writable post-Gatekeeper-approval in practice for a running app) | LOW–MEDIUM | Directly maps to existing `config.py` "single source of path truth" pattern — needs a macOS branch alongside the existing dev-mode vs PyInstaller-frozen (LOCALAPPDATA) branch. Each browser profile's isolated Chrome user-data-dir already exists as a concept (`browser-data/<profile>`); on macOS this whole tree should live under `~/Library/Application Support/Open-Anti-Browser/browser-data/<profile>` rather than next to the executable, since the `.app` bundle should be treated as read-only. |
| Engine binary placement that survives Gatekeeper + code-signing checks on nested executables | The bundled Chrome kernel is a full app-like binary tree (not a single exe), and macOS re-validates *nested* Mach-O executables/dylibs against their own ad-hoc signature and quarantine state independently of the parent `.app` | MEDIUM | If the Chrome kernel are unpacked from a zip/tar during CI packaging without preserving their original ad-hoc signature or by breaking symlinks (common `zip`/`GitHub Actions upload-artifact` pitfall), the nested Chromium `Framework.framework/Versions/Current` symlink or main executable can end up "damaged" per Gatekeeper even though the outer `.app` was approved. Kernel packaging step must preserve symlinks (`ditto`, not plain `zip`) and must not re-flatten the app bundle structure. |

### Differentiators (Competitive Advantage)

Not required for a minimally-working macOS build, but meaningfully improve the "feels like a real Mac app, not a ported Windows tool" perception — directly serving this project's Core Value (isolated, trustworthy fingerprint environments, one-click).

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Custom dmg background image with "drag to Applications" arrow | Small visual polish that signals a maintained, professional release rather than a raw CI artifact; AdsPower/Multilogin-tier competitors all ship this | LOW | Nice-to-have only; explicitly out of scope for MVP if time-constrained — a plain dmg with just the `.app` + Applications alias is fully functional and still meets "table stakes." |
| Clear "macOS Limitations" section in-app (not just docs) explaining window-sync/arrangement is Windows-only, with link to docs | Prevents confused bug reports from macOS users who expect feature parity with the Windows README/marketing; also builds trust that the gap is a deliberate, documented decision rather than a bug | LOW | Cheap to add given the platform-detection work already required for hiding Firefox/window controls (see dependencies below). |
| One-command `xattr` fix bundled as a helper script or copy-paste block in both GitHub Release body and in-app first-run banner | Reduces the single biggest first-run drop-off risk for an unsigned distribution; competitors in this exact niche (antidetect/fingerprint browsers) universally hit this same complaint from macOS users in reviews/forums | LOW | Already required as documentation (table stakes); the differentiator is surfacing it *inside the app* (e.g., a "download the kernel" or "first launch" screen) in addition to release notes, so users don't need to leave the app to find it. |
| Auto-detect Mac architecture and point to the correct dmg download in any in-app "check for updates" or download-link surface | Avoids user confusion between arm64/Intel builds (this is a common support burden for any project shipping separate per-arch installers, e.g. ungoogled-chromium-macos does this via distinct filenames) | LOW–MEDIUM | Depends on whether this project already has an update-check / download-link UI; if it only relies on GitHub Releases page, simply naming the dmg files clearly (`OpenAntiBrowser-<version>-arm64.dmg` / `-x64.dmg`) achieves most of the benefit without new UI work. |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|------------------|-------------|
| Apple Developer ID signing + notarization for "MVP" | Removes the scary Gatekeeper dialog entirely, feels like the "correct" fix | Requires a paid Apple Developer account ($99/yr), a signing identity, `codesign --options runtime` + `notarytool submit` pipeline, and ongoing certificate maintenance; already explicitly out-of-scope per project decisions. Also, PyInstaller-built bundles are notorious for notarization failures (unsigned nested dylibs/base_library.zip placement issues) requiring nontrivial extra CI tooling | Ship unsigned + clear "Open Anyway" / `xattr` instructions now; revisit signing as a later milestone once there's a signing budget/identity |
| Universal (arm64+x64 fat) single dmg | Feels like "one download for everyone", matches how Apple ships its own apps | Doubles build complexity (Chromium universal builds are notoriously heavy/slow to produce, especially cross-compiled or built via lipo-merging two full Chromium trees) for a niche desktop tool where users can trivially pick the right download; already explicitly out of scope | Two architecture-specific dmgs, clearly named, as already decided |
| Full feature parity for window sync/arrangement via a CDP-based cross-platform reimplementation, attempted in this milestone | "It already works on Windows, just make it also work on Mac" seems like a small ask | The existing synchronizer's window *arrangement* (show/uniform-size/grid) is fundamentally win32-API-bound (no equivalent primitive without Accessibility-API/private API work on macOS); the CDP-based event-replay half is theoretically portable but nontrivial to validate and is explicitly deferred; attempting both in the same milestone as "get Chrome-only macOS working at all" risks delaying or destabilizing the core deliverable | Ship macOS v0.2 with sync/arrangement disabled + explicit UI messaging; scope a dedicated future milestone for CDP-only cross-platform sync once core macOS support is stable |
| Auto-updater (Sparkle-style in-app update) for macOS in this milestone | Users expect "check for updates" on a modern Mac app | Requires either signing (Sparkle checks signatures) or a custom insecure updater, plus separate CI/release-channel plumbing; not part of the stated v0.2 scope (CI already just produces GitHub Release assets) | Rely on GitHub Releases + manual re-download for this milestone, matching how the Windows Inno Setup build is currently distributed (no evidence this project already auto-updates on Windows either) |
| Building the Chrome kernel for macOS inside GitHub Actions CI | "Just add a macOS runner job like the Windows one" seems symmetrical | Full Chromium builds do not fit in Actions runner time/disk limits (this is the stated reason for local-Mac-build + kernel-release-asset approach); attempting it wastes CI minutes and will time out or run out of disk | Kernel is built once locally on a Mac and uploaded as a release asset; app-level CI job only downloads and repackages it, mirroring the existing single-source-of-truth pattern (`CHROME_ENGINE_ZIP_URL` in `config.py`) |

## Feature Dependencies

```
[Read CFBundleName/Icon from Info.plist in PyInstaller BUNDLE()]
    └──requires──> [PyInstaller macOS spec using --onedir + BUNDLE(), not --onefile]
                       └──requires──> [Working PyInstaller macOS build target added to CI/build tooling]

[Per-profile data dir under ~/Library/Application Support/<App>]
    └──requires──> [config.py platform branch: macOS path resolution alongside existing dev-mode/LOCALAPPDATA branch]

[Chrome kernel launch inside .app-relative writable path]
    └──requires──> [Per-profile data dir convention above]
    └──requires──> [Kernel packaging preserves symlinks/signatures (ditto, not zip) during CI repackage]

[Gatekeeper "Open Anyway" documented flow]
    └──enhances──> [Unsigned dmg distribution] (does not replace signing, but is the accepted mitigation)

[xattr -d com.apple.quarantine documented + optionally surfaced in-app]
    └──enhances──> [Gatekeeper "Open Anyway" documented flow] (faster path for terminal-comfortable users; also fixes nested-kernel-binary quarantine re-trigger)

[In-app "macOS Limitations" messaging: hide Firefox engine, disable window sync/arrangement]
    └──requires──> [Existing platform-detection point already needed for pywin32/window_manager conditional import on backend]
    └──conflicts──> [Attempting to build CDP-based cross-platform window sync in same milestone] (scope conflict, not technical — explicitly deferred)

[Universal codesigning/notarization]
    └──conflicts──> [Unsigned ad-hoc distribution decision for this milestone] (mutually exclusive choices for this milestone; notarization requires paid Developer ID account, not budgeted)
```

### Dependency Notes

- **App identity (menu bar name, Dock icon, Cmd+Q) requires a real `.app` bundle, not a onefile binary:** PyInstaller's `--onefile` mode on macOS produces a bare executable that Finder/Dock/menu-bar integration treats as a foreground terminal-style process, not a Cocoa app. The Windows build likely uses `--onefile` or `--onedir` inside an Inno Setup installer; macOS needs its own PyInstaller spec targeting `BUNDLE()` (onedir under the hood) with a custom `Info.plist`. This is a build-tooling dependency that should land before any UI/UX polish work on macOS.
- **Per-profile Application Support path requires a `config.py` platform branch:** the existing single-source-of-truth pattern (dev root vs PyInstaller-frozen/LOCALAPPDATA root, portable-mode marker file) needs a third branch for macOS that resolves to `~/Library/Application Support/Open-Anti-Browser/` for all writable data (settings, profiles JSON, browser-data, extensions, downloads, runtime), keeping the `.app` bundle itself read-only-after-install, consistent with macOS norms and avoiding permission/Gatekeeper re-check headaches from writing inside the bundle.
- **Kernel nested-binary quarantine requires signature/symlink-preserving packaging:** because the Chrome kernel is bundled *inside* the dmg (per the project's decision to ship offline-ready, not download-on-first-launch), the CI step that assembles the final `.app` + kernel into a dmg must not break the kernel's own internal structure (Chromium's `Framework.framework/Versions/Current` symlink, ad-hoc-signed nested executables) — using `zip`/`GitHub Actions upload-artifact` naively is a known way to corrupt this, producing "is damaged and can't be opened" for the *inner* kernel even when the outer app was approved via Gatekeeper. Use `ditto` (or equivalent symlink-preserving tooling) when moving the kernel artifact through CI.
- **In-app platform messaging enhances, doesn't require, the docs-level Gatekeeper instructions:** these are two separate audiences (release-notes readers who haven't installed yet, vs. already-running users hitting a hidden/disabled feature) and can be built independently, but both hang off the same underlying platform-detection utility the backend needs anyway for conditional pywin32/window_manager imports — worth centralizing as one `is_macos()`/`is_windows()` helper used by both backend gating and any frontend platform flag surfaced via API.
- **Universal binary and notarization both conflict with this milestone's explicit decisions:** listed here only so the roadmap doesn't accidentally reintroduce them as "quick wins" — both were deliberately scoped out (see PROJECT.md Key Decisions) and doing either changes the CI/build shape enough that it should be its own future milestone, not a footnote in this one.

## MVP Definition

### Launch With (v1 — this milestone, v0.2)

Minimum viable macOS port per the already-decided scope in PROJECT.md.

- [ ] dmg with `.app` + Applications alias (plain layout, no custom background needed) — this is the only install path that will work reliably; users won't know to run the app from inside the mounted dmg
- [ ] Correct `Info.plist` (`CFBundleName`, `CFBundleIdentifier`, `.icns` icon) via a macOS-specific PyInstaller `BUNDLE()` spec — required for the app to behave like a real Mac app at all (menu bar name, Dock icon, working Cmd+Q)
- [ ] Chrome kernel (arm64 + x64) bundled inside the dmg, placed so it survives Gatekeeper on both the outer `.app` and the inner kernel binaries (ditto-based packaging, not naive zip)
- [ ] `config.py` macOS path branch writing all app data to `~/Library/Application Support/Open-Anti-Browser/`
- [ ] Firefox engine hidden (not just disabled) in the macOS UI — there is no macOS Firefox kernel, so showing it disabled-with-tooltip is misleading; hide entirely
- [ ] Window sync / window arrangement controls disabled-with-tooltip (not hidden) in the macOS UI, tooltip explicitly states "Windows only" — these are meaningful, discoverable Windows features users may know about from documentation/marketing, so hiding them silently would look like a missing/broken feature rather than a documented platform gap
- [ ] Release notes with step-by-step unsigned-app first-launch instructions (System Settings > Privacy & Security > Open Anyway flow) plus the `xattr -dr com.apple.quarantine` terminal alternative, for both the outer app and, if needed, after moving to Applications
- [ ] CI macOS job producing two dmgs (arm64, x64) attached to the same GitHub Release as the Windows installer

### Add After Validation (v1.x)

- [ ] Custom dmg background image / drag-to-Applications graphic — add once the plain dmg is confirmed working end-to-end for real macOS users
- [ ] In-app first-run banner surfacing the `xattr` fix / Gatekeeper instructions (in addition to release notes) — add if release-notes-only proves insufficient (support tickets, GitHub issues about "app is damaged")
- [ ] Auto-detecting the correct arch download link in any in-app update-check surface — add once there's evidence users are downloading the wrong architecture

### Future Consideration (v2+)

- [ ] Apple Developer ID signing + notarization — defer until there's budget for a Developer account; removes the entire unsigned-app UX burden if pursued later
- [ ] CDP-based cross-platform window sync (no arrangement, sync only) — defer to a dedicated milestone; validate technical feasibility (CDP/marionette-equivalent event replay across windows without win32) before committing UI/UX design around it
- [ ] Universal (arm64+x64) single dmg — defer indefinitely unless Chromium tooling changes make universal builds materially cheaper; current two-dmg approach is a permanent, acceptable tradeoff per project decision, not just a temporary MVP shortcut
- [ ] Sparkle-style auto-updater — defer; requires signing infrastructure as a prerequisite, so naturally follows signing/notarization work

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| dmg with Applications alias | HIGH | LOW | P1 |
| Correct Info.plist / app identity (name, icon, Cmd+Q) | HIGH | LOW–MEDIUM | P1 |
| Kernel bundled + symlink-safe CI packaging | HIGH | MEDIUM | P1 |
| `~/Library/Application Support` data path branch | HIGH | LOW–MEDIUM | P1 |
| Hide Firefox engine on macOS | MEDIUM | LOW | P1 |
| Disable-with-tooltip window sync/arrangement on macOS | MEDIUM | LOW | P1 |
| Release-notes Gatekeeper/xattr instructions | HIGH | LOW | P1 |
| CI macOS job producing arm64+x64 dmgs | HIGH | MEDIUM | P1 |
| Custom dmg background image | LOW | LOW | P3 |
| In-app first-run Gatekeeper/xattr banner | MEDIUM | LOW | P2 |
| Arch-aware download link in-app | LOW | LOW–MEDIUM | P3 |
| Signing + notarization | HIGH (removes friction) | HIGH (cost + ongoing) | P3 (explicitly deferred) |
| CDP cross-platform window sync | MEDIUM | HIGH | P3 (explicitly deferred) |
| Universal binary dmg | LOW | HIGH | P3 (explicitly rejected) |

**Priority key:**
- P1: Must have for launch (this v0.2 milestone)
- P2: Should have, add when possible (early v0.2.x follow-up)
- P3: Nice to have / explicitly deferred to a future milestone

## Competitor Feature Analysis

| Feature | AdsPower / Multilogin (fingerprint-browser competitors) | ungoogled-chromium-macos (upstream engine project) | Our Approach |
|---------|--------------------------------------------------|-----------------------------------------------------|--------------|
| Distribution format | Native macOS installers (dmg-based); marketed as cross-platform (Win/macOS/Linux) | Signed + notarized per-architecture dmg (`ungoogled-chromium_<version>_<arm64\|x86_64>-macos.dmg`) | dmg per architecture (arm64, x64), matching the upstream engine's own convention |
| Code signing | Signed (commercial products, presumably have Developer ID); still, users report needing to click through Gatekeeper "Allow Anyway" / disable Gatekeeper on newer macOS in support docs — signing alone does not eliminate all first-run friction on recent macOS if notarization/stapling has any gap | Signed + notarized | Unsigned by decision (no Developer account budgeted this milestone); document the (larger, expected) Gatekeeper friction explicitly rather than pretend it doesn't exist |
| Per-profile data isolation | Isolated profile directories with browser storage (LocalStorage/IndexedDB/extension data) backed up per profile — same conceptual model as this project's existing `browser-data/<profile>` | N/A (single-user browser, not a profile manager) | Continue existing `browser-data/<profile>` model, relocated under `~/Library/Application Support/Open-Anti-Browser/` on macOS instead of an app-relative folder |
| Windows-only feature communication | Not directly observed in search results (AdsPower/Multilogin are both natively cross-platform products, so they don't face a "some features are Windows-only" problem in the same way) | N/A | This project is the outlier here — win32-dependent window sync/arrangement has no drop-in equivalent, so the "disable with tooltip, don't silently drop" approach is a self-directed pattern, not one borrowed from a competitor |

## Sources

- [Open unsigned applications on macOS Sequoia and newer — Hacks Guide Wiki](https://wiki.hacks.guide/wiki/Open_unsigned_applications_on_macOS_Sequoia_and_newer) — MEDIUM confidence (web, cross-checked)
- [macOS Sequoia removes Control-click Gatekeeper bypass — idownloadblog](https://www.idownloadblog.com/2024/08/07/apple-macos-sequoia-gatekeeper-change-install-unsigned-apps-mac/) — MEDIUM
- [Bug or intentional? macOS 15.1 removes ability to launch unsigned apps — OSnews](https://www.osnews.com/story/141055/bug-or-intentional-macos-15-1-completely-removes-ability-to-launch-unsigned-applications/) — MEDIUM
- [What to do when you can't open an app you just installed in macOS Sequoia — Macworld](https://www.macworld.com/article/2457844/what-to-do-when-you-cant-open-an-app-you-just-installed-in-macos-sequoia.html) — MEDIUM
- [Allow downloaded Apps to Open in macOS Tahoe: "App is Damaged" — swissmacuser.ch](https://swissmacuser.ch/fix-macos-tahoe-app-is-damaged-and-cant-be-opened-move-trash/) — MEDIUM
- [macOS Installation and Security notes on unsigned apps — chrplr.github.io](https://chrplr.github.io/note-about-macos-unsigned-apps/) — MEDIUM
- [macOS security and com.apple.quarantine extended attribute — ISSCloud](https://www.isscloud.io/guides/macos-security-and-com-apple-quarantine-extended-attribute/) — MEDIUM
- [Your Mac App Is Not Broken: Gatekeeper distrust of unsigned tools — Margrop Blog](https://blog.margrop.net/en/post/macos-gatekeeper-unsigned-app-fix/) — MEDIUM
- [ungoogled-chromium-macos releases (SourceForge mirror / GitHub / Codeberg)](https://sourceforge.net/projects/ungoogled-chromium-mac.mirror/files/) — MEDIUM
- [ungoogled-software/ungoogled-chromium-macos — DeepWiki](https://deepwiki.com/ungoogled-software/ungoogled-chromium-macos) — MEDIUM
- [PySide6 QMenuBar docs — Qt for Python](https://doc.qt.io/qtforpython-6/PySide6/QtWidgets/QMenuBar.html) — MEDIUM
- [Mac application menu title — Qt Forum](https://forum.qt.io/topic/33287/mac-application-menu-title-solved) — MEDIUM
- [How to customize the display name of an app in the macOS dock — Apple Developer Forums](https://developer.apple.com/forums/thread/756303) — MEDIUM
- [Code signing and notarization fails on macOS .app bundles — PyInstaller issue #5112](https://github.com/pyinstaller/pyinstaller/issues/5112) — MEDIUM
- [Signing and notarizing a Python macOS UI application — haim.dev](https://haim.dev/posts/2020-08-08-python-macos-app) — MEDIUM
- [AdsPower — Top 10 Anti Fingerprint Browsers blog](https://www.adspower.com/blog/top-10-anti-fingerprint-browsers-2024) — LOW (vendor marketing content, not independently verified)
- [Multilogin vs AdsPower comparison](https://multilogin.com/compare/multilogin-vs-adspower/) — LOW (vendor/affiliate comparison content)
- [How to transfer profiles to AdsPower from other antidetects — AdsPower help docs](https://help.adspower.com/docs/transfer_profiles_to_adspower_from_another_antidetect) — MEDIUM (vendor docs describing own product's data model, reasonably reliable for factual claims about profile backup contents)

---
*Feature research for: macOS port of Open-Anti-Browser (Chrome-only fingerprint browser manager)*
*Researched: 2026-07-23*
