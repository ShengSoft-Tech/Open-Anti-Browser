<!-- RELEASE_VERSION: 0.2.0 -->

## 下载前必读：系统要求

**硬件与系统要求（需同时满足）：**

- Apple Silicon（M 系列）芯片
- macOS 15 或更新版本

本次发布只提供一个安装包，为 arm64 架构，不提供其他架构版本可供选择。

**如何自查（推荐使用图形界面，无需打开终端）：**

1. 点击屏幕左上角的苹果 Logo，选择“关于本机”
2. 查看“芯片”一行：必须显示 Apple M 系列芯片（例如 Apple M1 / M2 / M3 / M4 等）
3. 查看系统版本号：必须是 macOS 15 或更高

如果你习惯使用终端，也可以执行以下命令进行自查（可选，并非必需）：

```
uname -m && sw_vers -productVersion
```

结果应为 `arm64`，以及一个 15 或更高的版本号，即为满足要求。

**如果你的 Mac 不满足以上要求：**
如果系统版本低于 macOS 15，预计应用会被系统拒绝打开；如果是 Intel（x64）Mac，则无法运行这个仅支持 arm64 架构的安装包。以上两种情况均未在真实设备上实测验证，是根据应用声明的最低系统版本与单一架构构建方式推断得出，仅供参考。

## 关于签名与信任状态的说明

本应用未使用 Apple 开发者证书签名，也未经过公证（Notarization）。完成下面的放行步骤后，应用能够运行，只是因为本机上的一次性隔离标记（quarantine）已经被移除，并不是因为 Apple 或 Gatekeeper 对这个应用给出了任何担保；对该应用包执行 Gatekeeper 评估（assessment），仍然会报告拒绝。这是未经苹果签名与公证的应用的正常状态，不是安全隐患。

---

## 首次打开被拦截？这是正常现象

本应用未做 Apple 开发者签名，首次打开会被系统拦截，这是预期行为，并不代表安装包损坏或程序有问题。

1. **再次双击打开应用即可。** 首次双击后 macOS 会短暂弹出拦截提示，应用随即自动退出；关闭提示后再双击一次通常就能正常打开——这是在真实硬件上实测得到的行为，不是推测。

<details>
<summary>如果第二次双击仍然打不开</summary>

2. 打开“系统设置 → 隐私与安全性”，滚动到“安全性”区域，找到关于 Open-Anti-Browser 的提示，点击“仍要打开”。
3. 如果以上都不行，打开“终端”（Terminal），完整复制粘贴以下命令并回车：

   ```
   xattr -dr com.apple.quarantine "/Applications/Open-Anti-Browser.app"
   ```

   如果把应用安装在了别的位置，请把命令里引号内的路径换成实际安装路径。

</details>

应用能够正常运行，是因为它不再带有系统隔离标记（quarantine），并不代表它已通过 Apple 签名认证或已被 Gatekeeper 信任——这是这类未签名应用的预期正常状态，不是安全隐患。

## Before You Download: System Requirements

**Hardware and OS requirements (both must be true):**

- Apple Silicon (M-series) chip
- macOS 15 or newer

Only one installer is published for this release, built for arm64 — there is no other architecture to choose from.

**How to check (recommended: GUI, no Terminal needed):**

1. Click the Apple logo in the top-left corner, then choose "About This Mac"
2. Check the "Chip" row: it must show an Apple M-series chip (e.g. Apple M1 / M2 / M3 / M4)
3. Check the macOS version number: it must be macOS 15 or higher

If you're comfortable with Terminal, you can also run this optional check:

```
uname -m && sw_vers -productVersion
```

A passing result is `arm64` together with a version number of 15 or higher.

**What to expect if your Mac doesn't meet these requirements:**
On macOS versions earlier than 15, the app is expected to be refused by the system when you try to open it. On an Intel (x64) Mac, this arm64-only package cannot run at all. Neither outcome has been verified on real hardware — both are inferred from the app's declared minimum system version and its single-architecture build, and are provided for reference only.

## About Signing and Trust

This app is not signed with an Apple Developer ID and is not notarized. After completing the steps below, the app runs only because the one-time local quarantine mark has been removed — not because Apple or Gatekeeper has given it any kind of endorsement. A Gatekeeper assessment of the app bundle still reports a rejection. This is the normal, expected state for an ad-hoc-signed app like this one, not a security concern.

---

## First launch blocked? This is expected

This app is not signed with an Apple Developer ID, so macOS blocks it on first launch by design — this does not mean the installer is broken or the app itself is faulty.

1. **Just double-click the app again.** On the first double-click, macOS briefly shows a block dialog and the app quits itself; after dismissing that dialog, double-clicking again usually opens it normally — this is the behaviour measured on real hardware, not a guess.

<details>
<summary>If it still won't open after the second double-click</summary>

2. Open "System Settings → Privacy & Security", scroll to the "Security" section, find the notice about Open-Anti-Browser, and click "Open Anyway".
3. If that still doesn't work, open "Terminal", copy and paste the following command exactly, and press Enter:

   ```
   xattr -dr com.apple.quarantine "/Applications/Open-Anti-Browser.app"
   ```

   If you installed the app somewhere else, replace the path inside the quotes with the actual install location.

</details>

The app runs because it is no longer quarantined by the system, not because it has been signed by Apple or trusted by Gatekeeper — this is the expected, normal state for an app like this, not a security concern.
