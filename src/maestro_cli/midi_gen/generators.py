"""
MIDI Pattern Generators for Drums, Bass, Chords, Melody
Each generator returns a mido.MidiTrack ready to be inserted in a MidiFile.
"""

from __future__ import annotations
import random
import math
from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass

import mido

from .theory import (
    ChordVoicing, Progression, Key, Scale, ScaleType,
    NOTE_NAMES, GENRE_CONFIGS, GenreConfig,
)


# ---------------------------------------------------------------------------
# Timing helpers
# ---------------------------------------------------------------------------

TPB = 480  # ticks per beat (quarter note)

def ticks(beats: float) -> int:
    return int(round(TPB * beats))

def swing_offset(beat_16th: int, swing: float) -> int:
    """
    Compute swing timing offset for a 16th-note position.
    swing=0.5 → straight, swing=0.67 → full triplet swing.
    Only affects odd 16th-note positions (upbeats).
    """
    if beat_16th % 2 == 1:
        ideal = ticks(0.25)          # straight 16th
        swung = ticks(2/3 * swing * 2 * 0.5 + 0.5 * (1 - swing) * 0.5)
        return int((swing - 0.5) * TPB * 0.5)
    return 0


def jitter(ms: float, bpm: int) -> int:
    """Convert ms timing jitter to ticks."""
    ticks_per_ms = TPB / (60_000 / bpm)
    return int(random.gauss(0, ms * ticks_per_ms))


def vel_vary(base: int, stddev: float) -> int:
    return max(1, min(127, base + int(random.gauss(0, stddev))))


# ---------------------------------------------------------------------------
# Event dataclass (simpler intermediate)
# ---------------------------------------------------------------------------

@dataclass
class NoteEvent:
    channel: int
    note: int
    velocity: int
    start_tick: int
    duration_ticks: int


def events_to_track(events: List[NoteEvent], channel: int = 0, program: int = 0) -> mido.MidiTrack:
    """Convert a list of NoteEvents (absolute start times) to a mido MidiTrack."""
    track = mido.MidiTrack()
    if program >= 0 and channel != 9:
        track.append(mido.Message("program_change", channel=channel, program=program, time=0))

    # Build message list with absolute times
    msgs: List[Tuple[int, mido.Message]] = []
    for ev in events:
        msgs.append((ev.start_tick, mido.Message(
            "note_on", channel=ev.channel, note=ev.note,
            velocity=ev.velocity, time=0)))
        msgs.append((ev.start_tick + ev.duration_ticks, mido.Message(
            "note_on", channel=ev.channel, note=ev.note,
            velocity=0, time=0)))

    msgs.sort(key=lambda x: x[0])

    # Convert to delta times
    prev = 0
    for abs_t, msg in msgs:
        msg.time = max(0, abs_t - prev)
        prev = abs_t
        track.append(msg)

    return track


# ============================================================================
# DRUM GENERATOR
# ============================================================================

# GM drum map
KICK   = 36
SNARE  = 38
CLAP   = 39
HIHAT_CLOSED = 42
HIHAT_OPEN   = 46
HIHAT_PEDAL  = 44
RIDE         = 51
CRASH        = 49
TOM_HI       = 50
TOM_MID      = 47
TOM_LOW      = 43
SHAKER       = 70
COWBELL      = 56
CONGA_HI     = 62
CONGA_LOW    = 63
CLAVE        = 75
RIMSHOT      = 37
GHOST        = 38  # same as snare but low velocity


# 16-step patterns (0=off, 1-127=velocity)
# Each list is 16 steps (16th notes per bar)

DRUM_PATTERNS: Dict[str, Dict[str, List[int]]] = {
    "boom_bap": {
        "kick":  [110, 0, 0, 0,  0, 0, 0, 0,  95, 0, 0, 0,  0, 0, 0, 0],
        "snare": [0, 0, 0, 0,  100, 0, 0, 0,  0, 0, 0, 0,  105, 0, 0, 0],
        "hihat": [75, 0, 75, 0,  75, 0, 75, 0,  75, 0, 75, 0,  75, 0, 75, 0],
        "ghost": [0, 25, 0, 30,  0, 0, 35, 0,  0, 28, 0, 0,  0, 32, 0, 25],
    },
    "afrobeat": {
        "kick":  [110, 0, 0, 0,  0, 0, 90, 0,  0, 0, 105, 0,  0, 0, 0, 0],
        "snare": [0, 0, 0, 0,  100, 0, 0, 0,  0, 0, 0, 0,  105, 0, 0, 0],
        "hihat": [80, 80, 80, 80,  80, 80, 80, 80,  80, 80, 80, 80,  80, 80, 80, 80],
        "clave": [85, 0, 0, 85,  0, 85, 0, 0,  85, 0, 0, 85,  0, 0, 85, 0],
    },
    "gospel_swing": {
        "kick":  [110, 0, 0, 0,  0, 0, 0, 0,  95, 0, 0, 0,  0, 0, 0, 0],
        "snare": [0, 0, 0, 0,  100, 0, 0, 0,  0, 0, 0, 0,  108, 0, 0, 0],
        "hihat": [70, 0, 70, 0,  70, 0, 70, 0,  70, 0, 70, 0,  70, 0, 70, 0],
        "ghost": [0, 30, 0, 25,  0, 35, 0, 0,  0, 28, 35, 0,  0, 30, 0, 30],
        "ride":  [0, 0, 0, 0,  0, 0, 0, 0,  0, 0, 0, 0,  0, 0, 0, 0],
    },
    "soul_layback": {
        "kick":  [100, 0, 0, 0,  0, 0, 0, 0,  85, 0, 0, 0,  0, 0, 0, 0],
        "snare": [0, 0, 0, 0,  95, 0, 0, 0,  0, 0, 0, 0,  100, 0, 0, 0],
        "hihat": [65, 0, 65, 0,  65, 0, 65, 0,  65, 0, 65, 0,  65, 0, 65, 0],
        "ghost": [0, 20, 0, 0,  0, 0, 28, 0,  0, 22, 0, 0,  0, 0, 25, 0],
    },
    "funk_pocket": {
        "kick":  [110, 0, 0, 0,  90, 0, 0, 0,  100, 0, 0, 0,  0, 0, 0, 80],
        "snare": [0, 0, 0, 0,  100, 0, 0, 0,  0, 0, 0, 0,  105, 0, 0, 0],
        "hihat": [85, 0, 85, 85,  85, 0, 85, 0,  85, 85, 85, 0,  85, 0, 85, 85],
        "ghost": [0, 35, 0, 40,  0, 40, 0, 35,  0, 35, 40, 0,  0, 40, 0, 35],
    },
    "trap": {
        "kick":  [110, 0, 0, 0,  0, 0, 0, 0,  0, 0, 95, 0,  0, 110, 0, 0],
        "snare": [0, 0, 0, 0,  100, 0, 0, 0,  0, 0, 0, 0,  105, 0, 0, 0],
        "hihat": [90, 90, 90, 90,  90, 90, 90, 90,  90, 90, 90, 90,  90, 90, 90, 90],
        "open_hh": [0, 0, 0, 0,  0, 0, 0, 0,  0, 0, 0, 0,  0, 0, 90, 0],
    },
    "rnb": {
        "kick":  [100, 0, 0, 0,  0, 0, 0, 0,  90, 0, 0, 0,  0, 0, 85, 0],
        "snare": [0, 0, 0, 0,  100, 0, 0, 0,  0, 0, 0, 0,  105, 0, 0, 0],
        "hihat": [75, 0, 75, 0,  75, 0, 75, 0,  75, 0, 75, 0,  75, 0, 75, 0],
        "ghost": [0, 25, 0, 30,  0, 0, 25, 0,  0, 30, 0, 0,  0, 25, 0, 0],
    },
    "jazz_swing": {
        "kick":  [80, 0, 0, 0,  0, 0, 0, 0,  70, 0, 0, 0,  0, 0, 0, 0],
        "snare": [0, 0, 0, 0,  90, 0, 0, 0,  0, 0, 0, 0,  85, 0, 0, 0],
        "ride":  [80, 0, 65, 0,  80, 0, 65, 0,  80, 0, 65, 0,  80, 0, 65, 0],
        "hihat": [0, 0, 70, 0,  0, 0, 70, 0,  0, 0, 70, 0,  0, 0, 70, 0],
    },
    "latin_clave": {
        "kick":  [100, 0, 0, 0,  0, 0, 0, 0,  90, 0, 0, 0,  0, 0, 0, 0],
        "snare": [0, 0, 0, 0,  95, 0, 0, 0,  0, 0, 0, 0,  100, 0, 0, 0],
        "clave": [90, 0, 0, 90,  0, 90, 0, 0,  90, 0, 0, 90,  0, 0, 90, 0],
        "conga_hi":  [70, 0, 70, 0,  70, 0, 70, 0,  70, 0, 70, 0,  70, 0, 70, 0],
        "conga_low": [0, 80, 0, 0,  0, 0, 80, 0,  0, 80, 0, 0,  0, 0, 80, 0],
    },
    "house_4x4": {
        "kick":  [110, 0, 0, 0,  110, 0, 0, 0,  110, 0, 0, 0,  110, 0, 0, 0],
        "snare": [0, 0, 0, 0,  100, 0, 0, 0,  0, 0, 0, 0,  100, 0, 0, 0],
        "hihat": [75, 75, 75, 75,  75, 75, 75, 75,  75, 75, 75, 75,  75, 75, 75, 75],
        "open_hh": [0, 0, 0, 0,  0, 0, 0, 70,  0, 0, 0, 0,  0, 0, 0, 70],
    },
    "reggae_one_drop": {
        "kick":  [0, 0, 0, 0,  0, 0, 0, 0,  100, 0, 0, 0,  0, 0, 0, 0],
        "snare": [0, 0, 0, 0,  90, 0, 0, 0,  0, 0, 0, 0,  90, 0, 0, 0],
        "hihat": [70, 0, 70, 0,  70, 0, 70, 0,  70, 0, 70, 0,  70, 0, 70, 0],
        "rimshot": [85, 0, 0, 0,  0, 0, 0, 0,  0, 0, 0, 0,  0, 0, 0, 0],
    },
    "lofi_drums": {
        "kick":  [100, 0, 0, 0,  0, 0, 0, 0,  85, 0, 0, 0,  0, 0, 0, 0],
        "snare": [0, 0, 0, 0,  90, 0, 0, 0,  0, 0, 0, 0,  95, 0, 0, 0],
        "hihat": [60, 0, 55, 0,  60, 0, 55, 0,  60, 0, 55, 0,  60, 0, 55, 0],
        "ghost": [0, 18, 0, 0,  0, 20, 0, 0,  0, 0, 18, 0,  0, 0, 0, 20],
    },
}

DRUM_NOTE_MAP: Dict[str, int] = {
    "kick": KICK, "snare": SNARE, "clap": CLAP,
    "hihat": HIHAT_CLOSED, "open_hh": HIHAT_OPEN, "pedal_hh": HIHAT_PEDAL,
    "ride": RIDE, "crash": CRASH,
    "tom_hi": TOM_HI, "tom_mid": TOM_MID, "tom_low": TOM_LOW,
    "shaker": SHAKER, "cowbell": COWBELL,
    "conga_hi": CONGA_HI, "conga_low": CONGA_LOW,
    "clave": CLAVE, "rimshot": RIMSHOT, "ghost": GHOST,
}


class DrumGenerator:
    """Generate a full drum track in a given style."""

    def __init__(
        self,
        style: str = "boom_bap",
        bars: int = 8,
        bpm: int = 90,
        swing: float = 0.5,
        humanize_jitter_ms: float = 10.0,
        humanize_vel_stddev: float = 8.0,
        seed: Optional[int] = None,
    ):
        self.style = style
        self.bars = bars
        self.bpm = bpm
        self.swing = swing
        self.humanize_jitter_ms = humanize_jitter_ms
        self.humanize_vel_stddev = humanize_vel_stddev
        self.rng = random.Random(seed)

    def _pattern(self) -> Dict[str, List[int]]:
        return DRUM_PATTERNS.get(self.style, DRUM_PATTERNS["boom_bap"])

    def _swing_tick(self, step: int) -> int:
        """Return absolute tick for a 16th-note step with swing applied."""
        # Base tick: step * (TPB / 4)
        base = step * (TPB // 4)
        if step % 2 == 1 and self.swing > 0.5:
            # Swing pushes odd 16ths later
            extra = int((self.swing - 0.5) * 2 * (TPB // 3))
            base += extra
        return base

    def generate(self) -> mido.MidiTrack:
        events: List[NoteEvent] = []
        pattern = self._pattern()
        steps = 16

        for bar in range(self.bars):
            bar_start = bar * TPB * 4  # 4 beats per bar
            for step in range(steps):
                step_tick = self._swing_tick(step)
                abs_tick = bar_start + step_tick

                for voice, vels in pattern.items():
                    vel = vels[step % len(vels)]
                    if vel == 0:
                        continue
                    note = DRUM_NOTE_MAP.get(voice, SNARE)

                    # Humanize
                    final_vel = vel_vary(vel, self.humanize_vel_stddev)
                    time_jit = int(self.rng.gauss(0, self.humanize_jitter_ms * (TPB / (60_000 / self.bpm))))
                    final_tick = max(0, abs_tick + time_jit)

                    events.append(NoteEvent(
                        channel=9, note=note, velocity=final_vel,
                        start_tick=final_tick, duration_ticks=TPB // 8,
                    ))

        return events_to_track(events, channel=9, program=-1)


# ============================================================================
# BASS GENERATOR
# ============================================================================

class BassGenerator:
    """Generate a bass track following a chord progression."""

    def __init__(
        self,
        progression: Progression,
        style: str = "boom_bap",
        bars: int = 8,
        bpm: int = 90,
        swing: float = 0.5,
        octave: int = 2,
        humanize_jitter_ms: float = 8.0,
        humanize_vel_stddev: float = 6.0,
        seed: Optional[int] = None,
    ):
        self.progression = progression
        self.style = style
        self.bars = bars
        self.bpm = bpm
        self.swing = swing
        self.octave = octave
        self.humanize_jitter_ms = humanize_jitter_ms
        self.humanize_vel_stddev = humanize_vel_stddev
        self.rng = random.Random(seed)

    def _get_chord_at_bar(self, bar: int) -> ChordVoicing:
        """Return the chord voicing for a given bar."""
        cumulative = 0
        chords = self.progression.chords
        bars_per = self.progression.bars_per_chord
        for i, b in enumerate(bars_per):
            cumulative += b
            if bar < cumulative:
                return chords[i % len(chords)]
        return chords[0]

    def _bass_pattern_steps(self, chord: ChordVoicing) -> List[Tuple[int, int, int]]:
        """
        Return list of (step_16th, note, velocity) for one bar.
        Style-specific patterns.
        """
        root = chord.root_midi - (chord.octave - self.octave) * 12  # transpose to bass octave
        while root > 43:  # keep below G2
            root -= 12
        while root < 28:  # E1 minimum
            root += 12
        fifth = root + 7

        patterns = {
            "boom_bap": [
                (0, root, 100), (6, root, 85), (10, fifth, 80),
            ],
            "afrobeat": [
                (0, root, 100), (3, root + 12, 75), (5, root, 85),
                (8, root, 100), (11, fifth, 80), (13, root, 90),
            ],
            "afrobeat_bass": [
                (0, root, 100), (2, root, 75), (5, root+7, 80),
                (8, root, 100), (10, root, 75), (13, root+5, 75),
            ],
            "gospel": [
                (0, root, 105), (4, root, 85), (8, root, 100), (12, fifth, 80),
            ],
            "neo_soul": [
                (0, root, 95), (3, root, 70), (6, fifth, 80),
                (8, root, 90), (11, root, 68), (14, root + 2, 75),
            ],
            "funk": [
                (0, root, 110), (2, root, 80), (4, root, 95),
                (6, fifth, 85), (8, root, 110), (10, root, 75),
                (12, root + 5, 80), (14, root, 70),
            ],
            "trap": [
                (0, root, 100), (8, root, 90), (12, fifth, 85),
            ],
            "rnb": [
                (0, root, 95), (4, root, 80), (6, fifth, 85), (10, root, 90),
            ],
            "jazz_walk": [
                (0, root), (4, root + 2), (8, root + 5), (12, root + 7),
            ],
            "latin_tumbao": [
                (2, root, 100), (4, root, 90), (6, fifth, 85),
                (10, root, 100), (12, root, 90), (14, fifth, 80),
            ],
            "house": [
                (0, root, 110), (4, root, 90), (8, root, 110), (12, root, 90),
            ],
            "reggae_skank": [
                (0, root, 100), (12, root, 90),
            ],
            "lofi_bass": [
                (0, root, 85), (6, root, 70), (8, fifth, 75),
            ],
        }
        raw = patterns.get(self.style, patterns["boom_bap"])
        # Normalize: some styles have 2-tuples (no vel), use 95
        result = []
        for item in raw:
            if len(item) == 2:
                result.append((item[0], item[1], 95))
            else:
                result.append(item)
        return result

    def generate(self) -> mido.MidiTrack:
        events: List[NoteEvent] = []
        step_ticks = TPB // 4  # 16th note

        for bar in range(self.bars):
            bar_start = bar * TPB * 4
            chord = self._get_chord_at_bar(bar)
            steps = self._bass_pattern_steps(chord)

            for step, note, vel in steps:
                # swing
                if step % 2 == 1 and self.swing > 0.5:
                    step_start = bar_start + step * step_ticks + int((self.swing - 0.5) * 2 * (TPB // 3))
                else:
                    step_start = bar_start + step * step_ticks

                # humanize
                final_vel = vel_vary(vel, self.humanize_vel_stddev)
                time_jit = int(self.rng.gauss(0, self.humanize_jitter_ms * (TPB / (60_000 / self.bpm))))
                final_tick = max(0, step_start + time_jit)

                # duration: fill until next step or end of bar
                dur = step_ticks * 3  # dotted 8th default
                events.append(NoteEvent(
                    channel=1, note=note, velocity=final_vel,
                    start_tick=final_tick, duration_ticks=dur,
                ))

        # GM program: Electric Bass (finger) = 33
        return events_to_track(events, channel=1, program=33)


# ============================================================================
# CHORDS GENERATOR
# ============================================================================

class ChordsGenerator:
    """Generate a chords track (piano/keys) from a progression."""

    def __init__(
        self,
        progression: Progression,
        style: str = "boom_bap",
        bars: int = 8,
        bpm: int = 90,
        swing: float = 0.5,
        octave: int = 3,
        voicing: str = "close",
        humanize_jitter_ms: float = 12.0,
        humanize_vel_stddev: float = 10.0,
        seed: Optional[int] = None,
    ):
        self.progression = progression
        self.style = style
        self.bars = bars
        self.bpm = bpm
        self.swing = swing
        self.octave = octave
        self.voicing = voicing
        self.humanize_jitter_ms = humanize_jitter_ms
        self.humanize_vel_stddev = humanize_vel_stddev
        self.rng = random.Random(seed)

    def _get_chord_at_bar(self, bar: int) -> ChordVoicing:
        cumulative = 0
        chords = self.progression.chords
        bars_per = self.progression.bars_per_chord
        for i, b in enumerate(bars_per):
            cumulative += b
            if bar < cumulative:
                return chords[i % len(chords)]
        return chords[0]

    def _chord_hits(self, bar: int) -> List[Tuple[int, float, int]]:
        """
        Return list of (step_16th, duration_beats, velocity_base) for chord attacks.
        Style-specific rhythmic placement.
        """
        hits = {
            "boom_bap":    [(0, 2.0, 70), (8, 1.5, 65)],
            "afrobeat":    [(0, 1.0, 75), (6, 1.0, 70), (10, 0.5, 65)],
            "gospel":      [(0, 2.0, 78), (6, 1.0, 72), (8, 2.0, 78)],
            "gospel_swing":[(0, 2.0, 78), (5, 0.5, 68), (8, 2.0, 75), (13, 0.5, 65)],
            "neo_soul":    [(0, 1.5, 65), (5, 1.0, 60), (8, 1.5, 65), (13, 0.75, 58)],
            "funk":        [(0, 0.5, 80), (2, 0.25, 65), (6, 0.5, 80), (10, 0.5, 75)],
            "trap":        [(0, 4.0, 60), (8, 4.0, 58)],
            "rnb":         [(0, 2.0, 68), (7, 1.5, 62), (10, 1.5, 65)],
            "jazz_swing":  [(0, 1.5, 72), (6, 1.0, 65), (10, 1.5, 70)],
            "latin":       [(0, 1.0, 75), (4, 0.5, 68), (8, 1.0, 75), (12, 0.5, 68)],
            "house":       [(0, 4.0, 62), (8, 4.0, 60)],
            "reggae":      [(4, 0.5, 70), (6, 0.5, 68), (12, 0.5, 70), (14, 0.5, 68)],
            "lofi":        [(0, 2.0, 55), (9, 1.5, 50)],
        }
        return hits.get(self.style, hits["boom_bap"])

    def generate(self) -> mido.MidiTrack:
        events: List[NoteEvent] = []
        step_ticks = TPB // 4

        for bar in range(self.bars):
            bar_start = bar * TPB * 4
            chord = self._get_chord_at_bar(bar)
            # Rebuild voicing at target octave
            cv = ChordVoicing(
                root=chord.root, quality=chord.quality,
                octave=self.octave, spread=self.voicing,
                inversion=chord.inversion,
            )
            notes = cv.midi_notes

            for step, dur_beats, vel_base in self._chord_hits(bar):
                # swing
                if step % 2 == 1 and self.swing > 0.5:
                    step_start = bar_start + step * step_ticks + int((self.swing - 0.5) * 2 * (TPB // 3))
                else:
                    step_start = bar_start + step * step_ticks

                time_jit = int(self.rng.gauss(0, self.humanize_jitter_ms * (TPB / (60_000 / self.bpm))))
                final_tick = max(0, step_start + time_jit)
                dur = ticks(dur_beats)

                for n in notes:
                    final_vel = vel_vary(vel_base, self.humanize_vel_stddev)
                    events.append(NoteEvent(
                        channel=0, note=n, velocity=final_vel,
                        start_tick=final_tick, duration_ticks=dur,
                    ))

        # Program 4 = Electric Piano (Rhodes)
        return events_to_track(events, channel=0, program=4)


# ============================================================================
# MELODY GENERATOR
# ============================================================================

class MelodyGenerator:
    """Generate a melodic lead line from the scale and progression."""

    def __init__(
        self,
        progression: Progression,
        style: str = "jazzy",
        bars: int = 8,
        bpm: int = 90,
        swing: float = 0.5,
        octave: int = 5,
        density: float = 0.6,   # note density 0.0-1.0
        humanize_jitter_ms: float = 12.0,
        humanize_vel_stddev: float = 10.0,
        seed: Optional[int] = None,
    ):
        self.progression = progression
        self.style = style
        self.bars = bars
        self.bpm = bpm
        self.swing = swing
        self.octave = octave
        self.density = density
        self.humanize_jitter_ms = humanize_jitter_ms
        self.humanize_vel_stddev = humanize_vel_stddev
        self.rng = random.Random(seed)

    def _scale_notes(self) -> List[int]:
        """Get available scale notes for melody, 2 octaves from self.octave."""
        return self.progression.key.scale.notes(self.octave, octaves=2)

    def _chord_tones(self, bar: int) -> List[int]:
        """Get chord tones at melody octave."""
        cumulative = 0
        chords = self.progression.chords
        bars_per = self.progression.bars_per_chord
        for i, b in enumerate(bars_per):
            cumulative += b
            if bar < cumulative:
                chord = chords[i % len(chords)]
                base_oct = self.octave
                return [n + (base_oct - chord.octave) * 12 for n in chord.midi_notes]
        return chords[0].midi_notes

    def _style_rhythm(self) -> List[Tuple[float, float]]:
        """Return list of (beat_position, duration_beats) for melodic phrase positions."""
        # Returns positions in beats (0-based per bar, so 0.0-3.99)
        rhythms = {
            "jazzy":        [(0, 1.0), (1.5, 0.5), (2, 1.0), (3.5, 0.5)],
            "bebop":        [(0, 0.25), (0.5, 0.25), (1, 0.5), (1.5, 0.25), (2, 0.5), (2.5, 0.25), (3, 0.75)],
            "gospel":       [(0, 1.0), (1, 0.5), (2, 1.5), (3.5, 0.5)],
            "soulful":      [(0, 1.5), (2, 1.0), (3.5, 0.5)],
            "call_response":[(0, 1.0), (2, 1.0)],
            "melodic":      [(0, 2.0), (2, 2.0)],
            "smooth":       [(0, 1.0), (1, 0.5), (1.5, 0.5), (2, 1.0), (3, 1.0)],
            "funky":        [(0, 0.5), (0.75, 0.25), (1, 0.5), (2, 0.5), (2.75, 0.25), (3, 0.5)],
            "roots":        [(0, 2.0), (2.5, 1.5)],
            "lofi":         [(0, 1.5), (2, 2.0)],
            "latin":        [(0, 0.75), (1, 0.5), (1.5, 0.75), (2.5, 1.5)],
            "hypnotic":     [(0, 2.0), (2, 2.0)],
        }
        return rhythms.get(self.style, rhythms["jazzy"])

    def generate(self) -> mido.MidiTrack:
        events: List[NoteEvent] = []
        scale_notes = self._scale_notes()
        rhythm = self._style_rhythm()
        prev_note = scale_notes[len(scale_notes) // 2]  # start at middle of scale

        for bar in range(self.bars):
            bar_start = bar * TPB * 4
            chord_tones = self._chord_tones(bar)

            for beat_pos, dur_beats in rhythm:
                # density filter
                if self.rng.random() > self.density:
                    continue

                # Choose note: mostly scale tones, occasionally chord tones
                if self.rng.random() < 0.4:
                    # Chord tone
                    note = self.rng.choice(chord_tones)
                else:
                    # Scale tone near previous note (stepwise motion)
                    scale_near = [n for n in scale_notes if abs(n - prev_note) <= 5]
                    if scale_near:
                        note = self.rng.choice(scale_near)
                    else:
                        note = self.rng.choice(scale_notes)

                # Keep in range
                while note > self.octave * 12 + 19:
                    note -= 12
                while note < self.octave * 12:
                    note += 12

                prev_note = note

                # Timing
                abs_tick = bar_start + ticks(beat_pos)
                if int(beat_pos * 4) % 2 == 1 and self.swing > 0.5:
                    abs_tick += int((self.swing - 0.5) * 2 * (TPB // 3))

                time_jit = int(self.rng.gauss(0, self.humanize_jitter_ms * (TPB / (60_000 / self.bpm))))
                final_tick = max(0, abs_tick + time_jit)

                vel_base = 75
                final_vel = vel_vary(vel_base, self.humanize_vel_stddev)

                events.append(NoteEvent(
                    channel=2, note=note, velocity=final_vel,
                    start_tick=final_tick, duration_ticks=ticks(dur_beats * 0.85),
                ))

        # Program 0 = Grand Piano, 65 = Alto Sax, 4 = Rhodes
        prog_map = {"bebop": 65, "jazzy": 65, "soulful": 0, "funky": 33}
        program = prog_map.get(self.style, 0)
        return events_to_track(events, channel=2, program=program)
