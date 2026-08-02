from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent


def get_env(*names, default=None):
    for name in names:
        value = os.getenv(name)
        if value not in (None, ""):
            return value
    return default


def get_path(*parts):
    return BASE_DIR.joinpath(*parts)
