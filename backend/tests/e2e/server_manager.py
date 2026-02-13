"""Server lifecycle management for E2E tests.

Checks if backend and services gateway are running, starts them if not,
and provides cleanup on exit.
"""

import subprocess
import time
import sys
import os
import signal
import logging
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[3]  # conversationalBuilderPOC/
BACKEND_DIR = PROJECT_ROOT / "backend"
SERVICES_DIR = PROJECT_ROOT / "services"

BACKEND_URL = "http://localhost:8000"
SERVICES_URL = "http://localhost:8001"

HEALTH_TIMEOUT = 30  # seconds to wait for server startup
HEALTH_INTERVAL = 1  # seconds between health checks


class ServerManager:
    """Manages backend and services gateway lifecycle."""

    def __init__(self):
        self._backend_proc: subprocess.Popen | None = None
        self._services_proc: subprocess.Popen | None = None

    def check_health(self, url: str, timeout: float = 3.0) -> bool:
        """Check if a server is responding to health checks."""
        try:
            resp = httpx.get(f"{url}/health", timeout=timeout)
            return resp.status_code == 200
        except (httpx.ConnectError, httpx.ReadTimeout, httpx.ConnectTimeout):
            return False

    def is_backend_running(self) -> bool:
        return self.check_health(BACKEND_URL)

    def is_services_running(self) -> bool:
        return self.check_health(SERVICES_URL)

    def start_services_gateway(self) -> bool:
        """Start the services gateway if not already running."""
        if self.is_services_running():
            logger.info("Services gateway already running on port 8001")
            return True

        logger.info("Starting services gateway...")
        venv_python = SERVICES_DIR / "venv" / "bin" / "python"
        if not venv_python.exists():
            venv_python = sys.executable

        self._services_proc = subprocess.Popen(
            [str(venv_python), "-m", "uvicorn", "app.main:app", "--port", "8001"],
            cwd=str(SERVICES_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os.setsid,
        )

        return self._wait_for_health(SERVICES_URL, "services gateway")

    def start_backend(self) -> bool:
        """Start the backend if not already running."""
        if self.is_backend_running():
            logger.info("Backend already running on port 8000")
            return True

        logger.info("Starting backend...")
        venv_python = BACKEND_DIR / "venv" / "bin" / "python"
        if not venv_python.exists():
            venv_python = sys.executable

        self._backend_proc = subprocess.Popen(
            [str(venv_python), "-m", "uvicorn", "app.main:app", "--port", "8000"],
            cwd=str(BACKEND_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os.setsid,
        )

        return self._wait_for_health(BACKEND_URL, "backend")

    def _wait_for_health(self, url: str, name: str) -> bool:
        """Wait for a server to become healthy."""
        deadline = time.time() + HEALTH_TIMEOUT
        while time.time() < deadline:
            if self.check_health(url):
                logger.info(f"{name} is healthy")
                return True
            time.sleep(HEALTH_INTERVAL)

        logger.error(f"{name} failed to start within {HEALTH_TIMEOUT}s")
        return False

    def ensure_running(self) -> bool:
        """Ensure both servers are running. Returns True if both are healthy."""
        services_ok = self.start_services_gateway()
        if not services_ok:
            return False

        backend_ok = self.start_backend()
        if not backend_ok:
            return False

        return True

    def stop(self):
        """Stop any servers we started (not externally-managed ones)."""
        for name, proc in [("backend", self._backend_proc), ("services", self._services_proc)]:
            if proc is not None:
                logger.info(f"Stopping {name} (pid={proc.pid})")
                try:
                    os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                    proc.wait(timeout=5)
                except (ProcessLookupError, subprocess.TimeoutExpired):
                    try:
                        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                    except ProcessLookupError:
                        pass
        self._backend_proc = None
        self._services_proc = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.stop()
