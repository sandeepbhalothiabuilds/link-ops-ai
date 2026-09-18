from __future__ import annotations

import argparse
import os
import shutil
import stat
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--app-repo", type=Path, required=True)
    args = parser.parse_args()
    app_repo = args.app_repo.resolve()
    output = Path("build/product").resolve()
    if output.exists():
        shutil.rmtree(output, onerror=_remove_readonly)
    output.mkdir(parents=True)
    shutil.copytree(
        app_repo / "src" / "linkops_ai",
        output / "linkops_ai",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    shutil.copy2(Path("lambda_code/handler.py"), output / "handler.py")
    requirements = [
        "boto3>=1.35.0",
        "fastapi>=0.115.0",
        "mangum>=0.17.0",
        "pydantic>=2.9.0",
        "pydantic-settings>=2.6.0",
        "structlog>=24.4.0",
    ]
    requirements_file = output / "requirements.txt"
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
            str(output),
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
    print(f"Product source staged in {output}.")


def _remove_readonly(function: Callable[[str], None], path: str, _exc_info: object) -> None:
    os.chmod(path, stat.S_IWRITE)
    function(path)


if __name__ == "__main__":
    main()
