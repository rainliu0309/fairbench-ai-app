"""Run the web API, ARq worker, and contract simulator in one Render service.

Render's free tier does not provide a separate background-worker instance. The
process supervisor below keeps the production API and one low-concurrency ARq
worker in the same container while preserving Redis-backed asynchronous jobs.
The internal simulator is retained for controlled product-flow verification.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from collections.abc import Sequence


def start_process(command: Sequence[str]) -> subprocess.Popen[bytes]:
    return subprocess.Popen(command)


def main() -> int:
    port = os.environ.get("PORT", "8000")
    processes = [
        start_process(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "main:app",
                "--host",
                "0.0.0.0",
                "--port",
                port,
            ]
        ),
        start_process(["arq", "worker_settings.WorkerSettings"]),
        start_process(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "simulator_main:app",
                "--host",
                "127.0.0.1",
                "--port",
                "8080",
            ]
        ),
    ]
    stopping = False

    def stop_all(_: int, __: object) -> None:
        nonlocal stopping
        stopping = True
        for process in processes:
            if process.poll() is None:
                process.terminate()

    signal.signal(signal.SIGTERM, stop_all)
    signal.signal(signal.SIGINT, stop_all)

    try:
        while not stopping:
            for process in processes:
                return_code = process.poll()
                if return_code is not None:
                    stop_all(signal.SIGTERM, None)
                    return return_code if return_code != 0 else 1
            time.sleep(0.5)
    finally:
        deadline = time.monotonic() + 10
        for process in processes:
            if process.poll() is None:
                process.terminate()
        for process in processes:
            remaining = max(0.0, deadline - time.monotonic())
            try:
                process.wait(timeout=remaining)
            except subprocess.TimeoutExpired:
                process.kill()
        for process in processes:
            process.wait()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
