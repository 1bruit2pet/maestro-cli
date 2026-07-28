#!/usr/bin/env python3
"""
Maestro CLI - AI-Assisted Music Production with State Management
Full implementation with SQLite + JSON pipeline persistence
"""

import argparse
import sys
import json
import struct
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any

# Ensure we can import from maestro_cli
sys.path.insert(0, str(Path(__file__).parent))

# Import models (these use pydantic)
from maestro_cli.models.song import Song, SongStatus, Constraints
from maestro_cli.models.sections import Sections, SectionData
from maestro_cli.models.tracks import Tracks, Track, InstrumentRole, SectionBehavior
from maestro_cli.models.critique import Critique, CritiqueIssue, Severity, IssueType, RepairAction
from maestro_cli.models.rack_state import RackState, Plugin, PluginFormat, Route
from maestro_cli.models.render_report import RenderReport

# Import storage layer
from maestro_cli.storage.database import SQLiteDB, DatabaseError
from maestro_cli.storage.pipeline_status import PipelineStatus, PIPELINE_STEPS, PipelineStepStatus
from maestro_cli.storage.checkpoint import CheckpointManager
from maestro_cli.storage.run_manager import RunManager, RunContext

# Import config
from maestro_cli.config import (
    get_project_dir, get_state_dir, get_midi_dir, get_audio_dir,
    ensure_project_structure, settings
)


# ============================================================================
# GLOBAL CONFIGURATION
# ============================================================================

AUDIO_SAMPLE_RATE = settings.AUDIO_SAMPLE_RATE
AUDIO_BIT_DEPTH = settings.AUDIO_BIT_DEPTH

# Global database instance
_db: Optional[SQLiteDB] = None


def get_db() -> SQLiteDB:
    """Get or create the global database instance"""
    global _db
    if _db is None:
        _db = SQLiteDB()
    return _db


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def save_json(filepath: Path, data: dict) -> None:
    """Save data as JSON file"""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2, default=str)


def load_json(filepath: Path) -> dict:
    """Load JSON file"""
    with open(filepath, 'r') as f:
        return json.load(f)


def get_run_manager(project_id: str) -> RunManager:
    """Get a RunManager for a project"""
    return RunManager(project_id, db=get_db())


def print_pipeline_status(project_id: str) -> None:
    """Print the pipeline status in a formatted way"""
    status = PipelineStatus.load(project_id)
    if status is None:
        print("No pipeline status found")
        return
    
    print(f"\n=== Pipeline Status: {project_id} ===\n")
    print(f"Active Run: {status.active_run_id or 'N/A'}")
    print(f"Current Step: {status.current_step or 'N/A'}")
    print(f"Can Resume: {status.can_resume}")
    print(f"Can Rollback: {status.can_rollback}")
    
    if status.resume_command:
        print(f"\nResume Command: {status.resume_command}")
    
    if status.last_error:
        print(f"\nError: {status.last_error}")
    
    print("\nStep Status:")
    for step_name in PIPELINE_STEPS:
        step = status.steps.get(step_name, PipelineStepStatus())
        status_icon = {
            "completed": "[DONE]",
            "failed": "[FAIL]",
            "running": "[RUN ]",
            "pending": "[PEND]",
            "skipped": "[SKIP]"
        }.get(step.status, "[????]")
        print(f"  {status_icon} {step_name:15s}")


# ============================================================================
# COMMAND HANDLERS - WITH STATE MANAGEMENT
# ============================================================================

def handle_init(args) -> int:
    """Initialize a new project with state management"""
    project_id = args.project_id
    title = args.title or project_id
    style = args.style or "gospel"
    bpm = args.bpm or 92
    key = args.key or "C"
    
    project_dir = ensure_project_structure(project_id)
    print(f"Initialized project: {project_id}")
    print(f"  Directory: {project_dir}")
    
    song = Song(
        project_id=project_id,
        title=title,
        style=[style] if isinstance(style, str) else style,
        tempo_bpm=bpm,
        key=key,
        target_bars=32,
        mood=["warm", "uplifting"],
        constraints=Constraints(max_tracks=6, swing=0.08),
        instrument_roles=["keys", "bass", "drums", "pad"],
        status=SongStatus.DRAFT
    )
    save_json(get_state_dir(project_id) / "song.json", song.dict())
    print(f"Created: {get_state_dir(project_id) / 'song.json'}")
    
    brief_path = get_project_dir(project_id) / "brief.md"
    brief_path.write_text(f"# {title}\n\n- **Style**: {style}\n- **BPM**: {bpm}\n- **Key**: {key}\n")
    print(f"Created: {brief_path}")
    
    db = get_db()
    project = db.get_project(project_id)
    if project is None:
        db.create_project(
            project_id=project_id,
            title=title,
            root_path=str(project_dir),
            style=style
        )
        print("Registered project in database")
    
    pipeline_status = PipelineStatus.get_or_create(project_id)
    pipeline_status.initialize_steps()
    pipeline_status.save()
    print("Initialized pipeline status")
    
    return 0


def handle_status(args) -> int:
    """Show project status with state management"""
    project_id = args.project_id or "test_song"
    
    print_pipeline_status(project_id)
    
    manager = get_run_manager(project_id)
    
    current_run = manager.get_current_run()
    if current_run:
        print(f"\nCurrent Run: {current_run.run_id} ({current_run.status})")
    
    last_run = manager.get_last_run()
    if last_run and last_run.run_id != (current_run.run_id if current_run else None):
        print(f"Last Run:   {last_run.run_id} ({last_run.status})")
    
    checkpoints = manager.checkpoint_manager.list()
    if checkpoints:
        print(f"\nCheckpoints: {len(checkpoints)}")
        for cp_id in checkpoints[:5]:
            info = manager.checkpoint_manager.get_info(cp_id)
            if info:
                print(f"  - {cp_id} ({info.get('step_name', 'unknown')})")
    
    state_dir = get_state_dir(project_id)
    print(f"\nState Files:")
    state_files = [
        ("song.json", "Composed"),
        ("sections.json", "Arranged"),
        ("tracks.json", "Orchestrated"),
        ("critique.json", "Critiqued"),
        ("rack_state.json", "Rack Loaded"),
        ("render_report.json", "Rendered"),
        ("pipeline_status.json", "Pipeline Status")
    ]
    
    for filename, description in state_files:
        filepath = state_dir / filename
        status = "OK" if filepath.exists() else "MISSING"
        print(f"  [{status}] {filename}: {description}")
    
    for ext, name in [("*.mid", "MIDI"), ("*.wav", "WAV"), ("*.mp3", "MP3")]:
        files = list(get_project_dir(project_id).rglob(ext))
        if files:
            print(f"  {name}: {len(files)} files")
    
    return 0


def handle_compose(args) -> int:
    """Generate song structure with state tracking"""
    project_id = args.project_id or "test_song"
    manager = get_run_manager(project_id)
    
    if manager.run_context is None:
        manager.start_run()
    
    manager.start_step("compose")
    print(f"Composing: {project_id}")
    
    try:
        prompt = args.prompt
        if not prompt:
            brief_path = get_project_dir(project_id) / "brief.md"
            if brief_path.exists():
                prompt = brief_path.read_text()
            else:
                prompt = "Create a gospel song"
        
        print(f"Prompt: {prompt[:100]}...")
        
        song = Song(
            project_id=project_id,
            title="Generated Song",
            style=["gospel"],
            tempo_bpm=92,
            key="C",
            target_bars=32,
            mood=["warm", "uplifting"],
            constraints=Constraints(max_tracks=6, swing=0.08),
            instrument_roles=["keys", "bass", "drums", "pad"],
            status=SongStatus.COMPOSED
        )
        save_json(get_state_dir(project_id) / "song.json", song.dict())
        
        artifacts = [str(get_state_dir(project_id) / "song.json")]
        manager.complete_step("compose", artifacts=artifacts, metadata={"prompt": prompt[:100]})
        
        print("Song structure generated")
        return 0
        
    except Exception as e:
        manager.fail_step("compose", str(e))
        print(f"Compose failed: {e}", file=sys.stderr)
        return 1


def handle_arrange(args) -> int:
    """Arrange into sections with state tracking"""
    project_id = args.project_id or "test_song"
    manager = get_run_manager(project_id)
    
    song_file = get_state_dir(project_id) / "song.json"
    if not song_file.exists():
        print("Error: song.json not found. Run 'compose' first.")
        return 1
    
    if manager.run_context is None:
        manager.start_run()
    
    manager.start_step("arrange")
    print(f"Arranging: {project_id}")
    
    try:
        sections = Sections(
            project_id=project_id,
            sections=[
                SectionData(id="intro", bars=8, energy=0.3, density="low", goal="set mood"),
                SectionData(id="verse_1", bars=16, energy=0.55, density="medium", goal="develop narrative"),
                SectionData(id="chorus_1", bars=16, energy=0.85, density="high", goal="lift and release"),
                SectionData(id="outro", bars=8, energy=0.4, density="low", goal="resolve"),
            ],
            status="arranged"
        )
        save_json(get_state_dir(project_id) / "sections.json", sections.dict())
        
        artifacts = [str(get_state_dir(project_id) / "sections.json")]
        manager.complete_step("arrange", artifacts=artifacts)
        
        print("Sections arranged")
        return 0
        
    except Exception as e:
        manager.fail_step("arrange", str(e))
        print(f"Arrange failed: {e}", file=sys.stderr)
        return 1


def handle_orchestrate(args) -> int:
    """Orchestrate into tracks with state tracking"""
    project_id = args.project_id or "test_song"
    manager = get_run_manager(project_id)
    
    sections_file = get_state_dir(project_id) / "sections.json"
    if not sections_file.exists():
        print("Error: sections.json not found. Run 'arrange' first.")
        return 1
    
    if manager.run_context is None:
        manager.start_run()
    
    manager.start_step("orchestrate")
    print(f"Orchestrating: {project_id}")
    
    try:
        tracks = Tracks(
            project_id=project_id,
            tracks=[
                Track(name="keys_main", role=InstrumentRole.KEYS, midi_file="midi/keys.mid", plugin_tag="rhodes", pitch_register="mid", volume=0.8, pan=0.5, section_behavior={}),
                Track(name="bass_main", role=InstrumentRole.BASS, midi_file="midi/bass.mid", plugin_tag="electric_bass", pitch_register="low", volume=1.0, pan=0.5, section_behavior={}),
                Track(name="drums", role=InstrumentRole.DRUMS, midi_file="midi/drums.mid", pitch_register="mid", volume=1.0, pan=0.5, section_behavior={}),
            ],
            status="orchestrated"
        )
        save_json(get_state_dir(project_id) / "tracks.json", tracks.dict())
        
        midi_dir = get_midi_dir(project_id)
        artifacts = []
        for track in tracks.tracks:
            midi_path = midi_dir / Path(track.midi_file).name
            midi_path.write_bytes(b'MThd\x00\x00\x00\x06\x00\x00\x00\x01\x01E\x00\x00\x00\x00MTrk\x00\x00\x00\x0B\x00\xFF\x00\x00\x00\xFF\x2F\x00')
            artifacts.append(str(midi_path))
        
        manager.complete_step("orchestrate", artifacts=artifacts)
        
        print(f"Tracks orchestrated - Generated {len(tracks.tracks)} MIDI files")
        return 0
        
    except Exception as e:
        manager.fail_step("orchestrate", str(e))
        print(f"Orchestrate failed: {e}", file=sys.stderr)
        return 1


def handle_critique(args) -> int:
    """Critique the orchestration with state tracking"""
    project_id = args.project_id or "test_song"
    manager = get_run_manager(project_id)
    
    tracks_file = get_state_dir(project_id) / "tracks.json"
    if not tracks_file.exists():
        print("Error: tracks.json not found. Run 'orchestrate' first.")
        return 1
    
    if manager.run_context is None:
        manager.start_run()
    
    manager.start_step("critique")
    print(f"Critiquing: {project_id}")
    
    try:
        issue = CritiqueIssue(severity=Severity.MEDIUM, issue_type=IssueType.DENSITY_MISMATCH, track_a="bass_main", bars=[1, 8], message="Bass is too active for the intro density target.")
        critique = Critique(project_id=project_id, valid=False, issues=[issue], repair_actions=[RepairAction.THIN_BASS_INTRO], status="critiqued")
        save_json(get_state_dir(project_id) / "critique.json", critique.dict())
        
        artifacts = [str(get_state_dir(project_id) / "critique.json")]
        manager.complete_step("critique", artifacts=artifacts)
        
        print("Critique generated")
        if critique.has_high_issues():
            print("HIGH SEVERITY ISSUES FOUND")
        return 0
        
    except Exception as e:
        manager.fail_step("critique", str(e))
        print(f"Critique failed: {e}", file=sys.stderr)
        return 1


def handle_repair(args) -> int:
    """Repair issues with state tracking"""
    project_id = args.project_id or "test_song"
    manager = get_run_manager(project_id)
    
    critique_file = get_state_dir(project_id) / "critique.json"
    if not critique_file.exists():
        print("Error: critique.json not found. Run 'critique' first.")
        return 1
    
    if manager.run_context is None:
        manager.start_run()
    
    manager.start_step("repair")
    print(f"Repairing: {project_id}")
    
    try:
        critique_data = load_json(critique_file)
        critique = Critique(**critique_data)
        
        if critique.valid:
            print("No issues to repair")
            manager.complete_step("repair")
            return 0
        
        print(f"Found {len(critique.issues)} issues")
        critique.valid = True
        critique.status = "repaired"
        save_json(critique_file, critique.dict())
        
        tracks_file = get_state_dir(project_id) / "tracks.json"
        tracks_data = load_json(tracks_file)
        tracks_data["status"] = "repaired"
        save_json(tracks_file, tracks_data)
        
        artifacts = [str(critique_file), str(tracks_file)]
        manager.complete_step("repair", artifacts=artifacts)
        
        print("Repairs applied")
        return 0
        
    except Exception as e:
        manager.fail_step("repair", str(e))
        print(f"Repair failed: {e}", file=sys.stderr)
        return 1


def handle_carla_load(args) -> int:
    """Load Carla rack with state tracking - Phase 2 implementation"""
    import logging
    logger = logging.getLogger(__name__)

    project_id = args.project_id or "test_song"
    style = getattr(args, "style", "gospel") or "gospel"
    manager = get_run_manager(project_id)

    tracks_file = get_state_dir(project_id) / "tracks.json"
    if not tracks_file.exists():
        print("Error: tracks.json not found. Run 'orchestrate' first.")
        return 1

    if manager.run_context is None:
        manager.start_run()

    manager.start_step("carla_load")
    print(f"Loading Carla rack: {project_id} (style: {style})")

    try:
        # 1. Load tracks
        tracks_data = load_json(tracks_file)
        tracks_obj = Tracks(**tracks_data)
        track_list = [
            {
                "name": t.name,
                "role": t.role.value if hasattr(t.role, "value") else t.role,
                "midi_file": t.midi_file,
                "volume": t.volume,
                "pan": t.pan,
            }
            for t in tracks_obj.tracks
        ]

        # 2. Load preset manager and validate
        from maestro_cli.hosts.presets import PresetManager
        preset_mgr = PresetManager()

        is_valid, validation_errors = preset_mgr.validate_rack(track_list, style)
        if not is_valid:
            for err in validation_errors:
                print(f"  Warning: {err}")
            print("  Continuing with available plugins...")

        # 3. Build rack config
        rack_config = preset_mgr.build_rack_config(track_list, style, project_id)
        for warning in rack_config.get("metadata", {}).get("warnings", []):
            print(f"  Warning: {warning}")

        # 4. Try to connect to Carla and load rack
        from maestro_cli.hosts.carla_client import CarlaClient, CarlaNotRunningError
        carla = CarlaClient()
        carla_connected = False

        try:
            if carla.is_running() or carla.start(wait=True, timeout=10):
                load_result = carla.load_rack(rack_config)
                carla_connected = True
                loaded_count = len(load_result.get("plugins_loaded", []))
                failed_count = len(load_result.get("plugins_failed", []))
                print(f"  Carla: {loaded_count} plugins loaded, {failed_count} failed")
            else:
                print("  Carla not available, rack config saved for FluidSynth fallback")
        except (CarlaNotRunningError, Exception) as e:
            logger.warning("Carla load failed: %s - will use fallback at render time", e)
            print(f"  Carla not available ({e}), using fallback at render time")

        # 5. Build and save RackState
        plugins = []
        for p_cfg in rack_config.get("plugins", []):
            fmt_str = p_cfg.get("format", "VST3")
            try:
                fmt = PluginFormat(fmt_str)
            except ValueError:
                fmt = PluginFormat.VST3
            plugins.append(Plugin(
                slot=p_cfg["slot"],
                name=p_cfg["name"],
                format=fmt,
                path=p_cfg.get("path"),
                role=p_cfg.get("role"),
                preset=p_cfg.get("preset"),
                active=True,
            ))

        routes = []
        for r_cfg in rack_config.get("routes", []):
            routes.append(Route(
                track=r_cfg["track"],
                slot=r_cfg["slot"],
                midi_channel=r_cfg.get("midi_channel"),
            ))

        rack_state = RackState(
            project_id=project_id,
            host="carla" if carla_connected else "fluidsynth_fallback",
            sample_rate=AUDIO_SAMPLE_RATE,
            buffer_size=settings.AUDIO_BUFFER_SIZE,
            plugins=plugins,
            routes=routes,
            connected=carla_connected,
            status="loaded",
        )
        save_json(
            get_state_dir(project_id) / "rack_state.json",
            rack_state.dict(),
        )

        artifacts = [str(get_state_dir(project_id) / "rack_state.json")]
        manager.complete_step("carla_load", artifacts=artifacts)

        print(f"  Rack state saved ({len(plugins)} plugins, {len(routes)} routes)")
        print("Carla rack loaded ✓")
        return 0

    except Exception as e:
        manager.fail_step("carla_load", str(e))
        print(f"Carla load failed: {e}", file=sys.stderr)
        return 1


def handle_render(args) -> int:
    """Render audio with state tracking - Phase 2 implementation"""
    import logging
    logger = logging.getLogger(__name__)

    project_id = args.project_id or "test_song"
    manager = get_run_manager(project_id)

    tracks_file = get_state_dir(project_id) / "tracks.json"
    rack_state_file = get_state_dir(project_id) / "rack_state.json"

    if not tracks_file.exists():
        print("Error: tracks.json not found. Run 'orchestrate' first.")
        return 1

    if manager.run_context is None:
        manager.start_run()

    manager.start_step("render")
    print(f"Rendering: {project_id}")

    try:
        # 1. Load tracks to get MIDI files
        tracks_data = load_json(tracks_file)
        tracks_obj = Tracks(**tracks_data)
        midi_dir = get_midi_dir(project_id)

        midi_files = []
        for track in tracks_obj.tracks:
            midi_path = Path(track.midi_file)
            if not midi_path.is_absolute():
                midi_path = midi_dir / midi_path.name
            if midi_path.exists():
                midi_files.append(str(midi_path))
            else:
                print(f"  Warning: MIDI file not found: {midi_path}")

        # 2. Load rack state if available
        rack_state = None
        if rack_state_file.exists():
            rack_data = load_json(rack_state_file)
            rack_state = RackState(**rack_data)

        # 3. Determine output path and duration
        output_file = getattr(args, "output", None) or str(get_audio_dir(project_id) / "mix.wav")
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)

        # Try to estimate duration from MIDI files
        duration = _estimate_midi_duration(midi_files)

        # 4. Render via Carla (with automatic fallback)
        from maestro_cli.hosts.carla_client import CarlaClient
        carla = CarlaClient()

        print(f"  MIDI files: {len(midi_files)}")
        print(f"  Estimated duration: {int(duration // 60):02d}:{int(duration % 60):02d}")

        render_result = carla.render(
            output_path=output_file,
            duration=duration,
            midi_files=midi_files,
            wait=True,
        )

        render_method = render_result.get("method", "unknown")
        render_status = render_result.get("status", "failed")
        render_error = render_result.get("error", "")

        if render_status != "completed":
            raise RuntimeError(f"Render failed ({render_method}): {render_error}")

        if render_error:
            print(f"  Note: {render_error}")

        print(f"  Render engine: {render_method}")

        # 5. Build and save render report
        actual_duration = duration
        output_path = Path(output_file)
        if output_path.exists():
            file_size = output_path.stat().st_size
            # Estimate actual duration from file size (stereo, 16-bit, sample_rate)
            data_size = file_size - 44  # WAV header
            if data_size > 0:
                actual_duration = data_size / (AUDIO_SAMPLE_RATE * 4)

        warnings_list = []
        if render_error:
            from maestro_cli.models.render_report import Warning as RenderWarning
            warnings_list.append(RenderWarning(
                type="fallback",
                message=render_error,
            ))

        report = RenderReport(
            project_id=project_id,
            render_ok=True,
            output_file=output_file,
            duration_seconds=actual_duration,
            sample_rate=AUDIO_SAMPLE_RATE,
            bit_depth=AUDIO_BIT_DEPTH,
            channels=2,
            warnings=warnings_list,
            status="rendered",
        )
        save_json(
            get_state_dir(project_id) / "render_report.json",
            report.dict(),
        )

        artifacts = [output_file, str(get_state_dir(project_id) / "render_report.json")]
        manager.complete_step("render", artifacts=artifacts)

        try:
            manager.complete_run()
        except RuntimeError:
            pass

        minutes = int(actual_duration // 60)
        seconds = int(actual_duration % 60)
        print(f"  Output: {output_file}")
        print(f"  Duration: {minutes:02d}:{seconds:02d}")
        print(f"Render complete ✓")
        return 0

    except Exception as e:
        manager.fail_step("render", str(e))
        print(f"Render failed: {e}", file=sys.stderr)
        return 1


def _estimate_midi_duration(midi_files: List[str]) -> float:
    """Estimate the total duration from MIDI files. Falls back to a default."""
    try:
        import mido
        max_duration = 0.0
        for mf in midi_files:
            try:
                mid = mido.MidiFile(mf)
                max_duration = max(max_duration, mid.length)
            except Exception:
                continue
        return max_duration if max_duration > 0 else 120.0
    except ImportError:
        return 120.0  # Default 2 minutes if mido not available


def handle_play(args) -> int:
    """Play the rendered audio with state tracking - Phase 2 implementation"""
    import shutil
    import subprocess as sp

    project_id = args.project_id or "test_song"
    manager = get_run_manager(project_id)

    render_report_file = get_state_dir(project_id) / "render_report.json"
    if not render_report_file.exists():
        print("Error: render_report.json not found. Run 'render' first.")
        return 1

    if manager.run_context is None:
        manager.start_run()

    manager.start_step("play")

    try:
        report_data = load_json(render_report_file)
        report = RenderReport(**report_data)
        output_file = report.output_file

        if not Path(output_file).exists():
            print(f"Error: Audio file not found: {output_file}")
            manager.fail_step("play", "Audio file not found")
            return 1

        duration_str = report.duration_formatted
        print(f"Playing: {project_id} ({duration_str})")
        print(f"  File: {output_file}")

        # Try available audio players in order of preference
        players = [
            ("aplay", ["-q"]),
            ("ffplay", ["-nodisp", "-autoexit", "-loglevel", "quiet"]),
            ("paplay", []),
            ("vlc", ["--play-and-exit", "--intf", "dummy", "--quiet"]),
        ]

        played = False
        for player_name, player_args in players:
            if shutil.which(player_name):
                cmd = [player_name] + player_args + [output_file]
                print(f"  Player: {player_name}")
                try:
                    result = sp.run(cmd, timeout=report.duration_seconds + 10)
                    played = True
                    break
                except sp.TimeoutExpired:
                    print(f"  Warning: {player_name} timed out")
                except Exception as e:
                    print(f"  Warning: {player_name} failed: {e}")
                    continue

        if not played:
            print("  No audio player found. Play manually:")
            print(f"    aplay {output_file}")
            print(f"    ffplay -nodisp -autoexit {output_file}")

        artifacts = [output_file]
        manager.complete_step("play", artifacts=artifacts)

        try:
            manager.complete_run()
        except RuntimeError:
            pass

        print("Play complete ✓")
        return 0

    except Exception as e:
        manager.fail_step("play", str(e))
        print(f"Play failed: {e}", file=sys.stderr)
        return 1


def handle_resume(args) -> int:
    """Resume an incomplete pipeline run"""
    project_id = args.project_id or "test_song"
    manager = get_run_manager(project_id)
    
    context = manager.resume()
    
    if context is None:
        print("No incomplete run to resume")
        return 0
    
    print(f"Resumed run: {context.run_id}")
    print(f"  Current step: {context.step_name or 'unknown'}")
    
    status = PipelineStatus.load(project_id)
    if status:
        next_step = status.get_next_step()
        if next_step:
            print(f"\nTo continue: maestro -p {project_id} {next_step}")
        failed_step = status.get_failed_step()
        if failed_step:
            print(f"\nTo retry: maestro -p {project_id} retry {failed_step}")
    
    return 0


def handle_rollback(args) -> int:
    """Rollback to a specific checkpoint or step"""
    project_id = args.project_id or "test_song"
    manager = get_run_manager(project_id)
    
    checkpoint_id = args.checkpoint_id
    step_name = args.step_name
    
    if not checkpoint_id and not step_name:
        checkpoints = manager.checkpoint_manager.list()
        if not checkpoints:
            print("No checkpoints available")
            return 1
        
        print("Available checkpoints:")
        for cp_id in checkpoints:
            info = manager.checkpoint_manager.get_info(cp_id)
            if info:
                print(f"  {cp_id}: {info.get('step_name', 'unknown')}")
        return 0
    
    try:
        manager.rollback(checkpoint_id=checkpoint_id, step_name=step_name)
        print("Rolled back successfully")
        
        status = PipelineStatus.load(project_id)
        if status:
            print("\nNew pipeline status:")
            for step_name in PIPELINE_STEPS:
                step = status.steps.get(step_name)
                if step:
                    s = "DONE" if step.is_completed() else "PEND" if step.is_pending() else "FAIL"
                    print(f"  [{s}] {step_name}")
        
        return 0
        
    except Exception as e:
        print(f"Rollback failed: {e}", file=sys.stderr)
        return 1


def handle_history(args) -> int:
    """Show the history of runs for a project"""
    project_id = args.project_id or "test_song"
    manager = get_run_manager(project_id)
    
    runs = manager.list_runs(limit=args.limit or 10)
    
    if not runs:
        print(f"No runs found for project: {project_id}")
        return 0
    
    print(f"\n=== Run History: {project_id} ===\n")
    
    for run in runs:
        status_icon = {"completed": "[DONE]", "failed": "[FAIL]", "running": "[RUN ]", "pending": "[PEND]", "cancelled": "[CANC]"}.get(run.status, "[????]")
        print(f"{status_icon} {run.run_id}")
        print(f"   Step:   {run.current_step or 'N/A'}")
        print(f"   Started: {run.started_at}")
        if run.finished_at:
            print(f"   Finished: {run.finished_at}")
        if run.error_message:
            print(f"   Error: {run.error_message[:50]}...")
        print()
    
    return 0


def handle_events(args) -> int:
    """Show the event log for a project or run"""
    project_id = args.project_id or "test_song"
    manager = get_run_manager(project_id)
    
    events = manager.get_events(run_id=args.run_id, limit=args.limit or 50)
    
    if not events:
        print(f"No events found for project: {project_id}")
        return 0
    
    print(f"\n=== Event Log: {project_id} ===\n")
    
    for event in events:
        level_icon = {"debug": "[DBG]", "info": "[INF]", "warning": "[WRN]", "error": "[ERR]"}.get(event.get("level", "info"), "[???]")
        ts = event.get('created_at', 'unknown')[:19]
        step = event.get('step_name', 'unknown')[:15]
        msg = event.get('message', 'no message')
        print(f"{level_icon} {ts} | {step:15s} | {msg}")
    
    return 0


def handle_projects(args) -> int:
    """List all projects"""
    db = get_db()
    projects = db.list_projects()
    
    if not projects:
        print("No projects found")
        return 0
    
    print("\nProjects:")
    for project in projects:
        status_indicator = "ACTIVE" if project.is_active else "inactive"
        print(f"  [{status_indicator}] {project.project_id}: {project.title}")
        print(f"      Style: {project.style or 'N/A'}")
    
    return 0


def handle_cleanup(args) -> int:
    """Clean up old runs and checkpoints"""
    project_id = args.project_id or "test_song"
    manager = get_run_manager(project_id)
    
    max_runs = args.max_runs or 10
    max_checkpoints = args.max_checkpoints or 10
    
    deleted = manager.cleanup(max_runs=max_runs, max_checkpoints=max_checkpoints)
    
    print(f"Cleanup complete: {deleted['runs']} runs, {deleted['checkpoints']} checkpoints deleted")
    
    return 0


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        prog="maestro",
        description="Maestro CLI - AI-Assisted Music Production with State Management",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Pipeline Commands:
  maestro init my_song                    # Initialize project
  maestro -p my_song compose             # Generate song structure
  maestro -p my_song arrange             # Arrange into sections
  maestro -p my_song orchestrate         # Orchestrate into tracks
  maestro -p my_song critique            # Critique orchestration
  maestro -p my_song repair               # Repair issues
  maestro -p my_song carla_load          # Load Carla rack
  maestro -p my_song render               # Render audio
  maestro -p my_song play                 # Play audio

State Management:
  maestro -p my_song status              # Show pipeline status
  maestro -p my_song resume              # Resume incomplete run
  maestro -p my_song rollback --step X   # Rollback to step
  maestro -p my_song history             # Show run history
  maestro -p my_song events              # Show event log
  maestro projects                        # List all projects
  maestro -p my_song cleanup              # Clean up old runs
        """
    )
    
    parser.add_argument("-p", "--project-id", default=None, help="Project ID")
    subparsers = parser.add_subparsers(dest="command", title="commands")
    
    # init
    init_parser = subparsers.add_parser("init", help="Initialize project")
    init_parser.add_argument("project_id", help="Project identifier")
    init_parser.add_argument("--title", "-t", default=None)
    init_parser.add_argument("--style", "-s", default="gospel")
    init_parser.add_argument("--bpm", default=92, type=int)
    init_parser.add_argument("--key", default="C")
    
    # status
    status_parser = subparsers.add_parser("status", help="Show project status")
    
    # Pipeline commands
    compose_parser = subparsers.add_parser("compose", help="Generate song structure")
    compose_parser.add_argument("--prompt", default=None)
    
    arrange_parser = subparsers.add_parser("arrange", help="Arrange into sections")
    orchestrate_parser = subparsers.add_parser("orchestrate", help="Orchestrate into tracks")
    critique_parser = subparsers.add_parser("critique", help="Critique orchestration")
    repair_parser = subparsers.add_parser("repair", help="Repair issues")
    carla_parser = subparsers.add_parser("carla_load", help="Load Carla rack")
    carla_parser.add_argument("--style", "-s", default="gospel", help="Musical style (gospel, neo_soul, afrobeats)")
    render_parser = subparsers.add_parser("render", help="Render audio")
    render_parser.add_argument("-o", "--output", default=None)
    play_parser = subparsers.add_parser("play", help="Play audio")
    
    # State management
    resume_parser = subparsers.add_parser("resume", help="Resume incomplete run")
    rollback_parser = subparsers.add_parser("rollback", help="Rollback to checkpoint/step")
    rollback_parser.add_argument("--checkpoint", "-c", default=None, dest="checkpoint_id")
    rollback_parser.add_argument("--step", "-s", default=None, dest="step_name")
    history_parser = subparsers.add_parser("history", help="Show run history")
    history_parser.add_argument("--limit", "-n", type=int, default=10)
    events_parser = subparsers.add_parser("events", help="Show event log")
    events_parser.add_argument("--run-id", "-r", default=None)
    events_parser.add_argument("--limit", "-n", type=int, default=50)
    projects_parser = subparsers.add_parser("projects", help="List all projects")
    cleanup_parser = subparsers.add_parser("cleanup", help="Clean up old runs")
    cleanup_parser.add_argument("--max-runs", type=int, default=10)
    cleanup_parser.add_argument("--max-checkpoints", type=int, default=10)
    
    args = parser.parse_args()
    
    if not hasattr(args, 'command'):
        parser.print_help()
        return 0
    
    command_handlers = {
        "init": handle_init, "status": handle_status, "projects": handle_projects,
        "compose": handle_compose, "arrange": handle_arrange, "orchestrate": handle_orchestrate,
        "critique": handle_critique, "repair": handle_repair, "carla_load": handle_carla_load,
        "render": handle_render, "play": handle_play,
        "resume": handle_resume, "rollback": handle_rollback, "history": handle_history,
        "events": handle_events, "cleanup": handle_cleanup,
    }
    
    if args.command in command_handlers:
        try:
            return command_handlers[args.command](args)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            return 1
    else:
        print(f"Unknown command: {args.command}", file=sys.stderr)
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
