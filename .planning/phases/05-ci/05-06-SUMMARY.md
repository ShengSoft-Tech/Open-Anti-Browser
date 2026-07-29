---
phase: 05-ci
plan: 06
subsystem: testing
tags: [macos, gatekeeper, quarantine, app-translocation, amfi, codesign, dmg, uat, manual-verification]

# Dependency graph
requires:
  - phase: 05-ci (05-02)
    provides: "launch_app.py macOS Cmd+Q interception (D-07) and frozen-runtime quarantine self-strip + D-12a fallback notice — both exercised for the first time on real hardware by this checkpoint"
  - phase: 05-ci (05-05)
    provides: "three-job workflow (build / build-macos / release) producing the dmg this checkpoint installs"
provides:
  - "Real-machine acceptance of the CI-produced arm64 dmg on macOS 15.7 (24G222): install, first launch, three exit paths, icon/name appearance, and fingerprint-Chrome launch all verified by a human on physical hardware"
  - "Objective, timestamped system-log evidence of the complete first-launch Gatekeeper/AMFI/ASP decision sequence — captured via `log stream`, not reconstructed from recall"
  - "Falsification of 05-RESEARCH's core premise: no App Translocation occurs after a Finder drag-install, and the in-app quarantine self-strip SUCCEEDS"
  - "Two blocking defects in 05-02's D-07 feature found, root-caused, fixed, and re-verified (see 05-02-GAP-FIX-SUMMARY.md and 05-02-GAP-FIX-2-SUMMARY.md)"
  - "Measured proof that a synthetic `xattr -w` quarantine tag is NOT equivalent to a real browser-download quarantine record"
affects: [06-docs]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Log-capture-before-interaction pattern for manual checkpoints: arm `log stream --predicate '<subsystem filters>'` in the background BEFORE asking a human to perform a one-shot UI interaction, so the objective decision sequence survives even when the human's recall of dialog wording does not. Applied twice here (Gatekeeper first-launch, AMFI kernel-launch) and both times it produced evidence that contradicted or materially refined the human's recollection."
    - "grep-self-match guard when counting processes: `ps -Ao command | grep -ic <term>` counts the grep pipeline's own command line, inflating residual-process counts. Use `pgrep -fc <pattern>` for counts and `pgrep -fl` for listings."

key-files:
  created:
    - .planning/phases/05-ci/05-06-SUMMARY.md
  modified: []

key-decisions:
  - "Did NOT trigger an extra CI run for Task 1 as literally written. Task 1's acceptance criterion is that the run's commit contains 05-02 and 05-05 changes; run 30402103536 (headSha e1a4ea9) already satisfied it with all eight phase feat/fix commits as ancestors, and the only newer commit was docs-only. Re-running 10-20 min of CI for a documentation delta had no evidential value. (Superseded anyway — two gap fixes forced three further real runs.)"
  - "Switched from the plan's synthetic-quarantine option to its browser-download option for the final round, after the first two rounds produced INCONSISTENT Gatekeeper behavior under synthetic tags. This was the right call: the real tag measured flags=0081 with a matching LSQuarantineEventsV2 database row, while both synthetic tags used flags=0083 with no database row. Conclusions from the synthetic rounds are treated as void."
  - "D1 icon-quality verdict: ACCEPTABLE. The user inspected the Dock at maximum magnification and Finder icon view at maximum size and judged the 512-as-1024 upscale acceptable. Recorded as a known trade-off; `assets/app.icns` is NOT regenerated in this phase."
  - "B1 dialog wording accepted as a documented gap rather than re-running a fourth install cycle. The user explicitly chose 'accept and note the gap'. The decision SEQUENCE is objectively established from syspolicyd logs; only the human-readable title/button text of the prompt is missing."
  - "Did NOT self-direct the D-12a fallback re-route (copying the kernel to ~/Library/Application Support/.../engines/). The plan forbids an executor from re-routing on its own, and the checkpoint's findings make the re-route unnecessary: self-strip succeeds, so the fallback notice is a genuine exception path rather than the expected first-launch main path."

patterns-established:
  - "Manual-checkpoint defect escalation: when a blocking checkpoint surfaces a code defect, fix it as a `fix(<originating-plan>)` gap-fix with its own SUMMARY and its own CI gate, then RESTART the affected checkpoint group from a clean install rather than continuing on the patched-in-place environment."

requirements-completed: [PKG-02, PKG-03, PKG-04]

coverage:
  - id: D1
    description: "dmg drag-install experience verified on real hardware: custom background renders, icon/Applications-alias placement correct, footer guidance readable and within the Gatekeeper-guidance safety boundary, drag-to-Applications completes"
    requirement: "PKG-04"
    verification:
      - kind: manual_procedural
        ref: "05-06 checkpoint group A, items A1-A5 — human visual inspection on macOS 15.7 arm64"
        status: pass
    human_judgment: true
    rationale: "Background rendering, icon alignment, and drag feel are visual/tactile judgments with no automatable equivalent."
  - id: D2
    description: "Complete first-launch decision sequence recorded with millisecond timestamps from syspolicyd/amfid/kernel logs, including the Gatekeeper prompt, the denial breadcrumb, the ASP process block, and the successful second launch"
    requirement: "PKG-03"
    verification:
      - kind: manual_procedural
        ref: "05-06 checkpoint group B, item B1 — `log stream` capture, scratchpad/gatekeeper-log.txt"
        status: pass
      - kind: other
        ref: "xattr -p com.apple.quarantine before/after first launch; ps process path inspection for /AppTranslocation/"
        status: pass
    human_judgment: true
    rationale: "Requires a human to perform the physical double-click; the dialog's rendered title/button text has no programmatic accessor. Partial gap recorded — see Open Items."
  - id: D3
    description: "Three exit paths behave per D-07: Cmd+Q exits fully, red-X only minimises to the menu-bar item, menu-bar 'exit' exits fully — each confirmed with process and port measurements"
    requirement: "PKG-02"
    verification:
      - kind: manual_procedural
        ref: "05-06 checkpoint group C, items C1-C4 — pgrep/lsof measurements after each human interaction"
        status: pass
    human_judgment: true
    rationale: "Requires physical keystrokes and clicks on real UI chrome (menu-bar extra, window close button)."
  - id: D4
    description: "Dock icon, menu-bar application name, and Finder Get Info all show correct branding and version 0.1.16; icon quality at maximum display size judged acceptable"
    requirement: "PKG-02"
    verification:
      - kind: manual_procedural
        ref: "05-06 checkpoint group D, items D1-D3 — human visual inspection plus plutil Info.plist extraction"
        status: pass
    human_judgment: true
    rationale: "RESEARCH Pitfall 5 states explicitly that a 512px source standing in for the 1024 tier produces NO automatic signal; only a human looking at the rendered icon can judge it."
  - id: D5
    description: "A fingerprint Chrome profile launches from the kernel embedded inside the .app bundle, and stopping it leaves zero residual kernel processes — the v0.2 'kernel in the package, install and go' decision proven on real hardware"
    requirement: "PKG-04"
    verification:
      - kind: manual_procedural
        ref: "05-06 checkpoint group E, items E1-E3 — human profile creation/launch/stop plus pgrep and lsof measurements"
        status: pass
      - kind: other
        ref: "AMFI log capture during kernel launch (scratchpad/amfi-chrome-log.txt) — confirms adhoc -423 without any ASP block"
        status: pass
    human_judgment: true
    rationale: "Per Phase 3 D-07's evidence, an unclean quarantine gets the kernel AMFI-killed with NO dialog; only a real launch on real hardware distinguishes success from silent death."
---

## What Was Built

Nothing. `files_modified` is empty by design — this plan is a blocking human-verification
checkpoint. Its output is evidence.

That said, the checkpoint did not merely observe: it surfaced **two blocking defects** in 05-02's
D-07 Cmd+Q feature, both of which were fixed under separate gap-fix cycles before the checkpoint
could complete. Those fixes are documented in `05-02-GAP-FIX-SUMMARY.md` and
`05-02-GAP-FIX-2-SUMMARY.md`.

## Test Environment

| | |
|---|---|
| Machine | MacBookPro18,4, Apple Silicon (arm64) |
| OS | macOS **15.7**, build **24G222** |
| dmg source | `workflow_dispatch` run **30418547844**, `main` @ **`acfcc9a`** |
| dmg SHA-256 | `a48f64689c58c7b06b0d50845e46eb0c30584bda83ab68558bd36c68c1c956e0` |
| dmg acquisition | **Real browser download** from the Actions artifacts page (Chrome), unzipped via Finder |
| Crash-report baseline | 0 before, **0 after** the entire final round |

## Task 1 — dmg Acquisition (deviation recorded)

The plan's Task 1 says to trigger a final CI run. **This was not done as literally written**, for
the reason recorded in `key-decisions`: the acceptance criterion is that the run's commit contains
05-02's and 05-05's changes, and run `30402103536` (headSha `e1a4ea9`) already had all eight phase
`feat`/`fix` commits as ancestors, with only a docs-only commit newer.

The point became moot: the two gap fixes forced three further real runs, and the final round used
the freshest of them (`30418547844`).

**Quarantine acquisition — the finding that voided two earlier rounds.** The plan offered two
options: synthesise a quarantine tag with `xattr -w`, or download through a browser. Rounds 1 and 2
used the synthetic path and produced *inconsistent* Gatekeeper behavior between them, which
prompted a switch to the real path. The measured difference:

| Source | flags | UUID | LSQuarantineEventsV2 row |
|---|---|---|---|
| **Real Chrome download** | **`0081`** | `85EB6132-…` (system-generated) | **present**, agent=Chrome |
| Round-1 synthetic | `0083` | `uuidgen` random | absent |
| Round-2 synthetic | `0083` | hand-written `A1B2C3D4-…` | absent |

The synthetic tags set an extra `0x0002` bit the real one does not, and neither had the
LaunchServices database association a genuine download creates. **Conclusions drawn from the two
synthetic rounds are treated as void.** Only the final, real-download round is reported below.

Inheritance on drag-install was identical in kind across all three rounds: the `.app` receives the
dmg's record with `0x0100` added (`0081` → `0181`).

## Verification Results — 23 items

### Group A — dmg open experience (PKG-04) — 5/5 PASS

| # | Item | Result |
|---|---|---|
| A1 | Custom background renders (not blank/default grey) | PASS |
| A2 | App icon and Applications alias aligned to background slots, no overlap/overflow | PASS |
| A3 | Footer guidance readable, not clipped, within safety boundary | PASS |
| A4 | Drag to Applications completes smoothly | PASS |
| A5 | dmg unmounts | PASS |

**A3 footer text, recorded verbatim:**

> 首次打开若被拦截属正常现象:在应用图标上点右键 → 「打开」
> If blocked on first launch, this is expected: right-click the app icon → "Open"

Safety audit against the plan's forbidden-phrase list — **zero matches** for `spctl`,
`--master-disable`, "allow any source", `sudo`, or any recursive operation on `~/Downloads` or
`/Applications`. Guidance scope is limited to right-click → Open on the single app icon. **T-05-25
(user led into over-broad system changes) is mitigated as designed.**

> **Note on A1–A3 evidence lineage:** these three were inspected in detail on round 1's dmg. The
> final dmg's `assets/app.icns` and `assets/dmg-background*.png` originate from the same unmodified
> 05-01 commits (`382c6e2`, `8475af3`) and were re-confirmed non-regressed at install time, but
> were not re-inspected in the same detail. A4/A5 were performed in every round.

### Group B — first-launch sequence (PKG-03 / D-12a) — 4 PASS, 4 N/A, 1 documented gap

**B1 — the complete decision sequence, from `log stream` capture (objective, millisecond-stamped):**

**Launch #1 — pid 35736, 22:32:20.578**

| Time | Event |
|---|---|
| `20.578` | `runningboardd` launches `/Applications/Open-Anti-Browser.app/Contents/MacOS/Open-Anti-Browser` |
| `20.590` | kernel AMFI: `'…/Open-Anti-Browser' is adhoc signed.` |
| `20.593` | `amfid`: `not valid: Error … Code=-423 "The file is adhoc signed or signed by an unknown certificate chain"` |
| `20.606` | `loginwindow`: **App ready** — the process really did start; Python began executing |
| `21.205`–`21.263`+ | `syspolicyd`: dozens of `GatekeeperPolicyScanError Code=-67018 "Code did not match any currently allowed policy"` while recursively scanning the bundle |
| `31.034` | `syspolicyd`: `GK evaluateScanResult: 0` → **`Prompt shown (6, 0), waiting for response`** ← **the dialog appeared** |
| `32.911` | `syspolicyd`: **`Adding Gatekeeper denial breadcrumb (open)`** ← the response was a **denial** |
| `32.924` | kernel: **`(AppleSystemPolicy) ASP: Security policy would not allow process: 35736`** |
| `32.935` | `loginwindow`: `applicationQuit` — launch #1 terminated by the system |

**Launch #2 — 22:32:35.818** (3.0 s after the denial)

- **No** second `Prompt shown`
- **No** second denial breadcrumb
- Ran successfully; that process (pid 36033) stayed alive for 35+ minutes with zero crash reports

**Mechanism — why launch #2 succeeded.** Launch #1 lived 12.3 s between "App ready" (`20.606`) and
being killed (`32.924`) — ample time for `maybe_strip_quarantine()` to run. It succeeded: the
`.app`'s `com.apple.quarantine` attribute is gone. Launch #2 therefore presented an
**un-quarantined** bundle, and Gatekeeper does not assess un-quarantined files. It ran unimpeded.

**The user's initial recollection was that they had approved the app via System Settings → Privacy
& Security. The evidence contradicts this** and the recollection is not used:

- Only **3.0 s** elapsed between the denial breadcrumb and launch #2 — not enough to navigate
  System Settings, click "Open Anyway", and authenticate.
- The log capture ran through `22:33:17` and contains **no** approval record.
- **`spctl --assess --type execute` still returns `rejected`** — to this moment, no Gatekeeper
  approval exists for this app.

This is precisely the `T-05-26` failure mode the plan named (mistaking "the user did something
manual" for "the mechanism worked"), caught here by the pre-armed log capture rather than by recall.

| # | Item | Result |
|---|---|---|
| B1 | Complete dialog sequence recorded | **PASS (sequence)** / **GAP (wording)** — see Open Items |
| B2 | App's own fallback notice compared verbatim against `build_quarantine_failure_message(None)` | **N/A** — self-strip succeeded, so by design the notice never fired |
| B3 | `xattr -p com.apple.quarantine` after first launch | **PASS** — `xattr: /Applications/Open-Anti-Browser.app: No such xattr: com.apple.quarantine` (start value was `0181;6a698ac1;Chrome;85EB6132-5F18-4F3A-B536-21FA83E2EEA7`) |
| B4 | Process path checked for `/AppTranslocation/` | **PASS** — `/Applications/Open-Anti-Browser.app/Contents/MacOS/Open-Anti-Browser`, **no translocation** |
| B5 | Official System Settings → "Open Anyway" path walked | **N/A** — never exercised; the app became usable without it (evidence above) |
| B6 | `xattr` re-measured after official approval | **N/A** — follows from B5 |
| B7 | Second launch: prompts? still translocated? | **PASS** — no prompt, no translocation, ran 35+ min clean |
| B8 | Fallback command typed manually | **N/A** — never needed |

**RESEARCH Open Question 1 — resolved, and it falsifies the premise.** `05-RESEARCH.md` asserted
that App Translocation is independent of the destination directory and that the in-app self-strip
must therefore fail on first launch. **Both halves are false on real hardware.** A Finder
drag-install to `/Applications` produced no translocation, and the self-strip succeeded — twice
under synthetic tags and once under a real one, three for three. Assumption **A1** is falsified.

**Consequence for D-12a:** the fallback notice is a genuine exception path, not the expected
first-launch main path. The D-12a re-route (copying the kernel to
`~/Library/Application Support/.../engines/`) is **not needed** and was not pursued.

### Group C — the three exit paths (PKG-02 / ROADMAP SC2 / D-07) — 4/4 PASS

Verified against the twice-fixed build. Both defects below were found by *this* group.

| # | Item | Result |
|---|---|---|
| C1 | Cmd+Q: window gone, menu-bar item gone, Dock exited | **PASS** |
| C2 | No residual process; port 8000 released; no crash report | **PASS** — `✓ 无残留进程`, `✓ 已释放`, 0 crash reports |
| C3 | Red-X: window gone but process alive and menu-bar item retained; clicking it reopens the main window | **PASS** — pid 31614 alive at **0.2 % CPU**, `127.0.0.1:8000` still LISTEN; click reopens |
| C4 | Menu-bar right-click → "退出程序" exits cleanly | **PASS** — no residual process, port released |

Menu-bar context-menu labels confirmed as **「打开主界面」** and **「退出程序」**, matching source.

The user's own characterisation of C3: *"点红叉没有关闭…和 windows 现象有点像，就是它会后台挂着"* —
the three paths are correctly differentiated, which is exactly D-07's intent.

> One measurement artifact worth recording: an intermediate C3 reading reported "process gone" only
> because the app had not been relaunched first — a false negative from running the measurement
> without performing the interaction. Re-run with the interaction performed, C3 passes.

### Group D — icon and application name (PKG-02) — 3/3 PASS

| # | Item | Result |
|---|---|---|
| D1 | Dock icon is the app logo; quality at maximum size | **PASS — verdict: ACCEPTABLE** |
| D2 | Menu-bar application name is correct (not `launch_app` / `Python`) | **PASS** — `Open-Anti-Browser` |
| D3 | Finder Get Info shows correct icon, name, version | **PASS** |

`Info.plist` measured values:

```
CFBundleName             Open-Anti-Browser
CFBundleDisplayName      Open-Anti-Browser
CFBundleShortVersionString  0.1.16
CFBundleIdentifier       com.shengsoft.openantibrowser
LSMinimumSystemVersion   15.0
```

**Icon resolution finding (refines 05-01's record).** Unpacking the shipped `app.icns` yields
**9 tiers**, topping out at `icon_512x512.png` = 512×512. The `icon_512x512@2x` tier (which would be
1024×1024) is **absent entirely** — not present-at-512, but missing.

This also means the plan's D1 instruction ("magnify the Dock to maximum") is a **weak test for this
particular concern**: maximum Dock magnification is 128 pt = 256 physical px on Retina, and
`icon_128x128@2x` is a native 256×256, so the Dock renders at native resolution no matter what. The
tier actually stresses at **Finder icon view, maximum icon size** (512 pt = 1024 px → 2× upscale).
The user inspected both and returned **ACCEPTABLE**.

**Actionable-if-revisited:** `frontend/public/logo.png` exists in-repo at **1536×1024** — materially
larger than the 512×512 `assets/logo-512.png` the icns was built from. Should the verdict ever be
revisited, a true 1024 tier is achievable from existing assets (needs square crop/pad). Not done in
this phase; the verdict is ACCEPTABLE.

### Group E — it actually works after install (D-15) — 3/3 PASS

| # | Item | Result |
|---|---|---|
| E1 | New Chrome-engine profile created | **PASS** |
| E2 | Fingerprint Chrome window really launched | **PASS** — kernel at `…/Open-Anti-Browser.app/Contents/Resources/engines/chrome/Chromium.app`, debug port `127.0.0.1:52182` LISTEN |
| E3 | Stop leaves no residual Chromium | **PASS** — `pgrep -fc 'Open-Anti-Browser.app.*Chromium'` = **0**; port 52182 released |

**D-15's core question is answered affirmatively:** the kernel ships inside the package and works
on install, launched from within the `.app`.

**AMFI capture during kernel launch:**

```
kernel: AMFI: '…/engines/chrome/Chromium.app/Contents/MacOS/Chromium' is adhoc signed.
amfid:  …/Chromium not valid: Error … Code=-423 "adhoc signed or signed by an unknown certificate chain"
```

Same `-423` as the host app — and crucially, **no `Security policy would not allow process`**.
Because quarantine had been stripped, ASP does not intervene. This is the positive-direction
confirmation of Phase 3 D-07's evidence (which established that an *unclean* quarantine gets the
kernel AMFI-killed silently, with no dialog). **T-05-27 mitigated.**

**One log signal investigated and dismissed as benign:**

```
AMFI: '…/Chromium Framework.framework/…/Libraries/libGLESv2.dylib' has no CMS blob?
AMFI: '…/libGLESv2.dylib': Unrecoverable CT signature issue, bailing out.
```

Measured on the installed product, all three `Libraries/*.dylib` **are** validly signed:

```
libEGL.dylib             flags=0x20002 (adhoc, linker-signed)  hashes=23+0
libGLESv2.dylib          flags=0x20002 (adhoc, linker-signed)  hashes=1677+0
libvk_swiftshader.dylib  flags=0x20002 (adhoc, linker-signed)  hashes=3772+0
```

Ad-hoc signatures have no CMS/CT blob **by definition** (CMS is a certificate-chain structure), so
AMFI's message is it abandoning Certificate-Transparency validation that was never applicable — not
a signing hole. The CI signing script does not need to sign these individually: step 2's
`codesign --force --sign - "$FRAMEWORK/Versions/Current"` already seals `Libraries/`.
`codesign --verify --deep --strict` on the installed app **passes**.

## Defects Found (both fixed before this checkpoint could complete)

### Defect 1 — app crashed ~2 s after launch, 100 % reproducible

Round 1's double-click produced no dialog at all: the app launched, reached main-window `show()`,
and SIGSEGV'd. Three identical crash reports.

```
Thread 0 (CrBrowserMain), EXC_BAD_ACCESS, KERN_INVALID_ADDRESS at 0x8
  0  libpyside6   PySide::typeName(QObject const*) + 36
  1  libpyside6   PySide::getWrapperForQObject(QObject*, _typeobject*)
  2  QtCore.abi3  QObjectWrapper::sbk_o_eventFilter(...)
  3  QtCore.abi3  QObjectWrapper::eventFilter(QObject*, QEvent*)
  4  QtCore       QCoreApplicationPrivate::sendThroughApplicationEventFilters
 18  QtQuick      QQuickDeliveryAgentPrivate::setFocusInScope
 40  AppKit       -[NSWindow makeKeyAndOrderFront:]
 49  QtWidgets.abi3  Sbk_QWidgetFunc_show
```

Root cause: `qt_app.installEventFilter(...)`. Qt gives filters installed on
`QCoreApplication::instance()` thread-wide scope, forcing PySide to build a Python wrapper for every
QObject receiving any event; QtQuick's internal focus delivery during Cocoa window activation hands
it objects PySide cannot safely wrap. Ruled out as Gatekeeper/translocation/signing-related by
reproducing it with quarantine already stripped.

Fixed by replacing the filter with a `QApplication` subclass overriding `event()`. See
`05-02-GAP-FIX-SUMMARY.md`.

### Defect 2 — Cmd+Q spun forever instead of exiting

With the crash fixed, C1 revealed the next layer: Cmd+Q closed the window, hid the tray icon, and
released port 8000 (so `shutdown()` genuinely ran) — but left the process alive at **59.6 % CPU**.
`SIGTERM` had no effect; `SIGKILL` was required. `sample` put **1978 of 1978** samples in
`QCoreApplicationPrivate::sendPostedEvents`.

Root cause: `DesktopApplication.event()` unconditionally returned `True` for `QEvent::Quit`, so
`super().event(e)` — where `QCoreApplication`'s default Quit handling performs the actual exit —
was never reached. Meanwhile `closeEvent` ends with `QTimer.singleShot(0, quit)`, posting another
Quit that was swallowed identically. Closed loop.

**This was not a regression from the first gap fix.** The original `installEventFilter` shape had
the identical flaw — a filter returning `True` also blocks delivery to the QApplication. **D-07's
Cmd+Q had never worked in any shipped form**; the launch crash simply prevented anyone from ever
pressing it.

Fixed by always forwarding to `super().event(e)`, plus a `_closing` idempotency guard on
`force_exit()`. See `05-02-GAP-FIX-2-SUMMARY.md`.

### Why no automated gate caught either

| Gate | Why it missed |
|---|---|
| `tests/test_macos_desktop_runtime.py` (21 tests) | Exercises pure logic functions against a fake window; never touches Qt/PySide integration |
| CI `--backend-only` smoke test | By definition never enters `run_desktop()`, so no GUI event loop runs |
| `codesign --verify --deep --strict` | Signatures were genuinely fine and unrelated |
| GUI smoke gate added by gap-fix 1 (18 s survival) | Would have **passed** on defect 2 — that bug makes the process survive *too well* |

Both gaps are now closed by the extended CI gate (survive 18 s, then a real Quit request must
terminate the process within 12 s), validated in both directions on real runs — buggy code fails it
(`30418065169`), fixed code passes it (`30418547844`).

**This is the checkpoint justifying its own existence.** `05-VALIDATION.md` predicted that this
class of defect is manual-only; it was right on both counts.

## Open Items

### 1. B1 dialog wording — documented gap (user-accepted)

The decision *sequence* is objectively established from `syspolicyd` logs. What is missing is the
prompt's rendered **title and button labels**, and which button was pressed. The user's recollection
of this is demonstrably unreliable (it contradicted the log evidence) and is therefore not recorded
as fact. The user explicitly chose to accept the gap rather than run a fourth install cycle.

Phase 6 will need this wording to write user-facing release documentation, and will perform a real
install anyway. **Carried forward as a Phase 6 input.**

### 2. dmg background guidance does not match the actual working path — NEEDS FIXING (Phase 6 scope)

The measured real-user path on macOS 15.7 is:

> double-click → Gatekeeper prompt → denied → **app exits** → double-click again → **works**

The dmg background instead instructs *"在应用图标上点右键 → 「打开」"* / *"right-click the app icon
→ Open"*. That path was never exercised here and is not what made the app usable.

Worse, there is a real experience gap: after the first denial the user's only signal is "the app
closed". Nothing tells them a second double-click will work. A user who does not know this is
likely to give up or follow the background's right-click advice, which may not even be available on
macOS 15.

**Specific, actionable requirement** (deliberately NOT executed here — PKG/DOCS division of labour
is fixed in the plan, and this is DOCS):
- `assets/dmg-background.png` + `@2x`: revise the footer to describe the observed path.
- Phase 6 release notes: document "blocked once, then launch again" as the expected first-run flow.

### 3. B5/B6/B8 permanently N/A for this configuration

The official System-Settings approval path was never exercised because the app became usable
without it. If Phase 6 wants that path documented, it needs a deliberate setup where the self-strip
is prevented.

### 4. `spctl --assess` remains `rejected`

The app runs, but is not Gatekeeper-approved — it works because it is no longer quarantined, not
because it was ever allowed. This is expected for an ad-hoc-signed app and is worth stating plainly
in the release notes so nobody mistakes "it runs" for "it is trusted by Gatekeeper".

### 5. macOS 15.0 minimum, carried from 05-04

`LSMinimumSystemVersion` is 15.0, driven by PySide6/shiboken6's own binding libraries measuring
`minos=15.0`. The shipped app cannot launch on macOS < 15 (Sequoia, 2024). Not a 05-06 finding, but
it belongs in the release documentation.

## Issues Encountered

Beyond the two defects above:

- **Two rounds voided by synthetic quarantine tags.** Rounds 1 and 2 used `xattr -w`-synthesised
  quarantine and produced inconsistent Gatekeeper behavior. Measurement later showed the synthetic
  tags differ from a real download in both flags (`0083` vs `0081`) and LaunchServices database
  association. Only the real-download round is reported.
- **grep self-match inflated a residual-process count.** `ps -Ao command | grep -ic chromium`
  counted the grep pipeline's own command line, and separately matched IntelliJ IDEA's CEF helpers
  (whose paths contain "Chromium Embedded Framework"), initially suggesting 6 residual kernel
  processes. `pgrep -fc 'Open-Anti-Browser.app.*Chromium'` returns **0**. E3 passes.
- **One false-negative C3 reading** from running the measurement without first performing the
  interaction.

## Next Phase Readiness

Phase 6 (release docs + end-to-end verification) inherits, as concrete inputs:

1. The measured first-run path — *blocked once, app exits, launch again* — which is what the release
   notes must describe.
2. The dmg background text fix (Open Item 2).
3. The B1 dialog wording still to be captured (Open Item 1).
4. `spctl` remains `rejected`; macOS 15.0 minimum (Open Items 4 and 5).
5. Confirmation that D-12a's re-route is unnecessary — the self-strip works.
