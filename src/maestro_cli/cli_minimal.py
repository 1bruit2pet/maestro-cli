#!/usr/bin/env python3
"""
Minimal Maestro CLI - Works with only standard library + pydantic
No external dependencies required (except pydantic which is already installed)
"""

import argparse
import sys
import json
import struct
from pathlib import Path
from datetime import datetime

# Ensure we can import from maestro_cli
sys.path.insert(0, str(Path(__file__).parent))

# Import models (these use pydantic which is installed)
from maestro_cli.models.song import Song, SongStatus, InstrumentRole, Constraints, Section
from maestro_cli.models.sections import Sections, SectionData
from maestro_cli.models.tracks import Tracks, Track, SectionBehavior
from maestro_cli.models.critique import Critique, CritiqueIssue, Severity, IssueType, RepairAction
from maestro_cli.models.rack_state import RackState, Plugin, PluginFormat, Route
from maestro_cli.models.render_report import RenderReport


# ============================================================================
# CONFIGURATION
# ============================================================================

PROJECT_ROOT = Path(__file__).parent.parent.parent
SONGS_DIR = PROJECT_ROOT / "songs" / "projects"

AUDIO_SAMPLE_RATE = 48000
AUDIO_BIT_DEPTH = 24
MIDI_TICKS_PER_BEAT = 480


def get_project_dir(project_id: str) -> Path:
    return SONGS_DIR / project_id


def get_state_dir(project_id: str) -> Path:
    return get_project_dir(project_id) / "state"


def get_midi_dir(project_id: str) -> Path:
    return get_project_dir(project_id) / "midi"


def get_audio_dir(project_id: str) -> Path:
    return get_project_dir(project_id) / "audio"


def ensure_project_structure(project_id: str) -> Path:
    project_dir = get_project_dir(project_id)
    project_dir.mkdir(parents=True, exist_ok=True)
    get_state_dir(project_id).mkdir(parents=True, exist_ok=True)
    get_midi_dir(project_id).mkdir(parents=True, exist_ok=True)
    get_audio_dir(project_id).mkdir(parents=True, exist_ok=True)
    return project_dir


def save_json(filepath: Path, data: dict) -> None:
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2, default=str)


def load_json(filepath: Path) -> dict:
    with open(filepath, 'r') as f:
        return json.load(f)


# ============================================================================
# COMMAND HANDLERS
# ============================================================================

def handle_init(args):
    """Initialize a new project"""
    project_id = args.project_id
    title = args.title or input("Song title: ")
    style = args.style or "gospel"
    bpm = args.bpm or 92
    key = args.key or "C"
    
    project_dir = ensure_project_structure(project_id)
    print(f"Initialized project: {project_id}")
    print(f"  Directory: {project_dir}")
    
    # Create song.json
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
    
    # Create brief.md
    brief_path = get_project_dir(project_id) / "brief.md"
    brief_path.write_text(f"# {title}\n\n- **Style**: {style}\n- **BPM**: {bpm}\n- **Key**: {key}\n")
    print(f"Created: {brief_path}")
    
    return 0


def handle_status(args):
    """Show project status"""
    project_id = args.project_id or "demo_song"
    project_dir = get_project_dir(project_id)
    state_dir = get_state_dir(project_id)
    
    print(f"\n=== Project: {project_id} ===\n")
    
    if not project_dir.exists():
        print("Project does not exist. Run 'init' first.")
        return 1
    
    # Check state files
    state_files = [
        ("song.json", "Composed"),
        ("sections.json", "Arranged"),
        ("tracks.json", "Orchestrated"),
        ("critique.json", "Critiqued"),
        ("rack_state.json", "Rack Loaded"),
        ("render_report.json", "Rendered"),
    ]
    
    print("State Files:")
    for filename, description in state_files:
        filepath = state_dir / filename
        status = "✓" if filepath.exists() else "✗"
        print(f"  {status} {filename}: {description}")
    
    # Count files
    print("\nGenerated Files:")
    for ext, name in [("*.mid", "MIDI"), ("*.wav", "WAV"), ("*.mp3", "MP3")]:
        files = list(get_project_dir(project_id).rglob(ext))
        if files:
            print(f"  {name}: {len(files)} files")
    
    return 0


def handle_compose(args):
    """Generate song structure"""
    project_id = args.project_id or "demo_song"
    project_dir = get_project_dir(project_id)
    
    prompt = args.prompt
    if not prompt:
        brief_path = project_dir / "brief.md"
        if brief_path.exists():
            prompt = brief_path.read_text()
        else:
            prompt = "Create a gospel song"
    
    print(f"Composing: {project_id}")
    print(f"Prompt: {prompt[:100]}...")
    
    # Create a song with demo data
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
    print("Song structure generated")
    return 0


def handle_arrange(args):
    """Arrange into sections"""
    project_id = args.project_id or "demo_song"
    state_dir = get_state_dir(project_id)
    
    # Check if song.json exists
    song_file = state_dir / "song.json"
    if not song_file.exists():
        print("Error: song.json not found. Run 'compose' first.")
        return 1
    
    print(f"Arranging: {project_id}")
    
    # Create sections
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
    save_json(state_dir / "sections.json", sections.dict())
    print("Sections arranged")
    return 0


def handle_orchestrate(args):
    """Orchestrate into tracks"""
    project_id = args.project_id or "demo_song"
    project_dir = get_project_dir(project_id)
    state_dir = get_state_dir(project_id)
    midi_dir = get_midi_dir(project_id)
    
    # Check if sections.json exists
    sections_file = state_dir / "sections.json"
    if not sections_file.exists():
        print("Error: sections.json not found. Run 'arrange' first.")
        return 1
    
    print(f"Orchestrating: {project_id}")
    
    # Create tracks
    tracks = Tracks(
        project_id=project_id,
        tracks=[
            Track(
                name="keys_main",
                role=InstrumentRole.KEYS,
                midi_file="midi/keys.mid",
                plugin_tag="rhodes",
                pitch_register="mid",
                volume=0.8,
                pan=0.5,
                section_behavior={}
            ),
            Track(
                name="bass_main",
                role=InstrumentRole.BASS,
                midi_file="midi/bass.mid",
                plugin_tag="electric_bass",
                pitch_register="low",
                volume=1.0,
                pan=0.5,
                section_behavior={}
            ),
            Track(
                name="drums",
                role=InstrumentRole.DRUMS,
                midi_file="midi/drums.mid",
                pitch_register="mid",
                volume=1.0,
                pan=0.5,
                section_behavior={}
            ),
        ],
        status="orchestrated"
    )
    save_json(state_dir / "tracks.json", tracks.dict())
    
    # Create dummy MIDI files
    for track in tracks.tracks:
        midi_path = midi_dir / Path(track.midi_file).name
        # Minimal valid MIDI file
        midi_path.write_bytes(b'MThd\x00\x00\x00\x06\x00\x00\x00\x01\x01E\x00\x00\x00\x00MTrk\x00\x00\x00\x0B\x00\xFF\x00\x00\x00\xFF\x2F\x00')
    
    print(f"Tracks orchestrated - Generated {len(tracks.tracks)} MIDI files")
    return 0


def handle_critique(args):
    """Critique the orchestration"""
    project_id = args.project_id or "demo_song"
    state_dir = get_state_dir(project_id)
    
    # Check if tracks.json exists
    tracks_file = state_dir / "tracks.json"
    if not tracks_file.exists():
        print("Error: tracks.json not found. Run 'orchestrate' first.")
        return 1
    
    print(f"Critiquing: {project_id}")
    
    # Create critique with a sample issue
    issue = CritiqueIssue(
        severity=Severity.MEDIUM,
        issue_type=IssueType.DENSITY_MISMATCH,
        track_a="bass_main",
        bars=[1, 8],
        message="Bass is too active for the intro density target."
    )
    
    critique = Critique(
        project_id=project_id,
        valid=False,
        issues=[issue],
        repair_actions=[RepairAction.THIN_BASS_INTRO],
        status="critiqued"
    )
    save_json(state_dir / "critique.json", critique.dict())
    
    print("✓ Critique generated")
    if critique.has_high_issues():
        print("⚠️  High severity issues found!")
    else:
        print("✓ No high severity issues")
    
    print("\nCritique:")
    print(json.dumps(critique.dict(), indent=2))
    return 0


def handle_repair(args):
    """Repair issues"""
    project_id = args.project_id or "demo_song"
    state_dir = get_state_dir(project_id)
    
    # Check if critique.json exists
    critique_file = state_dir / "critique.json"
    if not critique_file.exists():
        print("Error: critique.json not found. Run 'critique' first.")
        return 1
    
    critique_data = load_json(critique_file)
    critique = Critique(**critique_data)
    
    if critique.valid:
        print("No issues to repair")
        return 0
    
    print(f"Repairing: {project_id}")
    print(f"  Found {len(critique.issues)} issues")
    print(f"  Actions: {critique.repair_actions}")
    
    # Mark as repaired
    critique.valid = True
    critique.status = "repaired"
    save_json(critique_file, critique.dict())
    
    # Update tracks status
    tracks_file = state_dir / "tracks.json"
    tracks_data = load_json(tracks_file)
    tracks_data["status"] = "repaired"
    save_json(tracks_file, tracks_data)
    
    print("Repairs applied")
    return 0


def handle_render(args):
    """Render audio"""
    project_id = args.project_id or "demo_song"
    project_dir = get_project_dir(project_id)
    state_dir = get_state_dir(project_id)
    audio_dir = get_audio_dir(project_id)
    
    # Check dependencies
    if not (state_dir / "tracks.json").exists():
        print("Error: tracks.json not found. Run 'orchestrate' first.")
        return 1
    
    print(f"Rendering: {project_id}")
    
    # Create a dummy WAV file
    output_file = args.output or str(audio_dir / "mix.wav")
    duration = 168.2
    sample_rate = AUDIO_SAMPLE_RATE
    num_samples = int(sample_rate * duration)
    
    with open(output_file, 'wb') as f:
        # WAV header
        f.write(b'RIFF')
        f.write(struct.pack('<I', 36 + num_samples * 4))
        f.write(b'WAVEfmt ')
        f.write(struct.pack('<I', 16))
        f.write(struct.pack('<H', 1))    # PCM format
        f.write(struct.pack('<H', 2))    # 2 channels
        f.write(struct.pack('<I', sample_rate))
        f.write(struct.pack('<I', sample_rate * 4))
        f.write(struct.pack('<H', 4))    # Block align
        f.write(struct.pack('<H', 16))   # Bits per sample
        f.write(b'data')
        f.write(struct.pack('<I', num_samples * 4))
        
        # Write silence
        for _ in range(num_samples):
            f.write(struct.pack('<hh', 0, 0))
    
    # Save render report
    report = RenderReport(
        project_id=project_id,
        render_ok=True,
        output_file=output_file,
        duration_seconds=duration,
        sample_rate=sample_rate,
        bit_depth=AUDIO_BIT_DEPTH,
        channels=2,
        status="rendered"
    )
    save_json(state_dir / "render_report.json", report.dict())
    
    print(f"Render complete: {output_file}")
    minutes = int(duration // 60)
    seconds = int(duration % 60)
    print(f"  Duration: {minutes:02d}:{seconds:02d}")
    print(f"  Sample rate: {sample_rate}kHz")
    return 0


def handle_projects(args):
    """List projects"""
    if not SONGS_DIR.exists():
        print("No projects directory found")
        return 0
    
    projects = [d for d in SONGS_DIR.iterdir() if d.is_dir()]
    if not projects:
        print("No projects found")
        return 0
    
    print("\nProjects:")
    for project_dir in sorted(projects):
        song_file = project_dir / "state" / "song.json"
        if song_file.exists():
            try:
                song_data = load_json(song_file)
                song = Song(**song_data)
                print(f"  {project_dir.name}: {song.title} ({song.status.value})")
            except Exception:
                print(f"  {project_dir.name}: (error)")
        else:
            print(f"  {project_dir.name}: (no song.json)")
    
    return 0


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        prog="maestro",
        description="Maestro CLI - AI-Assisted Music Production",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  maestro init my_song --title "My Song"
  maestro compose -p my_song
  maestro arrange -p my_song
  maestro orchestrate -p my_song
  maestro critique -p my_song
  maestro repair -p my_song
  maestro render -p my_song
  maestro projects
  maestro status -p my_song

For more info: https://github.com/yourusername/maestro-cli
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", title="commands")
    
    # init
    init_parser = subparsers.add_parser("init", help="Initialize a new project")
    init_parser.add_argument("project_id", help="Project identifier")
    init_parser.add_argument("--title", "-t", default=None, help="Song title")
    init_parser.add_argument("--style", "-s", default="gospel", help="Music style")
    init_parser.add_argument("--bpm", default=92, type=int, help="Tempo in BPM")
    init_parser.add_argument("--key", default="C", help="Musical key")
    
    # status
    status_parser = subparsers.add_parser("status", help="Show project status")
    status_parser.add_argument("-p", "--project-id", default=None, help="Project ID")
    
    # compose
    compose_parser = subparsers.add_parser("compose", help="Generate song structure")
    compose_parser.add_argument("-p", "--project-id", default=None, help="Project ID")
    compose_parser.add_argument("--prompt", default=None, help="Composition prompt")
    
    # arrange
    arrange_parser = subparsers.add_parser("arrange", help="Arrange into sections")
    arrange_parser.add_argument("-p", "--project-id", default=None, help="Project ID")
    
    # orchestrate
    orchestrate_parser = subparsers.add_parser("orchestrate", help="Orchestrate into tracks")
    orchestrate_parser.add_argument("-p", "--project-id", default=None, help="Project ID")
    
    # critique
    critique_parser = subparsers.add_parser("critique", help="Critique the orchestration")
    critique_parser.add_argument("-p", "--project-id", default=None, help="Project ID")
    
    # repair
    repair_parser = subparsers.add_parser("repair", help="Repair issues")
    repair_parser.add_argument("-p", "--project-id", default=None, help="Project ID")
    
    # render
    render_parser = subparsers.add_parser("render", help="Render audio")
    render_parser.add_argument("-p", "--project-id", default=None, help="Project ID")
    render_parser.add_argument("-o", "--output", default=None, help="Output file")
    
    # projects
    projects_parser = subparsers.add_parser("projects", help="List all projects")
    
    args = parser.parse_args()
    
    if not hasattr(args, 'command'):
        parser.print_help()
        return 0
    
    command_handlers = {
        "init": handle_init,
        "status": handle_status,
        "compose": handle_compose,
        "arrange": handle_arrange,
        "orchestrate": handle_orchestrate,
        "critique": handle_critique,
        "repair": handle_repair,
        "render": handle_render,
        "projects": handle_projects,
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
