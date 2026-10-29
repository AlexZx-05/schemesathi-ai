from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def load_project_environment(project_root: Path = PROJECT_ROOT) -> None:
    load_dotenv(project_root / ".env", override=False)


load_project_environment()
