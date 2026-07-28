"""
Simplified configuration without pydantic-settings dependency
"""

import os
from pathlib import Path
from typing import Optional


class Settings:
    """Simple settings class that reads from environment variables"""
    
    # Project structure
    PROJECT_ROOT: Path = Path(__file__).parent.parent.parent
    SONGS_DIR: Path = PROJECT_ROOT / "songs" / "projects"
    CONFIG_DIR: Path = PROJECT_ROOT / "configs"
    PROMPTS_DIR: Path = PROJECT_ROOT / "prompts"
    
    @classmethod
    def get(cls, key: str, default: Optional[str] = None) -> str:
        """Get a setting from environment or use default"""
        return os.environ.get(key, default or "")
    
    @classmethod
    def get_int(cls, key: str, default: int = 0) -> int:
        """Get an integer setting"""
        try:
            return int(os.environ.get(key, str(default)))
        except ValueError:
            return default
    
    @classmethod
    def get_float(cls, key: str, default: float = 0.0) -> float:
        """Get a float setting"""
        try:
            return float(os.environ.get(key, str(default)))
        except ValueError:
            return default
    
    @classmethod
    def get_bool(cls, key: str, default: bool = False) -> bool:
        """Get a boolean setting"""
        value = os.environ.get(key, str(default)).lower()
        return value in ("true", "1", "yes", "on")
    
    @property
    def songs_dir(self) -> Path:
        """Get the songs directory"""
        env_songs = self.get("SONGS_DIR")
        if env_songs:
            return Path(env_songs)
        return self.SONGS_DIR
    
    @property
    def config_dir(self) -> Path:
        """Get the configs directory"""
        env_config = self.get("CONFIG_DIR")
        if env_config:
            return Path(env_config)
        return self.CONFIG_DIR
    
    @property
    def prompts_dir(self) -> Path:
        """Get the prompts directory"""
        env_prompts = self.get("PROMPTS_DIR")
        if env_prompts:
            return Path(env_prompts)
        return self.PROMPTS_DIR


# Global settings instance
settings = Settings()


def get_project_dir(project_id: str) -> Path:
    """Get the directory for a specific project"""
    return settings.songs_dir / project_id


def get_state_dir(project_id: str) -> Path:
    """Get the state directory for a project"""
    return get_project_dir(project_id) / "state"


def get_midi_dir(project_id: str) -> Path:
    """Get the MIDI directory for a project"""
    return get_project_dir(project_id) / "midi"


def get_audio_dir(project_id: str) -> Path:
    """Get the audio directory for a project"""
    return get_project_dir(project_id) / "audio"


def get_logs_dir(project_id: str) -> Path:
    """Get the logs directory for a project"""
    return get_project_dir(project_id) / "logs"


def get_presets_dir(project_id: str) -> Path:
    """Get the presets directory for a project"""
    return get_project_dir(project_id) / "presets"


def ensure_project_structure(project_id: str):
    """Create all necessary directories for a project"""
    project_dir = get_project_dir(project_id)
    project_dir.mkdir(parents=True, exist_ok=True)
    
    directories = [
        get_state_dir(project_id),
        get_midi_dir(project_id),
        get_audio_dir(project_id),
        get_logs_dir(project_id),
        get_presets_dir(project_id),
    ]
    
    for d in directories:
        d.mkdir(parents=True, exist_ok=True)
    
    return project_dir
