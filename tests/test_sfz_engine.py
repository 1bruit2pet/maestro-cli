import pytest
from pathlib import Path
from maestro_cli.hosts.sfz_engine import SFZRenderEngine

def test_sfz_engine_fallback(tmp_path):
    engine = SFZRenderEngine()
    midi_file = tmp_path / "test.mid"
    output_wav = tmp_path / "output.wav"
    
    # Create valid dummy MIDI file
    import mido
    mid = mido.MidiFile()
    track = mido.MidiTrack()
    mid.tracks.append(track)
    track.append(mido.Message('note_on', note=60, velocity=80, time=0))
    track.append(mido.Message('note_off', note=60, velocity=0, time=480))
    mid.save(midi_file)

    # Render WAV using SF2 fallback
    result_wav = engine.render_sf2(midi_file, Path("/non/existent/sf2"), output_wav)
    assert result_wav.exists()
    assert result_wav.stat().st_size > 0
