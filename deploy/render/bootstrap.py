"""Apply deployment settings before the upstream JSON-driven entrypoint."""
import json
import os
from pathlib import Path


def configure(root: Path, env: dict) -> None:
    import bcrypt

    token = env.get("DEEPTUTOR_MCP_TOKEN", "")
    if len(token) < 32:
        raise RuntimeError("Set DEEPTUTOR_MCP_TOKEN to at least 32 random characters")
    settings = root / "data/user/settings"
    settings.mkdir(parents=True, exist_ok=True)

    def read(name):
        path = settings / f"{name}.json"
        return json.loads(path.read_text()) if path.exists() else {}

    def write(name, data):
        path = settings / f"{name}.json"
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2))
        temporary.chmod(0o600)
        temporary.replace(path)

    auth = read("auth")
    if not auth.get("password_hash"):
        password = env.get("DEEPTUTOR_ADMIN_PASSWORD", "")
        if not 16 <= len(password.encode()) <= 72:
            raise RuntimeError("Set DEEPTUTOR_ADMIN_PASSWORD to 16–72 bytes before first boot")
        auth.update(username="admin", password_hash=bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode())
    auth.update(enabled=True, cookie_secure=True)
    write("auth", auth)
    system = read("system")
    system.update(backend_port=8001, backend_workers=1,
                  frontend_port=int(env.get("PORT", "10000")),
                  next_public_api_base="http://127.0.0.1:8001",
                  next_public_api_base_external="", sandbox_allow_subprocess=False)
    if env.get("RENDER_EXTERNAL_URL"):
        system["cors_origins"] = [env["RENDER_EXTERNAL_URL"]]
    write("system", system)


if __name__ == "__main__":
    configure(Path("/app"), os.environ)
