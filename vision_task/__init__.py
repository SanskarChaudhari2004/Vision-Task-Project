"""Vision Task package entry point.

This package may include multiple app implementations (e.g., "app (2).py")
during development and merges. Prefer the most complete/updated app source
when available.
"""

from pathlib import Path
import importlib.util

# Prefer the full-featured app implementations (if present) over the minimal stub.
_APP_CANDIDATES = ["app (2).py", "app (1).py", "app.py"]

def _load_app_create_app():
    pkg_dir = Path(__file__).resolve().parent
    for candidate in _APP_CANDIDATES:
        candidate_path = pkg_dir / candidate
        if candidate_path.exists():
            spec = importlib.util.spec_from_file_location("vision_task._app_impl", str(candidate_path))
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module.create_app
    raise ImportError("No app implementation found (searched: {}).".format(_APP_CANDIDATES))

create_app = _load_app_create_app()

__all__ = ["create_app"]
