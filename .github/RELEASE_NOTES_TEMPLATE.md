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
