"""
Path utilities
"""

from pathlib import Path
from typing import Optional


def get_relative_path(path: Path, relative_to: Optional[Path] = None) -> Path:
    """Get a path relative to another path (or current directory)"""
    if relative_to is None:
        relative_to = Path.cwd()
    return path.relative_to(relative_to)


def ensure_directory(path: Path) -> Path:
    """Ensure a directory exists"""
    path.mkdir(parents=True, exist_ok=True)
    return path


def clean_path(path: str) -> Path:
    """Clean and normalize a path string"""
    # Replace ~ with home directory
    from pathlib import Path
    path = Path(path)
    if path == Path("~"):
        return Path.home()
    return path.expanduser().resolve()
