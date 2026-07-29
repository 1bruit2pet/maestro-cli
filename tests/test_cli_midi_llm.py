import pytest
from typer.testing import CliRunner
from maestro_cli.cli import app
from pathlib import Path

runner = CliRunner()

def test_cli_infill_command():
    result = runner.invoke(app, ["infill", "-p", "test_song", "--track", "bass", "--bars", "1-4"])
    assert result.exit_code == 0
    assert "Infilling track 'bass'" in result.output

def test_cli_transcribe_command(tmp_path):
    audio = tmp_path / "test.wav"
    audio.write_bytes(b"RIFF....WAVEfmt ")
    result = runner.invoke(app, ["transcribe", "-i", str(audio), "-p", "test_song", "-m", "small"])
    assert result.exit_code == 0
    assert "Transcribing Audio with MuScriptor" in result.output

def test_cli_edit_transpose():
    result = runner.invoke(app, ["edit", "transpose", "-p", "test_song", "-t", "bass", "-s", "+2"])
    assert result.exit_code == 0
    assert "Transposed track 'bass'" in result.output

def test_cli_edit_quantize():
    result = runner.invoke(app, ["edit", "quantize", "-p", "test_song", "-t", "drums", "-g", "1/16"])
    assert result.exit_code == 0
    assert "Quantized track 'drums'" in result.output

def test_cli_analyze():
    result = runner.invoke(app, ["analyze", "-p", "test_song"])
    assert result.exit_code == 0
    assert "Analyzing musical features" in result.output

def test_cli_humanize():
    result = runner.invoke(app, ["humanize", "-p", "test_song", "-t", "piano", "-g", "funk"])
    assert result.exit_code == 0
    assert "Applying ML Humanization" in result.output

def test_cli_sing():
    result = runner.invoke(app, ["sing", "-p", "test_song", "-t", "vocal", "-v", "gospel_lead"])
    assert result.exit_code == 0
    assert "Rendering Singing Voice" in result.output
