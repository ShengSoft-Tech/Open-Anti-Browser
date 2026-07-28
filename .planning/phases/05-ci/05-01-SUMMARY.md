---
phase: 05-ci
plan: 01
subsystem: infra
tags: [macos, packaging, icns, dmg, sips, iconutil, tiffutil, headless-chromium]

# Dependency graph
requires: []
provides:
  - "assets/app.icns — Mac OS X icon file (10-tier iconset, 16..512 + @2x) for PyInstaller --icon / CFBundleIconFile"
  - "assets/dmg-background.png (600x400) + assets/dmg-background@2x.png (1200x800) — create-dmg --background source images"
affects: [05-03, 05-06]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Binary assets generated locally with macOS system tools (sips/iconutil/tiffutil) and committed as-is; generation scripts/HTML never committed (CLAUDE.md '打包脚本不入仓' convention)"

key-files:
  created:
    - assets/app.icns
    - assets/dmg-background.png
    - assets/dmg-background@2x.png
  modified: []

key-decisions:
  - "icon_512x512@2x.png tier is real 512x512 (source cap), not true 1024x1024 — accepted per D-06, measured explicitly rather than trusting iconutil's silent exit-0 (RESEARCH Pitfall 5)"
  - "dmg background generated via headless engines/chrome/Chromium.app screenshot of a scratch HTML file (zero new dependencies) rather than any image-editing tool"
  - "Background footer text limited to 'right-click the app icon -> Open' guidance only, per plan prohibition against global Gatekeeper-disable / sudo / recursive-directory instructions"

patterns-established:
  - "Asset-generation-process-not-committed: iconset dir, scratch HTML, and screenshot intermediates all stayed in scratchpad; only final PNG/ICNS committed"

requirements-completed: []  # PKG-02/PKG-04 are shared across 05-01/05-02/05-03/05-04/05-06; requirements.ready-ids confirmed both still blocked by sibling plans, so not marked complete here

coverage:
  - id: D1
    description: "assets/app.icns generated from assets/logo-512.png via sips + iconutil, valid Mac OS X icon file, round-trips through iconutil -c iconset with >=9 png tiers"
    requirement: "PKG-02"
    verification:
      - kind: other
        ref: "file assets/app.icns | grep 'Mac OS X icon' && iconutil -c iconset roundtrip (9 files) — both executed and passed during this run"
        status: pass
    human_judgment: true
    rationale: "Icon must also be visually confirmed as a recognizable, undistorted application logo — automated checks (file type + roundtrip) cannot judge visual quality; this was done via Read-tool visual inspection during execution but a human sign-off on final packaged appearance is still valuable at ship time."
  - id: D2
    description: "assets/dmg-background.png (600x400) + @2x (1200x800) generated with drag-install composition aligned to 05-03 create-dmg coordinates, footer text safety-checked against forbidden Gatekeeper-bypass phrases"
    requirement: "PKG-04"
    verification:
      - kind: other
        ref: "sips pixel-dimension checks + tiffutil -cathidpicheck (2 images written) — both executed and passed during this run"
        status: pass
    human_judgment: true
    rationale: "Text-safety grep and dimension checks are automated and passed, but final visual composition (icon-slot alignment vs 05-03's actual create-dmg run, color harmony in real Finder window) can only be fully confirmed once 05-03 assembles the real dmg."

duration: 10min
completed: 2026-07-28
status: complete
---

# Phase 5 Plan 1: macOS App Icon & DMG Background Assets Summary

**Generated `assets/app.icns` (10-tier iconset via sips/iconutil from existing logo-512.png) and `assets/dmg-background.png`/`@2x` (600x400/1200x800, rendered via headless Chromium screenshot of a scratch HTML) — both committed as the hard-prerequisite binary assets that 05-03's PyInstaller `--icon` and create-dmg `--background` steps will consume.**

## Performance

- **Duration:** 10 min
- **Started:** 2026-07-28T17:29:00Z
- **Completed:** 2026-07-28T17:31:16Z
- **Tasks:** 2 completed
- **Files modified:** 3 (all new)

## Accomplishments
- `assets/app.icns` generated from the existing `assets/logo-512.png` source using the exact `sips`/`iconutil` command sequence from RESEARCH Pattern 4; verified as a valid `Mac OS X icon` file that round-trips cleanly through `iconutil -c iconset`.
- `assets/dmg-background.png` (600×400) and `assets/dmg-background@2x.png` (1200×800) generated with a drag-install composition (app-icon slot → arrow → Applications slot) matching 05-03's planned `create-dmg` window/icon coordinates, plus a bilingual footer notice that stays within the Phase 4 Gatekeeper-guidance safety boundary.
- Both background images verified to combine into a single retina TIFF via `tiffutil -cathidpicheck` (the exact operation 05-03 will perform in CI).

## Task Commits

Each task was committed atomically:

1. **Task 1: 从 logo-512.png 生成 assets/app.icns (D-06)** - `382c6e2` (feat)
2. **Task 2: 生成 dmg 拖拽安装背景图 assets/dmg-background.png 与 @2x (D-10)** - `8475af3` (feat)

**Plan metadata:** _pending — this commit_

_Note: No TDD tasks in this plan; both tasks were single-commit binary asset generation._

## Files Created/Modified
- `assets/app.icns` - macOS application icon (10-tier iconset packed via `iconutil`), source of PyInstaller `--icon` and `CFBundleIconFile`
- `assets/dmg-background.png` - 600×400 @1x dmg drag-install background image
- `assets/dmg-background@2x.png` - 1200×800 @2x (retina) dmg drag-install background image

## Icon Generation Detail (Task 1)

Command sequence executed exactly per RESEARCH Pattern 4 (10 `sips -z` calls + 1 `cp` + `iconutil -c icns`), producing an iconset with tiers 16/16@2x/32/32@2x/128/128@2x/256/256@2x/512/512@2x from the 512×512 source `assets/logo-512.png`.

**Explicit pixel measurement of the two largest tiers (RESEARCH Pitfall 5 — `iconutil` accepts an undersized `icon_512x512@2x.png` silently, exit 0, no warning, so this cannot be inferred from the build's success alone):**

```
icon_512x512@2x.png:
  pixelWidth: 512
  pixelHeight: 512

icon_256x256@2x.png:
  pixelWidth: 512
  pixelHeight: 512
```

`icon_512x512@2x.png` is genuinely **512×512, not the Apple-recommended true 1024×1024** — this is the source image's hard cap (`assets/logo-512.png` is 512×512), and D-06 explicitly accepts this trade-off ("1024 档位按实际质量取舍"). The measurement above is the required explicit record; `iconutil`'s exit code 0 alone would not have surfaced this.

**Visual confirmation (via Read tool on `icon_512x512.png` before commit):** the icon renders as a clearly recognizable comedy/tragedy theater-masks logo (blue smiling mask + orange frowning mask on a gray ribbon backdrop) — not blank, not a solid color block, and not visibly stretched/distorted by the `sips -z` resize operations. Judged acceptable to ship.

**Round-trip verification:** `iconutil -c iconset assets/app.icns -o <tmp>` exited 0 and produced 9 PNG files (matches the ≥9 acceptance threshold).

**git status after Task 1:** only `assets/app.icns` staged/committed; the scratch `icon.iconset` directory (built under the session scratchpad, never inside the repo tree) was removed after the round-trip check and never touched git.

## DMG Background Generation Detail (Task 2)

**Generation method:** a scratch HTML file (`dmg-bg.html`, written to the session scratchpad, never committed) laid out the composition with CSS absolute positioning matching 05-03's planned `create-dmg` parameters (600×400 window, 128px icon size, app-icon alias at (150,190), Applications alias at (450,190)). Screenshotted via the repo's existing `engines/chrome/Chromium.app/Contents/MacOS/Chromium` in headless mode:
- `--headless=new --disable-gpu --no-sandbox --hide-scrollbars --window-size=600,400 --force-device-scale-factor=1` → `assets/dmg-background.png` (600×400, confirmed via `sips -g pixelWidth -g pixelHeight`)
- same command with `--force-device-scale-factor=2` → `assets/dmg-background@2x.png` (1200×800, confirmed via `sips -g pixelWidth -g pixelHeight`)

No new dependencies were introduced — both the Chromium binary and the macOS system tools (`sips`, `tiffutil`) were already present.

**Composition:** two light rounded-rectangle placeholder slots (150×150, centered at (150,190) and (450,190) respectively, dashed light-blue border) representing where Finder will overlay the real app icon and the `/Applications` alias icon, joined by a right-pointing arrow (SVG, spanning x=225→375 at y≈190). Color palette is a light gray/blue gradient background consistent with a standard light-mode Finder window (no dark background, so an unsigned app's icon stays legible against it).

**Footer text (verbatim, exact bytes as rendered in both PNGs):**

- 中文: `首次打开若被拦截属正常现象:在应用图标上点右键 →「打开」`
- English: `If blocked on first launch, this is expected: right-click the app icon → "Open"`

**Visual confirmation (via Read tool on both PNGs before commit):** placeholder-slot positions align with the planned create-dmg coordinates (left slot under where the app icon will land, right slot under where the Applications alias will land), the arrow points right, both lines of footer text are fully visible and not clipped, and the Chinese text renders correctly with no tofu/missing-glyph boxes.

**Forbidden-phrase audit:** grepped the source HTML (and by extension the rendered text) for `spctl`, `--master-disable`, `sudo`, `~/Downloads`, and any bare `/Applications` directory-wide reference — **zero matches**. The only mention in the whole composition is the single-application "right-click → Open" guidance, matching the plan's `prohibitions` clause and staying consistent with `macosGatekeeperNotice.js`'s `GATEKEEPER_XATTR_COMMAND` safety posture (single-bundle scope, no privilege escalation, no global toggle).

**`tiffutil -cathidpicheck` result:** `2 images written` — confirms the two PNGs combine into a valid multi-resolution TIFF, the exact operation 05-03's CI job will perform before handing the result to `create-dmg`.

**git status after Task 2:** only `assets/dmg-background.png` and `assets/dmg-background@2x.png` staged/committed; the scratch HTML and both intermediate screenshot PNGs (session scratchpad copies) were deleted after the images were copied into `assets/` and never touched git.

## Decisions Made

- Used the repo's existing headless Chromium binary (`engines/chrome/Chromium.app`) to render the dmg background HTML rather than any external image tool — zero new dependencies, and the composition can be regenerated identically if the source HTML is ever recreated (though per plan instruction the HTML itself is intentionally not committed).
- Kept the dmg background footer text strictly to the single "right-click → Open" instruction specified in the plan's `<action>` block, rather than reproducing the fuller multi-step System Settings flow from `macosGatekeeperNotice.js` — the plan explicitly scoped the background image to this one layer of guidance and reserved the fuller flow for the in-app Gatekeeper notice (D-10: "另一载体" — a complementary, not duplicate, guidance surface).
- Did not mark `requirements-completed` for PKG-02/PKG-04 in this SUMMARY's frontmatter despite them being in this plan's `requirements` field — `requirements.ready-ids` confirmed both IDs are still blocked by sibling plans (05-02/05-03/05-04/05-06) not yet executed; marking them complete now would misrepresent REQUIREMENTS.md traceability. They will be marked once the last contributing plan for each ID lands.

## Deviations from Plan

None - plan executed exactly as written. Both tasks' `<action>` and `<verify>` steps were followed literally; no auto-fixes, no architectural questions, no blocking issues.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required. Both assets are self-contained binary files generated entirely with macOS system tools already present on this machine.

## Next Phase Readiness

`05-03-PLAN.md`'s build-macos job can now reference `assets/app.icns` (via PyInstaller `--icon`) and `assets/dmg-background.png` + `@2x` (via `create-dmg --background`, combined through `tiffutil -cathidpicheck`) without any missing-asset gap. The 05-VALIDATION.md Wave 0 asset prerequisite for this plan is closed. No blockers for 05-02 through 05-06.

---
*Phase: 05-ci*
*Completed: 2026-07-28*

## Self-Check: PASSED

- FOUND: `assets/app.icns`
- FOUND: `assets/dmg-background.png`
- FOUND: `assets/dmg-background@2x.png`
- FOUND: commit `382c6e2` (Task 1)
- FOUND: commit `8475af3` (Task 2)
