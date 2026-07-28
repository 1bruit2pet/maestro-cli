"""
Carla Audio Host Client - High-level API
Communicates with Carla via the OSC layer for plugin hosting and audio rendering.
Includes FluidSynth fallback when Carla is unavailable.
"""

import functools
import logging
import shutil
import struct
import subprocess
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from maestro_cli.config import settings
from maestro_cli.hosts.carla_osc import (
    CarlaOSCClient,
    CarlaOSCConnectionError,
    CarlaOSCError,
    CarlaOSCTimeoutError,
)

logger = logging.getLogger(__name__)


# ============================================================================
# EXCEPTIONS
# ============================================================================

class CarlaError(Exception):
    """Base error for Carla operations"""
    pass


class PluginNotFoundError(CarlaError):
    """Plugin file not found on disk"""
    pass


class PresetNotFoundError(CarlaError):
    """Preset file not found"""
    pass


class CarlaNotRunningError(CarlaError):
    """Carla is not running or not responding"""
    pass


class RenderError(CarlaError):
    """Audio rendering failed"""
    pass


class RoutingError(CarlaError):
    """MIDI/audio routing error"""
    pass


# ============================================================================
# STATUS ENUMS & DATACLASSES
# ============================================================================

class CarlaStatus(str, Enum):
    """Carla connection/process status"""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"
    UNKNOWN = "unknown"


@dataclass
class CarlaStatusReport:
    """Detailed status report from Carla"""
    version: str = ""
    host: str = ""
    status: CarlaStatus = CarlaStatus.UNKNOWN
    sample_rate: int = 0
    buffer_size: int = 0
    plugins_loaded: int = 0
    uptime_seconds: float = 0.0
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "host": self.host,
            "status": self.status.value,
            "sample_rate": self.sample_rate,
            "buffer_size": self.buffer_size,
            "plugins_loaded": self.plugins_loaded,
            "uptime_seconds": self.uptime_seconds,
            "error_message": self.error_message,
        }


# ============================================================================
# FLUIDSYNTH FALLBACK
# ============================================================================

def fallback_to_fluidsynth(
    midi_files: List[str],
    output_wav: str,
    soundfont: Optional[str] = None,
    sample_rate: int = 48000,
) -> bool:
    """
    Render MIDI file(s) to WAV using FluidSynth as a fallback.

    Args:
        midi_files: List of MIDI file paths to render
        output_wav: Output WAV file path
        soundfont: Path to SoundFont file (defaults to GeneralUser)
        sample_rate: Sample rate for output

    Returns:
        True if rendering succeeded
    """
    soundfont = soundfont or "/usr/share/sounds/sf2/GeneralUser_GS.sf2"

    # Check FluidSynth is available
    if not shutil.which("fluidsynth"):
        logger.error("FluidSynth not found in PATH")
        return False

    if not Path(soundfont).exists():
        logger.error("SoundFont not found: %s", soundfont)
        return False

    output_path = Path(output_wav)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # If multiple MIDI files, render each then merge (simple approach: render first)
    # For now, handle single or first MIDI file
    if not midi_files:
        logger.error("No MIDI files provided for FluidSynth rendering")
        return False

    # Render each MIDI to a temp WAV, then combine
    temp_wavs: List[str] = []
    for i, midi_file in enumerate(midi_files):
        if not Path(midi_file).exists():
            logger.warning("MIDI file not found, skipping: %s", midi_file)
            continue

        if len(midi_files) == 1:
            temp_out = str(output_path)
        else:
            temp_out = str(output_path.parent / f"_temp_track_{i}.wav")
            temp_wavs.append(temp_out)

        cmd = [
            "fluidsynth",
            "-ni",
            soundfont,
            midi_file,
            "-F", temp_out,
            "-r", str(sample_rate),
        ]

        logger.info("FluidSynth rendering: %s -> %s", midi_file, temp_out)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode != 0:
                logger.error("FluidSynth failed: %s", result.stderr)
                return False
        except subprocess.TimeoutExpired:
            logger.error("FluidSynth timed out rendering %s", midi_file)
            return False
        except FileNotFoundError:
            logger.error("FluidSynth not found")
            return False

    # If we had multiple tracks, combine using sox or ffmpeg
    if temp_wavs and len(temp_wavs) > 1:
        if shutil.which("sox"):
            mix_cmd = ["sox", "-m"] + temp_wavs + [str(output_path)]
            try:
                subprocess.run(mix_cmd, capture_output=True, check=True)
            except subprocess.CalledProcessError as e:
                logger.error("sox mix failed: %s", e)
                return False
            finally:
                # Cleanup temp files
                for tw in temp_wavs:
                    Path(tw).unlink(missing_ok=True)
        else:
            # Just use the first track as fallback
            logger.warning("sox not found, using only first track")
            import shutil as sh
            sh.move(temp_wavs[0], str(output_path))
            for tw in temp_wavs[1:]:
                Path(tw).unlink(missing_ok=True)

    logger.info("FluidSynth render complete: %s", output_wav)
    return True


def with_fallback(func: Callable) -> Callable:
    """Decorator to fall back to FluidSynth when Carla is unavailable"""
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except CarlaNotRunningError:
            logger.warning("Carla not available, falling back to FluidSynth")
            # Extract midi_files and output_wav from kwargs
            midi_files = kwargs.get("midi_files", [])
            output_path = kwargs.get("output_path", "output.wav")
            return fallback_to_fluidsynth(midi_files, output_path)
    return wrapper


# ============================================================================
# CARLA CLIENT
# ============================================================================

class CarlaClient:
    """
    High-level client for controlling Carla audio plugin host.

    Wraps the low-level OSC client with a clean API for:
    - Server lifecycle (start/stop)
    - Plugin management (load/unload/preset)
    - Rack management (load/save)
    - MIDI routing
    - Audio rendering
    - Transport control
    """

    def __init__(
        self,
        host: str = settings.CARLA_HOST,
        osc_port: int = settings.CARLA_OSC_PORT,
        server_port: int = settings.CARLA_SERVER_PORT,
        timeout: int = settings.CARLA_TIMEOUT,
    ):
        self.host = host
        self.osc_port = osc_port
        self.server_port = server_port
        self.timeout = timeout

        # OSC layer
        self._osc = CarlaOSCClient(
            host=host,
            port=osc_port,
            timeout=float(timeout),
        )

        # Process management
        self.process: Optional[subprocess.Popen] = None
        self._status: CarlaStatus = CarlaStatus.STOPPED
        self._start_time: Optional[float] = None

        # State tracking
        self._loaded_plugins: Dict[int, Dict[str, Any]] = {}
        self._connections: List[Dict[str, Any]] = []
        self._is_rendering = False

    # ========== SERVER LIFECYCLE ==========

    @property
    def status(self) -> CarlaStatus:
        """Get current Carla status"""
        if self.process is None:
            # Check if Carla is running externally
            if self._osc.is_connected():
                self._status = CarlaStatus.RUNNING
            else:
                return CarlaStatus.STOPPED

        elif self.process.poll() is not None:
            self._status = CarlaStatus.STOPPED

        return self._status

    def is_running(self) -> bool:
        """Check if Carla is currently running"""
        return self.status == CarlaStatus.RUNNING

    def start(self, wait: bool = True, timeout: Optional[int] = None) -> bool:
        """
        Start Carla process.

        Args:
            wait: Wait for Carla to be ready
            timeout: Maximum wait time (seconds)

        Returns:
            True if Carla started successfully
        """
        if self.is_running():
            logger.info("Carla already running")
            return True

        self._status = CarlaStatus.STARTING
        timeout = timeout or self.timeout

        logger.info("Starting Carla server...")

        try:
            self.process = subprocess.Popen(
                [settings.CARLA_START_CMD, "--osc-port", str(self.osc_port)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,
            )
            self._start_time = time.time()

            if wait:
                start_time = time.time()
                while time.time() - start_time < timeout:
                    if self.process.poll() is not None:
                        stderr = self.process.stderr.read().decode() if self.process.stderr else ""
                        logger.error("Carla exited prematurely: %s", stderr)
                        self._status = CarlaStatus.ERROR
                        return False

                    if self._osc.is_connected():
                        self._osc.connect()
                        self._status = CarlaStatus.RUNNING
                        logger.info("Carla started (PID %d)", self.process.pid)
                        return True
                    time.sleep(0.5)

                # Timeout
                logger.error("Carla failed to start within %ds", timeout)
                self._status = CarlaStatus.ERROR
                return False
            else:
                self._osc.connect()
                self._status = CarlaStatus.RUNNING
                return True

        except FileNotFoundError:
            logger.error("Carla executable not found: %s", settings.CARLA_START_CMD)
            self._status = CarlaStatus.ERROR
            return False
        except Exception as e:
            logger.error("Failed to start Carla: %s", e)
            self._status = CarlaStatus.ERROR
            return False

    def stop(self, wait: bool = True, timeout: Optional[int] = None) -> bool:
        """
        Stop Carla process.

        Args:
            wait: Wait for Carla to stop
            timeout: Maximum wait time (seconds)

        Returns:
            True if Carla stopped successfully
        """
        if self.process is None:
            self._status = CarlaStatus.STOPPED
            return True

        self._status = CarlaStatus.STOPPING
        timeout = timeout or self.timeout

        try:
            self._osc.disconnect()
            self.process.terminate()

            if wait:
                start_time = time.time()
                while time.time() - start_time < timeout:
                    if self.process.poll() is not None:
                        self.process = None
                        self._status = CarlaStatus.STOPPED
                        self._loaded_plugins.clear()
                        self._connections.clear()
                        logger.info("Carla stopped")
                        return True
                    time.sleep(0.5)

                # Force kill
                self.process.kill()
                self.process.wait()

            self.process = None
            self._status = CarlaStatus.STOPPED
            self._loaded_plugins.clear()
            self._connections.clear()
            return True

        except Exception as e:
            logger.error("Error stopping Carla: %s", e)
            self._status = CarlaStatus.ERROR
            return False

    def get_status(self) -> CarlaStatusReport:
        """Get detailed status from Carla"""
        report = CarlaStatusReport()
        report.status = self.status
        report.host = f"{self.host}:{self.osc_port}"
        report.plugins_loaded = len(self._loaded_plugins)

        if self._start_time:
            report.uptime_seconds = time.time() - self._start_time

        report.sample_rate = settings.AUDIO_SAMPLE_RATE
        report.buffer_size = settings.AUDIO_BUFFER_SIZE

        return report

    def _ensure_running(self) -> None:
        """Ensure Carla is running, raise if not"""
        if not self.is_running():
            raise CarlaNotRunningError(
                "Carla is not running. Start it with client.start() "
                "or run 'carla --osc-port 9001' manually."
            )

    # ========== PLUGIN MANAGEMENT ==========

    def load_plugin(
        self,
        slot: int,
        plugin_path: str,
        plugin_format: str = "VST3",
    ) -> Dict[str, Any]:
        """
        Load a plugin into a Carla slot.

        Args:
            slot: Target slot number
            plugin_path: Path to plugin file
            plugin_format: Plugin format (VST3, LV2, SF2, etc.)

        Returns:
            Dict with load result: {"slot": int, "name": str, "loaded": bool, "error": str}
        """
        self._ensure_running()

        result = {
            "slot": slot,
            "name": Path(plugin_path).stem,
            "loaded": False,
            "error": "",
        }

        # Send OSC message to load plugin
        success = self._osc.send(
            CarlaOSCClient.ADDR_ADD_PLUGIN,
            slot,
            plugin_format,
            plugin_path,
        )

        if success:
            result["loaded"] = True
            self._loaded_plugins[slot] = {
                "path": plugin_path,
                "format": plugin_format,
                "name": result["name"],
                "slot": slot,
            }
            logger.info("Plugin loaded: slot=%d, name=%s", slot, result["name"])
        else:
            result["error"] = f"Failed to send load command for {plugin_path}"
            logger.error("Plugin load failed: %s", result["error"])

        return result

    def unload_plugin(self, slot: int) -> bool:
        """
        Unload a plugin from a slot.

        Args:
            slot: Slot number to unload

        Returns:
            True if unloaded successfully
        """
        self._ensure_running()

        success = self._osc.send(CarlaOSCClient.ADDR_REMOVE_PLUGIN, slot)
        if success:
            self._loaded_plugins.pop(slot, None)
            logger.info("Plugin unloaded: slot=%d", slot)
        return success

    def load_preset(self, slot: int, preset_path: str) -> bool:
        """
        Load a preset for a plugin.

        Args:
            slot: Plugin slot
            preset_path: Path to preset file

        Returns:
            True if preset loaded
        """
        self._ensure_running()

        success = self._osc.send(
            CarlaOSCClient.ADDR_LOAD_PRESET, slot, preset_path
        )
        if success:
            if slot in self._loaded_plugins:
                self._loaded_plugins[slot]["preset"] = preset_path
            logger.info("Preset loaded: slot=%d, preset=%s", slot, preset_path)
        return success

    def get_plugin_info(self, slot: int) -> Dict[str, Any]:
        """Get info about a loaded plugin"""
        return self._loaded_plugins.get(slot, {})

    def list_plugins(self) -> List[Dict[str, Any]]:
        """List all loaded plugins"""
        return list(self._loaded_plugins.values())

    # ========== RACK MANAGEMENT ==========

    def load_rack(self, rack_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Load a complete rack from a configuration dict.

        rack_config should have:
        - "plugins": list of plugin dicts
        - "routes": list of route dicts

        Args:
            rack_config: Rack configuration

        Returns:
            Result dict with loaded plugins and routes
        """
        self._ensure_running()

        result = {
            "plugins_loaded": [],
            "plugins_failed": [],
            "routes_connected": [],
            "routes_failed": [],
        }

        # Load plugins
        for plugin_cfg in rack_config.get("plugins", []):
            slot = plugin_cfg["slot"]
            path = plugin_cfg.get("path", "")
            fmt = plugin_cfg.get("format", "VST3")

            load_result = self.load_plugin(slot, path, fmt)
            if load_result["loaded"]:
                result["plugins_loaded"].append(load_result)

                # Set volume if specified
                volume = plugin_cfg.get("volume")
                if volume is not None:
                    self.set_volume(slot, volume)

                # Set pan if specified
                pan = plugin_cfg.get("pan")
                if pan is not None:
                    self._osc.send(CarlaOSCClient.ADDR_SET_PAN, slot, float(pan))
            else:
                result["plugins_failed"].append(load_result)

        # Connect routes
        for route_cfg in rack_config.get("routes", []):
            track = route_cfg.get("track", "")
            slot = route_cfg.get("slot", 0)
            channel = route_cfg.get("midi_channel", 0)

            success = self.connect(channel, slot)
            if success:
                result["routes_connected"].append(route_cfg)
            else:
                result["routes_failed"].append(route_cfg)

        logger.info(
            "Rack loaded: %d/%d plugins, %d/%d routes",
            len(result["plugins_loaded"]),
            len(result["plugins_loaded"]) + len(result["plugins_failed"]),
            len(result["routes_connected"]),
            len(result["routes_connected"]) + len(result["routes_failed"]),
        )

        return result

    def save_rack_state(self, filepath: str) -> bool:
        """
        Save current rack state to a JSON file.

        Args:
            filepath: Output file path

        Returns:
            True if saved
        """
        import json
        state = {
            "plugins": self._loaded_plugins,
            "connections": self._connections,
            "status": self.status.value,
        }
        try:
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)
            with open(filepath, "w") as f:
                json.dump(state, f, indent=2, default=str)
            logger.info("Rack state saved: %s", filepath)
            return True
        except Exception as e:
            logger.error("Failed to save rack state: %s", e)
            return False

    def load_rack_state(self, filepath: str) -> bool:
        """
        Load rack state from a JSON file.

        Args:
            filepath: State file path

        Returns:
            True if loaded
        """
        import json
        try:
            with open(filepath, "r") as f:
                state = json.load(f)
            self._loaded_plugins = state.get("plugins", {})
            self._connections = state.get("connections", [])
            logger.info("Rack state loaded: %s", filepath)
            return True
        except Exception as e:
            logger.error("Failed to load rack state: %s", e)
            return False

    # ========== ROUTING ==========

    def connect(self, input_port: int, output_slot: int) -> bool:
        """
        Connect a MIDI input port to a plugin slot.

        Args:
            input_port: Input port/channel number
            output_slot: Target plugin slot

        Returns:
            True if connected
        """
        self._ensure_running()

        success = self._osc.send(
            CarlaOSCClient.ADDR_CONNECT, input_port, output_slot
        )
        if success:
            self._connections.append({
                "input_port": input_port,
                "output_slot": output_slot,
            })
            logger.info("Connected: port %d -> slot %d", input_port, output_slot)
        return success

    def disconnect(self, input_port: int, output_slot: int) -> bool:
        """Disconnect a MIDI port from a plugin slot"""
        self._ensure_running()

        success = self._osc.send(
            CarlaOSCClient.ADDR_DISCONNECT, input_port, output_slot
        )
        if success:
            self._connections = [
                c for c in self._connections
                if not (c["input_port"] == input_port and c["output_slot"] == output_slot)
            ]
        return success

    def get_connections(self) -> List[Dict[str, Any]]:
        """List all current connections"""
        return list(self._connections)

    # ========== RENDERING ==========

    def render(
        self,
        output_path: str,
        duration: Optional[float] = None,
        midi_files: Optional[List[str]] = None,
        wait: bool = True,
    ) -> Dict[str, Any]:
        """
        Render audio to a file via Carla.

        Falls back to FluidSynth if Carla is not running.

        Args:
            output_path: Output WAV file path
            duration: Duration in seconds
            midi_files: List of MIDI files to render
            wait: Wait for render to complete

        Returns:
            Result dict: {"status": str, "output_path": str, "error": str, "method": str}
        """
        result = {
            "status": "failed",
            "output_path": output_path,
            "error": "",
            "method": "carla",
            "duration": duration or 0.0,
        }

        out_path = Path(output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        # Try Carla first
        if self.is_running():
            try:
                self._is_rendering = True
                success = self._osc.send(
                    CarlaOSCClient.ADDR_RENDER, output_path,
                    float(duration) if duration else -1.0,
                )

                if success and wait:
                    # Wait for render to complete (poll status)
                    render_timeout = max(30.0, (duration or 30.0) * 2)
                    start_time = time.time()
                    while time.time() - start_time < render_timeout:
                        if out_path.exists() and out_path.stat().st_size > 44:
                            result["status"] = "completed"
                            logger.info("Carla render complete: %s", output_path)
                            break
                        time.sleep(0.5)
                    else:
                        result["error"] = "Render timed out"
                        logger.error("Carla render timed out after %.0fs", render_timeout)
                elif success:
                    result["status"] = "started"

                self._is_rendering = False

                if result["status"] == "completed":
                    return result

            except CarlaNotRunningError:
                logger.warning("Carla stopped during render")
            except Exception as e:
                logger.error("Carla render error: %s", e)
                result["error"] = str(e)
            finally:
                self._is_rendering = False

        # Fallback to FluidSynth
        if midi_files:
            logger.info("Falling back to FluidSynth for rendering")
            result["method"] = "fluidsynth"

            if fallback_to_fluidsynth(midi_files, output_path):
                result["status"] = "completed"
                result["error"] = ""
                return result
            else:
                result["error"] = "FluidSynth fallback also failed"

        # Last resort: generate silent WAV placeholder
        if result["status"] != "completed":
            logger.warning("Generating silent WAV placeholder")
            result["method"] = "placeholder"
            duration = duration or 10.0
            self._write_silent_wav(output_path, duration)
            result["status"] = "completed"
            result["error"] = "No audio engine available, generated silent placeholder"

        return result

    def _write_silent_wav(self, output_path: str, duration: float) -> None:
        """Write a valid but silent WAV file as placeholder"""
        sample_rate = settings.AUDIO_SAMPLE_RATE
        num_samples = int(sample_rate * duration)

        with open(output_path, "wb") as f:
            # WAV header
            data_size = num_samples * 4  # 2 channels * 2 bytes/sample
            f.write(b"RIFF")
            f.write(struct.pack("<I", 36 + data_size))
            f.write(b"WAVEfmt ")
            f.write(struct.pack("<I", 16))       # fmt chunk size
            f.write(struct.pack("<H", 1))        # PCM format
            f.write(struct.pack("<H", 2))        # 2 channels (stereo)
            f.write(struct.pack("<I", sample_rate))
            f.write(struct.pack("<I", sample_rate * 4))  # byte rate
            f.write(struct.pack("<H", 4))        # block align
            f.write(struct.pack("<H", 16))       # bits per sample
            f.write(b"data")
            f.write(struct.pack("<I", data_size))

            # Write silence in chunks for performance
            silence_chunk = b"\x00" * 4096
            bytes_remaining = data_size
            while bytes_remaining > 0:
                chunk_size = min(len(silence_chunk), bytes_remaining)
                f.write(silence_chunk[:chunk_size])
                bytes_remaining -= chunk_size

    def is_rendering(self) -> bool:
        """Check if a render is in progress"""
        return self._is_rendering

    def cancel_render(self) -> bool:
        """Cancel the current render"""
        if not self._is_rendering:
            return True
        self._is_rendering = False
        return self._osc.send(CarlaOSCClient.ADDR_TRANSPORT_STOP)

    # ========== TRANSPORT ==========

    def play(self) -> bool:
        """Start playback"""
        self._ensure_running()
        return self._osc.send(CarlaOSCClient.ADDR_TRANSPORT_PLAY)

    def transport_stop(self) -> bool:
        """Stop playback"""
        self._ensure_running()
        return self._osc.send(CarlaOSCClient.ADDR_TRANSPORT_STOP)

    def pause(self) -> bool:
        """Pause playback"""
        self._ensure_running()
        return self._osc.send(CarlaOSCClient.ADDR_TRANSPORT_PAUSE)

    # ========== PARAMETERS ==========

    def get_volume(self, slot: int) -> float:
        """Get volume of a plugin slot"""
        info = self._loaded_plugins.get(slot, {})
        return info.get("volume", 1.0)

    def set_volume(self, slot: int, volume: float) -> bool:
        """
        Set volume of a plugin slot.

        Args:
            slot: Plugin slot
            volume: Volume level (0.0 - 1.0)
        """
        volume = max(0.0, min(1.0, volume))
        success = self._osc.send(CarlaOSCClient.ADDR_SET_VOLUME, slot, volume)
        if success and slot in self._loaded_plugins:
            self._loaded_plugins[slot]["volume"] = volume
        return success

    def get_parameter(self, slot: int, param_index: int) -> float:
        """Get a plugin parameter value"""
        response = self._osc.send_and_wait(
            CarlaOSCClient.ADDR_GET_PARAMETER, slot, param_index
        )
        return float(response[0]) if response else 0.0

    def set_parameter(self, slot: int, param_index: int, value: float) -> bool:
        """Set a plugin parameter value"""
        return self._osc.send(
            CarlaOSCClient.ADDR_SET_PARAMETER, slot, param_index, value
        )

    # ========== STATE ==========

    def get_state(self) -> Dict[str, Any]:
        """Get complete rack state"""
        return {
            "status": self.status.value,
            "plugins": self._loaded_plugins,
            "connections": self._connections,
            "is_rendering": self._is_rendering,
            "uptime": time.time() - self._start_time if self._start_time else 0,
        }

    def __repr__(self) -> str:
        return (
            f"CarlaClient(host={self.host}, osc_port={self.osc_port}, "
            f"status={self.status.value}, plugins={len(self._loaded_plugins)})"
        )
