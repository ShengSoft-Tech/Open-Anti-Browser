from __future__ import annotations

import sys
from typing import Any, Callable

if sys.platform == "win32":
    import math

    import psutil
    import win32api
    import win32con
    import win32gui
    import win32process

    ENGINE_WINDOW_CLASSES = {
        "chrome": {"Chrome_WidgetWin_1", "Chrome_WidgetWin_0"},
        "firefox": {"MozillaWindowClass"},
    }

    def list_monitors() -> list[dict[str, Any]]:
        monitors: list[dict[str, Any]] = []
        for index, (handle, _, _) in enumerate(win32api.EnumDisplayMonitors()):
            info = win32api.GetMonitorInfo(handle)
            work_left, work_top, work_right, work_bottom = info["Work"]
            mon_left, mon_top, mon_right, mon_bottom = info["Monitor"]
            device = str(info.get("Device") or f"MONITOR_{index + 1}")
            monitors.append(
                {
                    "id": device,
                    "index": index,
                    "name": device,
                    "primary": bool(info.get("Flags", 0) & win32con.MONITORINFOF_PRIMARY),
                    "work_area": {
                        "left": work_left,
                        "top": work_top,
                        "width": max(0, work_right - work_left),
                        "height": max(0, work_bottom - work_top),
                    },
                    "bounds": {
                        "left": mon_left,
                        "top": mon_top,
                        "width": max(0, mon_right - mon_left),
                        "height": max(0, mon_bottom - mon_top),
                    },
                }
            )
        return monitors

    def show_windows(runtime_lookup: Callable[[str], dict[str, Any] | None], profile_ids: list[str]) -> dict[str, Any]:
        windows = _collect_profile_windows(runtime_lookup, profile_ids)
        shown = 0
        for entry in windows:
            hwnd = entry["hwnd"]
            try:
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                win32gui.SetWindowPos(
                    hwnd,
                    win32con.HWND_TOP,
                    0,
                    0,
                    0,
                    0,
                    win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_SHOWWINDOW,
                )
                try:
                    win32gui.SetForegroundWindow(hwnd)
                except Exception:
                    pass
                shown += 1
            except Exception:
                continue
        return {"ok": True, "count": shown}

    def set_uniform_size(runtime_lookup: Callable[[str], dict[str, Any] | None], profile_ids: list[str]) -> dict[str, Any]:
        windows = _collect_profile_windows(runtime_lookup, profile_ids)
        if len(windows) < 2:
            return {"ok": True, "count": len(windows)}

        base_rect = windows[0]["rect"]
        target_width = int(base_rect["width"])
        target_height = int(base_rect["height"])
        updated = 0
        for entry in windows[1:]:
            rect = entry["rect"]
            try:
                win32gui.MoveWindow(entry["hwnd"], rect["left"], rect["top"], target_width, target_height, True)
                updated += 1
            except Exception:
                continue
        return {"ok": True, "count": updated + 1, "width": target_width, "height": target_height}

    def arrange_windows(
        runtime_lookup: Callable[[str], dict[str, Any] | None],
        profile_ids: list[str],
        monitor_id: str | None = None,
        arrange_mode: str = "grid",
    ) -> dict[str, Any]:
        windows = _collect_profile_windows(runtime_lookup, profile_ids)
        if not windows:
            return {"ok": True, "count": 0}

        monitor = _pick_monitor(monitor_id)
        work = monitor["work_area"]
        if arrange_mode == "overlap":
            _arrange_overlap(windows, work)
        else:
            _arrange_grid(windows, work)
        return {"ok": True, "count": len(windows), "monitor": monitor}

    def _pick_monitor(monitor_id: str | None) -> dict[str, Any]:
        monitors = list_monitors()
        if not monitors:
            raise RuntimeError("没有找到可用显示器")
        if monitor_id:
            for item in monitors:
                if item["id"] == monitor_id:
                    return item
        for item in monitors:
            if item["primary"]:
                return item
        return monitors[0]

    def _arrange_grid(windows: list[dict[str, Any]], work: dict[str, Any]) -> None:
        gap = 14
        count = len(windows)
        cols = max(1, math.ceil(math.sqrt(count)))
        rows = max(1, math.ceil(count / cols))
        total_gap_x = gap * (cols + 1)
        total_gap_y = gap * (rows + 1)
        cell_width = max(420, int((work["width"] - total_gap_x) / cols))
        cell_height = max(320, int((work["height"] - total_gap_y) / rows))
        for index, entry in enumerate(windows):
            row = index // cols
            col = index % cols
            x = int(work["left"] + gap + col * (cell_width + gap))
            y = int(work["top"] + gap + row * (cell_height + gap))
            try:
                win32gui.ShowWindow(entry["hwnd"], win32con.SW_RESTORE)
                win32gui.MoveWindow(entry["hwnd"], x, y, cell_width, cell_height, True)
            except Exception:
                continue

    def _arrange_overlap(windows: list[dict[str, Any]], work: dict[str, Any]) -> None:
        base_width = max(520, int(work["width"] * 0.76))
        base_height = max(420, int(work["height"] * 0.78))
        offset_x = 34
        offset_y = 26
        for index, entry in enumerate(windows):
            x = int(work["left"] + 26 + index * offset_x)
            y = int(work["top"] + 26 + index * offset_y)
            try:
                win32gui.ShowWindow(entry["hwnd"], win32con.SW_RESTORE)
                win32gui.MoveWindow(entry["hwnd"], x, y, base_width, base_height, True)
            except Exception:
                continue

    def _collect_profile_windows(
        runtime_lookup: Callable[[str], dict[str, Any] | None],
        profile_ids: list[str],
    ) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for profile_id in profile_ids:
            runtime = runtime_lookup(profile_id)
            if not runtime:
                continue
            pid = int(runtime.get("pid") or 0)
            engine = str(runtime.get("engine") or "").lower()
            if not pid or not engine:
                continue
            window = _pick_primary_window(pid, engine)
            if window:
                window["profile_id"] = profile_id
                results.append(window)
        return results

    def _pick_primary_window(pid: int, engine: str) -> dict[str, Any] | None:
        pid_set = _process_tree_pids(pid)
        class_names = ENGINE_WINDOW_CLASSES.get(engine, set())
        candidates: list[dict[str, Any]] = []

        def callback(hwnd: int, _) -> bool:
            if not win32gui.IsWindowVisible(hwnd):
                return True
            try:
                _, owner_pid = win32process.GetWindowThreadProcessId(hwnd)
            except Exception:
                return True
            if owner_pid not in pid_set:
                return True
            class_name = str(win32gui.GetClassName(hwnd) or "")
            if class_names and class_name not in class_names:
                return True
            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
            width = max(0, right - left)
            height = max(0, bottom - top)
            if width < 320 or height < 220:
                return True
            title = str(win32gui.GetWindowText(hwnd) or "")
            candidates.append(
                {
                    "hwnd": hwnd,
                    "title": title,
                    "class_name": class_name,
                    "rect": {
                        "left": left,
                        "top": top,
                        "width": width,
                        "height": height,
                    },
                    "area": width * height,
                }
            )
            return True

        win32gui.EnumWindows(callback, None)
        if not candidates:
            return None
        candidates.sort(key=lambda item: (item["area"], bool(item["title"])), reverse=True)
        return candidates[0]

    def _process_tree_pids(root_pid: int) -> set[int]:
        pid_set = {int(root_pid)}
        try:
            process = psutil.Process(root_pid)
            for child in process.children(recursive=True):
                pid_set.add(int(child.pid))
        except Exception:
            pass
        return pid_set

else:
    _UNSUPPORTED_MSG = "窗口排列仅在 Windows 上可用"

    def list_monitors() -> list[dict[str, Any]]:
        raise RuntimeError(_UNSUPPORTED_MSG)

    def show_windows(runtime_lookup: Callable[[str], dict[str, Any] | None], profile_ids: list[str]) -> dict[str, Any]:
        raise RuntimeError(_UNSUPPORTED_MSG)

    def set_uniform_size(runtime_lookup: Callable[[str], dict[str, Any] | None], profile_ids: list[str]) -> dict[str, Any]:
        raise RuntimeError(_UNSUPPORTED_MSG)

    def arrange_windows(
        runtime_lookup: Callable[[str], dict[str, Any] | None],
        profile_ids: list[str],
        monitor_id: str | None = None,
        arrange_mode: str = "grid",
    ) -> dict[str, Any]:
        raise RuntimeError(_UNSUPPORTED_MSG)
