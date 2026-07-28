"""
Critique model - Validation and repair suggestions
"""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class Severity(str, Enum):
    """Severity level of an issue"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class IssueType(str, Enum):
    """Type of issue detected"""
    REGISTER_COLLISION = "register_collision"
    DENSITY_MISMATCH = "density_mismatch"
    POLYPHONY_OVERFLOW = "polyphony_overflow"
    RANGE_VIOLATION = "range_violation"
    RHYTHMIC_CONFLICT = "rhythmic_conflict"
    INSTRUMENT_MISSING = "instrument_missing"
    VELOCITY_ISSUE = "velocity_issue"
    TIME_SIGNATURE_MISMATCH = "time_signature_mismatch"
    TEMPO_INCONSISTENCY = "tempo_inconsistency"
    PLUGIN_MISMATCH = "plugin_mismatch"


class CritiqueIssue(BaseModel):
    """A single issue found during critique"""
    severity: Severity = Field(..., description="Issue severity level")
    issue_type: IssueType = Field(..., description="Type of issue")
    track_a: Optional[str] = Field(
        default=None,
        description="First track involved (if applicable)"
    )
    track_b: Optional[str] = Field(
        default=None,
        description="Second track involved (if applicable)"
    )
    section: Optional[str] = Field(
        default=None,
        description="Section where issue occurs"
    )
    bars: Optional[List[int]] = Field(
        default=None,
        description="Specific bars affected"
    )
    message: str = Field(..., description="Human-readable description")
    details: Optional[str] = Field(
        default=None,
        description="Technical details"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "severity": "high",
                "issue_type": "register_collision",
                "track_a": "keys_main",
                "track_b": "lead_main",
                "bars": [17, 24],
                "message": "Lead and keys overlap too heavily in the upper-mid register."
            }
        }


class RepairAction(str, Enum):
    """Possible repair actions"""
    THIN_BASS_INTRO = "thin_bass_intro"
    RAISE_LEAD_REGISTER = "raise_lead_register"
    REDUCE_POLYPHONY = "reduce_polyphony"
    ADJUST_VELOCITY = "adjust_velocity"
    FIX_RHYTHM = "fix_rhythm"
    CHANGE_PLUGIN = "change_plugin"
    SPLIT_TRACK = "split_track"
    MERGE_TRACKS = "merge_tracks"
    REVOICE_CHORDS = "revoice_chords"
    SIMPLIFY_SECTION = "simplify_section"


class Critique(BaseModel):
    """
    Critique and validation of the orchestration.
    Acts as a gatekeeper before rendering.
    """
    project_id: str = Field(..., description="Project identifier")
    valid: bool = Field(default=False, description="Is the orchestration valid?")
    issues: List[CritiqueIssue] = Field(
        default_factory=list,
        description="List of detected issues"
    )
    repair_actions: List[RepairAction] = Field(
        default_factory=list,
        description="Suggested repair actions"
    )
    status: str = Field(default="critiqued", description="Pipeline status")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "project_id": "my_song",
                "valid": False,
                "issues": [
                    {
                        "severity": "high",
                        "issue_type": "register_collision",
                        "track_a": "keys_main",
                        "track_b": "lead_main",
                        "bars": [17, 24],
                        "message": "Lead and keys overlap too heavily in the upper-mid register."
                    },
                    {
                        "severity": "medium",
                        "issue_type": "density_mismatch",
                        "track": "bass_main",
                        "bars": [1, 8],
                        "message": "Bass is too active for the intro density target."
                    }
                ],
                "repair_actions": [
                    "thin_bass_intro",
                    "raise_lead_register_chorus"
                ],
                "status": "critiqued"
            }
        }
    
    def has_high_issues(self) -> bool:
        """Check if there are any high severity issues"""
        return any(issue.severity == Severity.HIGH for issue in self.issues)
    
    def get_issues_by_track(self, track_name: str) -> List[CritiqueIssue]:
        """Get all issues involving a specific track"""
        return [
            issue for issue in self.issues
            if issue.track_a == track_name or issue.track_b == track_name
        ]
    
    def get_issues_by_section(self, section_id: str) -> List[CritiqueIssue]:
        """Get all issues in a specific section"""
        return [
            issue for issue in self.issues
            if issue.section == section_id
        ]
