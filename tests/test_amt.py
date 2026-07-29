import pytest
from maestro_cli.amt_tokenizer import AMTTokenizer, NoteEvent

def test_amt_token_encode_decode():
    tokenizer = AMTTokenizer(time_step_ms=10)
    
    notes = [
        NoteEvent(onset=0.0, duration=0.5, pitch=60, velocity=90, instrument="piano"),
        NoteEvent(onset=0.5, duration=0.25, pitch=64, velocity=85, instrument="bass"),
    ]
    
    token_str = tokenizer.encode_notes(notes)
    assert "ONSET_0" in token_str
    assert "PITCH_60" in token_str
    assert "INST_piano" in token_str
    assert "VEL_90" in token_str
    
    decoded_notes = tokenizer.decode_tokens(token_str)
    assert len(decoded_notes) == 2
    assert decoded_notes[0].pitch == 60
    assert decoded_notes[0].instrument == "piano"
    assert decoded_notes[0].onset == 0.0
    assert decoded_notes[1].pitch == 64
    assert decoded_notes[1].instrument == "bass"
    assert decoded_notes[1].onset == 0.5
