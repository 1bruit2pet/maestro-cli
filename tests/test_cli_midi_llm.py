import pytest
from typer.testing import CliRunner
from maestro_cli.cli import app

runner = CliRunner()

def test_cli_infill_command():
    result = runner.invoke(app, ["infill", "-p", "test_song", "--track", "bass", "--bars", "1-4"])
    assert result.exit_code == 0
    assert "Infilling track 'bass'" in result.output
    assert "Infilled" in result.output
