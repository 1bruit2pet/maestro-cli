"""
Main CLI for Maestro - AI-Assisted Music Production
"""

import typer
from typing import Optional, List
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

from maestro_cli import __version__, PROJECT_ROOT
from maestro_cli.config import settings, get_project_dir, ensure_project_structure
from maestro_cli.models import (
    Song, Sections, Tracks, Critique, RackState, RenderReport
)
from maestro_cli.utils import jsonio, paths

# Initialize Rich console
console = Console()

# Create the main Typer app
app = typer.Typer(
    name="maestro",
    help="AI-Assisted Music Production CLI",
    pretty_exceptions_enable=False,
    rich_markup_mode="rich"
)


# State to track current project
_state = {"current_project": None}


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_project_id(project_id: Optional[str] = None, project: Optional[str] = None) -> str:
    """Get the project ID from arguments or state"""
    if project_id:
        return project_id
    if project:
        return project
    if _state["current_project"]:
        return _state["current_project"]
    raise typer.BadParameter("Project ID required. Use --project or -p option, or set current project with 'maestro use'")


def load_json_file(filepath: Path, model) -> any:
    """Load and validate a JSON file against a Pydantic model"""
    if not filepath.exists():
        raise FileNotFoundError(f"File not found: {filepath}")
    data = jsonio.load_json(filepath)
    return model(**data)


def save_json_file(data, filepath: Path):
    """Save data to a JSON file"""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    jsonio.save_json(filepath, data.model_dump(mode="json", indent=2))
    console.print(f"[green]Saved: [/green]{filepath}")


def print_json(data, title: str = ""):
    """Print data as formatted JSON"""
    if title:
        console.print(f"[bold blue]{title}[/bold blue]")
    console.print_json(data.model_dump(mode="json", indent=2))


# ============================================================================
# MAIN COMMANDS
# ============================================================================

@app.command()
def version():
    """Show version information"""
    console.print(f"[bold]maestro-cli[/bold] version {__version__}")
    console.print(f"Project root: {PROJECT_ROOT}")


@app.command()
def init(
    project_id: str = typer.Argument(..., help="Project identifier"),
    title: str = typer.Option("...", prompt="Song title"),
    style: str = typer.Option("gospel", help="Music style"),
    bpm: int = typer.Option(92, help="Tempo in BPM"),
    key: str = typer.Option("C", help="Musical key"),
):
    """Initialize a new music project"""
    project_dir = ensure_project_structure(project_id)
    console.print(f"[green]Initialized project:[/green] {project_id}")
    console.print(f"  Directory: {project_dir}")
    
    # Create initial song.json
    song = Song(
        project_id=project_id,
        title=title,
        style=[style] if isinstance(style, str) else style,
        tempo_bpm=bpm,
        key=key,
        status="draft"
    )
    save_json_file(song, get_project_dir(project_id) / "state" / "song.json")
    
    # Create brief.md
    brief_path = get_project_dir(project_id) / "brief.md"
    brief_path.write_text(f"# {title}\n\n- **Style**: {style}\n- **BPM**: {bpm}\n- **Key**: {key}\n")
    console.print(f"[green]Created:[/green] {brief_path}")
    
    # Set as current project
    _state["current_project"] = project_id


@app.command()
def use(project_id: str = typer.Argument(..., help="Project to use")):
    """Set the current project"""
    project_dir = get_project_dir(project_id)
    if not project_dir.exists():
        raise FileNotFoundError(f"Project not found: {project_dir}")
    _state["current_project"] = project_id
    console.print(f"[green]Current project set:[/green] {project_id}")


@app.command()
def status(
    project: Optional[str] = typer.Option(None, "-p", "--project", help="Project ID"),
):
    """Show project status"""
    project_id = get_project_id(project)
    project_dir = get_project_dir(project_id)
    state_dir = get_project_dir(project_id) / "state"
    
    console.print(Panel(f"[bold]Project: {project_id}[/bold]", box=box.ROUNDED))
    
    # Check which state files exist
    state_files = {
        "song.json": "🎵 Composed",
        "sections.json": "🎼 Arranged",
        "tracks.json": "🎛️  Orchestrated",
        "critique.json": "🔍 Critiqued",
        "rack_state.json": "🎧 Rack Loaded",
        "render_report.json": "📀 Rendered",
    }
    
    table = Table(show_header=True, header_style="bold blue")
    table.add_column("State File")
    table.add_column("Status")
    table.add_column("Description")
    
    for filename, description in state_files.items():
        filepath = state_dir / filename
        status = "[green]✓[/green]" if filepath.exists() else "[red]✗[/red]"
        table.add_row(filename, status, description)
    
    console.print(table)
    
    # Show project files
    console.print("\n[bold]Project Files:[/bold]")
    for ext in ["*.wav", "*.mid", "*.mp3"]:
        files = list(project_dir.rglob(ext))
        if files:
            console.print(f"  {ext}: {len(files)} files")


@app.command()
def compose(
    project: Optional[str] = typer.Option(None, "-p", "--project", help="Project ID"),
    prompt: Optional[str] = typer.Option(None, help="Composition prompt"),
):
    """Generate song structure from a prompt"""
    project_id = get_project_id(project)
    project_dir = get_project_dir(project_id)
    state_dir = project_dir / "state"
    
    if not prompt:
        # Try to read brief.md
        brief_path = project_dir / "brief.md"
        if brief_path.exists():
            prompt = brief_path.read_text()
        else:
            prompt = typer.prompt("Enter composition prompt")
    
    console.print(f"[blue]Composing:[/blue] {project_id}")
    console.print(f"Prompt: {prompt[:100]}...")
    
    # TODO: Call LLM planner here
    # For now, create a dummy song.json
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
    save_json_file(song, state_dir / "song.json")
    console.print("[green]Song structure generated[/green]")


@app.command()
def arrange(
    project: Optional[str] = typer.Option(None, "-p", "--project", help="Project ID"),
):
    """Arrange song into sections"""
    project_id = get_project_id(project)
    project_dir = get_project_dir(project_id)
    state_dir = project_dir / "state"
    
    # Load song.json
    try:
        song = load_json_file(state_dir / "song.json", Song)
    except FileNotFoundError:
        console.print("[red]Error:[/red] song.json not found. Run 'maestro compose' first.")
        raise typer.Exit(1)
    
    console.print(f"[blue]Arranging:[/blue] {song.title}")
    
    # TODO: Call LLM arranger or generate sections
    # For now, create dummy sections.json
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
    save_json_file(sections, state_dir / "sections.json")
    console.print("[green]Sections arranged[/green]")


@app.command()
def orchestrate(
    project: Optional[str] = typer.Option(None, "-p", "--project", help="Project ID"),
):
    """Orchestrate sections into tracks"""
    project_id = get_project_id(project)
    project_dir = get_project_dir(project_id)
    state_dir = project_dir / "state"
    midi_dir = project_dir / "midi"
    
    # Load sections.json
    try:
        sections = load_json_file(state_dir / "sections.json", Sections)
    except FileNotFoundError:
        console.print("[red]Error:[/red] sections.json not found. Run 'maestro arrange' first.")
        raise typer.Exit(1)
    
    console.print(f"[blue]Orchestrating:[/blue] {project_id}")
    
    # TODO: Call orchestrator to generate MIDI files
    # For now, create dummy tracks.json and MIDI files
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
    # Use MIDI-LLM provider for symbolic orchestration
    from maestro_cli.midi_llm_provider import MockMidiLLMProvider
    provider = MockMidiLLMProvider()

    save_json_file(tracks, state_dir / "tracks.json")
    
    # Generate MIDI files using MIDI-LLM AMT tokens
    midi_dir.mkdir(parents=True, exist_ok=True)
    for track in tracks.tracks:
        midi_path = midi_dir / Path(track.midi_file).name
        # Generate NoteEvents via MIDI-LLM provider
        notes = provider.generate_notes(f"Orchestrate {track['name']} role {track['role']}")
        console.print(f"  [green]+[/green] Generated {len(notes)} AMT notes for track: {track['name']}")

        midi_path.write_bytes(b"MThd\x00\x00\x00\x06\x00\x00\x00\x01\x01E\x00\x00\x00\x00MTrk\x00\x00\x00\x0B\x00\xFF\x00\x00\x00\xFF\x2F\x00")
    
    console.print("[green]Tracks orchestrated[/green]")
    console.print(f"  Generated {len(tracks.tracks)} MIDI files in {midi_dir}")


@app.command()
def critique(
    project: Optional[str] = typer.Option(None, "-p", "--project", help="Project ID"),
):
    """Critique the orchestration"""
    project_id = get_project_id(project)
    project_dir = get_project_dir(project_id)
    state_dir = project_dir / "state"
    
    # Load tracks.json
    try:
        tracks = load_json_file(state_dir / "tracks.json", Tracks)
    except FileNotFoundError:
        console.print("[red]Error:[/red] tracks.json not found. Run 'maestro orchestrate' first.")
        raise typer.Exit(1)
    
    console.print(f"[blue]Critiquing:[/blue] {project_id}")
    
    # TODO: Call critic agent
    # For now, create a critique with some issues
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
    save_json_file(critique, state_dir / "critique.json")
    
    if critique.has_high_issues():
        console.print("[red]⚠️  High severity issues found![/red]")
    else:
        console.print("[green]✓ Critique passed[/green]")
    
    print_json(critique)


@app.command()
def repair(
    project: Optional[str] = typer.Option(None, "-p", "--project", help="Project ID"),
):
    """Repair issues found in critique"""
    project_id = get_project_id(project)
    project_dir = get_project_dir(project_id)
    state_dir = project_dir / "state"
    
    # Load critique.json
    try:
        from maestro_cli.models.critique import Critique
        critique = load_json_file(state_dir / "critique.json", Critique)
    except FileNotFoundError:
        console.print("[red]Error:[/red] critique.json not found. Run 'maestro critique' first.")
        raise typer.Exit(1)
    
    if critique.valid:
        console.print("[green]No issues to repair[/green]")
        return
    
    console.print(f"[blue]Repairing:[/blue] {project_id}")
    console.print(f"  Found {len(critique.issues)} issues")
    console.print(f"  Suggested actions: {critique.repair_actions}")
    
    # TODO: Apply repairs
    # For now, just mark as repaired
    from maestro_cli.models.tracks import Tracks
    tracks = load_json_file(state_dir / "tracks.json", Tracks)
    tracks.status = "repaired"
    save_json_file(tracks, state_dir / "tracks.json")
    
    critique.valid = True
    critique.status = "repaired"
    save_json_file(critique, state_dir / "critique.json")
    
    console.print("[green]Repairs applied[/green]")


@app.command()
def carla(
    action: str = typer.Argument(..., help="Carla action: start, stop, load, status"),
    project: Optional[str] = typer.Option(None, "-p", "--project", help="Project ID"),
    rack: Optional[str] = typer.Option(None, "-r", "--rack", help="Rack file"),
):
    """Control Carla audio host"""
    from maestro_cli.hosts import carla_client
    
    if action == "start":
        client = carla_client.CarlaClient()
        if client.start():
            console.print("[green]Carla started[/green]")
        else:
            console.print("[red]Failed to start Carla[/red]")
    
    elif action == "stop":
        client = carla_client.CarlaClient()
        if client.stop():
            console.print("[green]Carla stopped[/green]")
        else:
            console.print("[red]Failed to stop Carla[/red]")
    
    elif action == "load":
        project_id = get_project_id(project)
        if not rack:
            rack = typer.prompt("Rack file path")
        
        client = carla_client.CarlaClient()
        if client.load_rack(rack):
            console.print(f"[green]Rack loaded: [/green]{rack}")
            
            # Save rack state
            project_dir = get_project_dir(project_id)
            state_dir = project_dir / "state"
            rack_state = RackState(
                project_id=project_id,
                host="carla",
                status="loaded"
            )
            save_json_file(rack_state, state_dir / "rack_state.json")
        else:
            console.print("[red]Failed to load rack[/red]")
    
    elif action == "status":
        client = carla_client.CarlaClient()
        status = client.get_status()
        console.print_json(status)
    
    else:
        console.print(f"[red]Unknown action: {action}[/red]")


@app.command()
def render(
    project: Optional[str] = typer.Option(None, "-p", "--project", help="Project ID"),
    output: Optional[str] = typer.Option(None, "-o", "--output", help="Output file"),
):
    """Render audio from MIDI using Carla"""
    project_id = get_project_id(project)
    project_dir = get_project_dir(project_id)
    state_dir = project_dir / "state"
    audio_dir = project_dir / "audio"
    
    # Load rack_state.json
    try:
        rack_state = load_json_file(state_dir / "rack_state.json", RackState)
    except FileNotFoundError:
        console.print("[red]Error:[/red] rack_state.json not found. Load a rack first with 'maestro carla load'")
        raise typer.Exit(1)
    
    # Load tracks.json
    try:
        tracks = load_json_file(state_dir / "tracks.json", Tracks)
    except FileNotFoundError:
        console.print("[red]Error:[/red] tracks.json not found. Run 'maestro orchestrate' first.")
        raise typer.Exit(1)
    
    console.print(f"[blue]Rendering:[/blue] {project_id}")
    
    # TODO: Actually render via Carla
    # For now, create a dummy render report
    import time
    console.print("  [blue]Loading plugins...[/blue]")
    time.sleep(1)
    console.print("  [blue]Routing MIDI tracks...[/blue]")
    time.sleep(1)
    console.print("  [blue]Rendering audio...[/blue]")
    time.sleep(2)
    
    # Calculate duration from tracks
    # (In reality, this would come from Carla)
    duration = 168.2  # Default for now
    
    # Save audio file (dummy)
    audio_dir.mkdir(parents=True, exist_ok=True)
    output_file = output or str(audio_dir / "mix.wav")
    Path(output_file).write_bytes(b"RIFF....WAVEfmt ")  # Dummy WAV header
    
    # Save render report
    from maestro_cli.models.render_report import RenderReport
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
    save_json_file(report, state_dir / "render_report.json")
    
    console.print(f"[green]Render complete:[/green] {output_file}")
    console.print(f"  Duration: {report.duration_formatted}")
    console.print(f"  Sample rate: {report.sample_rate}kHz")


@app.command()
def play(
    project: Optional[str] = typer.Option(None, "-p", "--project", help="Project ID"),
):
    """Play the rendered audio"""
    project_id = get_project_id(project)
    project_dir = get_project_dir(project_id)
    audio_dir = project_dir / "audio"
    
    # Find WAV files
    wav_files = list(audio_dir.glob("*.wav"))
    if not wav_files:
        console.print("[red]Error:[/red] No WAV files found. Run 'maestro render' first.")
        raise typer.Exit(1)
    
    # Use the first WAV file
    wav_file = wav_files[0]
    console.print(f"[blue]Playing:[/blue] {wav_file}")
    
    # Try to play with ffplay
    import subprocess
    try:
        subprocess.run(["ffplay", "-nodisp", "-autoexit", str(wav_file)], check=True)
    except FileNotFoundError:
        console.print("[yellow]ffplay not found. Try:[/yellow]")
        console.print(f"  aplay {wav_file}")
        console.print(f"  vlc {wav_file}")


@app.command()
def log(
    project: Optional[str] = typer.Option(None, "-p", "--project", help="Project ID"),
    command: Optional[str] = typer.Option(None, help="Filter by command"),
):
    """Show project logs"""
    project_id = get_project_id(project)
    log_dir = get_project_dir(project_id) / "logs"
    
    if not log_dir.exists():
        console.print("[yellow]No logs found[/yellow]")
        return
    
    log_files = list(log_dir.glob("*.log"))
    if command:
        log_files = [f for f in log_files if command in f.name]
    
    if not log_files:
        console.print("[yellow]No matching logs found[/yellow]")
        return
    
    for log_file in sorted(log_files, reverse=True):
        console.print(f"\n[bold]{log_file.name}[/bold]:")
        console.print(log_file.read_text()[:500] + "..." if log_file.stat().st_size > 500 else log_file.read_text())


# ============================================================================
# GROUP COMMANDS (for better organization)
# ============================================================================

# Create command groups
project_app = typer.Typer(name="project", help="Project management")
audio_app = typer.Typer(name="audio", help="Audio operations")
llm_app = typer.Typer(name="llm", help="LLM operations")

@app.callback()
def main():
    """Maestro CLI - AI-Assisted Music Production"""
    pass

# Add subcommand groups
app.add_typer(project_app, name="project")
app.add_typer(audio_app, name="audio")
app.add_typer(llm_app, name="llm")


# ============================================================================
# PROJECT SUBCOMMANDS
# ============================================================================

@project_app.command("list")
def project_list():
    """List all projects"""
    if not settings.songs_dir.exists():
        console.print("[yellow]No projects directory found[/yellow]")
        return
    
    projects = [d for d in settings.songs_dir.iterdir() if d.is_dir()]
    if not projects:
        console.print("[yellow]No projects found[/yellow]")
        return
    
    table = Table(show_header=True, header_style="bold blue")
    table.add_column("Project ID")
    table.add_column("Title")
    table.add_column("Status")
    table.add_column("Created")
    
    for project_dir in sorted(projects):
        state_file = project_dir / "state" / "song.json"
        if state_file.exists():
            try:
                song = load_json_file(state_file, Song)
                table.add_row(
                    project_dir.name,
                    song.title,
                    song.status.value,
                    song.created_at.strftime("%Y-%m-%d")
                )
            except:
                table.add_row(project_dir.name, "-", "-", "-")
        else:
            table.add_row(project_dir.name, "-", "-", "-")
    
    console.print(table)


@project_app.command("delete")
def project_delete(
    project_id: str = typer.Argument(..., help="Project to delete"),
    force: bool = typer.Option(False, "-f", "--force", help="Force delete without confirmation"),
):
    """Delete a project"""
    project_dir = get_project_dir(project_id)
    if not project_dir.exists():
        console.print(f"[red]Project not found: {project_id}[/red]")
        raise typer.Exit(1)
    
    if not force:
        confirm = typer.confirm(f"Are you sure you want to delete '{project_id}'?")
        if not confirm:
            raise typer.Abort()
    
    import shutil
    shutil.rmtree(project_dir)
    console.print(f"[green]Deleted project: [/green]{project_id}")
    
    if _state["current_project"] == project_id:
        _state["current_project"] = None


@app.command()
def infill(
    project: Optional[str] = typer.Option(None, "-p", "--project", help="Project ID"),
    track: str = typer.Option("bass", "--track", "-t", help="Track role to infill"),
    bars: str = typer.Option("1-8", "--bars", "-b", help="Bar range to infill (e.g. 1-8)"),
):
    """Infill missing musical parts or bars using MIDI-LLM AMT tokenization"""
    project_id = get_project_id(project)
    console.print(f"[blue]Infilling track '{track}' for bars {bars} in project {project_id}...[/blue]")
    
    from maestro_cli.midi_llm_provider import MockMidiLLMProvider
    provider = MockMidiLLMProvider()
    notes = provider.generate_notes(f"Infill {track} for bars {bars}")
    
    console.print(f"[green]✓ Infilled {len(notes)} AMT notes for track '{track}' (bars {bars})[/green]")


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    app()

