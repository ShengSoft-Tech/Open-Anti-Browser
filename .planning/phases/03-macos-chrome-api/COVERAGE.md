# Phase 3 — API Coverage Declaration

No external API integration: this phase drives a locally-bundled Chromium binary via `subprocess.Popen` and exposes an internal, read-only `GET /api/capabilities` endpoint plus a `bootstrap()` capabilities block. It integrates no third-party external API/SDK/service — the only "APIs" touched are (1) the project's own local FastAPI surface (`/api/*`, already unauthenticated per existing architecture) and (2) OS-native command-line tools (`xattr`, `psutil` process management) that ship with macOS / are existing pinned dependencies.

Therefore no external-API coverage matrix applies. This reasoned declaration stands in place of a coverage matrix per the `api-coverage.verify-pre` gate.
