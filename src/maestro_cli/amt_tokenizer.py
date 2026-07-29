"""
AMT (Anticipatory Music Transformer) Tokenizer & MIDI Converter Module
Translates between MIDI note events and symbolic AMT tokens used by MIDI-LLM.
"""

from typing import List, Dict, Any, Tuple, Optional
import dataclasses

# AMT Token Prefixes
PREFIX_ONSET = "ONSET_"
PREFIX_DURATION = "DUR_"
PREFIX_INST = "INST_"
PREFIX_PITCH = "PITCH_"
PREFIX_VELOCITY = "VEL_"

# Standard General MIDI Instrument Mapping
DEFAULT_INSTRUMENTS = {
    "piano": 0,
    "keys": 4,
    "organ": 16,
    "guitar": 24,
    "bass": 32,
    "strings": 48,
    "brass": 56,
    "sax": 64,
    "synth": 80,
    "drums": 128
}


@dataclasses.dataclass
class NoteEvent:
    onset: float      # in seconds or ticks
    duration: float   # in seconds or ticks
    pitch: int        # 0-127
    velocity: int     # 1-127
    instrument: str   # instrument name or ID
    channel: int = 0


class AMTTokenizer:
    """
    Tokenizer and detokenizer for Anticipatory Music Transformer (AMT) representations.
    Used by MIDI-LLM for symbolic music generation.
    """

    def __init__(self, time_step_ms: int = 10, max_duration_ms: int = 4000):
        self.time_step_ms = time_step_ms
        self.max_duration_ms = max_duration_ms

    def note_to_tokens(self, note: NoteEvent) -> List[str]:
        """Convert a single NoteEvent into a sequence of AMT tokens."""
        onset_idx = int(round(note.onset * 1000 / self.time_step_ms))
        dur_idx = int(round(note.duration * 1000 / self.time_step_ms))
        
        return [
            f"{PREFIX_ONSET}{onset_idx}",
            f"{PREFIX_INST}{note.instrument}",
            f"{PREFIX_PITCH}{note.pitch}",
            f"{PREFIX_DURATION}{dur_idx}",
            f"{PREFIX_VELOCITY}{note.velocity}",
        ]

    def encode_notes(self, notes: List[NoteEvent]) -> str:
        """Encode a list of NoteEvents into an AMT token string for LLM input."""
        sorted_notes = sorted(notes, key=lambda n: (n.onset, n.pitch))
        tokens = []
        for note in sorted_notes:
            tokens.extend(self.note_to_tokens(note))
        return " ".join(tokens)

    def decode_tokens(self, token_str: str) -> List[NoteEvent]:
        """Decode an AMT token string back into a list of NoteEvent objects."""
        tokens = token_str.strip().split()
        notes: List[NoteEvent] = []
        
        current_onset: Optional[float] = None
        current_inst: str = "piano"
        current_pitch: Optional[int] = None
        current_dur: float = 0.5
        current_vel: int = 80

        for token in tokens:
            if token.startswith(PREFIX_ONSET):
                try:
                    step = int(token.replace(PREFIX_ONSET, ""))
                    current_onset = (step * self.time_step_ms) / 1000.0
                except ValueError:
                    pass
            elif token.startswith(PREFIX_INST):
                current_inst = token.replace(PREFIX_INST, "")
            elif token.startswith(PREFIX_PITCH):
                try:
                    current_pitch = int(token.replace(PREFIX_PITCH, ""))
                except ValueError:
                    pass
            elif token.startswith(PREFIX_DURATION):
                try:
                    dur_step = int(token.replace(PREFIX_DURATION, ""))
                    current_dur = (dur_step * self.time_step_ms) / 1000.0
                except ValueError:
                    pass
            elif token.startswith(PREFIX_VELOCITY):
                try:
                    current_vel = int(token.replace(PREFIX_VELOCITY, ""))
                except ValueError:
                    pass
                
                # When VELOCITY token is encountered, commit the note
                if current_onset is not None and current_pitch is not None:
                    notes.append(NoteEvent(
                        onset=current_onset,
                        duration=current_dur,
                        pitch=current_pitch,
                        velocity=current_vel,
                        instrument=current_inst
                    ))
                    current_pitch = None

        return notes
