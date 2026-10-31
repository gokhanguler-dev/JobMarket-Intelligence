from pathlib import Path
from dotenv import load_dotenv


def load_project_env(project_root: Path, override: bool = False) -> bool:
    """
    Load the project's .env file when it is readable.

    Local development:
        Reads .env normally.

    Docker / production:
        If .env cannot be read, continue using environment variables
        injected by Docker/Compose.
    """
    env_path = project_root / ".env"

    try:
        if env_path.is_file():
            return load_dotenv(env_path, override=override)
    except PermissionError:
        pass

    return False
