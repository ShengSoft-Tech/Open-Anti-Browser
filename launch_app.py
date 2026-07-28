from __future__ import annotations

import argparse
import atexit
import hashlib
import os
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

from uvicorn import Config, Server

from backend.config import APP_ROOT, ASSETS_DIR, BIND_HOST, FRONTEND_DIST_DIR
from backend.main import app
from backend._g import _7 as _0x2f
from backend.runtime_control import clear_backend_only_state, find_available_port as find_backend_port, write_backend_only_state
from backend.ui_bridge import register_directory_picker_callback, register_exit_callback


APP_TITLE = "Open-Anti-Browser · 开源指纹浏览器"

# macOS quarantine 兜底提示的命令目标：与 frontend/src/lib/macosGatekeeperNotice.js
# 的 GATEKEEPER_XATTR_COMMAND 逐字对齐（Phase 5 D-12/D-12a），不得另起第三套措辞。
QUARANTINE_ATTRIBUTE = "com.apple.quarantine"
CANONICAL_INSTALL_BUNDLE = "/Applications/Open-Anti-Browser.app"


def find_available_port(preferred: int = 8000, span: int = 20) -> int:
    for port in range(preferred, preferred + span):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind((BIND_HOST, port))
                return port
            except OSError:
                continue
    raise RuntimeError(f"没有找到可用端口，请先关闭占用 {preferred}~{preferred + span - 1} 的程序。")


def wait_for_port(port: int, timeout: float = 20.0) -> None:
    stop_at = time.time() + timeout
    while time.time() < stop_at:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.5)
            if sock.connect_ex(("127.0.0.1", port)) == 0:
                return
        time.sleep(0.2)
    raise RuntimeError("本地服务启动超时。")


def resolve_window_icon_path() -> Path | None:
    candidates = [
        ASSETS_DIR / "app.ico",
        ASSETS_DIR / "logo-512.png",
        FRONTEND_DIST_DIR / "logo.png",
        FRONTEND_DIST_DIR / "logo.jpeg",
        Path(__file__).resolve().parent / "frontend" / "public" / "logo.png",
        Path(__file__).resolve().parent / "frontend" / "public" / "logo.jpeg",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def should_intercept_quit_event() -> bool:
    # 唯一的平台判定入口：macOS 上 Cmd+Q 会走 closeEvent 的托盘分支被 event.ignore() 吞掉
    # （D-07），需要单独接一条路径收敛到既有的窗口退出方法。Windows/Linux 不拦截，
    # closeEvent 逐字不变。
    return sys.platform == "darwin"


def handle_macos_quit_request(window) -> bool:
    # 只换触发源，不平行发明第二套 shutdown 逻辑：退出仍然走既有的窗口退出方法
    # （-> closeEvent 的 shutdown 分支 -> event.accept() -> quit()）。
    window.force_exit()
    return True


def is_macos_frozen_runtime() -> bool:
    return sys.platform == "darwin" and bool(getattr(sys, "frozen", False))


def resolve_app_bundle_root(executable: str | None = None) -> Path | None:
    target = Path(executable or sys.executable).resolve()
    for parent in target.parents:
        if parent.suffix == ".app":
            return parent
    return None


def is_translocated_path(path) -> bool:
    # App Translocation 触发时 sys.executable 落在只读的
    # /private/var/folders/.../AppTranslocation/<uuid>/d/... 挂载点下（RESEARCH Pitfall 4）。
    # 按「Don't Hand-Roll」结论用子串判定，不调用任何私有 API。
    return "/AppTranslocation/" in str(path)


def strip_quarantine_from_bundle(bundle: Path) -> tuple[bool, str]:
    # 必须递归作用于整个 bundle：Phase 3 D-07 已实证只剥主二进制不够，framework
    # dylib 与 helper 也带 quarantine。参数为列表形式传入，不经 shell，无注入面。
    result = subprocess.run(
        ["xattr", "-dr", QUARANTINE_ATTRIBUTE, str(bundle)],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0, (result.stderr or "").strip()


def quarantine_command_target(bundle) -> str:
    # translocate 之后 sys.executable 指向只读随机路径，敲了也没用——命令必须
    # 换算成规范安装位置，与前端 GATEKEEPER_XATTR_COMMAND 保持逐字一致。
    if bundle is None or is_translocated_path(bundle):
        return CANONICAL_INSTALL_BUNDLE
    return str(bundle)


def build_quarantine_failure_message(bundle) -> str:
    target = quarantine_command_target(bundle)
    command = f"xattr -dr {QUARANTINE_ATTRIBUTE} {target}"
    return (
        "首次打开 Open-Anti-Browser 时出现这个提示是正常现象，不代表应用损坏或出错。\n\n"
        "macOS 会给刚安装的应用加上一次性的隔离标记，需要手动清除一次才能正常启动内置的浏览器内核。"
        "请打开“终端”（Terminal），完整复制粘贴以下命令并回车：\n\n"
        f"{command}\n\n"
        "若你把应用安装在了别的位置，请把命令末尾的路径换成实际安装位置。"
    )


def maybe_strip_quarantine() -> str | None:
    # 三重前置守卫：非 darwin / 非冻结态 / 推导不出 bundle 根，任一成立都不触碰 subprocess。
    if not is_macos_frozen_runtime():
        return None
    bundle = resolve_app_bundle_root()
    if bundle is None:
        return None
    succeeded, _stderr = strip_quarantine_from_bundle(bundle)
    if succeeded:
        return None
    return build_quarantine_failure_message(bundle)


def build_server(port: int) -> tuple[Server, threading.Thread]:
    config = Config(
        app=app,
        host=BIND_HOST,
        port=port,
        log_level="warning",
        access_log=False,
        log_config=None,
    )
    server = Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    return server, thread


def _desktop_instance_server_name() -> str:
    identity = str(Path(sys.argv[0]).resolve()).lower()
    digest = hashlib.sha1(identity.encode("utf-8")).hexdigest()[:16]
    return f"OpenAntiBrowserDesktop_{digest}"


def _desktop_chromium_flags() -> list[str]:
    desired_flags = [
        "--disable-features=CalculateNativeWinOcclusion,BackForwardCache",
    ]
    current_flags = os.environ.get("QTWEBENGINE_CHROMIUM_FLAGS", "").strip().split()
    merged_flags = [flag for flag in current_flags if flag]
    existing_flags = set(merged_flags)
    for flag in desired_flags:
        if flag not in existing_flags:
            merged_flags.append(flag)
            existing_flags.add(flag)
    return merged_flags


def _desktop_qt_opengl_backend() -> str:
    override = str(os.environ.get("OAB_DESKTOP_QT_OPENGL") or "").strip().lower()
    if override in {"software", "desktop", "angle"}:
        return override
    return "angle"


def _configure_desktop_webview_env() -> None:
    os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = " ".join(_desktop_chromium_flags()).strip()
    os.environ["QT_OPENGL"] = _desktop_qt_opengl_backend()


def run_backend_only(port: int | None = None) -> int:
    target_port = port or find_backend_port(18000, 20)
    write_backend_only_state(os.getpid(), target_port)
    atexit.register(clear_backend_only_state)
    try:
        server = Server(
            Config(
                app=app,
                host=BIND_HOST,
                port=target_port,
                log_level="warning",
                access_log=False,
                log_config=None,
            )
        )
        server.run()
        return 0
    finally:
        clear_backend_only_state()


def run_desktop() -> int:
    _configure_desktop_webview_env()
    from PySide6.QtCore import QEvent, QObject, Qt, QTimer, QUrl, Signal, Slot
    from PySide6.QtGui import QAction, QCloseEvent, QIcon
    from PySide6.QtNetwork import QLocalServer, QLocalSocket
    from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile, QWebEngineSettings
    from PySide6.QtWebEngineWidgets import QWebEngineView
    from PySide6.QtWidgets import QApplication, QFileDialog, QMainWindow, QMenu, QMessageBox, QSystemTrayIcon

    QApplication.setAttribute(Qt.AA_ShareOpenGLContexts, True)
    desktop_backend = _desktop_qt_opengl_backend()
    if desktop_backend == "software":
        QApplication.setAttribute(Qt.AA_UseSoftwareOpenGL, True)
    elif desktop_backend == "desktop":
        QApplication.setAttribute(Qt.AA_UseDesktopOpenGL, True)
    elif desktop_backend == "angle" and hasattr(Qt, "AA_UseOpenGLES"):
        QApplication.setAttribute(getattr(Qt, "AA_UseOpenGLES"), True)

    class DirectoryPickerBridge(QObject):
        pick_directory_requested = Signal(str, str)

        def __init__(self, owner: "DesktopMainWindow") -> None:
            super().__init__(owner)
            self.owner = owner
            self._result: str | None = None
            self.pick_directory_requested.connect(self._pick_directory, Qt.BlockingQueuedConnection)

        def pick_directory(self, title: str = "", initial_dir: str = "") -> str | None:
            self._result = None
            self.pick_directory_requested.emit(title, initial_dir)
            return self._result

        @Slot(str, str)
        def _pick_directory(self, title: str, initial_dir: str) -> None:
            start_dir = str(initial_dir or APP_ROOT)
            chosen = QFileDialog.getExistingDirectory(
                self.owner,
                title or "选择扩展文件夹",
                start_dir,
            )
            self._result = chosen or None

    class DesktopMainWindow(QMainWindow):
        def __init__(self, url: str, server: Server, thread: threading.Thread) -> None:
            super().__init__()
            self.url = url
            self.server = server
            self.server_thread = thread
            self._closing = False
            self._force_exit = False
            self._tray_notified = False
            self._recovering_renderer = False
            self.tray_icon: QSystemTrayIcon | None = None

            self.setWindowTitle(APP_TITLE)
            self.setWindowIcon(window_icon)
            self.resize(1480, 960)
            self.setMinimumSize(1180, 760)

            self.web_profile = QWebEngineProfile(APP_TITLE, self)
            self.web_profile.setPersistentStoragePath(str(APP_ROOT / "data" / "qt-webview"))
            self.web_profile.setCachePath(str(APP_ROOT / "data" / "qt-webview-cache"))
            self.web_profile.setPersistentCookiesPolicy(QWebEngineProfile.ForcePersistentCookies)

            self.browser = QWebEngineView(self)
            self.browser.setPage(QWebEnginePage(self.web_profile, self.browser))
            self.browser.settings().setAttribute(QWebEngineSettings.LocalStorageEnabled, True)
            self.browser.settings().setAttribute(QWebEngineSettings.JavascriptEnabled, True)
            self.browser.settings().setAttribute(QWebEngineSettings.FullScreenSupportEnabled, True)
            self.browser.loadFinished.connect(self._handle_load_finished)
            self.browser.page().renderProcessTerminated.connect(self._handle_render_process_terminated)
            self.setCentralWidget(self.browser)
            self.browser.setUrl(QUrl(self.url))

            if QSystemTrayIcon.isSystemTrayAvailable():
                self._create_tray_icon()

        def _create_tray_icon(self) -> None:
            tray = QSystemTrayIcon(window_icon, self)
            tray.setToolTip(APP_TITLE)
            tray.activated.connect(self._handle_tray_activated)

            menu = QMenu()
            open_action = QAction("打开主界面", self)
            open_action.triggered.connect(self.restore_from_tray)
            exit_action = QAction("退出程序", self)
            exit_action.triggered.connect(self.force_exit)
            menu.addAction(open_action)
            menu.addSeparator()
            menu.addAction(exit_action)
            tray.setContextMenu(menu)
            tray.show()
            self.tray_icon = tray

        def _handle_load_finished(self, ok: bool) -> None:
            if ok:
                self._recovering_renderer = False
                return
            if self._closing:
                return
            QMessageBox.critical(
                self,
                APP_TITLE,
                f"页面加载失败。\n\n请确认本地服务是否正常启动：{self.url}",
            )

        def _handle_render_process_terminated(self, termination_status, exit_code: int) -> None:
            if self._closing:
                return
            if self._recovering_renderer:
                return
            self._recovering_renderer = True
            if self.tray_icon is not None:
                self.tray_icon.showMessage(
                    APP_TITLE,
                    "界面已自动恢复，请继续使用。",
                    QSystemTrayIcon.Warning,
                    2500,
                )
            QTimer.singleShot(450, lambda: self.browser.setUrl(QUrl(self.url)))

        def _handle_tray_activated(self, reason) -> None:
            if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
                self.restore_from_tray()

        def restore_from_tray(self) -> None:
            self.showNormal()
            self.setWindowState((self.windowState() & ~Qt.WindowMinimized) | Qt.WindowActive)
            self.raise_()
            self.activateWindow()

        def force_exit(self) -> None:
            self._force_exit = True
            self.showNormal()
            self.close()

        def closeEvent(self, event: QCloseEvent) -> None:
            if not self._force_exit and self.tray_icon is not None:
                self.hide()
                if not self._tray_notified:
                    self.tray_icon.showMessage(
                        APP_TITLE,
                        "程序已最小化到托盘，可在托盘图标中重新打开或退出。",
                        QSystemTrayIcon.Information,
                        2500,
                    )
                    self._tray_notified = True
                event.ignore()
                return
            self.shutdown()
            event.accept()
            QTimer.singleShot(0, QApplication.instance().quit)

        def shutdown(self) -> None:
            if self._closing:
                return
            self._closing = True
            self.server.should_exit = True
            self.server.force_exit = True
            self.browser.stop()
            if self.tray_icon is not None:
                self.tray_icon.hide()
            self.server_thread.join(timeout=8)

    class MacQuitEventFilter(QObject):
        # macOS Cmd+Q 只作为触发源，事件本身不携带任何 shutdown 逻辑
        # （逻辑全部在模块级的 handle_macos_quit_request 里）。
        def __init__(self, target_window: "DesktopMainWindow", parent: QObject) -> None:
            super().__init__(parent)
            self.target_window = target_window

        def eventFilter(self, obj, event) -> bool:
            if event.type() == QEvent.Type.Quit:
                return handle_macos_quit_request(self.target_window)
            return False

    qt_app = QApplication.instance() or QApplication([])
    qt_app.setApplicationDisplayName(APP_TITLE)
    qt_app.setApplicationName(APP_TITLE)
    qt_app.setQuitOnLastWindowClosed(False)
    icon_path = resolve_window_icon_path()
    window_icon = QIcon(str(icon_path)) if icon_path else QIcon()
    if not window_icon.isNull():
        qt_app.setWindowIcon(window_icon)

    instance_server_name = _desktop_instance_server_name()
    activation_socket = QLocalSocket()
    activation_socket.connectToServer(instance_server_name)
    if activation_socket.waitForConnected(500):
        activation_socket.write(b"activate")
        activation_socket.flush()
        activation_socket.waitForBytesWritten(500)
        activation_socket.disconnectFromServer()
        return 0
    activation_socket.abort()

    instance_server = QLocalServer()
    if not instance_server.listen(instance_server_name):
        QLocalServer.removeServer(instance_server_name)
        if not instance_server.listen(instance_server_name):
            QMessageBox.critical(None, APP_TITLE, "程序实例检测失败，请先关闭已有程序后重试")
            return 1

    quarantine_failure_message = maybe_strip_quarantine()
    if quarantine_failure_message:
        # D-12a：这是首次打开时的预期主路径，不是异常，用 information 而非 critical。
        QMessageBox.information(None, APP_TITLE, quarantine_failure_message)

    try:
        port = find_available_port(8000, 20)
        server, thread = build_server(port)
        wait_for_port(port)
    except Exception as exc:
        QMessageBox.critical(None, APP_TITLE, f"启动失败：\n{exc}")
        return 1

    window = DesktopMainWindow(f"http://127.0.0.1:{port}?shell=desktop", server, thread)
    directory_picker_bridge = DirectoryPickerBridge(window)

    if should_intercept_quit_event():
        # qt_app 作为 parent，保持强引用避免被 GC 回收。
        mac_quit_filter = MacQuitEventFilter(window, qt_app)
        qt_app.installEventFilter(mac_quit_filter)

    def handle_instance_activation() -> None:
        while instance_server.hasPendingConnections():
            connection = instance_server.nextPendingConnection()
            if connection is None:
                break
            connection.waitForReadyRead(200)
            try:
                connection.readAll()
            except Exception:
                pass
            connection.disconnectFromServer()
        QTimer.singleShot(0, window.restore_from_tray)

    instance_server.newConnection.connect(handle_instance_activation)

    def request_exit_from_api() -> None:
        QTimer.singleShot(0, window.force_exit)

    register_exit_callback(request_exit_from_api)
    register_directory_picker_callback(directory_picker_bridge.pick_directory)
    qt_app.aboutToQuit.connect(window.shutdown)
    qt_app.aboutToQuit.connect(lambda: register_exit_callback(None))
    qt_app.aboutToQuit.connect(lambda: register_directory_picker_callback(None))
    qt_app.aboutToQuit.connect(instance_server.close)
    qt_app.aboutToQuit.connect(lambda: QLocalServer.removeServer(instance_server_name))
    window.show()
    QTimer.singleShot(120, window.activateWindow)
    return qt_app.exec()


def main(argv: list[str] | None = None) -> int:
    _0x2f("runtime")

    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--backend-only", action="store_true")
    parser.add_argument("--port", type=int, default=None)
    args, _ = parser.parse_known_args(argv)

    if args.backend_only:
        return run_backend_only(args.port)
    return run_desktop()


if __name__ == "__main__":
    raise SystemExit(main())
