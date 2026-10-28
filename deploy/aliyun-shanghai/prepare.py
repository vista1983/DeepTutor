"""Initialize private deployment credentials on the target server, never print them.

Run as root on the verified Shanghai server only. Does not start a container,
change networking or modify any other application's configuration.
"""
import os
from pathlib import Path
import secrets


def prepare(root=Path("/opt/deeptutor")):
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    (root / "data").mkdir(mode=0o700, exist_ok=True)
    path = root / ".env"
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        print("Existing credential file preserved.")
        return
    with os.fdopen(fd, "w") as stream:
        stream.write("DEEPTUTOR_MCP_TOKEN=" + secrets.token_urlsafe(48) + "\n")
        stream.write("DEEPTUTOR_ADMIN_PASSWORD=" + secrets.token_urlsafe(32) + "\n")
    print("Private credential file created. No credentials displayed.")


if __name__ == "__main__":
    prepare()
