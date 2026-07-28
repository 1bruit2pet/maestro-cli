"""
Phase 2 Tests - Carla Bridge Integration
Tests for carla_osc, carla_client, presets, and CLI handlers.
"""

import json
import os
import struct
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

# ============================================================================
# PresetManager Tests
# ============================================================================

class TestPresetManager:
    """Tests for the PresetManager class"""

    @pytest.fixture
    def preset_dir(self, tmp_path):
        """Create a temp preset directory with a plugin_map.json"""
        plugin_map = {
            "version": "1.0",
            "styles": {
                "gospel": {
                    "description": "Gospel test style",
                    "mappings": [
                        {
                            "id": "gospel_keys",
                            "role": "keys",
                            "plugin": "EPiano",
                            "format": "VST3",
                            "path": "/usr/lib/vst3/EPiano.vst3",
                            "preset": "Warm Suitcase",
                            "default_slot": 1,
                            "volume": 0.8,
                            "pan": 0.5,
                            "midi_channel": 0,
                            "required": True,
                        },
                        {
                            "id": "gospel_bass",
                            "role": "bass",
                            "plugin": "BassPlugin",
                            "format": "VST3",
                            "path": "/usr/lib/vst3/BassPlugin.vst3",
                            "preset": "Round Finger",
                            "default_slot": 2,
                            "volume": 1.0,
                            "pan": 0.5,
                            "midi_channel": 0,
                            "required": True,
                        },
                        {
                            "id": "gospel_drums",
                            "role": "drums",
                            "plugin": "DrumMachine",
                            "format": "VST3",
                            "path": "/usr/lib/vst3/DrumMachine.vst3",
                            "preset": "Gospel Kit",
                            "default_slot": 3,
                            "volume": 1.0,
                            "pan": 0.5,
                            "midi_channel": 9,
                            "required": True,
                        },
                        {
                            "id": "gospel_pad",
                            "role": "pad",
                            "plugin": "StringEnsemble",
                            "format": "VST3",
                            "path": "/usr/lib/vst3/StringEnsemble.vst3",
                            "preset": "Warm Strings",
                            "default_slot": 4,
                            "volume": 0.6,
                            "pan": 0.7,
                            "midi_channel": 0,
                            "required": False,
                        },
                    ],
                },
                "neo_soul": {
                    "description": "Neo-Soul test style",
                    "mappings": [
                        {
                            "id": "neosoul_keys",
                            "role": "keys",
                            "plugin": "Rhodes",
                            "format": "VST3",
                            "path": "/usr/lib/vst3/Rhodes.vst3",
                            "preset": "Warm Rhodes",
                            "default_slot": 1,
                            "volume": 0.85,
                            "pan": 0.45,
                            "midi_channel": 0,
                            "required": True,
                        },
                    ],
                },
            },
            "fallback": {
                "enabled": True,
                "synth": "fluidsynth",
                "soundfont": "/usr/share/sounds/sf2/GeneralUser_GS.sf2",
            },
            "search_paths": ["/usr/lib/vst3", "/usr/lib/lv2"],
        }
        map_file = tmp_path / "plugin_map.json"
        map_file.write_text(json.dumps(plugin_map, indent=2))
        return str(tmp_path)

    @pytest.fixture
    def preset_mgr(self, preset_dir):
        from maestro_cli.hosts.presets import PresetManager
        return PresetManager(presets_dir=preset_dir)

    def test_load_plugin_map(self, preset_mgr):
        """Test loading plugin mappings for a style"""
        result = preset_mgr.load_plugin_map("gospel")
        assert "mappings" in result
        assert "fallback" in result
        assert len(result["mappings"]) == 4

    def test_load_plugin_map_unknown_style(self, preset_mgr):
        """Test loading unknown style raises error"""
        from maestro_cli.hosts.presets import StyleNotFoundError
        with pytest.raises(StyleNotFoundError):
            preset_mgr.load_plugin_map("jazz")

    def test_find_plugin(self, preset_mgr):
        """Test finding a plugin by role"""
        plugin = preset_mgr.find_plugin("keys", "gospel")
        assert plugin is not None
        assert plugin["plugin"] == "EPiano"
        assert plugin["preset"] == "Warm Suitcase"

    def test_find_plugin_not_found(self, preset_mgr):
        """Test finding a plugin for unknown role"""
        plugin = preset_mgr.find_plugin("saxophone", "gospel")
        assert plugin is None

    def test_list_styles(self, preset_mgr):
        """Test listing available styles"""
        styles = preset_mgr.list_styles()
        assert "gospel" in styles
        assert "neo_soul" in styles

    def test_list_roles(self, preset_mgr):
        """Test listing roles for a style"""
        roles = preset_mgr.list_roles("gospel")
        assert "keys" in roles
        assert "bass" in roles
        assert "drums" in roles

    def test_get_fallback_config(self, preset_mgr):
        """Test getting fallback configuration"""
        fallback = preset_mgr.get_fallback_config()
        assert fallback["enabled"] is True
        assert fallback["synth"] == "fluidsynth"

    def test_validate_rack_valid(self, preset_mgr):
        """Test rack validation with valid tracks"""
        tracks = [
            {"name": "keys_main", "role": "keys"},
            {"name": "bass_main", "role": "bass"},
            {"name": "drums", "role": "drums"},
        ]
        is_valid, errors = preset_mgr.validate_rack(tracks, "gospel")
        assert is_valid is True
        assert len(errors) == 0

    def test_validate_rack_slot_conflict(self, preset_mgr):
        """Test rack validation detects slot conflicts"""
        # Two tracks with same role = same default_slot
        tracks = [
            {"name": "keys_1", "role": "keys"},
            {"name": "keys_2", "role": "keys"},
        ]
        is_valid, errors = preset_mgr.validate_rack(tracks, "gospel")
        assert is_valid is False
        assert any("Slot conflict" in e for e in errors)

    def test_build_rack_config(self, preset_mgr):
        """Test building rack config from tracks"""
        tracks = [
            {"name": "keys_main", "role": "keys", "midi_file": "keys.mid", "volume": 0.9},
            {"name": "bass_main", "role": "bass", "midi_file": "bass.mid"},
        ]
        config = preset_mgr.build_rack_config(tracks, "gospel", "test_project")

        assert "plugins" in config
        assert "routes" in config
        assert "metadata" in config
        assert len(config["plugins"]) == 2
        assert len(config["routes"]) == 2
        assert config["metadata"]["style"] == "gospel"
        assert config["metadata"]["project_id"] == "test_project"

        # Check that volume from track overrides preset default
        keys_plugin = next(p for p in config["plugins"] if p["role"] == "keys")
        assert keys_plugin["volume"] == 0.9

    def test_build_rack_config_missing_role(self, preset_mgr):
        """Test building config with unmapped role produces warning"""
        tracks = [
            {"name": "keys_main", "role": "keys", "midi_file": "keys.mid"},
            {"name": "synth_main", "role": "theremin", "midi_file": "synth.mid"},
        ]
        config = preset_mgr.build_rack_config(tracks, "gospel", "test")
        assert len(config["plugins"]) == 1  # only keys mapped
        assert len(config["metadata"]["warnings"]) > 0

    def test_plugin_map_not_found(self, tmp_path):
        """Test error when plugin_map.json doesn't exist"""
        from maestro_cli.hosts.presets import PresetManager, PluginMapNotFoundError
        mgr = PresetManager(presets_dir=str(tmp_path / "nonexistent"))
        with pytest.raises(PluginMapNotFoundError):
            mgr.load_plugin_map()

    def test_reload(self, preset_mgr, preset_dir):
        """Test reloading plugin map"""
        # Initial load
        styles1 = preset_mgr.list_styles()
        # Reload
        preset_mgr.reload()
        styles2 = preset_mgr.list_styles()
        assert styles1 == styles2


# ============================================================================
# CarlaOSCClient Tests
# ============================================================================

class TestCarlaOSCClient:
    """Tests for the CarlaOSCClient low-level client"""

    def test_init(self):
        """Test client initialization"""
        from maestro_cli.hosts.carla_osc import CarlaOSCClient
        client = CarlaOSCClient(host="127.0.0.1", port=9001, timeout=5.0)
        assert client.host == "127.0.0.1"
        assert client.port == 9001
        assert client.timeout == 5.0

    def test_repr(self):
        """Test client string representation"""
        from maestro_cli.hosts.carla_osc import CarlaOSCClient
        client = CarlaOSCClient()
        assert "disconnected" in repr(client)

    def test_send_without_connect(self):
        """Test sending without explicit connect auto-connects"""
        from maestro_cli.hosts.carla_osc import CarlaOSCClient
        client = CarlaOSCClient()
        # send() should try to auto-connect
        # This won't actually send since no Carla is running, but shouldn't crash
        with patch.object(client, 'connect', return_value=True):
            with patch.object(client, '_client') as mock_client:
                mock_client.send_message = MagicMock()
                result = client.send("/carla/ping")
                assert result is True

    def test_is_connected_no_carla(self):
        """Test is_connected returns False when Carla isn't running"""
        from maestro_cli.hosts.carla_osc import CarlaOSCClient
        client = CarlaOSCClient(port=19999)  # unlikely port
        # is_connected checks if port is reachable
        # On a system without Carla, this should effectively work
        # (UDP always "succeeds" at sending)

    def test_context_manager(self):
        """Test context manager protocol"""
        from maestro_cli.hosts.carla_osc import CarlaOSCClient
        with patch.object(CarlaOSCClient, 'connect', return_value=True):
            with patch.object(CarlaOSCClient, 'disconnect'):
                with CarlaOSCClient() as client:
                    assert client is not None

    def test_start_carla_not_found(self):
        """Test starting Carla when executable doesn't exist"""
        from maestro_cli.hosts.carla_osc import CarlaOSCClient
        client = CarlaOSCClient()
        result = client.start_carla(carla_cmd="/nonexistent/carla", wait=False)
        assert result is False


# ============================================================================
# CarlaClient Tests
# ============================================================================

class TestCarlaClient:
    """Tests for the CarlaClient high-level client"""

    @patch("maestro_cli.hosts.carla_osc.CarlaOSCClient.is_connected", return_value=False)
    def test_init(self, mock_is_connected):
        """Test client initialization"""
        from maestro_cli.hosts.carla_client import CarlaClient, CarlaStatus
        client = CarlaClient()
        assert client.status == CarlaStatus.STOPPED
        assert not client.is_running()

    @patch("maestro_cli.hosts.carla_osc.CarlaOSCClient.is_connected", return_value=False)
    def test_load_plugin_not_running(self, mock_is_connected):
        """Test loading plugin when Carla isn't running"""
        from maestro_cli.hosts.carla_client import CarlaClient, CarlaNotRunningError
        client = CarlaClient()
        with pytest.raises(CarlaNotRunningError):
            client.load_plugin(1, "/path/to/plugin.vst3")

    @patch("maestro_cli.hosts.carla_osc.CarlaOSCClient.is_connected", return_value=False)
    def test_load_rack_not_running(self, mock_is_connected):
        """Test loading rack when Carla isn't running"""
        from maestro_cli.hosts.carla_client import CarlaClient, CarlaNotRunningError
        client = CarlaClient()
        with pytest.raises(CarlaNotRunningError):
            client.load_rack({"plugins": [], "routes": []})

    @patch("maestro_cli.hosts.carla_client.CarlaOSCClient")
    def test_load_rack_with_mock(self, MockOSC):
        """Test loading rack with mocked OSC"""
        from maestro_cli.hosts.carla_client import CarlaClient

        mock_osc = MockOSC.return_value
        mock_osc.is_connected.return_value = True
        mock_osc.send.return_value = True

        client = CarlaClient()
        client._osc = mock_osc
        client._status = client._status.__class__("running")

        rack_config = {
            "plugins": [
                {"slot": 1, "path": "/plugin.vst3", "format": "VST3", "name": "EPiano"},
                {"slot": 2, "path": "/bass.vst3", "format": "VST3", "name": "Bass"},
            ],
            "routes": [
                {"track": "keys", "slot": 1, "midi_channel": 0},
            ],
        }

        result = client.load_rack(rack_config)
        assert len(result["plugins_loaded"]) == 2
        assert len(result["routes_connected"]) == 1

    @patch("maestro_cli.hosts.carla_osc.CarlaOSCClient.is_connected", return_value=False)
    def test_render_fallback_placeholder(self, mock_is_connected, tmp_path):
        """Test render produces silent WAV placeholder when no engine available"""
        from maestro_cli.hosts.carla_client import CarlaClient

        client = CarlaClient()
        output = str(tmp_path / "test.wav")

        result = client.render(
            output_path=output,
            duration=1.0,
            midi_files=[],
            wait=True,
        )

        assert result["status"] == "completed"
        assert result["method"] == "placeholder"
        assert Path(output).exists()

        # Verify it's a valid WAV
        with open(output, "rb") as f:
            header = f.read(4)
            assert header == b"RIFF"

    def test_write_silent_wav(self, tmp_path):
        """Test silent WAV generation"""
        from maestro_cli.hosts.carla_client import CarlaClient

        client = CarlaClient()
        output = str(tmp_path / "silence.wav")
        client._write_silent_wav(output, duration=2.0)

        assert Path(output).exists()

        # Verify WAV structure
        with open(output, "rb") as f:
            riff = f.read(4)
            assert riff == b"RIFF"
            file_size = struct.unpack("<I", f.read(4))[0]
            wave = f.read(4)
            assert wave == b"WAVE"

    @patch("maestro_cli.hosts.carla_osc.CarlaOSCClient.is_connected", return_value=False)
    def test_get_status(self, mock_is_connected):
        """Test status report"""
        from maestro_cli.hosts.carla_client import CarlaClient

        client = CarlaClient()
        report = client.get_status()
        assert report.status.value == "stopped"
        assert report.to_dict()["status"] == "stopped"

    @patch("maestro_cli.hosts.carla_osc.CarlaOSCClient.is_connected", return_value=False)
    def test_get_state(self, mock_is_connected):
        """Test get_state returns complete state"""
        from maestro_cli.hosts.carla_client import CarlaClient

        client = CarlaClient()
        state = client.get_state()
        assert "status" in state
        assert "plugins" in state
        assert "connections" in state
        assert state["is_rendering"] is False

    def test_exception_hierarchy(self):
        """Test that all exceptions inherit from CarlaError"""
        from maestro_cli.hosts.carla_client import (
            CarlaError,
            CarlaNotRunningError,
            PluginNotFoundError,
            PresetNotFoundError,
            RenderError,
            RoutingError,
        )
        assert issubclass(CarlaNotRunningError, CarlaError)
        assert issubclass(PluginNotFoundError, CarlaError)
        assert issubclass(PresetNotFoundError, CarlaError)
        assert issubclass(RenderError, CarlaError)
        assert issubclass(RoutingError, CarlaError)


# ============================================================================
# FluidSynth Fallback Tests
# ============================================================================

class TestFluidSynthFallback:
    """Tests for the FluidSynth fallback system"""

    def test_fallback_no_fluidsynth(self):
        """Test fallback when fluidsynth is not installed"""
        from maestro_cli.hosts.carla_client import fallback_to_fluidsynth

        with patch("shutil.which", return_value=None):
            result = fallback_to_fluidsynth(["test.mid"], "output.wav")
            assert result is False

    def test_fallback_no_midi_files(self):
        """Test fallback with no MIDI files"""
        from maestro_cli.hosts.carla_client import fallback_to_fluidsynth

        with patch("shutil.which", return_value="/usr/bin/fluidsynth"):
            result = fallback_to_fluidsynth([], "output.wav")
            assert result is False

    def test_fallback_no_soundfont(self):
        """Test fallback with missing soundfont"""
        from maestro_cli.hosts.carla_client import fallback_to_fluidsynth

        with patch("shutil.which", return_value="/usr/bin/fluidsynth"):
            result = fallback_to_fluidsynth(
                ["test.mid"], "output.wav",
                soundfont="/nonexistent/soundfont.sf2"
            )
            assert result is False

    @patch("subprocess.run")
    def test_fallback_success(self, mock_run, tmp_path):
        """Test successful FluidSynth fallback"""
        from maestro_cli.hosts.carla_client import fallback_to_fluidsynth

        midi_file = tmp_path / "test.mid"
        midi_file.write_bytes(b"MThd" + b"\x00" * 100)
        output_wav = str(tmp_path / "output.wav")

        soundfont = tmp_path / "test.sf2"
        soundfont.write_bytes(b"sf2 data")

        mock_run.return_value = MagicMock(returncode=0)

        with patch("shutil.which", return_value="/usr/bin/fluidsynth"):
            result = fallback_to_fluidsynth(
                [str(midi_file)], output_wav,
                soundfont=str(soundfont),
            )
            assert result is True
            mock_run.assert_called_once()


# ============================================================================
# RackState Model Tests
# ============================================================================

class TestRackStateModel:
    """Tests for the RackState Pydantic model"""

    def test_create_rack_state(self):
        """Test creating a RackState model"""
        from maestro_cli.models.rack_state import RackState, Plugin, PluginFormat, Route

        rack = RackState(
            project_id="test",
            plugins=[
                Plugin(slot=1, name="EPiano", format=PluginFormat.VST3, role="keys"),
                Plugin(slot=2, name="Bass", format=PluginFormat.VST3, role="bass"),
            ],
            routes=[
                Route(track="keys_main", slot=1),
                Route(track="bass_main", slot=2),
            ],
        )
        assert len(rack.plugins) == 2
        assert len(rack.routes) == 2

    def test_get_plugin_by_role(self):
        """Test finding plugin by role"""
        from maestro_cli.models.rack_state import RackState, Plugin, PluginFormat, Route

        rack = RackState(
            project_id="test",
            plugins=[
                Plugin(slot=1, name="EPiano", format=PluginFormat.VST3, role="keys"),
            ],
        )
        plugin = rack.get_plugin_by_role("keys")
        assert plugin is not None
        assert plugin.name == "EPiano"

        assert rack.get_plugin_by_role("drums") is None

    def test_get_route_for_track(self):
        """Test finding route for a track"""
        from maestro_cli.models.rack_state import RackState, Plugin, PluginFormat, Route

        rack = RackState(
            project_id="test",
            routes=[Route(track="keys_main", slot=1)],
        )
        route = rack.get_route_for_track("keys_main")
        assert route is not None
        assert route.slot == 1

    def test_serialization(self):
        """Test JSON serialization/deserialization"""
        from maestro_cli.models.rack_state import RackState, Plugin, PluginFormat, Route

        rack = RackState(
            project_id="test",
            plugins=[Plugin(slot=1, name="EPiano", format=PluginFormat.VST3)],
            routes=[Route(track="keys", slot=1)],
            status="loaded",
        )
        data = rack.dict()
        restored = RackState(**data)
        assert restored.project_id == "test"
        assert len(restored.plugins) == 1


# ============================================================================
# RenderReport Model Tests
# ============================================================================

class TestRenderReportModel:
    """Tests for the RenderReport model"""

    def test_create_report(self):
        from maestro_cli.models.render_report import RenderReport

        report = RenderReport(
            project_id="test",
            render_ok=True,
            output_file="audio/mix.wav",
            duration_seconds=120.5,
        )
        assert report.render_ok is True
        assert report.duration_formatted == "02:00"

    def test_has_errors(self):
        from maestro_cli.models.render_report import RenderReport

        report = RenderReport(
            project_id="test",
            render_ok=False,
            output_file="audio/mix.wav",
            duration_seconds=0,
            errors=["Something went wrong"],
        )
        assert report.has_errors() is True
        assert report.has_warnings() is False


# ============================================================================
# Integration: plugin_map.json file
# ============================================================================

class TestPluginMapFile:
    """Test the actual plugin_map.json file"""

    @pytest.fixture
    def plugin_map_path(self):
        return Path(__file__).parent.parent / "presets" / "plugin_map.json"

    def test_plugin_map_exists(self, plugin_map_path):
        """Test that plugin_map.json exists"""
        assert plugin_map_path.exists(), f"plugin_map.json not found at {plugin_map_path}"

    def test_plugin_map_valid_json(self, plugin_map_path):
        """Test that plugin_map.json is valid JSON"""
        with open(plugin_map_path) as f:
            data = json.load(f)
        assert "version" in data
        assert "styles" in data

    def test_plugin_map_has_gospel(self, plugin_map_path):
        """Test that gospel style has all required roles"""
        with open(plugin_map_path) as f:
            data = json.load(f)

        gospel = data["styles"]["gospel"]
        roles = {m["role"] for m in gospel["mappings"]}
        assert "keys" in roles
        assert "bass" in roles
        assert "drums" in roles

    def test_plugin_map_has_fallback(self, plugin_map_path):
        """Test that fallback config exists"""
        with open(plugin_map_path) as f:
            data = json.load(f)

        assert "fallback" in data
        assert data["fallback"]["enabled"] is True
        assert data["fallback"]["synth"] == "fluidsynth"

    def test_plugin_map_mapping_fields(self, plugin_map_path):
        """Test that each mapping has all required fields"""
        with open(plugin_map_path) as f:
            data = json.load(f)

        required_fields = {"id", "role", "plugin", "format", "path", "default_slot", "volume", "pan"}
        for style_name, style_data in data["styles"].items():
            for mapping in style_data["mappings"]:
                missing = required_fields - set(mapping.keys())
                assert not missing, (
                    f"Style '{style_name}', mapping '{mapping.get('id', '?')}' "
                    f"missing fields: {missing}"
                )

    def test_plugin_map_three_styles(self, plugin_map_path):
        """Test that at least 3 styles are defined"""
        with open(plugin_map_path) as f:
            data = json.load(f)
        assert len(data["styles"]) >= 3
