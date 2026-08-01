"""
Procedural MIDI Engine for Maestro CLI
Adapted from: https://github.com/Will-Morr/Procedural_MIDI (Will-Morr, GPL-3.0)

Converts the live probabilistic MIDI generation system into an offline
MIDI file writer that integrates with Maestro's project model.

Original system: real-time output to LoopMIDI + VCV Rack
This adaptation: writes MIDI files compatible with claw-daw / mido
"""

import math
import logging
from random import random, seed as random_seed
from typing import List, Tuple, Optional, Dict
from pathlib import Path

import mido
from mido import MidiFile, MidiTrack, Message, MetaMessage, bpm2tempo

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Scale definitions (from Procedural_MIDI generative_v2.py)
# ---------------------------------------------------------------------------

SCALE_SET: Dict[str, List[int]] = {
    'Major':      [0, 2, 4, 5, 7, 9, 11],
    'Minor':      [0, 2, 3, 5, 7, 8, 10],
    'HarmMinor':  [0, 2, 3, 5, 7, 8, 11],
    'PentMajor':  [0, 2, 4, 7, 9],
    'PentMinor':  [0, 2, 3, 7, 9],
    'Dorian':     [0, 2, 3, 5, 7, 9, 10],
    'Mixolydian': [0, 2, 4, 5, 7, 9, 10],
}

SEVEN_NOTE_PRIORITY = [0.99, 0.3, 0.8, 0.7, 0.9, 0.3, 0.4]
PENT_NOTE_PRIORITY  = [0.9, 0.7, 0.8, 0.8, 0.7]

SCALE_PRIORITIES: Dict[str, List[float]] = {
    'Major':      SEVEN_NOTE_PRIORITY,
    'Minor':      SEVEN_NOTE_PRIORITY,
    'HarmMinor':  SEVEN_NOTE_PRIORITY,
    'PentMajor':  PENT_NOTE_PRIORITY,
    'PentMinor':  PENT_NOTE_PRIORITY,
    'Dorian':     SEVEN_NOTE_PRIORITY,
    'Mixolydian': SEVEN_NOTE_PRIORITY,
}

NOTE_RANGE_MIN = 36
NOTE_RANGE_MAX = 84

# Map Maestro key names → MIDI root note
KEY_TO_MIDI: Dict[str, int] = {
    'C': 60, 'C#': 61, 'Db': 61, 'D': 62, 'D#': 63, 'Eb': 63,
    'E': 64, 'F': 65, 'F#': 66, 'Gb': 66, 'G': 67, 'G#': 68,
    'Ab': 68, 'A': 69, 'A#': 70, 'Bb': 70, 'B': 71,
    # "C Major", "A Minor" etc
    'C Major': 60, 'A Minor': 69, 'G Major': 67, 'D Major': 62,
    'E Minor': 64, 'F Major': 65, 'B Minor': 71,
}

# Map style names → scale type
STYLE_TO_SCALE: Dict[str, str] = {
    'synthwave': 'Minor',
    'retrowave': 'Minor',
    'darksynth': 'HarmMinor',
    'pop':       'Major',
    'jazz':      'Dorian',
    'blues':     'PentMinor',
    'gospel':    'Major',
    'afrobeats': 'PentMinor',
    'neo_soul':  'Dorian',
    'lo-fi':     'PentMajor',
    'default':   'Minor',
}

# Bass behaviors (from bassSetting in original)
BASS_SETTINGS = ['hold', 'hold', 'clock', 'div_2', 'div_3', 'strike']
# Alto/Pad behaviors (from altoSetting in original)
ALTO_SETTINGS = ['match', 'match', 'decay', 'arpeggio', 'pulse', 'random']


# ---------------------------------------------------------------------------
# Core note generation helpers (ported from Procedural_MIDI)
# ---------------------------------------------------------------------------

def get_note_set(base_note: int, scale_name: str = 'Minor') -> Tuple[List[int], List[float]]:
    """
    Build a list of playable MIDI notes across the full range with priority weights.
    Ported from getNoteSet() in generative_v2.py.
    """
    intervals = SCALE_SET.get(scale_name, SCALE_SET['Minor'])
    priorities = SCALE_PRIORITIES.get(scale_name, SEVEN_NOTE_PRIORITY)

    # Bring root below range min
    while base_note >= NOTE_RANGE_MIN:
        base_note -= 12

    out_notes: List[int] = []
    out_priority: List[float] = []

    while base_note < NOTE_RANGE_MAX:
        for i, interval in enumerate(intervals):
            note = base_note + interval
            if note < NOTE_RANGE_MIN:
                continue
            if note > NOTE_RANGE_MAX:
                break
            out_notes.append(note)
            out_priority.append(priorities[i % len(priorities)])
        base_note += 12

    return out_notes, out_priority


def weighted_choice(notes: List[int], priorities: List[float]) -> int:
    """Pick a note weighted by its priority."""
    total = sum(priorities)
    r = random() * total
    cumulative = 0.0
    for note, p in zip(notes, priorities):
        cumulative += p
        if r <= cumulative:
            return note
    return notes[-1]


def pick_next_note(
    current_note: int,
    notes: List[int],
    priorities: List[float],
    scale_motion_velocity: float,
    gap_count: int,
    held_count: int,
) -> int:
    """
    Choose the next note using proximity-weighted randomization.
    Inspired by the motion-biased logic in generative_v2.py.
    """
    if not notes:
        return current_note

    # Weight by closeness to current note + scale priority + motion direction
    adjusted: List[float] = []
    for note, pri in zip(notes, priorities):
        dist = abs(note - current_note)
        # Proximity weight: closer = higher weight
        prox = 1.0 / (1.0 + dist * 0.3)
        # Directional bias from scale_motion_velocity
        direction_bias = 1.0
        if scale_motion_velocity > 0 and note > current_note:
            direction_bias = 1.3
        elif scale_motion_velocity < 0 and note < current_note:
            direction_bias = 1.3
        adjusted.append(pri * prox * direction_bias)

    # Boost notes that continue motion if we have momentum
    total = sum(adjusted)
    if total == 0:
        return current_note

    r = random() * total
    cumulative = 0.0
    for note, w in zip(notes, adjusted):
        cumulative += w
        if r <= cumulative:
            return note
    return notes[-1]


# ---------------------------------------------------------------------------
# Probabilistic play/skip decision (from generative_v2.py main loop logic)
# ---------------------------------------------------------------------------

def should_play_note(
    notes_since_chord_change: int,
    sig_div_count: int,
    gap_count: int,
    held_count: int,
    lead_legato: float,
    chord_sequence_duration: int,
) -> bool:
    play_odds = random()

    # Strong beats get boost
    if notes_since_chord_change == 0:
        play_odds *= 20
    elif notes_since_chord_change % sig_div_count == 0:
        play_odds *= 5

    # Long gaps force a note
    if gap_count > 10:
        play_odds *= gap_count - 8
    elif 0 < gap_count < 4:
        play_odds /= 2
    elif 4 <= gap_count < 8:
        play_odds /= 1.5

    # Sustained notes become more likely to stop
    if gap_count == 0:
        play_odds *= 1.0 - pow(0.95, held_count + 1)

    threshold = 0.3 + (lead_legato - 0.4) / 4
    return play_odds > threshold


# ---------------------------------------------------------------------------
# Main offline generator
# ---------------------------------------------------------------------------

class ProceduralMidiGenerator:
    """
    Generates a MIDI file using the probabilistic engine from Will-Morr/Procedural_MIDI.
    Supports three voices: lead (arpeggio/melody), bass, and alto (pad/harmony).
    """

    def __init__(
        self,
        tempo_bpm: int = 120,
        key: str = 'C',
        style: str = 'synthwave',
        total_bars: int = 32,
        ticks_per_beat: int = 480,
        rand_seed: Optional[int] = None,
    ):
        self.tempo_bpm = tempo_bpm
        self.ticks_per_beat = ticks_per_beat
        self.ticks_per_bar = ticks_per_beat * 4
        self.total_bars = total_bars

        # Resolve key → MIDI root note
        key_clean = key.strip()
        self.root_note = KEY_TO_MIDI.get(key_clean, KEY_TO_MIDI.get(key_clean.split()[0], 60))

        # Resolve style → scale type
        style_lower = style.lower().replace('-', '_').replace(' ', '_')
        self.scale_name = SCALE_STYLE_MAP.get(style_lower, 'Minor')

        if rand_seed is not None:
            random_seed(rand_seed)

        # Build chord sequence from root (I - VI - IV - V)
        self.chord_sequence = self._build_chord_sequence(self.root_note, self.scale_name)

        # Random per-session parameters (mimicking v2's vibes)
        self.lead_legato = 0.4 + random() * 0.4 + random() * 0.3
        self.alto_threshold = 0.01 + 0.5 * random() * random()
        self.bass_setting = BASS_SETTINGS[math.floor(random() * len(BASS_SETTINGS))]
        self.alto_setting = ALTO_SETTINGS[math.floor(random() * len(ALTO_SETTINGS))]

        # Chord timing: notes per chord (like chordSequenceDuration)
        # We use beats per bar × bars per chord. Default: 1 chord per 4 bars
        beats_per_chord = 16  # 4 bars × 4 beats
        self.chord_duration_ticks = beats_per_chord * ticks_per_beat
        self.sig_div_count = 4  # 4 beats per measure

        logger.info(
            "[ProceduralMIDI] key=%s root=%d scale=%s bpm=%d bars=%d "
            "bass=%s alto=%s legato=%.2f",
            key, self.root_note, self.scale_name, tempo_bpm, total_bars,
            self.bass_setting, self.alto_setting, self.lead_legato,
        )

    def _build_chord_sequence(self, root: int, scale_name: str) -> List[Tuple[int, str]]:
        """Build a I-vi-IV-V style chord progression from the root."""
        intervals = SCALE_SET.get(scale_name, SCALE_SET['Minor'])
        if len(intervals) >= 7:
            # I, VI, IV, V in scale degrees
            degrees = [0, 5, 3, 4]
        else:
            degrees = [0, 2, 1, 3]

        chords = []
        for d in degrees:
            note = root + intervals[d % len(intervals)]
            # Alternate scale type by degree for harmonic variety
            if d == 5:
                scale = 'Minor' if 'Major' in scale_name else 'Major'
            elif d == 4:
                scale = 'Mixolydian'
            else:
                scale = scale_name
            chords.append((note, scale))
        return chords

    def generate_lead(self) -> List[Tuple[int, int, int, int]]:
        """
        Generate lead/arpeggio voice.
        Returns list of (pitch, velocity, start_tick, duration_ticks).
        """
        events = []
        current_note = self.root_note
        scale_motion_velocity = 0.0
        gap_count = 0
        held_count = 0
        current_chord_idx = 0
        notes_since_chord_change = 0
        tick = 0

        chord_notes, chord_priorities = get_note_set(
            self.chord_sequence[0][0], self.chord_sequence[0][1]
        )

        step_ticks = self.ticks_per_beat // 2  # 8th note steps

        while tick < self.total_bars * self.ticks_per_bar:
            # Chord change?
            if notes_since_chord_change >= self.chord_duration_ticks // step_ticks:
                notes_since_chord_change = 0
                current_chord_idx = (current_chord_idx + 1) % len(self.chord_sequence)
                chord_notes, chord_priorities = get_note_set(
                    self.chord_sequence[current_chord_idx][0],
                    self.chord_sequence[current_chord_idx][1],
                )

            play = should_play_note(
                notes_since_chord_change,
                self.sig_div_count,
                gap_count,
                held_count,
                self.lead_legato,
                self.chord_duration_ticks // step_ticks,
            )

            if play:
                new_note = pick_next_note(
                    current_note, chord_notes, chord_priorities,
                    scale_motion_velocity, gap_count, held_count,
                )
                # Update motion velocity
                scale_motion_velocity = 0.7 * scale_motion_velocity + 0.3 * (new_note - current_note)
                current_note = new_note

                velocity = max(40, min(120, int(70 + 50 * (random() - 0.3))))
                # Duration: mostly 8th notes, sometimes quarter, rarely longer
                dur_r = random()
                if dur_r < 0.5:
                    dur = step_ticks
                elif dur_r < 0.8:
                    dur = step_ticks * 2
                else:
                    dur = step_ticks * 3

                events.append((current_note, velocity, tick, dur))
                gap_count = 0
                held_count += 1
            else:
                gap_count += 1
                held_count = 0

            tick += step_ticks
            notes_since_chord_change += 1

        return events

    def generate_bass(self) -> List[Tuple[int, int, int, int]]:
        """
        Generate bass voice based on self.bass_setting.
        Returns list of (pitch, velocity, start_tick, duration_ticks).
        """
        events = []
        tick = 0
        beat_ticks = self.ticks_per_beat
        chord_idx = 0
        notes_in_chord = 0
        chord_steps = self.chord_duration_ticks // beat_ticks

        while tick < self.total_bars * self.ticks_per_bar:
            if notes_in_chord >= chord_steps:
                notes_in_chord = 0
                chord_idx = (chord_idx + 1) % len(self.chord_sequence)

            root = self.chord_sequence[chord_idx][0] - 12  # 1 octave down
            root = max(24, min(root, 55))

            vel = -1
            if self.bass_setting == 'hold':
                vel = 100 if notes_in_chord == 0 else -1
            elif self.bass_setting == 'clock':
                vel = 100 if notes_in_chord == 0 else (60 if notes_in_chord % self.sig_div_count == 0 else -1)
            elif self.bass_setting == 'strike':
                vel = 120 if notes_in_chord == 0 else (-2 if notes_in_chord % self.sig_div_count == 0 else -1)
            elif self.bass_setting == 'div_2':
                vel = 100 if notes_in_chord == 0 else (70 if notes_in_chord % (self.sig_div_count * 2) == 0 else -1)
            elif self.bass_setting == 'div_3':
                vel = 100 if notes_in_chord == 0 else (70 if notes_in_chord % (self.sig_div_count * 3) == 0 else -1)
            else:
                vel = 90 if notes_in_chord % self.sig_div_count == 0 else -1

            if vel > 0:
                events.append((root, vel, tick, beat_ticks))

            tick += beat_ticks
            notes_in_chord += 1

        return events

    def generate_alto(self) -> List[Tuple[int, int, int, int]]:
        """
        Generate alto/pad voice based on self.alto_setting.
        Returns list of (pitch, velocity, start_tick, duration_ticks).
        """
        events = []
        tick = 0
        beat_ticks = self.ticks_per_beat
        chord_idx = 0
        notes_in_chord = 0
        chord_steps = self.chord_duration_ticks // beat_ticks
        arp_idx = 0
        arp_up = True

        while tick < self.total_bars * self.ticks_per_bar:
            if notes_in_chord >= chord_steps:
                notes_in_chord = 0
                chord_idx = (chord_idx + 1) % len(self.chord_sequence)

            chord_notes, chord_priorities = get_note_set(
                self.chord_sequence[chord_idx][0],
                self.chord_sequence[chord_idx][1],
            )

            # Limit to a 2-octave range for pad
            mid = (NOTE_RANGE_MIN + NOTE_RANGE_MAX) // 2
            chord_notes = [n for n in chord_notes if mid - 12 <= n <= mid + 12]
            if not chord_notes:
                tick += beat_ticks
                notes_in_chord += 1
                continue

            played = False
            if self.alto_setting == 'match':
                # Play chord tone on every beat
                if notes_in_chord % self.sig_div_count == 0:
                    note = chord_notes[notes_in_chord % len(chord_notes)]
                    vel = max(40, int(80 * self.alto_threshold + 40 * random()))
                    events.append((note, vel, tick, beat_ticks * 2))
                    played = True
            elif self.alto_setting == 'decay':
                if notes_in_chord == 0:
                    for note in chord_notes[:3]:
                        vel = int(90 - 20 * random())
                        events.append((note, vel, tick, self.chord_duration_ticks // 2))
                    played = True
            elif self.alto_setting == 'arpeggio':
                note = chord_notes[arp_idx % len(chord_notes)]
                vel = int(70 + 30 * random())
                events.append((note, vel, tick, beat_ticks))
                played = True
                if arp_up:
                    arp_idx += 1
                    if arp_idx >= len(chord_notes):
                        arp_idx = len(chord_notes) - 2
                        arp_up = False
                else:
                    arp_idx -= 1
                    if arp_idx < 0:
                        arp_idx = 1
                        arp_up = True
            elif self.alto_setting == 'pulse':
                if random() > (1.0 - self.alto_threshold):
                    note = weighted_choice(chord_notes, [1.0] * len(chord_notes))
                    vel = int(60 + 50 * random())
                    events.append((note, vel, tick, beat_ticks))
                    played = True
            elif self.alto_setting == 'random':
                if random() > 0.5:
                    note = weighted_choice(chord_notes, [1.0] * len(chord_notes))
                    vel = int(55 + 55 * random())
                    events.append((note, vel, tick, beat_ticks))
                    played = True

            tick += beat_ticks
            notes_in_chord += 1

        return events

    def events_to_midi_track(
        self,
        events: List[Tuple[int, int, int, int]],
        channel: int = 0,
        program: int = 0,
        track_name: str = 'track',
    ) -> MidiTrack:
        """Convert list of (pitch, velocity, start_tick, dur_ticks) to a MidiTrack."""
        track = MidiTrack()
        track.append(MetaMessage('track_name', name=track_name, time=0))
        if channel != 9:
            track.append(Message('program_change', program=program, channel=channel, time=0))

        # Build flat list of (tick, type, note, vel) events
        raw = []
        for pitch, vel, start, dur in events:
            if pitch < 0 or pitch > 127 or vel <= 0:
                continue
            raw.append((start, 'note_on', pitch, vel))
            raw.append((start + dur, 'note_off', pitch, 0))

        raw.sort(key=lambda x: (x[0], 0 if x[1] == 'note_off' else 1))

        prev_tick = 0
        for tick, msg_type, pitch, vel in raw:
            delta = tick - prev_tick
            if delta < 0:
                delta = 0
            track.append(Message(msg_type, note=pitch, velocity=vel, channel=channel, time=delta))
            prev_tick = tick

        track.append(MetaMessage('end_of_track', time=0))
        return track

    def generate_midi_file(
        self,
        output_path: Path,
        role: str = 'keys',
    ) -> Path:
        """
        Generate and save a MIDI file for the given role.
        Role can be: keys, bass, drums, pad, lead.
        """
        mid = MidiFile(type=1, ticks_per_beat=self.ticks_per_beat)

        # Tempo track
        tempo_track = MidiTrack()
        tempo_track.append(MetaMessage('set_tempo', tempo=bpm2tempo(self.tempo_bpm), time=0))
        tempo_track.append(MetaMessage('time_signature', numerator=4, denominator=4,
                                       clocks_per_click=24, notated_32nd_notes_per_beat=8, time=0))
        tempo_track.append(MetaMessage('end_of_track', time=0))
        mid.tracks.append(tempo_track)

        # Generate voice based on role
        if role in ('keys', 'lead', 'melody'):
            events = self.generate_lead()
            channel = 0
            program = 4  # Rhodes E-Piano
        elif role == 'bass':
            events = self.generate_bass()
            channel = 1
            program = 38  # Synth Bass
        elif role == 'drums':
            events = self._generate_drums()
            channel = 9
            program = 0
        else:  # pad, strings, harmony
            events = self.generate_alto()
            channel = 2
            program = 89  # Warm Pad

        note_track = self.events_to_midi_track(events, channel=channel, program=program, track_name=role)
        mid.tracks.append(note_track)
        mid.save(str(output_path))
        logger.info("[ProceduralMIDI] Saved %s → %s (%d events)", role, output_path, len(events))
        return output_path

    def _generate_drums(self) -> List[Tuple[int, int, int, int]]:
        """
        Generate a drum pattern using a 4-on-the-floor + probabilistic fills.
        """
        events = []
        beat = self.ticks_per_beat
        bar_ticks = self.ticks_per_bar
        tick = 0

        KICK  = 36
        SNARE = 38
        HIHAT = 42
        OPENHAT = 46
        CRASH = 49

        bar = 0
        while tick < self.total_bars * bar_ticks:
            is_fill_bar = (bar + 1) % 8 == 0  # fill every 8 bars

            for b in range(4):  # 4 beats per bar
                b_tick = tick + b * beat

                # Kick: beat 1 + 3, plus probabilistic extras
                if b in (0, 2):
                    events.append((KICK, 110, b_tick, beat // 2))
                elif random() < 0.15:
                    events.append((KICK, 80, b_tick, beat // 2))

                # Snare: beat 2 + 4
                if b in (1, 3):
                    events.append((SNARE, 100, b_tick, beat // 2))

                # Hi-hats: 8th notes with swing feel
                for h in range(2):
                    h_tick = b_tick + h * (beat // 2)
                    vel = 75 if h == 0 else 55
                    # Swing offset on offbeats
                    if h == 1:
                        h_tick += int(beat * 0.04)
                    hat = OPENHAT if (random() < 0.05) else HIHAT
                    events.append((hat, vel, h_tick, beat // 4))

                # Fill bar extras
                if is_fill_bar and b == 3:
                    events.append((SNARE, 115, b_tick + beat // 4, beat // 4))
                    events.append((SNARE, 120, b_tick + beat // 2, beat // 4))

            # Crash on bar 1 and fill bars
            if bar == 0 or is_fill_bar:
                events.append((CRASH, 90, tick, beat))

            tick += bar_ticks
            bar += 1

        return events


# ---------------------------------------------------------------------------
# Style→Scale map (placed here to avoid forward reference issues)
# ---------------------------------------------------------------------------

SCALE_STYLE_MAP: Dict[str, str] = {
    'synthwave':  'Minor',
    'retrowave':  'Minor',
    'darksynth':  'HarmMinor',
    'pop':        'Major',
    'jazz':       'Dorian',
    'blues':      'PentMinor',
    'gospel':     'Major',
    'afrobeats':  'PentMinor',
    'neo_soul':   'Dorian',
    'lo_fi':      'PentMajor',
    'default':    'Minor',
}


# ---------------------------------------------------------------------------
# Public API: generate_procedural_midi()
# ---------------------------------------------------------------------------

def generate_procedural_midi(
    output_path: Path,
    role: str,
    key: str = 'C',
    tempo_bpm: int = 120,
    style: str = 'synthwave',
    total_bars: int = 32,
    ticks_per_beat: int = 480,
    sections: Optional[list] = None,
    rand_seed: Optional[int] = None,
) -> Path:
    """
    High-level entry point. Generates a MIDI file for a given role using
    the probabilistic Procedural_MIDI engine.

    Args:
        output_path:    Where to write the .mid file.
        role:           'keys', 'bass', 'drums', or 'pad'
        key:            Musical key, e.g. 'C', 'C#', 'A Minor'
        tempo_bpm:      Tempo in BPM
        style:          Style string from Maestro project
        total_bars:     Total bars to generate
        ticks_per_beat: MIDI ticks per beat (default 480)
        sections:       Optional list of section dicts for varied energy

    Returns:
        Path to the saved MIDI file.
    """
    # Derive style string
    style_key = style.lower().strip().replace('-', '_').replace(' ', '_')
    if style_key not in SCALE_STYLE_MAP:
        style_key = 'default'

    gen = ProceduralMidiGenerator(
        tempo_bpm=tempo_bpm,
        key=key,
        style=style_key,
        total_bars=total_bars,
        ticks_per_beat=ticks_per_beat,
        rand_seed=rand_seed,
    )
    return gen.generate_midi_file(output_path, role=role)
