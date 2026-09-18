from pathlib import Path

import pytest

from linkops_ai.orchestration.recovery import GitRecovery


def test_restore_requires_explicit_approval(tmp_path: Path) -> None:
    import subprocess

    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    (tmp_path / "README.md").write_text("initial", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "commit", "-m", "initial"], cwd=tmp_path, check=True, capture_output=True
    )
    savepoint = GitRecovery(tmp_path).create_savepoint()
    with pytest.raises(PermissionError):
        GitRecovery(tmp_path).restore(savepoint)
