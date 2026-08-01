import pytest
from pathlib import Path
import mido
from maestro_cli.tuneflow_adapter import JJazzLabStyleRule, TuneFlowPluginAdapter

def test_jjazzlab_style_generator(tmp_path):
    generator = JJazzLabStyleRule(style_name="gospel_worship")
    mid = generator.generate_backing_track(["Fm9", "DbMaj7"], bars=4)
    assert len(mid.tracks) == 2

def test_tuneflow_plugin_adapter(tmp_path):
    input_midi = tmp_path / "input.mid"
    output_midi = tmp_path / "output.mid"
    
    mid = mido.MidiFile()
    track = mido.MidiTrack()
    mid.tracks.append(track)
    track.append(mido.Message('note_on', note=60, velocity=80, time=0))
    track.append(mido.Message('note_off', note=60, velocity=0, time=480))
    mid.save(input_midi)
    
    adapter = TuneFlowPluginAdapter()
    res_path = adapter.process_song_clip(input_midi, output_midi)
    assert res_path.exists()
