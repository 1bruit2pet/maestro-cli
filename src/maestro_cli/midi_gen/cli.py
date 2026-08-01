"""
Maestro MIDI Generator CLI — standalone generative commands
Usage:
  maestro gen new --genre boom-bap --bpm 90 --key Dm --bars 16 --out sketch.mid
  maestro gen chords --progression "i-VII-VI-VII" --key Dm --bpm 90 --out chords.mid
  maestro gen drums --style boom_bap --bars 8 --bpm 90 --swing 58 --out drums.mid
  maestro gen bass --chords-file chords.mid --key Dm --style boom_bap --out bass.mid
  maestro gen melody --key Dm --style jazzy --density 0.6 --bars 8 --out lead.mid
  maestro gen arrange --drums drums.mid --bass bass.mid --chords chords.mid --melody lead.mid --out song.mid
  maestro gen styles          # list available genres and styles
  maestro gen progressions    # list common progressions
"""

from __future__ import annotations
import typer
from typing import Optional, List
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich import box
from rich.panel import Panel

app = typer.Typer(
    name="gen",
    help="🎵 Real MIDI Generator — drums, bass, chords, melody, full arrangements",
    rich_markup_mode="rich",
)
console = Console()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_output(out: Optional[Path], default_name: str) -> Path:
    if out:
        return out
    return Path.cwd() / default_name


def _print_success(msg: str, path: Path):
    console.print(f"[bold green]✓[/bold green] {msg}")
    console.print(f"  [dim]→[/dim] [cyan]{path}[/cyan]")


def _build_progression(key_str: str, progression: str, bars_each: int, octave: int):
    """Helper to parse key + progression and return (key, prog) objects."""
    from maestro_cli.midi_gen.theory import Key, MusicTheory, GenreConfig
    key = Key.parse(key_str)
    prog = MusicTheory.build_progression(key, progression, bars_each=bars_each, octave=octave)
    return key, prog


# ---------------------------------------------------------------------------
# gen new — full quick-start arrangement
# ---------------------------------------------------------------------------

@app.command("new")
def gen_new(
    genre: str = typer.Option("boom-bap", "-g", "--genre",
        help="Genre: boom-bap | afrobeat | gospel | neo-soul | trap | rnb | funk | jazz | latin | house | reggae | lofi"),
    bpm: int = typer.Option(0, "-b", "--bpm", help="BPM (0 = genre default)"),
    key: str = typer.Option("Am", "-k", "--key",
        help="Key and mode: Dm, F#m, Bb, Cmaj, Adorian, etc."),
    bars: int = typer.Option(8, "-n", "--bars", help="Number of bars to generate"),
    out: Optional[Path] = typer.Option(None, "-o", "--out", help="Output .mid file"),
    swing: int = typer.Option(0, "--swing", help="Swing percentage (0=auto from genre, 50=straight, 58=light, 67=full)"),
    progression: str = typer.Option("", "-p", "--progression",
        help="Chord progression, e.g. 'i-VII-VI-VII' or 'Fm7-Bb7-EbMaj7'. Empty = genre default."),
    melody: bool = typer.Option(True, "--melody/--no-melody", help="Include melody track"),
    seed: Optional[int] = typer.Option(None, "--seed", help="Random seed for reproducibility"),
):
    """Generate a complete multi-track arrangement (.mid) from scratch."""
    from maestro_cli.midi_gen.theory import MusicTheory, Key, GENRE_CONFIGS
    from maestro_cli.midi_gen.generators import (
        DrumGenerator, BassGenerator, ChordsGenerator, MelodyGenerator
    )
    from maestro_cli.midi_gen.assembler import MidiAssembler

    cfg = MusicTheory.genre_config(genre)

    # Resolve defaults
    final_bpm = bpm if bpm > 0 else cfg.bpm_default
    final_swing = swing / 100.0 if swing > 0 else cfg.swing
    parsed_key = Key.parse(key)
    prog_str = progression if progression else cfg.default_progressions[0]
    out_path = _resolve_output(out, f"{genre.replace('-','_')}_{parsed_key.root}_{final_bpm}bpm.mid")

    bars_each = max(1, bars // 4)  # divide bars among 4 chord positions
    bars_each = min(bars_each, 4)
    _, prog = _build_progression(key, prog_str, bars_each, octave=3)

    console.print(Panel(
        f"[bold cyan]🎵 Generating {genre.upper()} arrangement[/bold cyan]\n"
        f"Key: [yellow]{key}[/yellow]  BPM: [yellow]{final_bpm}[/yellow]  "
        f"Bars: [yellow]{bars}[/yellow]  Swing: [yellow]{int(final_swing*100)}%[/yellow]\n"
        f"Progression: [magenta]{prog_str}[/magenta]",
        box=box.ROUNDED,
    ))

    assembler = MidiAssembler(bpm=final_bpm)

    # Drums
    console.print("  [dim]Generating drums...[/dim]")
    drums = DrumGenerator(
        style=cfg.drums_style, bars=bars, bpm=final_bpm, swing=final_swing,
        humanize_jitter_ms=cfg.humanize_jitter_ms, humanize_vel_stddev=cfg.humanize_vel_stddev,
        seed=seed,
    ).generate()
    assembler.add_track("Drums", drums)

    # Bass
    console.print("  [dim]Generating bass...[/dim]")
    bass = BassGenerator(
        progression=prog, style=cfg.bass_style, bars=bars, bpm=final_bpm, swing=final_swing,
        humanize_jitter_ms=cfg.humanize_jitter_ms, humanize_vel_stddev=cfg.humanize_vel_stddev,
        seed=(seed + 1) if seed else None,
    ).generate()
    assembler.add_track("Bass", bass)

    # Chords
    console.print("  [dim]Generating chords...[/dim]")
    chords_style = genre.replace("-", "_").replace(" ", "_")
    chords_track = ChordsGenerator(
        progression=prog, style=chords_style, bars=bars, bpm=final_bpm, swing=final_swing,
        humanize_jitter_ms=cfg.humanize_jitter_ms, humanize_vel_stddev=cfg.humanize_vel_stddev,
        seed=(seed + 2) if seed else None,
    ).generate()
    assembler.add_track("Chords", chords_track)

    # Melody
    if melody:
        console.print("  [dim]Generating melody...[/dim]")
        mel = MelodyGenerator(
            progression=prog, style=cfg.melody_style, bars=bars, bpm=final_bpm, swing=final_swing,
            humanize_jitter_ms=cfg.humanize_jitter_ms, humanize_vel_stddev=cfg.humanize_vel_stddev,
            seed=(seed + 3) if seed else None,
        ).generate()
        assembler.add_track("Melody", mel)

    # Export
    result = assembler.export_merged(out_path)
    _print_success(f"Full arrangement exported ({assembler.track_count} tracks)", result)


# ---------------------------------------------------------------------------
# gen chords — chords track only
# ---------------------------------------------------------------------------

@app.command("chords")
def gen_chords(
    progression: str = typer.Option("i-VII-VI-VII", "-p", "--progression",
        help="Chord progression: Roman numerals 'i-VII-VI-VII' or literal 'Fm7-Bb7-EbMaj7'"),
    key: str = typer.Option("Am", "-k", "--key", help="Musical key, e.g. Dm, Bb, F#m"),
    bpm: int = typer.Option(90, "-b", "--bpm"),
    bars: int = typer.Option(8, "-n", "--bars"),
    style: str = typer.Option("boom_bap", "-s", "--style",
        help="Voicing style: boom_bap|gospel|neo_soul|jazz_swing|funk|trap|lofi"),
    voicing: str = typer.Option("close", "--voicing",
        help="Voicing type: close|open|drop2"),
    octave: int = typer.Option(3, "--octave", help="Base octave for chords (3=mid, 4=bright)"),
    swing: int = typer.Option(50, "--swing", help="Swing % (50=straight, 58=medium, 67=full)"),
    out: Optional[Path] = typer.Option(None, "-o", "--out"),
    seed: Optional[int] = typer.Option(None, "--seed"),
):
    """Generate a chord progression MIDI track."""
    from maestro_cli.midi_gen.theory import Key, MusicTheory
    from maestro_cli.midi_gen.generators import ChordsGenerator
    from maestro_cli.midi_gen.assembler import MidiAssembler

    out_path = _resolve_output(out, "chords.mid")
    bars_each = max(1, bars // max(1, len(progression.split("-"))))
    _, prog = _build_progression(key, progression, bars_each, octave)

    console.print(f"[cyan]Chords:[/cyan] {progression} in [yellow]{key}[/yellow] @ {bpm} BPM")

    chords = ChordsGenerator(
        progression=prog, style=style, bars=bars, bpm=bpm,
        swing=swing / 100.0, octave=octave, voicing=voicing,
        seed=seed,
    ).generate()

    asm = MidiAssembler(bpm=bpm)
    asm.add_track("Chords", chords)
    result = asm.export_merged(out_path)
    _print_success("Chords exported", result)


# ---------------------------------------------------------------------------
# gen drums — drums track only
# ---------------------------------------------------------------------------

@app.command("drums")
def gen_drums(
    style: str = typer.Option("boom_bap", "-s", "--style",
        help="Drum style: boom_bap|afrobeat|gospel_swing|soul_layback|funk_pocket|trap|rnb|jazz_swing|latin_clave|house_4x4|reggae_one_drop|lofi_drums"),
    bars: int = typer.Option(8, "-n", "--bars"),
    bpm: int = typer.Option(90, "-b", "--bpm"),
    swing: int = typer.Option(50, "--swing",
        help="Swing % (50=straight, 58=light, 62=gospel, 67=full triplet)"),
    out: Optional[Path] = typer.Option(None, "-o", "--out"),
    seed: Optional[int] = typer.Option(None, "--seed"),
):
    """Generate a drum pattern MIDI track."""
    from maestro_cli.midi_gen.generators import DrumGenerator
    from maestro_cli.midi_gen.assembler import MidiAssembler

    out_path = _resolve_output(out, "drums.mid")
    console.print(f"[cyan]Drums:[/cyan] {style} | {bars} bars @ {bpm} BPM | swing {swing}%")

    drums = DrumGenerator(
        style=style, bars=bars, bpm=bpm, swing=swing / 100.0,
        seed=seed,
    ).generate()

    asm = MidiAssembler(bpm=bpm)
    asm.add_track("Drums", drums)
    result = asm.export_merged(out_path)
    _print_success("Drums exported", result)


# ---------------------------------------------------------------------------
# gen bass — bass track only
# ---------------------------------------------------------------------------

@app.command("bass")
def gen_bass(
    progression: str = typer.Option("i-VII-VI-VII", "-p", "--progression"),
    key: str = typer.Option("Am", "-k", "--key"),
    style: str = typer.Option("boom_bap", "-s", "--style",
        help="Bass style: boom_bap|afrobeat|gospel|neo_soul|funk|trap|rnb|jazz_walk|latin_tumbao|house|reggae_skank|lofi_bass"),
    bars: int = typer.Option(8, "-n", "--bars"),
    bpm: int = typer.Option(90, "-b", "--bpm"),
    octave: int = typer.Option(2, "--octave", help="Bass octave (1-2 typical)"),
    swing: int = typer.Option(50, "--swing"),
    out: Optional[Path] = typer.Option(None, "-o", "--out"),
    seed: Optional[int] = typer.Option(None, "--seed"),
):
    """Generate a bass line MIDI track following a chord progression."""
    from maestro_cli.midi_gen.theory import Key, MusicTheory
    from maestro_cli.midi_gen.generators import BassGenerator
    from maestro_cli.midi_gen.assembler import MidiAssembler

    out_path = _resolve_output(out, "bass.mid")
    bars_each = max(1, bars // max(1, len(progression.split("-"))))
    _, prog = _build_progression(key, progression, bars_each, octave=3)

    console.print(f"[cyan]Bass:[/cyan] {style} | {key} | {bars} bars @ {bpm} BPM")

    bass = BassGenerator(
        progression=prog, style=style, bars=bars, bpm=bpm,
        swing=swing / 100.0, octave=octave, seed=seed,
    ).generate()

    asm = MidiAssembler(bpm=bpm)
    asm.add_track("Bass", bass)
    result = asm.export_merged(out_path)
    _print_success("Bass exported", result)


# ---------------------------------------------------------------------------
# gen melody — melody track only
# ---------------------------------------------------------------------------

@app.command("melody")
def gen_melody(
    key: str = typer.Option("Am", "-k", "--key"),
    progression: str = typer.Option("i-VII-VI-VII", "-p", "--progression"),
    style: str = typer.Option("jazzy", "-s", "--style",
        help="Melody style: jazzy|bebop|gospel|soulful|call_response|melodic|smooth|funky|roots|lofi|latin|hypnotic"),
    bars: int = typer.Option(8, "-n", "--bars"),
    bpm: int = typer.Option(90, "-b", "--bpm"),
    octave: int = typer.Option(5, "--octave", help="Melody octave (4-6 typical)"),
    density: float = typer.Option(0.6, "--density", help="Note density 0.0-1.0"),
    swing: int = typer.Option(50, "--swing"),
    out: Optional[Path] = typer.Option(None, "-o", "--out"),
    seed: Optional[int] = typer.Option(None, "--seed"),
):
    """Generate a melody MIDI track over a chord progression."""
    from maestro_cli.midi_gen.theory import Key, MusicTheory
    from maestro_cli.midi_gen.generators import MelodyGenerator
    from maestro_cli.midi_gen.assembler import MidiAssembler

    out_path = _resolve_output(out, "melody.mid")
    bars_each = max(1, bars // max(1, len(progression.split("-"))))
    _, prog = _build_progression(key, progression, bars_each, octave=3)

    console.print(f"[cyan]Melody:[/cyan] {style} | {key} | {bars} bars @ {bpm} BPM | density {density:.0%}")

    melody = MelodyGenerator(
        progression=prog, style=style, bars=bars, bpm=bpm,
        swing=swing / 100.0, octave=octave, density=density,
        seed=seed,
    ).generate()

    asm = MidiAssembler(bpm=bpm)
    asm.add_track("Melody", melody)
    result = asm.export_merged(out_path)
    _print_success("Melody exported", result)


# ---------------------------------------------------------------------------
# gen arrange — combine separate MIDI files
# ---------------------------------------------------------------------------

@app.command("arrange")
def gen_arrange(
    drums: Optional[Path] = typer.Option(None, "--drums", help="Drums .mid file"),
    bass: Optional[Path] = typer.Option(None, "--bass", help="Bass .mid file"),
    chords: Optional[Path] = typer.Option(None, "--chords", help="Chords .mid file"),
    melody: Optional[Path] = typer.Option(None, "--melody", help="Melody .mid file"),
    bpm: int = typer.Option(90, "-b", "--bpm"),
    out: Optional[Path] = typer.Option(None, "-o", "--out"),
):
    """Combine separate MIDI part files into a single arrangement."""
    import mido as mido_lib
    from maestro_cli.midi_gen.assembler import MidiAssembler

    out_path = _resolve_output(out, "arrangement.mid")
    asm = MidiAssembler(bpm=bpm)
    added = []

    for name, part_path in [("Drums", drums), ("Bass", bass), ("Chords", chords), ("Melody", melody)]:
        if part_path and part_path.exists():
            src = mido_lib.MidiFile(str(part_path))
            for track in src.tracks:
                if any(msg.type in ("note_on", "note_off") for msg in track):
                    asm.add_track(name, track)
                    added.append(name)
                    break
        elif part_path:
            console.print(f"[yellow]⚠ Not found: {part_path}[/yellow]")

    if not added:
        console.print("[red]No valid MIDI parts found to arrange.[/red]")
        raise typer.Exit(1)

    console.print(f"[cyan]Arranging:[/cyan] {', '.join(added)}")
    result = asm.export_merged(out_path)
    _print_success(f"Arrangement with {len(added)} parts", result)


# ---------------------------------------------------------------------------
# gen styles — list available genres and styles
# ---------------------------------------------------------------------------

@app.command("styles")
def gen_styles():
    """List all available genres, drum styles, and progressions."""
    from maestro_cli.midi_gen.theory import GENRE_CONFIGS
    from maestro_cli.midi_gen.generators import DRUM_PATTERNS

    table = Table(title="🎸 Available Genres", box=box.ROUNDED, show_lines=True)
    table.add_column("Genre", style="cyan bold")
    table.add_column("BPM", justify="center")
    table.add_column("Default Key Mode")
    table.add_column("Default Progression", style="magenta")
    table.add_column("Swing")

    for genre, cfg in GENRE_CONFIGS.items():
        table.add_row(
            genre,
            f"{cfg.bpm_range[0]}-{cfg.bpm_range[1]}",
            cfg.key_mode,
            cfg.default_progressions[0],
            f"{int(cfg.swing*100)}%",
        )
    console.print(table)

    drum_table = Table(title="🥁 Available Drum Styles", box=box.SIMPLE)
    drum_table.add_column("Style", style="yellow")
    drum_table.add_column("Voices")
    for style, pattern in DRUM_PATTERNS.items():
        drum_table.add_row(style, ", ".join(pattern.keys()))
    console.print(drum_table)


# ---------------------------------------------------------------------------
# gen progressions — list common progressions
# ---------------------------------------------------------------------------

@app.command("progressions")
def gen_progressions():
    """Show common chord progressions with descriptions."""
    progs = [
        ("i-VII-VI-VII",    "Natural minor loop (boom-bap, neo-soul, lofi)"),
        ("i-iv-VII-III",    "Minor with flat-7 (hip-hop, trap)"),
        ("i-bVII-IV-V",     "Minor with raised 4th (afrobeats, dancehall)"),
        ("I-IV-V-I",        "Major I-IV-V cadence (gospel, pop)"),
        ("I-vi-IV-V",       "50s progression (pop, gospel, doo-wop)"),
        ("ii-V-I-VI",       "Jazz turnaround"),
        ("I-IV-V-IV",       "3-chord rock / reggae"),
        ("i-VI-III-VII",    "Andalusian cadence (flamenco, R&B)"),
        ("I-vi-ii-V",       "Classic jazz loop"),
        ("i-iv-i-V",        "Minor tonic–subdominant–dominant (latin, flamenco)"),
        ("Fm7-Bb7-EbMaj7-AbMaj7", "Gospel 2-5-1 in Eb (literal chords)"),
        ("Dm7-G7-CMaj7-Am7", "2-5-1-6 in C (jazz literal)"),
    ]

    table = Table(title="🎹 Common Chord Progressions", box=box.ROUNDED)
    table.add_column("Progression", style="magenta")
    table.add_column("Description")
    for prog, desc in progs:
        table.add_row(prog, desc)
    console.print(table)
    console.print("\n[dim]Use: maestro gen new -p 'i-VII-VI-VII' --key Dm[/dim]")
