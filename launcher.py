from __future__ import annotations

import argparse
import os
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 5000
BASE_DIR = Path(__file__).resolve().parent


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True, encoding="cp932", errors="ignore")


def find_listening_pids(port: int) -> set[int]:
    """Return Windows PIDs that are LISTENING on the specified TCP port."""
    pids: set[int] = set()
    result = _run(["netstat", "-ano", "-p", "tcp"])
    if result.returncode != 0:
        print("[WARN] netstatの実行に失敗しました。ポート確認をスキップします。")
        return pids

    marker = f":{port}"
    for line in result.stdout.splitlines():
        parts = line.split()
        # TCP  127.0.0.1:5000  0.0.0.0:0  LISTENING  1234
        if len(parts) < 5 or parts[0].upper() != "TCP":
            continue
        local_addr = parts[1]
        state = parts[3].upper()
        pid_text = parts[4]
        if state != "LISTENING":
            continue
        if not local_addr.endswith(marker):
            continue
        try:
            pid = int(pid_text)
        except ValueError:
            continue
        if pid != os.getpid():
            pids.add(pid)
    return pids


def task_name(pid: int) -> str:
    result = _run(["tasklist", "/FI", f"PID eq {pid}"])
    for line in result.stdout.splitlines():
        if str(pid) in line:
            return " ".join(line.split())
    return f"PID {pid}"


def kill_pids(pids: set[int]) -> None:
    if not pids:
        print("[OK] 既存の5000番ポート使用プロセスはありません。")
        return
    for pid in sorted(pids):
        print(f"[KILL] 5000番ポート使用中: {task_name(pid)}")
        result = _run(["taskkill", "/PID", str(pid), "/F", "/T"])
        if result.returncode == 0:
            print(f"[OK] PID {pid} を終了しました。")
        else:
            print(f"[WARN] PID {pid} の終了に失敗しました。管理者権限や社内制限の可能性があります。")
            if result.stderr.strip():
                print(result.stderr.strip())


def wait_port_free(port: int, timeout_sec: float = 5.0) -> bool:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        if not find_listening_pids(port):
            return True
        time.sleep(0.3)
    return False


def delayed_open(url: str, delay_sec: float = 1.2) -> None:
    def _open() -> None:
        time.sleep(delay_sec)
        webbrowser.open(url)
    threading.Thread(target=_open, daemon=True).start()


def main() -> int:
    parser = argparse.ArgumentParser(description="SeikanTool local launcher")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--no-kill", action="store_true", help="既存プロセスを終了せずに起動する")
    parser.add_argument("--open-browser", action="store_true", help="起動後にブラウザを開く")
    args = parser.parse_args()

    os.chdir(BASE_DIR)
    os.environ["SEIKAN_HOST"] = args.host
    os.environ["SEIKAN_PORT"] = str(args.port)

    print("====================================")
    print(" SeikanTool Launcher")
    print(f" URL: http://{args.host}:{args.port}")
    print("====================================")

    if not args.no_kill:
        pids = find_listening_pids(args.port)
        kill_pids(pids)
        if not wait_port_free(args.port):
            print(f"[ERROR] {args.port}番ポートが解放されません。")
            print("        run_no_kill.bat ではなく、タスクマネージャーで該当Pythonを終了してください。")
            return 1

    if args.open_browser:
        delayed_open(f"http://{args.host}:{args.port}")

    print("[START] Flaskアプリを起動します。終了は Ctrl + C です。")
    return subprocess.call([sys.executable, "app.py"])


if __name__ == "__main__":
    raise SystemExit(main())
