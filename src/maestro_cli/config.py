"""
Configuration management for Maestro CLI
"""

import os
from pathlib import Path
from typing import Optional
try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic.v1 import BaseSettings
from pydantic import Field



class Settings(BaseSettings):
    """Application settings loaded from environment and .env file"""
    
    # Project structure
    PROJECT_ROOT: Path = Path(__file__).parent.parent.parent
    SONGS_DIR: Path = Field(default_factory=lambda: Path("songs/projects"))
    CONFIG_DIR: Path = Field(default_factory=lambda: Path("configs"))
    PROMPTS_DIR: Path = Field(default_factory=lambda: Path("prompts"))
    
    # LLM Configuration
    LLM_API_KEY: Optional[str] = None
    LLM_BASE_URL: str = "https://api.openai.com/v1"
    LLM_MODEL: str = "gpt-4o"
    LLM_TIMEOUT: int = 60
    LLM_MAX_TOKENS: int = 4096
    LLM_TEMPERATURE: float = 0.7
    
    # Audio Configuration
    AUDIO_SAMPLE_RATE: int = 48000
    AUDIO_BIT_DEPTH: int = 24
    AUDIO_BUFFER_SIZE: int = 256
    
    # MIDI Configuration
    MIDI_TICKS_PER_BEAT: int = 480
    MIDI_VELOCITY_MIN: int = 64
    MIDI_VELOCITY_MAX: int = 127
    MIDI_HUMANIZE: bool = True
    MIDI_HUMANIZE_AMOUNT: float = 0.1
    
    # Carla Configuration
    CARLA_HOST: str = "127.0.0.1"
    CARLA_OSC_PORT: int = 9001
    CARLA_SERVER_PORT: int = 9002
    CARLA_TIMEOUT: int = 5
    CARLA_RACK_PATH: Optional[Path] = None
    CARLA_START_CMD: str = "carla"
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # or "text"
    LOG_DIR: Path = Field(default_factory=lambda: Path("logs"))
    
    # Debug
    DEBUG: bool = False
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"
    
    @property
    def songs_dir(self) -> Path:
        """Get the absolute path to songs directory"""
        if self.SONGS_DIR.is_absolute():
            return self.SONGS_DIR
        return self.PROJECT_ROOT / self.SONGS_DIR
    
    @property
    def config_dir(self) -> Path:
        """Get the absolute path to configs directory"""
        if self.CONFIG_DIR.is_absolute():
            return self.CONFIG_DIR
        return self.PROJECT_ROOT / self.CONFIG_DIR
    
    @property
    def prompts_dir(self) -> Path:
        """Get the absolute path to prompts directory"""
        if self.PROMPTS_DIR.is_absolute():
            return self.PROMPTS_DIR
        return self.PROJECT_ROOT / self.PROMPTS_DIR


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
