"""
Song model - The canonical state of a music project
"""

from enum import Enum
from typing import List, Optional, Union
from pydantic import BaseModel, Field, validator
from datetime import datetime


class SongStatus(str, Enum):
    """Status of the song in the pipeline"""
    DRAFT = "draft"
    COMPOSED = "composed"
    ARRANGED = "arranged"
    ORCHESTRATED = "orchestrated"
    CRITIQUED = "critiqued"
    REPAIRED = "repaired"
    RENDERED = "rendered"
    FINALIZED = "finalized"


class InstrumentRole(str, Enum):
    """Standard instrument roles"""
    KEYS = "keys"
    BASS = "bass"
    DRUMS = "drums"
    PAD = "pad"
    LEAD = "lead"
    RHYTHM = "rhythm"
    MELODY = "melody"
    HARMONY = "harmony"
    PERCUSSION = "percussion"
    CHOIR = "choir"
    BRASS = "brass"
    STRINGS = "strings"
    GUITAR = "guitar"
    PIANO = "piano"
    ORGAN = "organ"
    SYNTH = "synth"


class Constraints(BaseModel):
    """Creative and technical constraints"""
    max_tracks: int = Field(default=8, ge=1, le=16, description="Maximum number of tracks")
    tempo_changes: bool = Field(default=False, description="Allow tempo changes")
    time_signature_changes: bool = Field(default=False, description="Allow time signature changes")
    swing: float = Field(default=0.0, ge=0.0, le=1.0, description="Swing amount (0=none, 1=heavy)")
    max_polyphony: int = Field(default=8, ge=1, le=32, description="Maximum polyphony per track")
    humanize: bool = Field(default=True, description="Apply humanization")
    humanize_amount: float = Field(default=0.1, ge=0.0, le=1.0, description="Humanization strength")


class Section(BaseModel):
    """A section of the song"""
    id: str = Field(..., description="Unique section identifier")
    name: str = Field(..., description="Section name (Intro, Verse 1, Chorus, etc.)")
    bars: int = Field(..., ge=1, le=64, description="Duration in bars")
    chord_progression: Optional[List[str]] = Field(
        default=None,
        description="Chord progression for this section"
    )
    energy: float = Field(default=0.5, ge=0.0, le=1.0, description="Energy level (0-1)")
    density: str = Field(default="medium", description="Density: low, medium, high")
    mood: str = Field(default="neutral", description="Mood: calm, uplifting, dark, etc.")
    goal: str = Field(default="", description="Purpose of this section")
    
    @validator('density')
    def validate_density(cls, v):
        valid_densities = ['low', 'medium', 'high']
        if v not in valid_densities:
            raise ValueError(f'density must be one of {valid_densities}')
        return v


class Song(BaseModel):
    """
    The canonical state of a music project.
    This is the source of truth for the entire pipeline.
    """
    project_id: str = Field(..., description="Unique project identifier")
    title: str = Field(..., description="Song title")
    style: Union[str, List[str]] = Field(
        default=["gospel"],
        description="Music style(s)"
    )
    tempo_bpm: int = Field(..., ge=40, le=200, description="Tempo in BPM")
    time_signature: str = Field(default="4/4", description="Time signature")
    key: str = Field(..., description="Musical key (C, C#, D, etc.)")
    target_bars: int = Field(default=32, ge=4, le=256, description="Target duration in bars")
    mood: Union[str, List[str]] = Field(
        default=["warm", "uplifting"],
        description="Mood tags"
    )
    constraints: Constraints = Field(default_factory=Constraints, description="Creative constraints")
    instrument_roles: List[InstrumentRole] = Field(
        default_factory=list,
        description="List of instrument roles to use"
    )
    status: SongStatus = Field(default=SongStatus.DRAFT, description="Current pipeline status")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    
    # Computed fields
    duration_seconds: Optional[float] = Field(
        default=None,
        description="Estimated duration in seconds"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "project_id": "my_song",
                "title": "Grace Motion",
                "style": ["gospel", "neo-soul"],
                "tempo_bpm": 92,
                "time_signature": "4/4",
                "key": "F minor",
                "target_bars": 64,
                "mood": ["warm", "uplifting", "live-band"],
                "constraints": {
                    "max_tracks": 6,
                    "tempo_changes": False,
                    "swing": 0.08
                },
                "instrument_roles": ["keys", "bass", "drums", "pad", "lead"],
                "status": "composed"
            }
        }
    
    def model_post_init(self, __context):
        """Calculate duration_seconds from tempo and target_bars"""
        if self.duration_seconds is None:
            beats_per_bar = int(self.time_signature.split('/')[0])
            seconds_per_beat = 60.0 / self.tempo_bpm
            self.duration_seconds = self.target_bars * beats_per_bar * seconds_per_beat
