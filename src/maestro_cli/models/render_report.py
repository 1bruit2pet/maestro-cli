"""
Render Report model - Audio rendering results
"""

from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class Warning(BaseModel):
    """A warning generated during rendering"""
    type: str = Field(..., description="Warning type")
    message: str = Field(..., description="Warning message")
    track: Optional[str] = Field(default=None, description="Affected track")
    bar: Optional[int] = Field(default=None, description="Affected bar")


class RenderReport(BaseModel):
    """
    Report generated after audio rendering.
    Allows tracking render results without parsing text logs.
    """
    project_id: str = Field(..., description="Project identifier")
    render_ok: bool = Field(default=False, description="Did rendering succeed?")
    output_file: str = Field(..., description="Path to rendered audio file")
    duration_seconds: float = Field(..., description="Duration in seconds")
    sample_rate: int = Field(default=48000, description="Sample rate in Hz")
    bit_depth: int = Field(default=24, description="Bit depth")
    channels: int = Field(default=2, description="Number of channels")
    warnings: List[Warning] = Field(
        default_factory=list,
        description="List of warnings"
    )
    errors: List[str] = Field(
        default_factory=list,
        description="List of errors"
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    status: str = Field(default="rendered", description="Pipeline status")
    
    class Config:
        json_schema_extra = {
            "example": {
                "project_id": "my_song",
                "render_ok": True,
                "output_file": "audio/mix.wav",
                "duration_seconds": 168.2,
                "sample_rate": 48000,
                "bit_depth": 24,
                "channels": 2,
                "warnings": [],
                "errors": [],
                "timestamp": "2026-07-28T12:00:00Z",
                "status": "rendered"
            }
        }
    
    @property
    def duration_formatted(self) -> str:
        """Format duration as MM:SS"""
        minutes = int(self.duration_seconds // 60)
        seconds = int(self.duration_seconds % 60)
        return f"{minutes:02d}:{seconds:02d}"
    
    def has_errors(self) -> bool:
        """Check if rendering had errors"""
        return len(self.errors) > 0
    
    def has_warnings(self) -> bool:
        """Check if rendering had warnings"""
        return len(self.warnings) > 0
