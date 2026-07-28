"""
JSON I/O utilities
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional
import datetime


class MaestroJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for Maestro objects"""
    def default(self, obj):
        if isinstance(obj, Path):
            return str(obj)
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        if isinstance(obj, datetime.date):
            return obj.isoformat()
        return super().default(obj)


def load_json(filepath: Path) -> Dict[str, Any]:
    """Load JSON from a file"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(filepath: Path, data: Any, indent: Optional[int] = 2) -> None:
    """Save data to a JSON file"""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, cls=MaestroJSONEncoder, indent=indent, ensure_ascii=False)


def read_json(filepath: Path) -> Any:
    """Alias for load_json"""
    return load_json(filepath)


def write_json(filepath: Path, data: Any, indent: Optional[int] = 2) -> None:
    """Alias for save_json"""
    save_json(filepath, data, indent)
