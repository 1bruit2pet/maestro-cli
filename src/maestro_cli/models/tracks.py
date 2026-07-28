"""
Tracks model - Orchestrated tracks with MIDI files
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from .song import InstrumentRole


class SectionBehavior(BaseModel):
    """Behavior of an instrument in a specific section"""
    pattern: str = Field(default="", description="Playing pattern")
    pitch_register: str = Field(default="mid", description="Pitch register: low, mid, high")
    technique: str = Field(default="", description="Playing technique")
    
    @property
    def register_value(self) -> float:
        """Convert pitch_register to numeric value (0-1)"""
        registers = {"low": 0.25, "mid": 0.5, "high": 0.75}
        return registers.get(self.pitch_register, 0.5)


class Track(BaseModel):
    """A single track in the orchestration"""
    name: str = Field(..., description="Track name")
    role: InstrumentRole = Field(..., description="Instrument role")
    midi_file: str = Field(..., description="Path to MIDI file")
    plugin_tag: Optional[str] = Field(
        default=None,
        description="Tag for plugin selection (rhodes, electric_bass, etc.)"
    )
    pitch_register: str = Field(default="mid", description="Default pitch register")
    volume: float = Field(default=1.0, ge=0.0, le=1.0, description="Volume (0-1)")
    pan: float = Field(default=0.5, ge=0.0, le=1.0, description="Pan (0=left, 1=right)")
    section_behavior: Dict[str, SectionBehavior] = Field(
        default_factory=dict,
        description="Behavior per section"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "keys_main",
                "role": "keys",
                "midi_file": "midi/keys.mid",
                "plugin_tag": "rhodes",
                "register": "mid",
                "volume": 0.8,
                "pan": 0.5,
                "section_behavior": {
                    "intro": {"pattern": "sparse chords", "register": "low"},
                    "verse_1": {"pattern": "syncopated voicings", "register": "mid"},
                    "chorus_1": {"pattern": "wide voicings", "register": "high"}
                }
            }
        }


class Tracks(BaseModel):
    """
    The orchestrated tracks with MIDI files.
    This connects symbolic generation with runtime execution.
    """
    project_id: str = Field(..., description="Project identifier")
    tracks: List[Track] = Field(
        default_factory=list,
        description="List of orchestrated tracks"
    )
    status: str = Field(default="orchestrated", description="Pipeline status")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "project_id": "my_song",
                "tracks": [
                    {
                        "name": "keys_main",
                        "role": "keys",
                        "midi_file": "midi/keys.mid",
                        "plugin_tag": "rhodes",
                        "register": "mid",
                        "volume": 0.8,
                        "pan": 0.5
                    },
                    {
                        "name": "bass_main",
                        "role": "bass",
                        "midi_file": "midi/bass.mid",
                        "plugin_tag": "electric_bass",
                        "register": "low",
                        "volume": 1.0,
                        "pan": 0.5
                    }
                ],
                "status": "orchestrated"
            }
        }
    
    def get_track(self, name: str) -> Track:
        """Get a track by name"""
        for track in self.tracks:
            if track.name == name:
                return track
        raise ValueError(f"Track {name} not found")
    
    def get_tracks_by_role(self, role: InstrumentRole) -> List[Track]:
        """Get all tracks with a specific role"""
        return [track for track in self.tracks if track.role == role]
