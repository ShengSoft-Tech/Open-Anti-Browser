# Deferred Items — Phase 01

Out-of-scope discoveries made during plan execution, logged per executor scope-boundary rules
(not fixed here — pre-existing and unrelated to the current plan's file changes).

## 01-01

- **`tests.test_sync_regressions.SynchronizerRegressionTests.test_installer_closes_existing_desktop_app_before_install`**
  fails with `FileNotFoundError: installer/Open-Anti-Browser.iss` on a fresh macOS checkout.
  Root cause: `installer/` is gitignored per CLAUDE.md ("打包脚本已 gitignore,不要把打包配置加回仓库"),
  so the `.iss` file simply isn't present in this checkout. This failure is unrelated to the
  window_manager/runtime_control platform changes in 01-01 (it fails on any fresh checkout,
  any platform, because the referenced file doesn't exist in git). Not fixed — out of scope
  for XPLAT-01/02/04.
