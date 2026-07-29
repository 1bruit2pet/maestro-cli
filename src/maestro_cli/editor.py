"""
Atomic MIDI Editing Engine for Maestro CLI (100% Headless / CLI)
Uses mido / pretty_midi for deterministic MIDI transformations.
"""

from typing import List, Optional
from pathlib import Path
import mido


class MidiEditorCLI:
    """
    Headless MIDI Editor executing deterministic, atomic transformations on MIDI files.
    """

    @staticmethod
    def transpose(midi_path: Path, output_path: Path, semitones: int) -> Path:
        """Transpose all pitch notes in a MIDI file by N semitones."""
        mid = mido.MidiFile(midi_path)
        for track in mid.tracks:
            for msg in track:
                if msg.type in ('note_on', 'note_off'):
                    new_note = msg.note + semitones
                    msg.note = max(0, min(127, new_note))
        mid.save(output_path)
        return output_path

    @staticmethod
    def set_tempo(midi_path: Path, output_path: Path, bpm: float) -> Path:
        """Set or adjust the global tempo (BPM) of a MIDI file."""
        mid = mido.MidiFile(midi_path)
        new_tempo = mido.bpm2tempo(bpm)
        
        # Check if set_tempo message exists, update or insert at start
        updated = False
        for track in mid.tracks:
            for msg in track:
                if msg.type == 'set_tempo':
                    msg.tempo = new_tempo
                    updated = True
        
        if not updated and len(mid.tracks) > 0:
            mid.tracks[0].insert(0, mido.MetaMessage('set_tempo', tempo=new_tempo, time=0))
            
        mid.save(output_path)
        return output_path

    @staticmethod
    def quantize(midi_path: Path, output_path: Path, grid_fraction: float = 0.25) -> Path:
        """
        Quantize note onset times to the nearest grid step.
        grid_fraction: 0.25 = 1/16th notes (relative to beat).
        """
        mid = mido.MidiFile(midi_path)
        ticks_per_beat = mid.ticks_per_beat
        grid_ticks = int(ticks_per_beat * grid_fraction)
        
        if grid_ticks <= 0:
            return midi_path

        for track in mid.tracks:
            accumulated_ticks = 0
            for msg in track:
                accumulated_ticks += msg.time
                if msg.type == 'note_on' and msg.velocity > 0:
                    # Align to nearest grid tick
                    remainder = accumulated_ticks % grid_ticks
                    if remainder < grid_ticks / 2:
                        adjustment = -remainder
                    else:
                        adjustment = grid_ticks - remainder
                    
                    new_time = max(0, msg.time + adjustment)
                    msg.time = new_time

        mid.save(output_path)
        return output_path
