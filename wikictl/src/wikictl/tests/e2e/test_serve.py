"""E2E tests for wikictl serve command."""

import socket
import threading
import time

from click.testing import CliRunner

from wikictl.cli import cli


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class TestServeCommand:
    def test_serve_starts_and_responds(self, tmp_path):
        import httpx

        runner = CliRunner()
        wiki = str(tmp_path)

        # Create an entry first
        runner.invoke(
            cli,
            ["--wiki-dir", wiki, "create", "-n", "test", "-d", "Test entry"],
            catch_exceptions=False,
        )

        port = _find_free_port()

        # Run serve in a background thread
        result_holder = {}

        def run_serve():
            result_holder["result"] = runner.invoke(
                cli,
                ["--wiki-dir", wiki, "serve", "--port", str(port)],
            )

        thread = threading.Thread(target=run_serve, daemon=True)
        thread.start()

        # Wait for server to start
        for _ in range(30):
            try:
                resp = httpx.get(f"http://127.0.0.1:{port}/api/entries", timeout=1.0)
                if resp.status_code == 200:
                    data = resp.json()
                    assert len(data) == 1
                    assert data[0]["name"] == "test"
                    return
            except (httpx.ConnectError, httpx.ReadError):
                time.sleep(0.2)

        raise AssertionError("Server did not start in time")
