import json
import os
import subprocess
from pathlib import Path

import pytest


@pytest.mark.skipif(os.name != "posix", reason="Docker startup uses a Linux shell")
@pytest.mark.parametrize("migration_exit_code", [0, 17])
def test_docker_startup_requires_successful_migration(tmp_path, migration_exit_code):
    dockerfile = Path(__file__).parents[1] / "Dockerfile"
    command = next(
        json.loads(line.removeprefix("CMD "))
        for line in dockerfile.read_text(encoding="utf-8").splitlines()
        if line.startswith("CMD ")
    )
    # Stand in only for external executables; execute the actual image startup command.
    for name, body in {
        "alembic": (
            '[ "$*" = "upgrade head" ] || exit 99\n'
            f"echo migration\nexit {migration_exit_code}\n"
        ),
        "uvicorn": "echo server\n",
    }.items():
        executable = tmp_path / name
        executable.write_text(f"#!/bin/sh\n{body}", encoding="utf-8")
        executable.chmod(0o755)
    result = subprocess.run(
        command,
        env={**os.environ, "PATH": f"{tmp_path}:{os.environ['PATH']}"},
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == migration_exit_code
    assert result.stdout.splitlines() == (
        ["migration", "server"] if migration_exit_code == 0 else ["migration"]
    )
