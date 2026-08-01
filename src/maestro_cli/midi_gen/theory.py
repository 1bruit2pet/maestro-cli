"""
Music Theory Engine for Maestro MIDI Generator
Covers: notes, scales, modes, chord voicings, progressions, Roman numeral analysis.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum


# ---------------------------------------------------------------------------
# Note names & MIDI mapping
# ---------------------------------------------------------------------------

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
ENHARMONICS: Dict[str, str] = {
    "Db": "C#", "Eb": "D#", "Fb": "E", "Gb": "F#", "Ab": "G#", "Bb": "A#", "Cb": "B",
}


def note_to_midi(note: str, octave: int = 4) -> int:
    """Convert note name + octave to MIDI number (C4 = 60)."""
    name = ENHARMONICS.get(note, note)
    idx = NOTE_NAMES.index(name)
    return (octave + 1) * 12 + idx


def midi_to_note(midi: int) -> Tuple[str, int]:
    """Convert MIDI number to (note_name, octave)."""
    octave = (midi // 12) - 1
    name = NOTE_NAMES[midi % 12]
    return name, octave


def parse_note(s: str) -> int:
    """Parse 'C4', 'F#3', 'Bb5' → MIDI int."""
    if len(s) >= 2 and s[-1].isdigit():
        octave = int(s[-1])
        name = s[:-1]
        if len(name) > 1 and s[-2].isdigit():
            octave = int(s[-2:])
            name = s[:-2]
    else:
        name = s
        octave = 4
    return note_to_midi(name, octave)


# ---------------------------------------------------------------------------
# Scale / Mode definitions  (semitone intervals from root)
# ---------------------------------------------------------------------------

class ScaleType(str, Enum):
    MAJOR = "major"
    NATURAL_MINOR = "natural_minor"
    HARMONIC_MINOR = "harmonic_minor"
    MELODIC_MINOR = "melodic_minor"
    DORIAN = "dorian"
    PHRYGIAN = "phrygian"
    LYDIAN = "lydian"
    MIXOLYDIAN = "mixolydian"
    LOCRIAN = "locrian"
    PENTATONIC_MAJOR = "pentatonic_major"
    PENTATONIC_MINOR = "pentatonic_minor"
    BLUES = "blues"
    WHOLE_TONE = "whole_tone"
    DIMINISHED = "diminished"


SCALE_INTERVALS: Dict[ScaleType, List[int]] = {
    ScaleType.MAJOR:            [0, 2, 4, 5, 7, 9, 11],
    ScaleType.NATURAL_MINOR:    [0, 2, 3, 5, 7, 8, 10],
    ScaleType.HARMONIC_MINOR:   [0, 2, 3, 5, 7, 8, 11],
    ScaleType.MELODIC_MINOR:    [0, 2, 3, 5, 7, 9, 11],
    ScaleType.DORIAN:           [0, 2, 3, 5, 7, 9, 10],
    ScaleType.PHRYGIAN:         [0, 1, 3, 5, 7, 8, 10],
    ScaleType.LYDIAN:           [0, 2, 4, 6, 7, 9, 11],
    ScaleType.MIXOLYDIAN:       [0, 2, 4, 5, 7, 9, 10],
    ScaleType.LOCRIAN:          [0, 1, 3, 5, 6, 8, 10],
    ScaleType.PENTATONIC_MAJOR: [0, 2, 4, 7, 9],
    ScaleType.PENTATONIC_MINOR: [0, 3, 5, 7, 10],
    ScaleType.BLUES:            [0, 3, 5, 6, 7, 10],
    ScaleType.WHOLE_TONE:       [0, 2, 4, 6, 8, 10],
    ScaleType.DIMINISHED:       [0, 2, 3, 5, 6, 8, 9, 11],
}


@dataclass
class Scale:
    root: str         # e.g. "D", "F#", "Bb"
    scale_type: ScaleType = ScaleType.MAJOR

    @property
    def root_midi(self) -> int:
        return note_to_midi(self.root, 0)

    @property
    def intervals(self) -> List[int]:
        return SCALE_INTERVALS[self.scale_type]

    def notes(self, octave: int = 4, octaves: int = 2) -> List[int]:
        """Return MIDI notes for the scale across `octaves` octaves."""
        base = note_to_midi(self.root, octave)
        result = []
        for o in range(octaves):
            for iv in self.intervals:
                result.append(base + o * 12 + iv)
        return result

    def degree(self, deg: int, octave: int = 4) -> int:
        """Return MIDI note for scale degree 1-7 (wraps octaves)."""
        ivs = self.intervals
        oct_offset = (deg - 1) // len(ivs)
        iv = ivs[(deg - 1) % len(ivs)]
        return note_to_midi(self.root, octave + oct_offset) + iv

    def contains(self, midi_note: int) -> bool:
        return (midi_note - self.root_midi) % 12 in self.intervals


# ---------------------------------------------------------------------------
# Key – wraps a scale + tonal context
# ---------------------------------------------------------------------------

@dataclass
class Key:
    root: str
    mode: str = "major"   # "major", "minor", "dorian", etc.

    @property
    def scale(self) -> Scale:
        type_map = {
            "major": ScaleType.MAJOR,
            "minor": ScaleType.NATURAL_MINOR,
            "harmonic_minor": ScaleType.HARMONIC_MINOR,
            "dorian": ScaleType.DORIAN,
            "phrygian": ScaleType.PHRYGIAN,
            "mixolydian": ScaleType.MIXOLYDIAN,
            "pentatonic": ScaleType.PENTATONIC_MINOR,
            "blues": ScaleType.BLUES,
        }
        st = type_map.get(self.mode.lower(), ScaleType.MAJOR)
        return Scale(self.root, st)

    @property
    def is_minor(self) -> bool:
        return self.mode.lower() in ("minor", "harmonic_minor", "natural_minor", "dorian", "phrygian")

    @property
    def relative_major(self) -> str:
        """For a minor key, return the relative major root."""
        root_idx = NOTE_NAMES.index(ENHARMONICS.get(self.root, self.root))
        return NOTE_NAMES[(root_idx + 3) % 12]

    @classmethod
    def parse(cls, s: str) -> "Key":
        """Parse strings like 'Dm', 'F#m', 'Bb', 'Am', 'Cmaj', 'Ddorian'."""
        s = s.strip()
        mode = "major"
        root = s
        if s.endswith("min") or s.endswith("m") and not s[:-1].endswith("m"):
            root = s.rstrip("min").rstrip("m")
            mode = "minor"
        elif s.lower().endswith("dorian"):
            root = s[:-6]
            mode = "dorian"
        elif s.lower().endswith("phrygian"):
            root = s[:-8]
            mode = "phrygian"
        elif s.lower().endswith("minor"):
            root = s[:-5]
            mode = "minor"
        elif s.lower().endswith("major") or s.lower().endswith("maj"):
            root = s[:-3] if s.lower().endswith("maj") else s[:-5]
            mode = "major"
        # normalize root
        root = root.strip()
        if len(root) >= 2 and root[1] == "b":
            root = ENHARMONICS.get(root[:2], root[:2])
        return cls(root=root, mode=mode)


# ---------------------------------------------------------------------------
# Chord Voicings
# ---------------------------------------------------------------------------

# Chord quality → intervals from root (semitones)
CHORD_INTERVALS: Dict[str, List[int]] = {
    "maj":      [0, 4, 7],
    "min":      [0, 3, 7],
    "dim":      [0, 3, 6],
    "aug":      [0, 4, 8],
    "sus2":     [0, 2, 7],
    "sus4":     [0, 5, 7],
    "maj7":     [0, 4, 7, 11],
    "min7":     [0, 3, 7, 10],
    "dom7":     [0, 4, 7, 10],
    "dim7":     [0, 3, 6, 9],
    "halfdim7": [0, 3, 6, 10],
    "maj9":     [0, 4, 7, 11, 14],
    "min9":     [0, 3, 7, 10, 14],
    "dom9":     [0, 4, 7, 10, 14],
    "min11":    [0, 3, 7, 10, 14, 17],
    "maj9#11":  [0, 4, 7, 11, 14, 18],
    "dom13":    [0, 4, 7, 10, 14, 21],
    "7alt":     [0, 4, 6, 10, 13],   # 7b5b9 alt dominant
    "add9":     [0, 4, 7, 14],
    "min_add9": [0, 3, 7, 14],
    "power":    [0, 7],
}


@dataclass
class ChordVoicing:
    root: str            # e.g. "F", "C#"
    quality: str = "maj" # key in CHORD_INTERVALS
    octave: int = 3      # base octave for root
    spread: str = "close"  # "close" | "open" | "drop2"
    inversion: int = 0   # 0=root, 1=first, 2=second

    @property
    def midi_notes(self) -> List[int]:
        root_midi = note_to_midi(self.root, self.octave)
        ivs = CHORD_INTERVALS.get(self.quality, CHORD_INTERVALS["maj"])
        notes = [root_midi + iv for iv in ivs]

        # Apply inversion
        for _ in range(self.inversion):
            notes[0] += 12
            notes.sort()

        # Apply voicing spread
        if self.spread == "open" and len(notes) >= 3:
            # Move middle note(s) up an octave
            mid = len(notes) // 2
            notes[mid] += 12
        elif self.spread == "drop2" and len(notes) >= 4:
            # Drop 2nd-highest voice down an octave
            notes[-2] -= 12
            notes.sort()

        return sorted(notes)

    @property
    def root_midi(self) -> int:
        return note_to_midi(self.root, self.octave)

    @property
    def bass_note(self) -> int:
        return min(self.midi_notes)


# ---------------------------------------------------------------------------
# Common chord progressions
# ---------------------------------------------------------------------------

# Roman-numeral → scale degree, quality for major / minor keys
# Format: (degree, quality, [optional bass degree for slash chords])
MAJOR_SCALE_CHORDS = {
    "I":    (1, "maj7"),   "i":    (1, "min7"),
    "II":   (2, "dom7"),   "ii":   (2, "min7"),
    "IIb":  (2, "dom7"),   "bII":  (2, "maj7"),
    "III":  (3, "maj7"),   "iii":  (3, "min7"),
    "IV":   (4, "maj7"),   "iv":   (4, "min7"),
    "V":    (5, "dom7"),   "v":    (5, "min7"),
    "VI":   (6, "maj7"),   "vi":   (6, "min7"),
    "bVII": (7, "maj7"),   "VII":  (7, "dim7"),
    "vii":  (7, "halfdim7"),
}


@dataclass
class Progression:
    key: Key
    chords: List[ChordVoicing] = field(default_factory=list)
    bars_per_chord: List[int] = field(default_factory=list)

    @classmethod
    def from_roman(
        cls,
        key: Key,
        roman_numerals: List[str],
        bars_each: int = 2,
        octave: int = 3,
        spread: str = "close",
    ) -> "Progression":
        """Build a Progression from Roman numeral list, e.g. ['i', 'VII', 'VI', 'VII']."""
        scale = key.scale
        voicings: List[ChordVoicing] = []

        for rn in roman_numerals:
            deg, quality = MAJOR_SCALE_CHORDS.get(rn, (1, "maj7"))
            root_midi = scale.degree(deg, octave=0)
            root_name = NOTE_NAMES[root_midi % 12]
            voicings.append(ChordVoicing(root=root_name, quality=quality, octave=octave, spread=spread))

        bars = [bars_each] * len(roman_numerals)
        return cls(key=key, chords=voicings, bars_per_chord=bars)

    @classmethod
    def from_string(
        cls,
        key: Key,
        progression_str: str,
        bars_each: int = 2,
        octave: int = 3,
    ) -> "Progression":
        """Parse 'i-VII-VI-VII' or 'Fm7-Bb7-EbMaj7-AbMaj7' strings."""
        parts = [p.strip() for p in progression_str.replace(",", "-").split("-")]
        # Detect if it's Roman or literal chord names
        is_roman = all(p[0].upper() in "IVvi" for p in parts if p)

        if is_roman:
            return cls.from_roman(key, parts, bars_each=bars_each, octave=octave)

        # Literal chord names like "Fm7", "Bb11", "DbMaj7"
        voicings: List[ChordVoicing] = []
        for chord_str in parts:
            root, quality = _parse_chord_literal(chord_str)
            voicings.append(ChordVoicing(root=root, quality=quality, octave=octave))

        bars = [bars_each] * len(voicings)
        return cls(key=key, chords=voicings, bars_per_chord=bars)

    @property
    def total_bars(self) -> int:
        return sum(self.bars_per_chord)


def _parse_chord_literal(s: str) -> Tuple[str, str]:
    """Parse chord string like 'Fm7', 'DbMaj7', 'Bb11', 'Gsus4' → (root, quality)."""
    s = s.strip()
    # Extract root (1-2 chars + optional accidental)
    root = s[0].upper()
    rest = s[1:]
    if rest and rest[0] in "#b":
        root += rest[0]
        rest = rest[1:]
    # Normalize flats
    root = ENHARMONICS.get(root, root)
    # Map quality string
    qual_map = {
        "maj7": "maj7", "maj9": "maj9", "maj": "maj",
        "m7": "min7", "min7": "min7", "m9": "min9", "min9": "min9",
        "m11": "min11", "min11": "min11", "m": "min",
        "7": "dom7", "9": "dom9", "11": "min11", "13": "dom13",
        "dim7": "dim7", "dim": "dim", "aug": "aug",
        "sus2": "sus2", "sus4": "sus4",
        "add9": "add9", "7alt": "7alt",
        "": "maj",
    }
    quality = qual_map.get(rest.lower(), qual_map.get(rest, "maj"))
    return root, quality


# ---------------------------------------------------------------------------
# Genre presets
# ---------------------------------------------------------------------------

class GenrePreset(str, Enum):
    BOOM_BAP = "boom-bap"
    AFROBEAT = "afrobeat"
    GOSPEL = "gospel"
    NEO_SOUL = "neo-soul"
    TRAP = "trap"
    RNB = "rnb"
    FUNK = "funk"
    JAZZ = "jazz"
    LATIN = "latin"
    HOUSE = "house"
    REGGAE = "reggae"
    LOFI = "lofi"


@dataclass
class GenreConfig:
    bpm_default: int
    bpm_range: Tuple[int, int]
    swing: float          # 0.5 = straight, 0.67 = full triplet swing
    key_mode: str         # default mode
    default_progressions: List[str]  # Roman numeral progressions
    drums_style: str
    bass_style: str
    melody_style: str
    humanize_jitter_ms: float
    humanize_vel_stddev: float


GENRE_CONFIGS: Dict[str, GenreConfig] = {
    "boom-bap": GenreConfig(
        bpm_default=90, bpm_range=(75, 100), swing=0.58,
        key_mode="minor",
        default_progressions=["i-VII-VI-VII", "i-iv-VII-III"],
        drums_style="boom_bap", bass_style="boom_bap", melody_style="jazzy",
        humanize_jitter_ms=14.0, humanize_vel_stddev=10.0,
    ),
    "afrobeat": GenreConfig(
        bpm_default=105, bpm_range=(95, 120), swing=0.52,
        key_mode="minor",
        default_progressions=["i-bVII-IV-V", "i-iv-i-V"],
        drums_style="afrobeat", bass_style="afrobeat", melody_style="call_response",
        humanize_jitter_ms=10.0, humanize_vel_stddev=8.0,
    ),
    "gospel": GenreConfig(
        bpm_default=92, bpm_range=(80, 110), swing=0.62,
        key_mode="major",
        default_progressions=["I-IV-V-I", "I-vi-IV-V"],
        drums_style="gospel_swing", bass_style="gospel", melody_style="gospel",
        humanize_jitter_ms=14.0, humanize_vel_stddev=12.0,
    ),
    "neo-soul": GenreConfig(
        bpm_default=86, bpm_range=(75, 96), swing=0.58,
        key_mode="minor",
        default_progressions=["i-VII-VI-VII", "ii-V-I-VI"],
        drums_style="soul_layback", bass_style="neo_soul", melody_style="soulful",
        humanize_jitter_ms=18.0, humanize_vel_stddev=9.0,
    ),
    "trap": GenreConfig(
        bpm_default=140, bpm_range=(120, 170), swing=0.5,
        key_mode="minor",
        default_progressions=["i-VII-VI-VII", "i-bVII-iv-V"],
        drums_style="trap", bass_style="trap", melody_style="melodic",
        humanize_jitter_ms=4.0, humanize_vel_stddev=6.0,
    ),
    "rnb": GenreConfig(
        bpm_default=88, bpm_range=(75, 100), swing=0.55,
        key_mode="minor",
        default_progressions=["i-VI-III-VII", "ii-V-I-IV"],
        drums_style="rnb", bass_style="rnb", melody_style="smooth",
        humanize_jitter_ms=12.0, humanize_vel_stddev=8.0,
    ),
    "funk": GenreConfig(
        bpm_default=100, bpm_range=(90, 118), swing=0.54,
        key_mode="minor",
        default_progressions=["i-IV-i-IV", "I-IV-V-I"],
        drums_style="funk_pocket", bass_style="funk", melody_style="funky",
        humanize_jitter_ms=6.0, humanize_vel_stddev=15.0,
    ),
    "jazz": GenreConfig(
        bpm_default=120, bpm_range=(90, 180), swing=0.65,
        key_mode="major",
        default_progressions=["ii-V-I-VI", "I-vi-ii-V"],
        drums_style="jazz_swing", bass_style="jazz_walk", melody_style="bebop",
        humanize_jitter_ms=20.0, humanize_vel_stddev=15.0,
    ),
    "latin": GenreConfig(
        bpm_default=110, bpm_range=(95, 130), swing=0.5,
        key_mode="minor",
        default_progressions=["i-VII-VI-VII", "i-iv-V-i"],
        drums_style="latin_clave", bass_style="latin_tumbao", melody_style="latin",
        humanize_jitter_ms=8.0, humanize_vel_stddev=10.0,
    ),
    "house": GenreConfig(
        bpm_default=124, bpm_range=(120, 135), swing=0.5,
        key_mode="minor",
        default_progressions=["i-VI-III-VII", "i-iv-i-V"],
        drums_style="house_4x4", bass_style="house", melody_style="hypnotic",
        humanize_jitter_ms=3.0, humanize_vel_stddev=5.0,
    ),
    "reggae": GenreConfig(
        bpm_default=80, bpm_range=(70, 95), swing=0.55,
        key_mode="major",
        default_progressions=["I-IV-V-IV", "I-vi-IV-V"],
        drums_style="reggae_one_drop", bass_style="reggae_skank", melody_style="roots",
        humanize_jitter_ms=12.0, humanize_vel_stddev=8.0,
    ),
    "lofi": GenreConfig(
        bpm_default=85, bpm_range=(70, 95), swing=0.57,
        key_mode="minor",
        default_progressions=["i-VII-VI-VII", "ii-V-I-VI"],
        drums_style="lofi_drums", bass_style="lofi_bass", melody_style="lofi",
        humanize_jitter_ms=20.0, humanize_vel_stddev=12.0,
    ),
}


class MusicTheory:
    """Facade for music theory operations."""

    @staticmethod
    def parse_key(s: str) -> Key:
        return Key.parse(s)

    @staticmethod
    def build_progression(
        key: Key,
        progression: str,
        bars_each: int = 2,
        octave: int = 3,
    ) -> Progression:
        return Progression.from_string(key, progression, bars_each=bars_each, octave=octave)

    @staticmethod
    def genre_config(genre: str) -> GenreConfig:
        return GENRE_CONFIGS.get(genre.lower(), GENRE_CONFIGS["boom-bap"])

    @staticmethod
    def default_progression_for_genre(genre: str, key: Key, bars_each: int = 2) -> Progression:
        cfg = GENRE_CONFIGS.get(genre.lower(), GENRE_CONFIGS["boom-bap"])
        prog_str = cfg.default_progressions[0]
        return Progression.from_string(key, prog_str, bars_each=bars_each, octave=3)
