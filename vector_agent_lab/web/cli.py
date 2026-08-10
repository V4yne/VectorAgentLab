"""Command helpers for running the local VectorAgentLab web server."""

import argparse
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000


def _resolve_path(value: Optional[str], default_name: str) -> Path:
    if value:
        return Path(value).expanduser().resolve()
    return (Path.cwd() / default_name).resolve()


def _read_pid(pid_file: Path) -> Optional[int]:
    try:
        return int(pid_file.read_text(encoding="utf-8").strip())
    except (FileNotFoundError, ValueError):
        return None


def _is_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _tail_log(log_file: Path, max_lines: int = 80) -> str:
    if not log_file.exists():
        return ""
    lines = log_file.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(lines[-max_lines:])


def start_server(
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    pid_file: Optional[str] = None,
    log_file: Optional[str] = None,
) -> int:
    """Start the web server in the background."""
    resolved_pid_file = _resolve_path(pid_file, ".vector_agent_lab_web.pid")
    resolved_log_file = _resolve_path(log_file, "vector_agent_lab_web.log")

    existing_pid = _read_pid(resolved_pid_file)
    if existing_pid and _is_running(existing_pid):
        print(f"VectorAgentLab web is already running: http://{host}:{port}")
        print(f"PID: {existing_pid}")
        return 0

    if resolved_pid_file.exists():
        resolved_pid_file.unlink()

    resolved_log_file.parent.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable,
        "-m",
        "vector_agent_lab.web.app",
        "--host",
        host,
        "--port",
        str(port),
    ]

    with resolved_log_file.open("a", encoding="utf-8") as log:
        process = subprocess.Popen(
            command,
            cwd=Path.cwd(),
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )

    resolved_pid_file.write_text(f"{process.pid}\n", encoding="utf-8")
    time.sleep(1)

    if process.poll() is not None:
        resolved_pid_file.unlink(missing_ok=True)
        print("Failed to start VectorAgentLab web.")
        print(f"Log: {resolved_log_file}")
        recent_log = _tail_log(resolved_log_file)
        if recent_log:
            print(recent_log)
        return 1

    print("VectorAgentLab web started.")
    print(f"URL: http://{host}:{port}")
    print(f"PID: {process.pid}")
    print(f"Log: {resolved_log_file}")
    return 0


def stop_server(pid_file: Optional[str] = None) -> int:
    """Stop the background web server."""
    resolved_pid_file = _resolve_path(pid_file, ".vector_agent_lab_web.pid")
    pid = _read_pid(resolved_pid_file)

    if not pid:
        print("VectorAgentLab web is not running.")
        return 0

    if not _is_running(pid):
        resolved_pid_file.unlink(missing_ok=True)
        print("VectorAgentLab web was not running. Removed stale pid file.")
        return 0

    os.kill(pid, signal.SIGTERM)

    for _ in range(20):
        if not _is_running(pid):
            resolved_pid_file.unlink(missing_ok=True)
            print("VectorAgentLab web stopped.")
            return 0
        time.sleep(0.2)

    print("VectorAgentLab web did not stop within the timeout.")
    print(f"PID: {pid}")
    return 1


def _start_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Start VectorAgentLab web in the background.")
    parser.add_argument("--host", default=os.getenv("VECTOR_AGENT_LAB_WEB_HOST", DEFAULT_HOST))
    parser.add_argument("--port", type=int, default=int(os.getenv("VECTOR_AGENT_LAB_WEB_PORT", DEFAULT_PORT)))
    parser.add_argument("--pid-file", default=os.getenv("VECTOR_AGENT_LAB_WEB_PID_FILE"))
    parser.add_argument("--log-file", default=os.getenv("VECTOR_AGENT_LAB_WEB_LOG_FILE"))
    return parser


def _stop_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Stop VectorAgentLab web.")
    parser.add_argument("--pid-file", default=os.getenv("VECTOR_AGENT_LAB_WEB_PID_FILE"))
    return parser


def start_main() -> None:
    """Console script entry for starting the web server."""
    args = _start_parser().parse_args()
    raise SystemExit(start_server(args.host, args.port, args.pid_file, args.log_file))


def stop_main() -> None:
    """Console script entry for stopping the web server."""
    args = _stop_parser().parse_args()
    raise SystemExit(stop_server(args.pid_file))


def main() -> None:
    """Module entry point with start/stop subcommands."""
    parser = argparse.ArgumentParser(description="Manage VectorAgentLab web.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    start_parser = subparsers.add_parser("start")
    start_parser.add_argument("--host", default=os.getenv("VECTOR_AGENT_LAB_WEB_HOST", DEFAULT_HOST))
    start_parser.add_argument("--port", type=int, default=int(os.getenv("VECTOR_AGENT_LAB_WEB_PORT", DEFAULT_PORT)))
    start_parser.add_argument("--pid-file", default=os.getenv("VECTOR_AGENT_LAB_WEB_PID_FILE"))
    start_parser.add_argument("--log-file", default=os.getenv("VECTOR_AGENT_LAB_WEB_LOG_FILE"))

    stop_parser = subparsers.add_parser("stop")
    stop_parser.add_argument("--pid-file", default=os.getenv("VECTOR_AGENT_LAB_WEB_PID_FILE"))

    args = parser.parse_args()
    if args.command == "start":
        raise SystemExit(start_server(args.host, args.port, args.pid_file, args.log_file))
    if args.command == "stop":
        raise SystemExit(stop_server(args.pid_file))


if __name__ == "__main__":
    main()

