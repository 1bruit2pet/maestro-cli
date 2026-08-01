# Maestro CLI

> **AI-Assisted Music Production CLI**
> Compose, arrange, orchestrate, and render music with LLM planning and Carla execution.

---

## 🎵 Features

- **Dual-LLM Architecture**: Two specialized LLMs — one for composition (Groq/OpenAI), one for MIDI generation (local llama.cpp)
- **LLM-Powered Composition**: Generate song structures from natural language prompts via Groq
- **MIDI-LLM Orchestration**: Local llama.cpp server generates AMT (Audio MIDI Transformer) tokens per instrument
- **Modular Pipeline**: Compose → Arrange → Orchestrate → Critique → Repair → Render
- **Carla Integration**: Host VST/LV2 plugins and render audio via OSC
- **MIDI 2.0 Ready**: Architecture prepared for UMP and MIDI-CI
- **Deterministic Workflow**: Each step reads validated JSON and writes validated JSON
- **Project Management**: Organize songs with versioned state files

---

## 🤖 Dual-LLM Architecture

Maestro uses **two distinct LLMs** for different tasks:

| Role | LLM | Task | Config |
|------|-----|------|--------|
| **Composition** | Groq `llama-3.3-70b-versatile` (distant) | `maestro compose` — génère la structure JSON (sections, accords, style) | `LLM_*` dans `.env` |
| **MIDI / Orchestration** | llama.cpp local HTTP (port 8080) | `maestro orchestrate` — génère les tokens AMT par instrument | `MIDI_LLM_*` dans `.env` |

### Flux de données

```
Prompt textuel
      │
      ▼
[Groq LLM] ──► song.json (structure: key, bpm, sections, chords)
      │
      ▼
[llama.cpp MIDI-LLM] ──► tokens AMT ──► fichiers .mid par instrument
      │
      ▼
[Carla / Claw-DAW] ──► mix.wav
```

### Configuration `.env`

```bash
# LLM de composition (Groq / OpenAI-compatible distant)
LLM_API_KEY=gsk_votre_clé_groq
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_MODEL=llama-3.3-70b-versatile

# MIDI-LLM local (llama.cpp HTTP)
MIDI_LLM_BASE_URL=http://127.0.0.1:8080/v1
MIDI_LLM_MODEL=midi-llm
MIDI_LLM_API_KEY=local
```

### Démarrer le serveur MIDI-LLM local

```bash
# Avec llama.cpp (llama-server)
llama-server -m /path/to/midi-llm.Q4_K_M.gguf --port 8080

# Si indisponible → MockMidiLLMProvider (heuristique musicale) s'active automatiquement
```

---

## 🚀 Quick Start

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/maestro-cli.git
cd maestro-cli

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e .

# Copy and configure environment
cp .env.example .env
# Edit .env with your API keys and settings
```

### 2. Create Your First Song

```bash
# Initialize a new project
maestro init my_first_song --title "My First Song" --style gospel --bpm 92 --key C

# Compose the song structure
maestro compose -p my_first_song --prompt "Create a uplifting gospel song with verse-chorus structure"

# Arrange into sections
maestro arrange -p my_first_song

# Orchestrate into MIDI tracks
maestro orchestrate -p my_first_song

# Critique the orchestration
maestro critique -p my_first_song

# Repair any issues
maestro repair -p my_first_song

# Start Carla and load plugins
maestro carla start
maestro carla load -p my_first_song -r ~/.carla/racks/gospel.rck

# Render to audio
maestro render -p my_first_song -o audio/mix.wav

# Play the result
maestro play -p my_first_song
```

---

## 📁 Project Structure

```
maestro-cli/
├── songs/projects/
│   └── my_first_song/
│       ├── brief.md              # Human-readable brief
│       ├── state/
│       │   ├── song.json         # Song metadata (source of truth)
│       │   ├── sections.json     # Arrangement structure
│       │   ├── tracks.json        # Orchestrated tracks
│       │   ├── critique.json      # Validation issues
│       │   ├── rack_state.json    # Carla runtime state
│       │   └── render_report.json # Render results
│       ├── midi/
│       │   ├── keys.mid
│       │   ├── bass.mid
│       │   └── drums.mid
│       ├── audio/
│       │   └── mix.wav
│       ├── logs/
│       │   └── *.log
│       └── presets/
│           └── carla_rack.json
├── configs/
│   └── app.toml                 # Configuration files
├── prompts/
│   ├── roles/
│   │   └── planner.md           # LLM role definitions
│   └── styles/
│       └── gospel.json          # Style-specific rules
├── src/maestro_cli/
│   ├── __main__.py
│   ├── cli.py                   # Main CLI
│   ├── config.py
│   ├── models/                  # Pydantic models
│   ├── commands/                # CLI subcommands
│   ├── llm/                     # LLM integration
│   ├── music/                  # Music theory
│   ├── midi/                   # MIDI handling
│   ├── hosts/                  # Audio hosts (Carla)
│   └── utils/                  # Utilities
└── pyproject.toml
└── .env.example
```

---

## 🎛️ Commands Reference

### Project Management

| Command | Description |
|---------|-------------|
| `maestro init PROJECT_ID` | Create a new project |
| `maestro use PROJECT_ID` | Set current project |
| `maestro status` | Show project status |
| `maestro project list` | List all projects |
| `maestro project delete PROJECT_ID` | Delete a project |

### Music Pipeline

| Command | Description | Input | Output |
|---------|-------------|-------|--------|
| `maestro compose` | Generate song structure | brief.md | state/song.json |
| `maestro arrange` | Create sections | state/song.json | state/sections.json |
| `maestro orchestrate` | Generate MIDI tracks | state/sections.json | state/tracks.json + midi/*.mid |
| `maestro critique` | Validate orchestration | state/tracks.json | state/critique.json |
| `maestro repair` | Fix issues | state/critique.json | state/tracks.json (updated) |
| `maestro render` | Render audio | state/rack_state.json | audio/mix.wav + state/render_report.json |

### Carla Control

| Command | Description |
|---------|-------------|
| `maestro carla start` | Start Carla process |
| `maestro carla stop` | Stop Carla process |
| `maestro carla load RACK` | Load a Carla rack |
| `maestro carla status` | Show Carla status |

### Utilities

| Command | Description |
|---------|-------------|
| `maestro play` | Play rendered audio |
| `maestro log` | Show project logs |
| `maestro version` | Show version info |

---

## 📋 JSON Schema Reference

### song.json

The canonical state of a music project:

```json
{
  "project_id": "my_song",
  "title": "Grace Motion",
  "style": ["gospel", "neo-soul"],
  "tempo_bpm": 92,
  "time_signature": "4/4",
  "key": "F minor",
  "target_bars": 64,
  "mood": ["warm", "uplifting", "live-band"],
  "constraints": {
    "max_tracks": 6,
    "tempo_changes": false,
    "swing": 0.08
  },
  "instrument_roles": ["keys", "bass", "drums", "pad", "lead"],
  "status": "composed"
}
```

### sections.json

The arrangement/structure of the song:

```json
{
  "project_id": "my_song",
  "sections": [
    {
      "id": "intro",
      "bars": 8,
      "energy": 0.3,
      "density": "low",
      "goal": "set mood"
    },
    {
      "id": "verse_1",
      "bars": 16,
      "energy": 0.55,
      "density": "medium",
      "goal": "develop narrative"
    }
  ],
  "status": "arranged"
}
```

### tracks.json

Orchestrated tracks with MIDI file references:

```json
{
  "project_id": "my_song",
  "tracks": [
    {
      "name": "keys_main",
      "role": "keys",
      "midi_file": "midi/keys.mid",
      "plugin_tag": "rhodes",
      "register": "mid",
      "volume": 0.8,
      "pan": 0.5,
      "section_behavior": {
        "intro": {"pattern": "sparse chords", "register": "low"}
      }
    }
  ],
  "status": "orchestrated"
}
```

### critique.json

Validation and repair suggestions:

```json
{
  "project_id": "my_song",
  "valid": false,
  "issues": [
    {
      "severity": "high",
      "issue_type": "register_collision",
      "track_a": "keys_main",
      "track_b": "lead_main",
      "bars": [17, 24],
      "message": "Lead and keys overlap in upper-mid register"
    }
  ],
  "repair_actions": ["raise_lead_register_chorus"],
  "status": "critiqued"
}
```

### rack_state.json

Carla runtime state:

```json
{
  "project_id": "my_song",
  "host": "carla",
  "sample_rate": 48000,
  "buffer_size": 256,
  "plugins": [
    {
      "slot": 1,
      "name": "EPiano",
      "format": "VST3",
      "role": "keys",
      "preset": "Warm Suitcase"
    }
  ],
  "routes": [
    {"track": "keys_main", "slot": 1}
  ],
  "connected": true,
  "status": "loaded"
}
```

### render_report.json

Audio rendering results:

```json
{
  "project_id": "my_song",
  "render_ok": true,
  "output_file": "audio/mix.wav",
  "duration_seconds": 168.2,
  "sample_rate": 48000,
  "bit_depth": 24,
  "channels": 2,
  "warnings": [],
  "errors": []
}
```

---

## 🔧 Configuration

### Environment Variables

Create a `.env` file from `.env.example` and configure:

```bash
LLM_API_KEY=your_openai_api_key
CARLA_START_CMD=carla
AUDIO_SAMPLE_RATE=48000
```

### Config Files

Configuration files in `configs/` override environment variables:

```toml
# configs/app.toml
[llm]
api_key = "${LLM_API_KEY}"
model = "gpt-4o"

[audio]
sample_rate = 48000
bit_depth = 24
```

---

## 🎨 Style Presets

Style presets in `prompts/styles/` define musical conventions:

```json
{
  "name": "gospel",
  "description": "Traditional gospel music style",
  "bpm_range": [90, 110],
  "typical_instruments": ["orgue", "basse", "batterie", "choeurs", "cuivres"],
  "harmonic_rules": {
    "preferred_chords": ["maj7", "min7", "dom7"],
    "avoid_chords": ["dim", "aug"]
  },
  "rhythmic_rules": {
    "swing": 0.08,
    "syncopation": 0.3
  }
}
```

---

## 🔌 Carla Integration

Maestro CLI integrates with [Carla](https://github.com/falkTX/Carla) for:

- **Plugin Hosting**: Load VST2, VST3, LV2, LADSPA, DSSI, SF2, SFZ
- **OSC Control**: Remote control via OSC protocol
- **Audio Routing**: JACK, ALSA, or PulseAudio backend
- **Preset Management**: Save/load plugin presets

### Installation

```bash
# Ubuntu/Debian
sudo apt install carla

# macOS (Homebrew)
brew install carla

# Windows
# Download from https://github.com/falkTX/Carla/releases
```

### Starting Carla

```bash
# Start with OSC enabled
carla --osc-port 9001

# Or via maestro
maestro carla start
```

---

## 📦 MIDI 2.0 Support

The architecture is prepared for MIDI 2.0 features:

- **UMP (Universal MIDI Packet)**: Full support planned
- **MIDI-CI (Capability Inquiry)**: Device capability detection
- **Per-Note Controllers**: Fine-grained expression control
- **Property Exchange**: Extended metadata

Current status: MIDI 1.0 is fully supported. MIDI 2.0 modules are stubbed and ready for implementation.

---

## 🧪 Development

### Install Dev Dependencies

```bash
pip install -e ".[dev]"
```

### Run Tests

```bash
pytest
```

### Code Quality

```bash
# Linting
ruff check .

# Formatting
ruff format .

# Type checking
mypy .
```

---

## 📜 License

MIT License - see LICENSE file for details.

---

## 🙏 Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

---

## 📞 Support

- **Issues**: https://github.com/yourusername/maestro-cli/issues
- **Discussions**: https://github.com/yourusername/maestro-cli/discussions
- **Email**: jonathan@music.ai
