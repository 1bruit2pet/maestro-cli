"""
Pydantic models for Maestro CLI
"""

from maestro_cli.models.song import Song, SongStatus, Section, InstrumentRole, Constraints
from maestro_cli.models.sections import Sections, SectionData
from maestro_cli.models.tracks import Tracks, Track
from maestro_cli.models.critique import Critique, CritiqueIssue, RepairAction
from maestro_cli.models.rack_state import RackState, Plugin, Route
from maestro_cli.models.render_report import RenderReport

# Structured Outputs (Phase 3)
from maestro_cli.structured_outputs import (
    ComposeOutput,
    ArrangeOutput,
    OrchestrateOutput,
    RepairOutput,
    AnalyzeOutput,
    OutputType,
    OutputStatus,
    ValidationResult,
    StructuredOutputValidator,
    validator,
)

__all__ = [
    "Song",
    "SongStatus", 
    "Section",
    "InstrumentRole",
    "Constraints",
    "Sections",
    "SectionData",
    "Tracks",
    "Track",
    "Critique",
    "CritiqueIssue",
    "RepairAction",
    "RackState",
    "Plugin",
    "Route",
    "RenderReport",
    # Phase 3
    "ComposeOutput",
    "ArrangeOutput", 
    "OrchestrateOutput",
    "RepairOutput",
    "AnalyzeOutput",
    "OutputType",
    "OutputStatus",
    "ValidationResult",
    "StructuredOutputValidator",
    "validator",
]
