# Carla Bridge - Phase 2 Documentation

## Overview

The Carla Bridge connects Maestro CLI's symbolic music pipeline to real audio output
via [Carla](https://kx.studio/Applications:Carla) audio plugin host, with FluidSynth
as a fallback when Carla is unavailable.

## Architecture

```
tracks.json → PresetManager → rack_config → CarlaClient → Carla (OSC)
                                                ↓ fallback
                                           FluidSynth → WAV
```

## Components

### 1. `hosts/carla_osc.py` — Low-level OSC Client

Wraps `python-osc` for communicating with Carla's OSC interface.

```python
from maestro_cli.hosts import CarlaOSCClient

client = CarlaOSCClient(host="127.0.0.1", port=9001, timeout=5.0)
client.connect()
client.send("/carla/load_plugin", 1, "VST3", "/path/to/plugin.vst3")
client.disconnect()
```

### 2. `hosts/carla_client.py` — High-level Carla Client

Clean API for plugin management, routing, and rendering.

```python
from maestro_cli.hosts import CarlaClient

carla = CarlaClient()
carla.start()                              # Start Carla process
carla.load_plugin(1, "/path/to.vst3")      # Load plugin in slot 1
carla.set_volume(1, 0.8)                   # Set volume
carla.connect(0, 1)                        # Route MIDI ch0 → slot 1
result = carla.render("output.wav", 120.0) # Render 2 minutes
carla.stop()
```

### 3. `hosts/presets.py` — Preset Manager

Maps musical roles to plugins using `presets/plugin_map.json`.

```python
from maestro_cli.hosts import PresetManager

mgr = PresetManager()
mgr.list_styles()                     # ['gospel', 'neo_soul', 'afrobeats']
plugin = mgr.find_plugin("keys", "gospel")  # EPiano, Warm Suitcase
config = mgr.build_rack_config(tracks, "gospel", "my_song")
```

### 4. `presets/plugin_map.json` — Plugin Mapping

Defines which plugins/presets to use for each musical role per style.

```json
{
  "styles": {
    "gospel": {
      "mappings": [
        {"role": "keys", "plugin": "EPiano", "preset": "Warm Suitcase", ...},
        {"role": "bass", "plugin": "BassPlugin", "preset": "Round Finger", ...}
      ]
    }
  },
  "fallback": {"synth": "fluidsynth", "soundfont": "..."}
}
```

## CLI Commands

### `maestro carla_load`

Loads a Carla rack from `tracks.json`:

```bash
maestro -p my_song carla_load              # Uses gospel style
maestro -p my_song carla_load --style neo_soul
```

**Steps:**
1. Load `tracks.json` from project state
2. Validate rack with `PresetManager`
3. Build rack config (plugins + routes)
4. Try connecting to Carla and loading plugins
5. Save `rack_state.json`

### `maestro render`

Renders MIDI to WAV:

```bash
maestro -p my_song render
maestro -p my_song render -o custom_output.wav
```

**Render cascade:**
1. **Carla** — If running, render via OSC
2. **FluidSynth** — If Carla unavailable, use `fluidsynth` CLI
3. **Placeholder** — If nothing available, generate silent WAV

### `maestro play`

Plays the rendered WAV:

```bash
maestro -p my_song play
```

**Player priority:** aplay → ffplay → paplay → vlc

## Error Handling

All Carla errors inherit from `CarlaError`:

| Exception | When |
|-----------|------|
| `CarlaNotRunningError` | Carla process not running |
| `PluginNotFoundError` | Plugin file not found on disk |
| `PresetNotFoundError` | Preset file not found |
| `RenderError` | Audio rendering failed |
| `RoutingError` | MIDI/audio routing error |

Preset errors inherit from `PresetError`:

| Exception | When |
|-----------|------|
| `PluginMapNotFoundError` | `plugin_map.json` not found |
| `StyleNotFoundError` | Requested style doesn't exist |
| `RoleMappingError` | No mapping for a required role |

## FluidSynth Fallback

When Carla is unavailable, the system falls back to FluidSynth:

```bash
fluidsynth -ni /usr/share/sounds/sf2/GeneralUser_GS.sf2 track.mid -F output.wav -r 48000
```

Requirements:
- `fluidsynth` in PATH
- A SoundFont file (`.sf2`)

## Configuration

Environment variables or `.env` file:

```env
CARLA_HOST=127.0.0.1
CARLA_OSC_PORT=9001
CARLA_TIMEOUT=5
CARLA_START_CMD=carla
AUDIO_SAMPLE_RATE=48000
AUDIO_BIT_DEPTH=24
```

## Testing

```bash
pytest tests/test_carla_integration.py -v
```
