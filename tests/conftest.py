"""Shared fixtures for Red Planet frontend tests."""

import subprocess
import sys
import time
from pathlib import Path

import pytest
import requests

REPO_DIR = Path(__file__).parent.parent
PORT = 8765
BASE_URL = f"http://localhost:{PORT}"


@pytest.fixture(scope="session")
def live_server():
    """Start the FastAPI backend once for the whole test session."""
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.main:app", "--port", str(PORT), "--log-level", "error"],
        cwd=REPO_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # Wait up to 10 s for the server to accept connections
    deadline = time.time() + 10
    while time.time() < deadline:
        try:
            requests.get(f"{BASE_URL}/api/health", timeout=1)
            break
        except requests.exceptions.ConnectionError:
            time.sleep(0.2)
    else:
        proc.terminate()
        pytest.fail("Backend did not start within 10 seconds")

    yield BASE_URL

    proc.terminate()
    proc.wait(timeout=5)
