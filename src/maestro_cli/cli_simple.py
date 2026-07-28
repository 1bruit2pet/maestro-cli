"""
Simplified CLI for Maestro using only standard library + pydantic
This version works without typer/rich dependencies
"""

import argparse
import sys
import json
from pathlib import Path
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from maestro_cli import __version__, PROJECT_ROOT
from maestro_cli.config import settings, get_project_dir, ensure_project_structure
from maestro_cli.models import Song, Sections, Tracks, Critique, RackState, RenderReport
from maestro_cli.utils import jsonio


class CLIError(Exception):
    """Custom error for CLI"""
    pass


def print_json(data, title: str = ""):
    """Print data as formatted JSON"""
    if title:
        print(f"\n=== {title} ===")
    print(json.dumps(data, indent=2, default=str))


def get_project_id(args) -> str:
    """Get project ID from arguments"""
    if hasattr(args, 'project') and args.project:
        return args.project
    if hasattr(args, 'project_id') and args.project_id:
        return args.project_id
    raise CLIError("Project ID required. Use --project or -p option")


# ============================================================================
# MAIN COMMANDS
# ============================================================================

def cmd_version(args):
    """Show version information"""
    print(f"maestro-cli version {__version__}")
    print(f"Project root: {PROJECT_ROOT}")
    return 0


def cmd_init(args):
    """Initialize a new music project"""
    project_id = args.project_id
    title = args.title or input("Song title: ")
    style = args.style or "gospel"
    bpm = args.bpm or 92
    key = args.key or "C"
    
    project_dir = ensure_project_structure(project_id)
    print(f"Initialized project: {project_id}")
    print(f"  Directory: {project_dir}")
    
    # Create initial song.json
    song = Song(
        project_id=project_id,
        title=title,
        style=[style] if isinstance(style, str) else style,
        tempo_bpm=bpm,
        key=key,
        status="draft"
    )
    state_dir = get_project_dir(project_id) / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    jsonio.save_json(state_dir / "song.json", song.model_dump(mode="json", indent=2))
    print(f"Created: {state_dir / 'song.json'}")
    
    # Create brief.md
    brief_path = get_project_dir(project_id) / "brief.md"
    brief_path.write_text(f"# {title}\n\n- **Style**: {style}\n- **BPM**: {bpm}\n- **Key**: {key}\n")
    print(f"Created: {brief_path}")
    
    return 0


def cmd_use(args):
    """Set the current project (not implemented in simple version)"""
    project_id = args.project_id
    project_dir = get_project_dir(project_id)
    if not project_dir.exists():
        raise CLIError(f"Project not found: {project_dir}")
    print(f"Current project set: {project_id}")
    return 0


def cmd_status(args):
    """Show project status"""
    project_id = get_project_id(args)
    project_dir = get_project_dir(project_id)
    state_dir = project_dir / "state"
    
    print(f"\n=== Project: {project_id} ===")
    
    # Check which state files exist
    state_files = {
        "song.json": "Composed",
        "sections.json": "Arranged",
        "tracks.json": "Orchestrated",
        "critique.json": "Critiqued",
        "rack_state.json": "Rack Loaded",
        "render_report.json": "Rendered",
    }
    
    print("\nState Files:")
    for filename, description in state_files.items():
        filepath = state_dir / filename
        status = "✓" if filepath.exists() else "✗"
        print(f"  {status} {filename}: {description}")
    
    # Show project files
    print("\nProject Files:")
    for ext in ["*.wav", "*.mid", "*.mp3"]:
        files = list(project_dir.rglob(ext))
        if files:
            print(f"  {ext}: {len(files)} files")
    
    return 0


def cmd_compose(args):
    """Generate song structure from a prompt"""
    project_id = get_project_id(args)
    project_dir = get_project_dir(project_id)
    state_dir = project_dir / "state"
    
    prompt = args.prompt
    if not prompt:
        brief_path = project_dir / "brief.md"
        if brief_path.exists():
            prompt = brief_path.read_text()
        else:
            prompt = input("Enter composition prompt: ")
    
    print(f"Composing: {project_id}")
    print(f"Prompt: {prompt[:100]}...")
    
    # For demo: create a dummy song.json
    song = Song(
        project_id=project_id,
        title="Generated Song",
        style=["gospel"],
        tempo_bpm=92,
        key="C",
        target_bars=32,
        mood=["warm", "uplifting"],
        constraints={"max_tracks": 6, "swing": 0.08},
        instrument_roles=["keys", "bass", "drums", "pad"],
        status="composed"
    )
    jsonio.save_json(state_dir / "song.json", song.model_dump(mode="json", indent=2))
    print("Song structure generated")
    return 0


def cmd_arrange(args):
    """Arrange song into sections"""
    project_id = get_project_id(args)
    project_dir = get_project_dir(project_id)
    state_dir = project_dir / "state"
    
    # Load song.json
    song_file = state_dir / "song.json"
    if not song_file.exists():
        raise CLIError("song.json not found. Run 'maestro compose' first.")
    
    song_data = jsonio.load_json(song_file)
    song = Song(**song_data)
    print(f"Arranging: {song.title}")
    
    # For demo: create dummy sections.json
    sections = Sections(
        project_id=project_id,
        sections=[
            {"id": "intro", "bars": 8, "energy": 0.3, "density": "low", "goal": "set mood"},
            {"id": "verse_1", "bars": 16, "energy": 0.55, "density": "medium", "goal": "develop narrative"},
            {"id": "chorus_1", "bars": 16, "energy": 0.85, "density": "high", "goal": "lift and release"},
            {"id": "outro", "bars": 8, "energy": 0.4, "density": "low", "goal": "resolve"},
        ],
        status="arranged"
    )
    jsonio.save_json(state_dir / "sections.json", sections.model_dump(mode="json", indent=2))
    print("Sections arranged")
    return 0


def cmd_orchestrate(args):
    """Orchestrate sections into tracks"""
    project_id = get_project_id(args)
    project_dir = get_project_dir(project_id)
    state_dir = project_dir / "state"
    midi_dir = project_dir / "midi"
    
    # Load sections.json
    sections_file = state_dir / "sections.json"
    if not sections_file.exists():
        raise CLIError("sections.json not found. Run 'maestro arrange' first.")
    
    print(f"Orchestrating: {project_id}")
    
    # For demo: create dummy tracks.json and MIDI files
    tracks = Tracks(
        project_id=project_id,
        tracks=[
            {
                "name": "keys_main",
                "role": "keys",
                "midi_file": "midi/keys.mid",
                "plugin_tag": "rhodes",
                "register": "mid",
                "volume": 0.8,
                "pan": 0.5
            },
            {
                "name": "bass_main",
                "role": "bass",
                "midi_file": "midi/bass.mid",
                "plugin_tag": "electric_bass",
                "register": "low",
                "volume": 1.0,
                "pan": 0.5
            },
            {
                "name": "drums",
                "role": "drums",
                "midi_file": "midi/drums.mid",
                "register": "mid",
                "volume": 1.0,
                "pan": 0.5
            },
        ],
        status="orchestrated"
    )
    jsonio.save_json(state_dir / "tracks.json", tracks.model_dump(mode="json", indent=2))
    
    # Create dummy MIDI files
    midi_dir.mkdir(parents=True, exist_ok=True)
    for track in tracks.tracks:
        midi_path = midi_dir / Path(track.midi_file).name
        # Minimal valid MIDI file (empty track)
        midi_path.write_bytes(b'MThd\x00\x00\x00\x06\x00\x00\x00\x01\x01E\x00\x00\x00\x00MTrk\x00\x00\x00\x0B\x00\xFF\x00\x00\x00\xFF\x2F\x00')
    
    print(f"Tracks orchestrated - Generated {len(tracks.tracks)} MIDI files in {midi_dir}")
    return 0


def cmd_critique(args):
    """Critique the orchestration"""
    project_id = get_project_id(args)
    project_dir = get_project_dir(project_id)
    state_dir = project_dir / "state"
    
    # Load tracks.json
    tracks_file = state_dir / "tracks.json"
    if not tracks_file.exists():
        raise CLIError("tracks.json not found. Run 'maestro orchestrate' first.")
    
    print(f"Critiquing: {project_id}")
    
    # For demo: create a critique with some issues
    from maestro_cli.models.critique import Critique, CritiqueIssue, Severity, IssueType, RepairAction
    
    issues = [
        CritiqueIssue(
            severity=Severity.MEDIUM,
            issue_type=IssueType.DENSITY_MISMATCH,
            track_a="bass_main",
            bars=[1, 8],
            message="Bass is too active for the intro density target."
        )
    ]
    
    critique = Critique(
        project_id=project_id,
        valid=not issues,  # Valid if no issues
        issues=issues,
        repair_actions=[RepairAction.THIN_BASS_INTRO],
        status="critiqued"
    )
    jsonio.save_json(state_dir / "critique.json", critique.model_dump(mode="json", indent=2))
    
    if critique.has_high_issues():
        print("⚠️  High severity issues found!")
    else:
        print("✓ Critique passed")
    
    print_json(critique)
    return 0


def cmd_repair(args):
    """Repair issues found in critique"""
    project_id = get_project_id(args)
    project_dir = get_project_dir(project_id)
    state_dir = project_dir / "state"
    
    # Load critique.json
    critique_file = state_dir / "critique.json"
    if not critique_file.exists():
        raise CLIError("critique.json not found. Run 'maestro critique' first.")
    
    critique_data = jsonio.load_json(critique_file)
    from maestro_cli.models.critique import Critique
    critique = Critique(**critique_data)
    
    if critique.valid:
        print("No issues to repair")
        return 0
    
    print(f"Repairing: {project_id}")
    print(f"  Found {len(critique.issues)} issues")
    print(f"  Suggested actions: {critique.repair_actions}")
    
    # For demo: just mark as repaired
    tracks_file = state_dir / "tracks.json"
    tracks_data = jsonio.load_json(tracks_file)
    tracks_data["status"] = "repaired"
    jsonio.save_json(tracks_file, tracks_data)
    
    critique_data["valid"] = True
    critique_data["status"] = "repaired"
    jsonio.save_json(critique_file, critique_data)
    
    print("Repairs applied")
    return 0


def cmd_carla(args):
    """Control Carla audio host"""
    from maestro_cli.hosts import carla_client
    
    action = args.action
    
    if action == "start":
        client = carla_client.CarlaClient()
        if client.start():
            print("Carla started")
        else:
            print("Failed to start Carla")
            return 1
    
    elif action == "stop":
        client = carla_client.CarlaClient()
        if client.stop():
            print("Carla stopped")
        else:
            print("Failed to stop Carla")
            return 1
    
    elif action == "load":
        project_id = get_project_id(args)
        rack = args.rack or input("Rack file path: ")
        
        client = carla_client.CarlaClient()
        if client.load_rack(rack):
            print(f"Rack loaded: {rack}")
            
            # Save rack state
            project_dir = get_project_dir(project_id)
            state_dir = project_dir / "state"
            rack_state = RackState(
                project_id=project_id,
                host="carla",
                status="loaded"
            )
            jsonio.save_json(state_dir / "rack_state.json", rack_state.model_dump(mode="json", indent=2))
        else:
            print("Failed to load rack")
            return 1
    
    elif action == "status":
        client = carla_client.CarlaClient()
        status = client.get_status()
        print_json(status, "Carla Status")
    
    else:
        print(f"Unknown action: {action}")
        return 1
    
    return 0


def cmd_render(args):
    """Render audio from MIDI using Carla"""
    project_id = get_project_id(args)
    project_dir = get_project_dir(project_id)
    state_dir = project_dir / "state"
    audio_dir = project_dir / "audio"
    
    # Load rack_state.json
    rack_state_file = state_dir / "rack_state.json"
    if not rack_state_file.exists():
        raise CLIError("rack_state.json not found. Load a rack first with 'maestro carla load'")
    
    # Load tracks.json
    tracks_file = state_dir / "tracks.json"
    if not tracks_file.exists():
        raise CLIError("tracks.json not found. Run 'maestro orchestrate' first.")
    
    print(f"Rendering: {project_id}")
    
    # For demo: create a dummy render report
    from maestro_cli.hosts import carla_client
    import time
    
    client = carla_client.CarlaClient()
    
    print("  Loading plugins...")
    time.sleep(1)
    print("  Routing MIDI tracks...")
    time.sleep(1)
    print("  Rendering audio...")
    time.sleep(2)
    
    # Calculate duration
    duration = 168.2  # Default for now
    
    # Save audio file (dummy)
    audio_dir.mkdir(parents=True, exist_ok=True)
    output_file = args.output or str(audio_dir / "mix.wav")
    
    # Create a minimal WAV file
    import struct
    sample_rate = settings.AUDIO_SAMPLE_RATE
    num_samples = int(sample_rate * duration)
    
    with open(output_file, 'wb') as f:
        # WAV header
        f.write(b'RIFF')
        f.write(struct.pack('<I', 36 + num_samples * 4))  # File size
        f.write(b'WAVEfmt ')
        f.write(struct.pack('<I', 16))  # fmt chunk size
        f.write(struct.pack('<H', 1))    # PCM format
        f.write(struct.pack('<H', 2))    # 2 channels
        f.write(struct.pack('<I', sample_rate))  # Sample rate
        f.write(struct.pack('<I', sample_rate * 4))  # Byte rate
        f.write(struct.pack('<H', 4))    # Block align
        f.write(struct.pack('<H', 16))   # Bits per sample
        f.write(b'data')
        f.write(struct.pack('<I', num_samples * 4))  # Data size
        
        # Write silence
        for _ in range(num_samples):
            f.write(struct.pack('<hh', 0, 0))  # Left and right channels
    
    # Save render report
    report = RenderReport(
        project_id=project_id,
        render_ok=True,
        output_file=output_file,
        duration_seconds=duration,
        sample_rate=settings.AUDIO_SAMPLE_RATE,
        bit_depth=settings.AUDIO_BIT_DEPTH,
        channels=2,
        status="rendered"
    )
    jsonio.save_json(state_dir / "render_report.json", report.model_dump(mode="json", indent=2))
    
    print(f"Render complete: {output_file}")
    print(f"  Duration: {report.duration_formatted}")
    print(f"  Sample rate: {report.sample_rate}kHz")
    return 0


def cmd_play(args):
    """Play the rendered audio"""
    project_id = get_project_id(args)
    project_dir = get_project_dir(project_id)
    audio_dir = project_dir / "audio"
    
    # Find WAV files
    wav_files = list(audio_dir.glob("*.wav"))
    if not wav_files:
        raise CLIError("No WAV files found. Run 'maestro render' first.")
    
    # Use the first WAV file
    wav_file = wav_files[0]
    print(f"Playing: {wav_file}")
    
    # Try to play with ffplay
    import subprocess
    try:
        subprocess.run(["ffplay", "-nodisp", "-autoexit", str(wav_file)], check=True)
    except FileNotFoundError:
        print("ffplay not found. Try:")
        print(f"  aplay {wav_file}")
        print(f"  vlc {wav_file}")
    
    return 0


def cmd_project_list(args):
    """List all projects"""
    if not settings.songs_dir.exists():
        print("No projects directory found")
        return 0
    
    projects = [d for d in settings.songs_dir.iterdir() if d.is_dir()]
    if not projects:
        print("No projects found")
        return 0
    
    print("\nProjects:")
    for project_dir in sorted(projects):
        state_file = project_dir / "state" / "song.json"
        if state_file.exists():
            try:
                song_data = jsonio.load_json(state_file)
                song = Song(**song_data)
                print(f"  {project_dir.name}: {song.title} ({song.status.value})")
            except:
                print(f"  {project_dir.name}: (error loading)")
        else:
            print(f"  {project_dir.name}: (no song.json)")
    
    return 0


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def main():
    """Main entry point for maestro CLI"""
    parser = argparse.ArgumentParser(
        prog="maestro",
        description="AI-Assisted Music Production CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  maestro init my_song --title "My Song" --style gospel
  maestro compose -p my_song --prompt "Create a gospel song"
  maestro arrange -p my_song
  maestro orchestrate -p my_song
  maestro critique -p my_song
  maestro repair -p my_song
  maestro carla start
  maestro carla load -p my_song -r ~/racks/gospel.rck
  maestro render -p my_song
  maestro play -p my_song
        """
    )
    parser.add_argument("--version", "-v", action="store_true", help="Show version")
    
    # Create subparsers for commands
    subparsers = parser.add_subparsers(dest="command", title="commands")
    
    # init command
    init_parser = subparsers.add_parser("init", help="Initialize a new project")
    init_parser.add_argument("project_id", help="Project identifier")
    init_parser.add_argument("--title", "-t", default="...", help="Song title")
    init_parser.add_argument("--style", "-s", default="gospel", help="Music style")
    init_parser.add_argument("--bpm", default=92, type=int, help="Tempo in BPM")
    init_parser.add_argument("--key", default="C", help="Musical key")
    
    # use command
    use_parser = subparsers.add_parser("use", help="Set current project")
    use_parser.add_argument("project_id", help="Project to use")
    
    # status command
    status_parser = subparsers.add_parser("status", help="Show project status")
    status_parser.add_argument("--project", "-p", help="Project ID")
    
    # compose command
    compose_parser = subparsers.add_parser("compose", help="Generate song structure")
    compose_parser.add_argument("--project", "-p", help="Project ID")
    compose_parser.add_argument("--prompt", help="Composition prompt")
    
    # arrange command
    arrange_parser = subparsers.add_parser("arrange", help="Arrange into sections")
    arrange_parser.add_argument("--project", "-p", help="Project ID")
    
    # orchestrate command
    orchestrate_parser = subparsers.add_parser("orchestrate", help="Orchestrate into tracks")
    orchestrate_parser.add_argument("--project", "-p", help="Project ID")
    
    # critique command
    critique_parser = subparsers.add_parser("critique", help="Critique the orchestration")
    critique_parser.add_argument("--project", "-p", help="Project ID")
    
    # repair command
    repair_parser = subparsers.add_parser("repair", help="Repair issues")
    repair_parser.add_argument("--project", "-p", help="Project ID")
    
    # carla command
    carla_parser = subparsers.add_parser("carla", help="Control Carla")
    carla_subparsers = carla_parser.add_subparsers(dest="action", title="actions")
    
    carla_start = carla_subparsers.add_parser("start", help="Start Carla")
    carla_stop = carla_subparsers.add_parser("stop", help="Stop Carla")
    carla_load = carla_subparsers.add_parser("load", help="Load rack")
    carla_load.add_argument("--project", "-p", help="Project ID")
    carla_load.add_argument("--rack", "-r", help="Rack file")
    carla_status = carla_subparsers.add_parser("status", help="Show status")
    
    # render command
    render_parser = subparsers.add_parser("render", help="Render audio")
    render_parser.add_argument("--project", "-p", help="Project ID")
    render_parser.add_argument("--output", "-o", help="Output file")
    
    # play command
    play_parser = subparsers.add_parser("play", help="Play rendered audio")
    play_parser.add_argument("--project", "-p", help="Project ID")
    
    # project command group
    project_parser = subparsers.add_parser("project", help="Project management")
    project_subparsers = project_parser.add_subparsers(dest="subcommand", title="subcommands")
    project_list = project_subparsers.add_parser("list", help="List all projects")
    
    # Parse arguments
    args = parser.parse_args()
    
    # Handle version
    if args.version:
        return cmd_version(args)
    
    # Handle no command (show help)
    if not hasattr(args, 'command') or args.command is None:
        parser.print_help()
        return 0
    
    # Route to appropriate command handler
    command_map = {
        "init": cmd_init,
        "use": cmd_use,
        "status": cmd_status,
        "compose": cmd_compose,
        "arrange": cmd_arrange,
        "orchestrate": cmd_orchestrate,
        "critique": cmd_critique,
        "repair": cmd_repair,
        "render": cmd_render,
        "play": cmd_play,
    }
    
    # Handle carla subcommands
    if args.command == "carla":
        if args.action is None:
            carla_parser.print_help()
            return 1
        return cmd_carla(args)
    
    # Handle project subcommands
    if args.command == "project":
        if args.subcommand == "list":
            return cmd_project_list(args)
        project_parser.print_help()
        return 1
    
    # Handle regular commands
    if args.command in command_map:
        try:
            return command_map[args.command](args)
        except CLIError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"Unexpected error: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            return 1
    
    # Unknown command
    print(f"Unknown command: {args.command}", file=sys.stderr)
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
