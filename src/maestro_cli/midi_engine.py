"""
Maestro MIDI Engine — Generateur MIDI symbolique réel.

Remplace le faux LLM provider par un moteur algorithmique solide basé sur
les métadonnées du Song (clé, tempo, style, sections) et mido.

Produit de vrais fichiers .mid multi-pistes jouables directement.
Pas de PyTorch, pas de modèle HuggingFace — rapide, déterministe, local.
"""

from __future__ import annotations

import logging
import math
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import mido
from mido import Message, MidiFile, MidiTrack, MetaMessage

logger = logging.getLogger(__name__)

# ============================================================================
# THÉORIE MUSICALE
# ============================================================================

# Demi-tons depuis C pour chaque note
NOTE_TO_SEMITONE: Dict[str, int] = {
    "C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3,
    "E": 4, "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8,
    "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11,
}

# Intervalles de gamme
SCALE_INTERVALS = {
    "major":       [0, 2, 4, 5, 7, 9, 11],
    "minor":       [0, 2, 3, 5, 7, 8, 10],
    "dorian":      [0, 2, 3, 5, 7, 9, 10],
    "mixolydian":  [0, 2, 4, 5, 7, 9, 10],
    "pentatonic":  [0, 2, 4, 7, 9],
    "blues":       [0, 3, 5, 6, 7, 10],
}

# Progressions d'accords par style (degrés de la gamme, 0-indexed)
STYLE_PROGRESSIONS: Dict[str, List[List[int]]] = {
    "gospel":     [[0, 3, 4, 0], [0, 5, 3, 4]],
    "neo_soul":   [[0, 3, 4, 5], [0, 2, 5, 3]],
    "afrobeats":  [[0, 3, 4, 3], [0, 5, 4, 0]],
    "jazz":       [[0, 1, 4, 0], [0, 3, 1, 4]],
    "rnb":        [[0, 3, 4, 5], [0, 5, 3, 4]],
    "pop":        [[0, 5, 3, 4], [0, 4, 5, 3]],
    "default":    [[0, 3, 4, 0]],
}

# Triades (intervalles depuis la fondamentale) par type d'accord
CHORD_TYPES = {
    "major": [0, 4, 7],
    "minor": [0, 3, 7],
    "dom7":  [0, 4, 7, 10],
    "maj7":  [0, 4, 7, 11],
    "min7":  [0, 3, 7, 10],
}

# Quel type d'accord pour chaque degré (mode majeur)
DEGREE_CHORD_MAJOR = ["major", "minor", "minor", "major", "major", "minor", "minor"]
DEGREE_CHORD_MINOR = ["minor", "minor", "major", "minor", "minor", "major", "major"]

# Canal MIDI General MIDI par rôle
GM_CHANNEL: Dict[str, int] = {
    "drums":  9,   # Canal percussions MIDI
    "keys":   0,
    "bass":   1,
    "pad":    2,
    "lead":   3,
    "rhythm": 4,
    "melody": 5,
    "choir":  6,
    "brass":  7,
    "strings": 8,
    "guitar": 10,
    "piano":  11,
    "organ":  12,
    "synth":  13,
}

# Programme GM par rôle
GM_PROGRAM: Dict[str, int] = {
    "keys":   4,    # Electric Piano 1
    "bass":   33,   # Electric Bass (finger)
    "pad":    89,   # Pad 2 (warm)
    "lead":   80,   # Lead 1 (square)
    "rhythm": 25,   # Acoustic Guitar (steel)
    "melody": 73,   # Flute
    "choir":  52,   # Choir Aahs
    "brass":  56,   # Trumpet
    "strings": 48,  # String Ensemble 1
    "guitar": 27,   # Electric Guitar (clean)
    "piano":  0,    # Acoustic Grand Piano
    "organ":  19,   # Rock Organ
    "synth":  81,   # Lead 2 (sawtooth)
    "drums":  0,    # (N/A - canal 9)
}

# Mapping GM Drum notes
DRUM_MAP = {
    "kick":    36,
    "snare":   38,
    "clap":    39,
    "hihat":   42,
    "open_hh": 46,
    "ride":    51,
    "crash":   49,
    "cowbell": 56,
    "clave":   75,
    "shaker":  70,
    "tom_lo":  41,
    "tom_hi":  50,
}


# ============================================================================
# STRUCTURES DE DONNÉES
# ============================================================================

@dataclass
class MidiNote:
    """Une note MIDI avec timing absolu en ticks."""
    pitch: int        # MIDI pitch 0-127
    velocity: int     # 0-127
    start_tick: int   # Tick de début (absolu)
    duration_ticks: int  # Durée en ticks


@dataclass
class TrackSpec:
    """Spécification d'un track à générer."""
    name: str
    role: str
    midi_file: str
    channel: int = 0
    program: int = 0


@dataclass
class SongSpec:
    """Paramètres de la pièce musicale."""
    key: str = "C"
    mode: str = "major"   # major / minor
    tempo_bpm: int = 92
    time_signature: Tuple[int, int] = (4, 4)
    style: str = "gospel"
    ticks_per_beat: int = 480
    total_bars: int = 32
    sections: List[Dict] = field(default_factory=list)
    swing: float = 0.0
    humanize: float = 0.06


# ============================================================================
# UTILITAIRES
# ============================================================================

def parse_key(key_str: str) -> Tuple[int, str]:
    """
    Parse une clé musicale comme 'F minor', 'C#', 'Bb major'.
    Retourne (root_semitone, mode).
    """
    key_str = key_str.strip()
    mode = "major"
    note_part = key_str

    for suffix in [" minor", "m", " major", " maj", " min"]:
        if key_str.lower().endswith(suffix.lower()):
            mode = "minor" if "min" in suffix.lower() else "major"
            note_part = key_str[: len(key_str) - len(suffix)].strip()
            break

    # Normaliser la casse de la note
    note_part = note_part.capitalize()
    if len(note_part) == 2 and note_part[1] in ("b",):
        note_part = note_part[0].upper() + "b"
    elif len(note_part) == 2 and note_part[1] == "#":
        note_part = note_part[0].upper() + "#"

    semitone = NOTE_TO_SEMITONE.get(note_part, 0)
    return semitone, mode


def build_scale(root: int, mode: str = "major", octave: int = 4) -> List[int]:
    """Construit la liste de pitches MIDI pour une gamme sur une octave."""
    base = root + octave * 12
    intervals = SCALE_INTERVALS.get(mode, SCALE_INTERVALS["major"])
    return [base + i for i in intervals]


def build_chord(root_pitch: int, chord_type: str = "major") -> List[int]:
    """Construit un accord depuis un pitch fondamental."""
    intervals = CHORD_TYPES.get(chord_type, CHORD_TYPES["major"])
    return [root_pitch + i for i in intervals]


def get_style_key(style_raw) -> str:
    """Normalise le style (peut être list ou str)."""
    if isinstance(style_raw, list):
        s = style_raw[0] if style_raw else "gospel"
    else:
        s = str(style_raw)
    s = s.lower().replace("-", "_").replace(" ", "_")
    return s if s in STYLE_PROGRESSIONS else "default"


def humanize_velocity(vel: int, amount: float) -> int:
    """Ajoute une variation humaine à la vélocité."""
    if amount <= 0:
        return vel
    delta = int(random.gauss(0, amount * 20))
    return max(10, min(127, vel + delta))


def humanize_timing(tick: int, amount: float, ticks_per_beat: int) -> int:
    """Ajoute un micro-timing humain."""
    if amount <= 0:
        return tick
    sigma = amount * ticks_per_beat * 0.08
    delta = int(random.gauss(0, sigma))
    return max(0, tick + delta)


def apply_swing(tick: int, ticks_per_beat: int, swing: float) -> int:
    """Applique du swing sur les subdivisions paires."""
    if swing <= 0:
        return tick
    sub = ticks_per_beat // 2
    pos_in_beat = tick % ticks_per_beat
    if abs(pos_in_beat - sub) < ticks_per_beat // 8:
        offset = int(swing * sub * 0.33)
        return tick + offset
    return tick


def notes_to_midi_track(
    notes: List[MidiNote],
    channel: int,
    program: int,
    ticks_per_beat: int,
    track_name: str = "",
    tempo_us: int = 500000,
    is_drums: bool = False,
) -> MidiTrack:
    """Convertit une liste de MidiNote en MidiTrack mido."""
    track = MidiTrack()

    if track_name:
        track.append(MetaMessage("track_name", name=track_name, time=0))
    if not is_drums:
        track.append(Message("program_change", channel=channel, program=program, time=0))

    # Construire tous les events (note_on + note_off) triés par tick absolu
    events: List[Tuple[int, Message]] = []
    for note in notes:
        on_msg = Message(
            "note_on",
            channel=channel,
            note=max(0, min(127, note.pitch)),
            velocity=max(0, min(127, note.velocity)),
            time=note.start_tick,
        )
        off_msg = Message(
            "note_on",
            channel=channel,
            note=max(0, min(127, note.pitch)),
            velocity=0,
            time=note.start_tick + note.duration_ticks,
        )
        events.append((note.start_tick, on_msg))
        events.append((note.start_tick + note.duration_ticks, off_msg))

    events.sort(key=lambda x: x[0])

    # Convertir en delta-time
    current_tick = 0
    for abs_tick, msg in events:
        delta = abs_tick - current_tick
        track.append(msg.copy(time=delta))
        current_tick = abs_tick

    track.append(MetaMessage("end_of_track", time=0))
    return track


# ============================================================================
# GÉNÉRATEURS PAR RÔLE
# ============================================================================

def generate_drums(spec: SongSpec, section_data: List[Dict]) -> List[MidiNote]:
    """
    Génère un pattern de batterie complet pour toutes les sections.
    Adapte la densité (low/medium/high) à chaque section.
    """
    notes: List[MidiNote] = []
    tpb = spec.ticks_per_beat
    beat = tpb
    half = tpb // 2
    quarter = tpb // 4
    eighth = tpb // 8

    style = get_style_key(spec.style)
    current_tick = 0

    for section in section_data:
        bars = section.get("bars", 8)
        density = section.get("density", "medium")
        energy = section.get("energy", 0.5)

        # Vélocités de base adaptées à l'énergie
        kick_vel = int(100 + energy * 27)
        snare_vel = int(85 + energy * 27)
        hh_vel = int(60 + energy * 30)

        for bar in range(bars):
            bar_start = current_tick + bar * beat * 4

            # === KICK ===
            notes.append(MidiNote(DRUM_MAP["kick"], kick_vel, bar_start, quarter))
            if density in ("medium", "high"):
                notes.append(MidiNote(DRUM_MAP["kick"], kick_vel - 10, bar_start + beat * 2 + half, quarter))
            if density == "high":
                notes.append(MidiNote(DRUM_MAP["kick"], kick_vel - 20, bar_start + beat * 3, quarter))

            # === SNARE ===
            notes.append(MidiNote(DRUM_MAP["snare"], snare_vel, bar_start + beat, quarter))
            notes.append(MidiNote(DRUM_MAP["snare"], snare_vel, bar_start + beat * 3, quarter))

            # === HI-HAT ===
            if density == "low":
                # Seulement sur les temps 1 et 3
                for b in range(4):
                    notes.append(MidiNote(DRUM_MAP["hihat"], hh_vel, bar_start + beat * b, eighth))
            elif density == "medium":
                # Double croches
                for b in range(8):
                    notes.append(MidiNote(DRUM_MAP["hihat"], hh_vel - (5 if b % 2 else 0),
                                          bar_start + b * half, eighth))
            else:  # high
                # Doubles croches + open hi-hat
                for b in range(8):
                    note = DRUM_MAP["open_hh"] if b == 6 else DRUM_MAP["hihat"]
                    notes.append(MidiNote(note, hh_vel - (5 if b % 2 else 0),
                                          bar_start + b * half, eighth))

            # === AFROBEATS/GOSPEL spécifique ===
            if style == "afrobeats":
                # Clave africaine
                notes.append(MidiNote(DRUM_MAP["clave"], 70, bar_start, eighth))
                notes.append(MidiNote(DRUM_MAP["clave"], 70, bar_start + quarter * 3, eighth))
                notes.append(MidiNote(DRUM_MAP["clave"], 70, bar_start + beat + quarter, eighth))
            elif style in ("gospel", "rnb"):
                # Shaker gospel
                for b in range(8):
                    if b % 2 == 1:
                        notes.append(MidiNote(DRUM_MAP["shaker"], 50, bar_start + b * half, eighth))

        current_tick += bars * beat * 4

    return notes


def generate_bass(spec: SongSpec, section_data: List[Dict], root: int, mode: str,
                  progression: List[int]) -> List[MidiNote]:
    """
    Génère une ligne de basse qui suit la progression d'accords.
    """
    notes: List[MidiNote] = []
    tpb = spec.ticks_per_beat
    beat = tpb
    half = tpb // 2
    quarter = tpb // 4
    intervals = SCALE_INTERVALS.get(mode, SCALE_INTERVALS["major"])
    current_tick = 0

    for section in section_data:
        bars = section.get("bars", 8)
        density = section.get("density", "medium")
        energy = section.get("energy", 0.5)

        bars_per_chord = max(1, 4 // len(progression))
        vel_base = int(90 + energy * 25)

        for bar in range(bars):
            bar_start = current_tick + bar * beat * 4
            chord_idx = (bar // bars_per_chord) % len(progression)
            degree = progression[chord_idx]
            root_pitch = (root + intervals[degree % len(intervals)]) % 12 + 36  # Octave 2

            # Fondamentale sur le 1
            dur = beat * 2 if density == "low" else beat
            vel = humanize_velocity(vel_base, spec.humanize)
            notes.append(MidiNote(root_pitch, vel, bar_start, dur))

            if density == "medium":
                # Passing note sur le 3
                fifth = root_pitch + 7
                notes.append(MidiNote(fifth, humanize_velocity(vel_base - 10, spec.humanize),
                                      bar_start + beat * 2, beat))

            elif density == "high":
                # Ligne syncopée
                fifth = root_pitch + 7
                oct_note = root_pitch + 12
                notes.append(MidiNote(fifth, humanize_velocity(vel_base - 5, spec.humanize),
                                      bar_start + beat, beat))
                notes.append(MidiNote(root_pitch, humanize_velocity(vel_base - 10, spec.humanize),
                                      bar_start + beat * 2, half))
                notes.append(MidiNote(oct_note, humanize_velocity(vel_base - 15, spec.humanize),
                                      bar_start + beat * 3, beat))

        current_tick += bars * beat * 4

    return notes


def generate_keys(spec: SongSpec, section_data: List[Dict], root: int, mode: str,
                  progression: List[int]) -> List[MidiNote]:
    """
    Génère des voicings de clavier (accords + mélodie).
    """
    notes: List[MidiNote] = []
    tpb = spec.ticks_per_beat
    beat = tpb
    half = tpb // 2
    quarter = tpb // 4
    intervals = SCALE_INTERVALS.get(mode, SCALE_INTERVALS["major"])
    chord_types = DEGREE_CHORD_MAJOR if mode == "major" else DEGREE_CHORD_MINOR
    current_tick = 0

    for section in section_data:
        bars = section.get("bars", 8)
        density = section.get("density", "medium")
        energy = section.get("energy", 0.5)
        vel_base = int(75 + energy * 30)
        bars_per_chord = max(1, 4 // len(progression))

        for bar in range(bars):
            bar_start = current_tick + bar * beat * 4
            chord_idx = (bar // bars_per_chord) % len(progression)
            degree = progression[chord_idx]
            chord_root = (root + intervals[degree % len(intervals)]) % 12 + 60  # Octave 4
            ctype = chord_types[degree % len(chord_types)]
            chord_pitches = build_chord(chord_root, ctype)

            if density == "low":
                # Voicing ouvert sur le 1 seulement
                dur = beat * 3
                for p in chord_pitches[:3]:
                    notes.append(MidiNote(p, humanize_velocity(vel_base, spec.humanize),
                                          bar_start, dur))

            elif density == "medium":
                # Voicings syncopés sur 1 et 3
                for b_offset in [0, beat * 2]:
                    for p in chord_pitches[:3]:
                        tick = humanize_timing(bar_start + b_offset, spec.humanize, tpb)
                        notes.append(MidiNote(p, humanize_velocity(vel_base, spec.humanize),
                                              tick, beat + half))

            else:  # high — voicings rythmiques + contre-mélodie
                offsets = [0, quarter * 3, beat * 2, beat * 3 - quarter]
                for b_offset in offsets:
                    chord_sel = chord_pitches[:3] if b_offset % beat == 0 else chord_pitches[1:]
                    for p in chord_sel:
                        tick = humanize_timing(bar_start + b_offset, spec.humanize, tpb)
                        notes.append(MidiNote(p, humanize_velocity(vel_base - 5, spec.humanize),
                                              tick, half))

        current_tick += bars * beat * 4

    return notes


def generate_pad(spec: SongSpec, section_data: List[Dict], root: int, mode: str,
                 progression: List[int]) -> List[MidiNote]:
    """Génère un pad atmosphérique (tenues longues)."""
    notes: List[MidiNote] = []
    tpb = spec.ticks_per_beat
    beat = tpb
    intervals = SCALE_INTERVALS.get(mode, SCALE_INTERVALS["major"])
    chord_types = DEGREE_CHORD_MAJOR if mode == "major" else DEGREE_CHORD_MINOR
    current_tick = 0

    for section in section_data:
        bars = section.get("bars", 8)
        energy = section.get("energy", 0.5)
        density = section.get("density", "medium")
        vel_base = int(50 + energy * 25)
        bars_per_chord = max(2, 4 // max(1, len(progression)))

        for bar in range(bars):
            if bar % bars_per_chord != 0:
                current_tick += beat * 4
                continue

            bar_start = current_tick
            chord_idx = (bar // bars_per_chord) % len(progression)
            degree = progression[chord_idx]
            chord_root = (root + intervals[degree % len(intervals)]) % 12 + 60
            ctype = chord_types[degree % len(chord_types)]
            chord_pitches = build_chord(chord_root, ctype)

            # Tenir les notes sur plusieurs barres
            hold_bars = min(bars_per_chord, bars - bar)
            dur = hold_bars * beat * 4 - beat // 2

            for i, p in enumerate(chord_pitches[:4]):
                p_adj = p - 12  # Octave plus basse pour le pad
                notes.append(MidiNote(p_adj, humanize_velocity(vel_base - i * 3, spec.humanize),
                                      bar_start, dur))

            current_tick += bars_per_chord * beat * 4
            continue

        # Si on n'a pas avancé dans la boucle, avancer quand même
        if bars % bars_per_chord != 0:
            current_tick += (bars % bars_per_chord) * beat * 4

    return notes


def generate_lead(spec: SongSpec, section_data: List[Dict], root: int, mode: str) -> List[MidiNote]:
    """Génère une mélodie lead pentatonique."""
    notes: List[MidiNote] = []
    tpb = spec.ticks_per_beat
    beat = tpb
    half = tpb // 2
    quarter = tpb // 4
    scale = build_scale(root, "pentatonic", octave=5)
    current_tick = 0

    for section in section_data:
        bars = section.get("bars", 8)
        energy = section.get("energy", 0.5)
        density = section.get("density", "medium")
        vel_base = int(80 + energy * 30)

        for bar in range(bars):
            bar_start = current_tick + bar * beat * 4

            if density == "low":
                # Quelques notes seulement
                if bar % 2 == 0:
                    p = random.choice(scale)
                    notes.append(MidiNote(p, humanize_velocity(vel_base, spec.humanize),
                                          bar_start, beat * 2))

            elif density == "medium":
                # Phrases de 2-3 notes par barre
                offsets = [0, beat + half, beat * 3]
                for off in offsets:
                    p = random.choice(scale)
                    dur = half + random.choice([0, quarter])
                    notes.append(MidiNote(p, humanize_velocity(vel_base, spec.humanize),
                                          bar_start + off, dur))

            else:  # high — mélodie active
                offsets = [0, quarter, beat, beat + quarter, beat * 2, beat * 2 + half, beat * 3]
                prev = None
                for off in offsets:
                    # Mouvement mélodique conjoint ou par tierce
                    if prev is None:
                        p = scale[len(scale) // 2]
                    else:
                        idx = scale.index(prev) if prev in scale else len(scale) // 2
                        step = random.choice([-1, 0, 1, 2])
                        idx = max(0, min(len(scale) - 1, idx + step))
                        p = scale[idx]
                    prev = p
                    dur = quarter + random.choice([0, quarter])
                    notes.append(MidiNote(p, humanize_velocity(vel_base, spec.humanize),
                                          bar_start + off, dur))

        current_tick += bars * beat * 4

    return notes


# ============================================================================
# MOTEUR PRINCIPAL
# ============================================================================

class MidiEngine:
    """
    Moteur de génération MIDI symbolique.

    Prend un SongSpec et génère de vrais fichiers .mid par rôle.
    Aucune dépendance ML — rapide et reproductible.
    """

    def __init__(self, seed: Optional[int] = None):
        if seed is not None:
            random.seed(seed)

    def _get_progression(self, spec: SongSpec) -> List[int]:
        """Choisit la progression d'accords selon le style."""
        style_key = get_style_key(spec.style)
        progs = STYLE_PROGRESSIONS.get(style_key, STYLE_PROGRESSIONS["default"])
        return progs[0]

    def generate_track(
        self,
        role: str,
        spec: SongSpec,
        output_path: Path,
    ) -> Path:
        """
        Génère un fichier MIDI pour un rôle donné.

        Args:
            role: Rôle instrumental ('drums', 'bass', 'keys', 'pad', 'lead', …)
            spec: Paramètres de la pièce musicale
            output_path: Chemin du fichier .mid à écrire

        Returns:
            Chemin du fichier créé
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        root, mode = parse_key(spec.key)
        progression = self._get_progression(spec)
        tempo_us = int(60_000_000 / spec.ticks_per_beat) if False else mido.bpm2tempo(spec.tempo_bpm)

        role = role.lower()

        # --- TENTATIVE DE GÉNÉRATION VIA LE MOTEUR MIDI-LLM (Port 8080) ---
        try:
            import requests
            from maestro_cli.config import settings
            from maestro_cli.midi_llm_provider import get_midi_llm_provider

            # Vérification rapide si le serveur est en ligne
            r = requests.get(f"{settings.MIDI_LLM_BASE_URL.rstrip('/')}/health", timeout=2)
            if r.status_code == 200:
                logger.info("[MIDI Engine] Serveur MIDI-LLM détecté en ligne. Génération du rôle: %s", role)
                provider = get_midi_llm_provider()
                prompt = f"Orchestrate a {role} track in the key of {spec.key} at {spec.tempo_bpm} BPM in {spec.style} style."
                note_events = provider.generate_notes(prompt, max_tokens=1024)

                if note_events:
                    # Convertir NoteEvent (secondes) en MidiNote (ticks)
                    midi_notes = []
                    ticks_per_second = spec.ticks_per_beat * (spec.tempo_bpm / 60.0)
                    for ne in note_events:
                        start_tick = int(ne.onset * ticks_per_second)
                        dur_ticks = int(ne.duration * ticks_per_second)
                        midi_notes.append(MidiNote(
                            pitch=ne.pitch,
                            velocity=ne.velocity,
                            start_tick=start_tick,
                            duration_ticks=dur_ticks
                        ))

                    is_drums = (role == "drums")
                    channel = GM_CHANNEL.get(role, 9 if is_drums else 0)
                    program = GM_PROGRAM.get(role, 0 if is_drums else 4)

                    mid = MidiFile(type=1, ticks_per_beat=spec.ticks_per_beat)
                    tempo_track = MidiTrack()
                    tempo_track.append(MetaMessage("set_tempo", tempo=tempo_us, time=0))
                    num, denom = spec.time_signature
                    tempo_track.append(MetaMessage("time_signature", numerator=num, denominator=denom, clocks_per_click=24, notated_32nd_notes_per_beat=8, time=0))
                    tempo_track.append(MetaMessage("end_of_track", time=0))
                    mid.tracks.append(tempo_track)

                    note_track = notes_to_midi_track(
                        midi_notes,
                        channel=channel,
                        program=program,
                        ticks_per_beat=spec.ticks_per_beat,
                        track_name=role,
                        tempo_us=tempo_us,
                        is_drums=is_drums,
                    )
                    mid.tracks.append(note_track)
                    mid.save(str(output_path))
                    logger.info("[MIDI Engine] Succès de l'orchestration via MIDI-LLM (%d notes).", len(midi_notes))
                    return output_path
        except Exception as e:
            logger.warning("[MIDI Engine] Échec ou indisponibilité du MIDI-LLM (%s). Bascule sur le fallback algorithmique local.", e)

        # --- FALLBACK : MOTEUR PROCÉDURAL (Procedural_MIDI) ---
        # Utilise le moteur probabiliste de Will-Morr/Procedural_MIDI
        # pour générer un MIDI harmoniquement varié sans LLM.
        logger.info("[MIDI Engine] Utilisation du moteur procédural pour role=%s", role)
        from maestro_cli.procedural_midi_engine import generate_procedural_midi
        # spec.style peut être une liste ou une chaîne selon la source JSON
        raw_style = spec.style or "default"
        style_str = raw_style[0] if isinstance(raw_style, list) else raw_style
        return generate_procedural_midi(
            output_path=output_path,
            role=role,
            key=spec.key or "C",
            tempo_bpm=spec.tempo_bpm,
            style=style_str,
            total_bars=spec.total_bars,
            ticks_per_beat=spec.ticks_per_beat,
            sections=spec.sections,
        )

    def generate_all_tracks(
        self,
        tracks: List[TrackSpec],
        spec: SongSpec,
        midi_dir: Path,
    ) -> Dict[str, Path]:
        """
        Génère tous les fichiers MIDI pour une liste de tracks.

        Returns:
            Dict {track_name: path_to_midi_file}
        """
        results: Dict[str, Path] = {}
        for track_spec in tracks:
            out_path = midi_dir / Path(track_spec.midi_file).name
            try:
                path = self.generate_track(track_spec.role, spec, out_path)
                results[track_spec.name] = path
            except Exception as e:
                logger.error("Erreur génération MIDI pour %s: %s", track_spec.name, e)
                raise
        return results


def song_to_spec(song_dict: dict, sections_list: list) -> SongSpec:
    """
    Convertit un dict Song + liste de sections en SongSpec.
    Entrée compatible avec les modèles Pydantic de maestro-cli.
    """
    style = song_dict.get("style", "gospel")
    key = song_dict.get("key", "C")
    tempo = song_dict.get("tempo_bpm", 92)
    total_bars = song_dict.get("target_bars", 32)
    ts_str = song_dict.get("time_signature", "4/4")
    try:
        num, denom = map(int, ts_str.split("/"))
    except Exception:
        num, denom = 4, 4

    constraints = song_dict.get("constraints", {})
    if isinstance(constraints, dict):
        swing = float(constraints.get("swing", 0.0))
        humanize = float(constraints.get("humanize_amount", 0.06))
    else:
        swing = float(getattr(constraints, "swing", 0.0))
        humanize = float(getattr(constraints, "humanize_amount", 0.06))

    return SongSpec(
        key=key,
        tempo_bpm=tempo,
        time_signature=(num, denom),
        style=style,
        ticks_per_beat=480,
        total_bars=total_bars,
        sections=sections_list,
        swing=swing,
        humanize=humanize,
    )
