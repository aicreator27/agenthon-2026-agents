"""Contract tests for the organizer House HTTP route."""

from __future__ import annotations

import json
import os
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

from agenthon_core.house import HouseUnavailable, chat_json


class _Handler(BaseHTTPRequestHandler):
    request_payload: dict[str, object] = {}
    authorization = ""

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers["Content-Length"])
        type(self).request_payload = json.loads(self.rfile.read(length))
        type(self).authorization = self.headers.get("Authorization", "")
        content = json.dumps({"plan": ["solve"], "python": "print('ok')", "notes": "mock"})
        response = {"choices": [{"message": {"content": f"```json\n{content}\n```"}}]}
        body = json.dumps(response).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


class HouseClientTests(unittest.TestCase):
    def test_uses_official_route_and_bearer_contract(self) -> None:
        server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        env = {
            "MODEL_ENDPOINT": f"http://127.0.0.1:{server.server_port}",
            "MODEL_NAME": "house-model-pin",
            "MODEL_TOKEN": "unit-token",
        }
        try:
            with patch.dict(os.environ, env, clear=False):
                payload = chat_json(system="system", user="user", max_tokens=4000)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)
        self.assertEqual(payload["python"], "print('ok')")
        self.assertEqual(_Handler.authorization, "Bearer unit-token")
        self.assertEqual(_Handler.request_payload["model"], "house-model-pin")
        self.assertEqual(_Handler.request_payload["max_tokens"], 4000)

    def test_rejects_incomplete_environment(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(HouseUnavailable):
                chat_json(system="system", user="user")


if __name__ == "__main__":
    unittest.main()
