import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib import request as urllib_request


SDK_ROOT = Path(__file__).resolve().parents[1]


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_ready(url: str, proc: subprocess.Popen[str], timeout: float = 10.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc.poll() is not None:
            stdout, stderr = proc.communicate(timeout=1)
            raise AssertionError(f"Reference server exited early.\nstdout:\n{stdout}\nstderr:\n{stderr}")
        try:
            with urllib_request.urlopen(f"{url}/.well-known/agent-card.json", timeout=0.5) as response:
                if response.status == 200:
                    return
        except Exception:
            time.sleep(0.1)
    raise AssertionError(f"Timed out waiting for reference server at {url}")


def test_a2a_v1_live_interop_example_runs_against_reference_server():
    port = _free_port()
    base_url = f"http://127.0.0.1:{port}"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SDK_ROOT / "src")

    server = subprocess.Popen(
        [
            sys.executable,
            "examples/a2a_v1_reference_server.py",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--api-token",
            "sdk-token",
        ],
        cwd=SDK_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        _wait_for_ready(base_url, server)
        result = subprocess.run(
            [
                sys.executable,
                "examples/a2a_v1_live_interop.py",
                "--gateway-url",
                base_url,
                "--api-token",
                "sdk-token",
                "--prompt",
                "hello from smoke",
                "--exercise-streams",
            ],
            cwd=SDK_ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=20,
        )
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait(timeout=5)

    assert result.returncode == 0, result.stderr
    assert "== Agent Card ==" in result.stdout
    assert "== Extended Agent Card ==" in result.stdout
    assert "== Authenticated Extended Agent Card ==" in result.stdout
    assert "== Task List ==" in result.stdout
    assert "== Send Message ==" in result.stdout
    assert "== Get Task ==" in result.stdout
    assert "== Send Streaming Message ==" in result.stdout
    assert "== Subscribe To Task ==" in result.stdout
    assert "reference echo: hello from smoke" in result.stdout
