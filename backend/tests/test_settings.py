import os
from pathlib import Path

from backend.app.settings import load_project_environment


def test_load_project_environment_reads_root_env_file(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
    (tmp_path / ".env").write_text(
        "GOOGLE_CLIENT_ID=test-client-id.apps.googleusercontent.com\n",
        encoding="utf-8",
    )

    load_project_environment(tmp_path)

    assert (
        os.environ["GOOGLE_CLIENT_ID"]
        == "test-client-id.apps.googleusercontent.com"
    )


def test_load_project_environment_does_not_override_process_environment(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "process-client-id")
    (tmp_path / ".env").write_text(
        "GOOGLE_CLIENT_ID=file-client-id\n", encoding="utf-8"
    )

    load_project_environment(tmp_path)

    assert os.environ["GOOGLE_CLIENT_ID"] == "process-client-id"
