from __future__ import annotations

import argparse
import os
import shutil
import stat
import subprocess
import sys
import zipfile
from collections.abc import Callable
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--app-repo", type=Path, required=True)
    args = parser.parse_args()
    app_repo = args.app_repo.resolve()
    stage = Path("build/agentcore").resolve()
    if stage.exists():
        shutil.rmtree(stage, onerror=_remove_readonly)
    stage.mkdir(parents=True)
    shutil.copytree(
        app_repo / "src" / "linkops_ai",
        stage / "linkops_ai",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    shutil.copy2(
        Path("runtime/code/agentcore_entrypoint.py"),
        stage / "agentcore_entrypoint.py",
    )
    requirements = [
        "boto3>=1.35.0",
        "langgraph>=1.0.0",
        "langgraph-checkpoint-aws>=1.2.2",
        "pydantic>=2.9.0",
        "pydantic-settings>=2.6.0",
        "structlog>=24.4.0",
    ]
    requirements_file = stage / "requirements.txt"
    requirements_file.write_text("\n".join(requirements) + "\n", encoding="utf-8")
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "-r",
            str(requirements_file),
            "-t",
            str(stage),
            "--platform",
            "manylinux2014_x86_64",
            "--python-version",
            "3.12",
            "--implementation",
            "cp",
            "--abi",
            "cp312",
            "--only-binary=:all:",
        ],
        check=True,
    )
    archive = Path("build/agentcore.zip").resolve()
    archive.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as output:
        for path in stage.rglob("*"):
            if path.is_file():
                output.write(path, path.relative_to(stage))
    print(f"AgentCore package created at {archive}")


def _remove_readonly(function: Callable[[str], None], path: str, _exc_info: object) -> None:
    os.chmod(path, stat.S_IWRITE)
    function(path)


if __name__ == "__main__":
    main()
