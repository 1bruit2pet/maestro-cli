"""
Tests du MidiEngine — vérifie que les fichiers MIDI générés sont valides.
"""

import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def spec():
    from maestro_cli.midi_engine import SongSpec
    return SongSpec(
        key="F minor",
        tempo_bpm=92,
        style="gospel",
        total_bars=32,
        sections=[
            {"id": "intro", "bars": 8, "density": "low", "energy": 0.3},
            {"id": "verse", "bars": 16, "density": "medium", "energy": 0.6},
            {"id": "chorus", "bars": 8, "density": "high", "energy": 0.9},
        ],
    )


@pytest.fixture
def engine():
    from maestro_cli.midi_engine import MidiEngine
    return MidiEngine(seed=42)


class TestMidiEngine:
    ROLES = ["drums", "bass", "keys", "pad", "lead"]

    def test_generate_all_roles(self, engine, spec):
        """Chaque rôle doit produire un .mid non vide."""
        with tempfile.TemporaryDirectory() as tmpdir:
            for role in self.ROLES:
                out = Path(tmpdir) / f"{role}.mid"
                result = engine.generate_track(role, spec, out)
                assert out.exists(), f"Fichier manquant pour {role}"
                assert out.stat().st_size > 50, f"Fichier trop petit pour {role}"

    def test_midi_file_valid(self, engine, spec):
        """Les fichiers MIDI générés doivent être lisibles par mido."""
        import mido
        with tempfile.TemporaryDirectory() as tmpdir:
            out = Path(tmpdir) / "keys.mid"
            engine.generate_track("keys", spec, out)
            mid = mido.MidiFile(str(out))
            assert mid.ticks_per_beat == 480
            assert len(mid.tracks) >= 2  # tempo track + note track

    def test_drums_notes_present(self, engine, spec):
        """La batterie doit contenir des notes on/off."""
        import mido
        with tempfile.TemporaryDirectory() as tmpdir:
            out = Path(tmpdir) / "drums.mid"
            engine.generate_track("drums", spec, out)
            mid = mido.MidiFile(str(out))
            note_on_count = sum(
                1 for track in mid.tracks
                for msg in track
                if msg.type == "note_on" and msg.velocity > 0
            )
            assert note_on_count > 10, "Pas assez de notes de batterie"

    def test_reproducible_with_seed(self, spec):
        """Même seed → mêmes fichiers MIDI."""
        from maestro_cli.midi_engine import MidiEngine
        with tempfile.TemporaryDirectory() as tmpdir:
            for i in range(2):
                out = Path(tmpdir) / f"bass_{i}.mid"
                MidiEngine(seed=99).generate_track("bass", spec, out)
            data0 = (Path(tmpdir) / "bass_0.mid").read_bytes()
            data1 = (Path(tmpdir) / "bass_1.mid").read_bytes()
            assert data0 == data1, "Les fichiers diffèrent malgré la même seed"

    def test_generate_all_tracks_batch(self, engine, spec):
        """generate_all_tracks doit retourner un dict complet."""
        from maestro_cli.midi_engine import TrackSpec
        track_specs = [
            TrackSpec(name=f"{r}_main", role=r, midi_file=f"midi/{r}.mid")
            for r in ["drums", "bass", "keys"]
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            results = engine.generate_all_tracks(track_specs, spec, Path(tmpdir))
            assert len(results) == 3
            for name, path in results.items():
                assert Path(path).exists()

    def test_parse_key_variants(self):
        """parse_key doit gérer différentes notations."""
        from maestro_cli.midi_engine import parse_key
        cases = [
            ("C", 0, "major"),
            ("F minor", 5, "minor"),
            ("G#", 8, "major"),
            ("Bb major", 10, "major"),
            ("D# minor", 3, "minor"),
        ]
        for key_str, expected_root, expected_mode in cases:
            root, mode = parse_key(key_str)
            assert root == expected_root, f"{key_str}: root {root} != {expected_root}"
            assert mode == expected_mode, f"{key_str}: mode {mode} != {expected_mode}"

    def test_song_to_spec(self):
        """song_to_spec doit convertir correctement un dict Song."""
        from maestro_cli.midi_engine import song_to_spec
        song_dict = {
            "key": "C# minor",
            "tempo_bpm": 110,
            "style": ["afrobeats"],
            "target_bars": 64,
            "time_signature": "6/8",
            "constraints": {"swing": 0.1, "humanize_amount": 0.08},
        }
        sections = [{"id": "main", "bars": 64, "density": "high", "energy": 0.8}]
        spec = song_to_spec(song_dict, sections)
        assert spec.tempo_bpm == 110
        assert spec.key == "C# minor"
        assert spec.time_signature == (6, 8)
        assert spec.swing == pytest.approx(0.1)
