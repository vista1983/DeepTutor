import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT = Path(__file__).parent


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"{name}.py")
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


bridge = module("mcp_bridge")
bootstrap = module("bootstrap")
TOKEN = "unit-test-token-not-for-deployment-12345"


class FakeService:
    def __init__(self):
        self.calls = []

    async def call(self, name, args, app):
        self.calls.append((name, args))
        if args.get("message") == "failure":
            raise RuntimeError("provider-secret-never-return-this")
        return {"turn_id": "turn-1", "status": "queued"}


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.app = FastAPI()
        self.service = FakeService()
        bridge.install(self.app, self.service, lambda: TOKEN)
        self.client = TestClient(self.app)

    def rpc(self, method, params=None):
        return self.client.post("/api/client-mcp", headers={"Authorization": "Bearer " + TOKEN}, json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).json()

    def test_rejects_unauthenticated_request(self):
        r = self.client.post("/api/client-mcp", json={"method": "tools/list"})
        self.assertEqual(r.status_code, 401)
        self.assertEqual(self.service.calls, [])

    def test_health_reports_real_readiness(self):
        self.assertEqual(self.client.get("/api/client-health").status_code, 503)
        self.app.state.ready = True
        self.assertEqual(self.client.get("/api/client-health").status_code, 200)

    def test_discovery_and_tools(self):
        self.assertIn("2026-07-28", self.rpc("server/discover")["result"]["supportedVersions"])
        self.assertEqual(len(self.rpc("tools/list")["result"]["tools"]), 6)

    def test_valid_task_is_forwarded(self):
        result = self.rpc("tools/call", {"name": "deeptutor_start", "arguments": {"message": "解释牛顿定律"}})
        self.assertEqual(json.loads(result["result"]["content"][0]["text"])["turn_id"], "turn-1")
        self.assertEqual(len(self.service.calls), 1)

    def test_rejects_unknown_and_extra_arguments(self):
        for args in ({"message": "x", "shell": "rm -rf /"}, {"message": "x", "capability": "exec"}, {"message": ""}):
            self.assertTrue(self.rpc("tools/call", {"name": "deeptutor_start", "arguments": args})["result"]["isError"])
        self.assertEqual(self.service.calls, [])

    def test_provider_error_does_not_leak(self):
        result = self.rpc("tools/call", {"name": "deeptutor_start", "arguments": {"message": "failure"}})
        self.assertTrue(result["result"]["isError"])
        self.assertNotIn("provider-secret", json.dumps(result))

    def test_rejects_large_request(self):
        r = self.client.post("/api/client-mcp", headers={"Authorization": "Bearer " + TOKEN}, content=b"x" * 131073)
        self.assertEqual(r.status_code, 413)

    def test_bootstrap_preserves_existing_password_and_other_settings(self):
        import bcrypt
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            env = {"DEEPTUTOR_MCP_TOKEN": TOKEN, "DEEPTUTOR_ADMIN_PASSWORD": "unit-test-password-123", "PORT": "10000"}
            bootstrap.configure(root, env)
            settings = root / "data/user/settings"
            auth = json.loads((settings / "auth.json").read_text())
            self.assertTrue(auth["enabled"])
            self.assertTrue(bcrypt.checkpw(env["DEEPTUTOR_ADMIN_PASSWORD"].encode(), auth["password_hash"].encode()))
            system = json.loads((settings / "system.json").read_text())
            system["custom_setting"] = "preserve"
            (settings / "system.json").write_text(json.dumps(system))
            env.pop("DEEPTUTOR_ADMIN_PASSWORD")
            bootstrap.configure(root, env)
            self.assertEqual(json.loads((settings / "auth.json").read_text())["password_hash"], auth["password_hash"])
            self.assertEqual(json.loads((settings / "system.json").read_text())["custom_setting"], "preserve")
            self.assertFalse(json.loads((settings / "system.json").read_text())["sandbox_allow_subprocess"])


if __name__ == "__main__":
    unittest.main()
