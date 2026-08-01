"""
MIDI Assembler — combines individual tracks into a single MidiFile
and handles export.
"""

from __future__ import annotations
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field
import mido


@dataclass
class TrackSpec:
    name: str
    track: mido.MidiTrack
    output_file: Optional[Path] = None


class MidiAssembler:
    """Assemble multiple tracks into a single multi-track MIDI file."""

    def __init__(self, bpm: int = 90, ticks_per_beat: int = 480):
        self.bpm = bpm
        self.ticks_per_beat = ticks_per_beat
        self.specs: List[TrackSpec] = []

    def add_track(self, name: str, track: mido.MidiTrack, output_file: Optional[Path] = None):
        self.specs.append(TrackSpec(name=name, track=track, output_file=output_file))

    def export_merged(self, output_path: Path) -> Path:
        """Export all tracks merged into a single .mid file (Type 1 MIDI)."""
        mid = mido.MidiFile(type=1, ticks_per_beat=self.ticks_per_beat)

        # Master tempo track
        master = mido.MidiTrack()
        master.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(self.bpm), time=0))
        master.append(mido.MetaMessage("track_name", name="Master", time=0))
        mid.tracks.append(master)

        # Add each track with its name
        for spec in self.specs:
            spec.track.insert(0, mido.MetaMessage("track_name", name=spec.name, time=0))
            mid.tracks.append(spec.track)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        mid.save(str(output_path))
        return output_path

    def export_individual(self, output_dir: Path) -> Dict[str, Path]:
        """Export each track as a separate .mid file (Type 0 MIDI, single track)."""
        output_dir.mkdir(parents=True, exist_ok=True)
        paths: Dict[str, Path] = {}

        for spec in self.specs:
            # Determine output path
            if spec.output_file:
                out = spec.output_file
            else:
                out = output_dir / f"{spec.name}.mid"

            mid = mido.MidiFile(type=0, ticks_per_beat=self.ticks_per_beat)
            master = mido.MidiTrack()
            master.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(self.bpm), time=0))
            mid.tracks.append(master)

            track = spec.track
            track.insert(0, mido.MetaMessage("track_name", name=spec.name, time=0))
            mid.tracks.append(track)

            out.parent.mkdir(parents=True, exist_ok=True)
            mid.save(str(out))
            paths[spec.name] = out

        return paths

    @property
    def track_names(self) -> List[str]:
        return [s.name for s in self.specs]

    @property
    def track_count(self) -> int:
        return len(self.specs)
