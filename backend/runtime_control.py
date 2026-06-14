from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import psutil

from .config import APP_ROOT, BIND_HOST, PROJECT_ROOT
from .services.network import kill_process_tree


CREATE_NEW_PROCESS_GROUP = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
DETACHED_PROCESS = getattr(subprocess, "DETACHED_PROCESS", 0x00000008)
RUNTIME_DIR = APP_ROOT / "runtime"
BACKEND_ONLY_STATE_FILE = RUNTIME_DIR / "backend-only.json"


def _read_state_file() -> dict[str, Any] | None:
    try:
        return json.loads(BACKEND_ONLY_STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return None


def _write_state_file(payload: dict[str, Any]) -> None:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    temp_path = BACKEND_ONLY_STATE_FILE.with_suffix(".json.tmp")
    temp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temp_path.replace(BACKEND_ONLY_STATE_FILE)


def clear_backend_only_state() -> None:
    try:
        BACKEND_ONLY_STATE_FILE.unlink(missing_ok=True)
    except Exception:
        pass


def write_backend_only_state(pid: int, port: int) -> dict[str, Any]:
    payload = {
        "running": True,
        "pid": pid,
        "port": port,
        "base_url": f"http://127.0.0.1:{port}/open-api",
        "docs_url": f"http://127.0.0.1:{port}/open-api/docs",
    }
    _write_state_file(payload)
    return payload


def _can_connect(port: int, timeout: float = 0.3) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)
        return sock.connect_ex(("127.0.0.1", int(port))) == 0


def _is_pid_alive(pid: int | None) -> bool:
    if not pid:
        return False
    try:
        process = psutil.Process(int(pid))
        return process.is_running() and process.status() != psutil.STATUS_ZOMBIE
    except Exception:
        return False


def get_backend_only_status(default_port: int = 18000) -> dict[str, Any]:
    state = _read_state_file() or {}
    pid = state.get("pid")
    port = int(state.get("port") or default_port)
    running = _is_pid_alive(pid) and _can_connect(port)
    if not running:
        clear_backend_only_state()
        return {
            "running": False,
            "pid": None,
            "port": default_port,
            "base_url": f"http://127.0.0.1:{default_port}/open-api",
            "docs_url": f"http://127.0.0.1:{default_port}/open-api/docs",
        }
    return {
        "running": True,
        "pid": int(pid),
        "port": port,
        "base_url": f"http://127.0.0.1:{port}/open-api",
        "docs_url": f"http://127.0.0.1:{port}/open-api/docs",
    }


def find_available_port(preferred: int = 18000, span: int = 20) -> int:
    for port in range(preferred, preferred + span):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind((BIND_HOST, port))
                return port
            except OSError:
                continue
    raise RuntimeError(f"没有找到可用端口，请先关闭占用 {preferred}~{preferred + span - 1} 的程序。")


def _backend_only_command(port: int) -> list[str]:
    if getattr(sys, "frozen", False):
        return [sys.executable, "--backend-only", f"--port={port}"]
    return [sys.executable, str(PROJECT_ROOT / "launch_app.py"), "--backend-only", f"--port={port}"]


def _launcher_cwd() -> str:
    if getattr(sys, "frozen", False):
        return str(Path(sys.executable).resolve().parent)
    return str(PROJECT_ROOT)


def _wait_for_port(port: int, timeout: float = 12.0) -> bool:
    stop_at = time.time() + timeout
    while time.time() < stop_at:
        if _can_connect(port):
            return True
        time.sleep(0.25)
    return False


def start_backend_only(preferred_port: int = 18000) -> dict[str, Any]:
    current = get_backend_only_status(preferred_port)
    if current["running"]:
        return current

    port = find_available_port(preferred_port, 20)
    command = _backend_only_command(port)
    process = subprocess.Popen(
        command,
        cwd=_launcher_cwd(),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP,
        close_fds=True,
        env={**os.environ},
    )
    if not _wait_for_port(port):
        try:
            kill_process_tree(process.pid)
        except Exception:
            pass
        clear_backend_only_state()
        raise RuntimeError("后端 API 模式启动超时，请稍后重试。")
    return get_backend_only_status(port)


def stop_backend_only(default_port: int = 18000) -> dict[str, Any]:
    state = get_backend_only_status(default_port)
    if not state["running"]:
        return state
    try:
        kill_process_tree(int(state["pid"]))
    finally:
        time.sleep(0.5)
        clear_backend_only_state()
    return get_backend_only_status(default_port)
