"""
Sections model - Structure of the song
"""

from typing import List
from pydantic import BaseModel, Field
from datetime import datetime


class SectionData(BaseModel):
    """Data for a single section"""
    id: str = Field(..., description="Unique section identifier")
    bars: int = Field(..., ge=1, le=64, description="Duration in bars")
    energy: float = Field(default=0.5, ge=0.0, le=1.0, description="Energy level (0-1)")
    density: str = Field(default="medium", description="Density: low, medium, high")
    goal: str = Field(default="", description="Purpose of this section")
    
    @property
    def duration_seconds(self, tempo_bpm: int, time_signature: str = "4/4") -> float:
        """Calculate duration in seconds"""
        beats_per_bar = int(time_signature.split('/')[0])
        return self.bars * beats_per_bar * (60.0 / tempo_bpm)


class Sections(BaseModel):
    """
    The arrangement/structure of a song.
    This is the interface between planner and orchestrator.
    """
    project_id: str = Field(..., description="Project identifier")
    sections: List[SectionData] = Field(
        default_factory=list,
        description="List of song sections"
    )
    status: str = Field(default="arranged", description="Pipeline status")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "project_id": "my_song",
                "sections": [
                    {
                        "id": "intro",
                        "bars": 8,
                        "energy": 0.3,
                        "density": "low",
                        "goal": "set mood"
                    },
                    {
                        "id": "verse_1",
                        "bars": 16,
                        "energy": 0.55,
                        "density": "medium",
                        "goal": "develop narrative"
                    },
                    {
                        "id": "chorus_1",
                        "bars": 16,
                        "energy": 0.85,
                        "density": "high",
                        "goal": "lift and release"
                    }
                ],
                "status": "arranged"
            }
        }
    
    def get_total_bars(self) -> int:
        """Calculate total number of bars"""
        return sum(section.bars for section in self.sections)
    
    def get_section(self, section_id: str) -> SectionData:
        """Get a section by ID"""
        for section in self.sections:
            if section.id == section_id:
                return section
        raise ValueError(f"Section {section_id} not found")
