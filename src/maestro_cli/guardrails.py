"""
Guardrails & Tripwire Validator System for Maestro CLI (Phase 3 PRD)
Enforces musical constraints, range checks, and safe control flow execution.
"""

from typing import List, Dict, Any, Optional
import dataclasses


class GuardrailViolationError(Exception):
    """Raised when a musical or structural guardrail rule is violated."""
    pass


@dataclasses.dataclass
class TripwireConfig:
    max_polyphony: int = 16
    min_pitch: int = 21   # A0
    max_pitch: int = 108  # C8
    max_velocity: int = 127
    min_velocity: int = 1
    max_duration_seconds: float = 600.0


class GuardrailValidator:
    """
    Validates MIDI note structures and project parameters against tripwire boundaries.
    """

    def __init__(self, config: Optional[TripwireConfig] = None):
        self.config = config or TripwireConfig()

    def validate_pitch(self, pitch: int, track_role: str = "general") -> bool:
        """Validate pitch is within acceptable MIDI piano range (21-108)."""
        if not (self.config.min_pitch <= pitch <= self.config.max_pitch):
            raise GuardrailViolationError(
                f"Tripwire: Pitch {pitch} on track '{track_role}' is out of range [{self.config.min_pitch}-{self.config.max_pitch}]"
            )
        return True

    def validate_velocity(self, velocity: int, track_role: str = "general") -> bool:
        """Validate velocity is within MIDI range 1-127."""
        if not (self.config.min_velocity <= velocity <= self.config.max_velocity):
            raise GuardrailViolationError(
                f"Tripwire: Velocity {velocity} on track '{track_role}' is out of range [{self.config.min_velocity}-{self.config.max_velocity}]"
            )
        return True

    def validate_polyphony_density(self, simultaneous_notes: int, track_role: str = "general") -> bool:
        """Validate simultaneous notes do not exceed max polyphony tripwire."""
        if simultaneous_notes > self.config.max_polyphony:
            raise GuardrailViolationError(
                f"Tripwire: Polyphony count {simultaneous_notes} on track '{track_role}' exceeds max limit {self.config.max_polyphony}"
            )
        return True
