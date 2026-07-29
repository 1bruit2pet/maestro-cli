import pytest
from maestro_cli.midi_llm_provider import MockMidiLLMProvider, VllmMidiProvider

def test_mock_midi_llm_provider():
    provider = MockMidiLLMProvider()
    tokens = provider.generate_midi_tokens("Create a funk bassline")
    assert "ONSET_0" in tokens
    assert "INST_piano" in tokens

    notes = provider.generate_notes("Create a funk bassline")
    assert len(notes) > 0
    assert notes[0].pitch == 60
    assert notes[0].instrument == "piano"

def test_vllm_fallback_when_offline():
    provider = VllmMidiProvider(api_url="http://localhost:9999/v1")
    tokens = provider.generate_midi_tokens("Create gospel progression")
    assert "ONSET_0" in tokens
    assert "PITCH_60" in tokens
