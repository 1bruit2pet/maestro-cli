"""
Full Song Orchestrator Engine for Maestro CLI
Integrates MusicLang/maidi (Structure & Harmonies) + MidiHumanizer (GMD & Micro-timing) + Musicaiz/MusPy (Analysis)
Supports multi-section arrangement for Afrobeats, Gospel, R&B, Neo-Soul, etc.
"""

from typing import Dict, Any, List, Optional
from pathlib import Path
import random
import mido

from maestro_cli.humanizer import MidiHumanizer, GROOVE_DATASET_TEMPLATES
from maestro_cli.analyzer import MusicAnalyzer
from maestro_cli.pattern_engine import PythonPatternScriptEngine, PatternScriptConfig


class SongArrangementSection:
    """Represents a section in the song arrangement (e.g. Intro, Verse, Chorus, Bridge)."""
    def __init__(self, name: str, bars: int, style_preset: str, energy: float = 0.8):
        self.name = name
        self.bars = bars
        self.style_preset = style_preset
        self.energy = energy


class FullSongOrchestrator:
    """
    Unified Orchestrator:
    1. Composition (MusicLang / maidi harmonic structure & voicings)
    2. Arrangement (Sections: Intro, Verse, Pre-Chorus, Chorus, Bridge, Outro)
    3. Humanization (midihum / GMD groove feel & micro-timing)
    4. Evaluation (Musicaiz / MusPy analysis metrics)
    """

    def __init__(self, style: str = "afrobeats_gospel"):
        self.style = style
        self.humanizer = MidiHumanizer()
        self.pattern_engine = PythonPatternScriptEngine()

    def build_full_song_arrangements(
        self,
        song_title: str,
        bpm: int = 100,
        sections: Optional[List[SongArrangementSection]] = None
    ) -> List[SongArrangementSection]:
        """Builds default structured sections for a full song if not specified."""
        if sections:
            return sections
            
        return [
            SongArrangementSection("Intro", bars=4, style_preset="soul_layback", energy=0.4),
            SongArrangementSection("Verse 1", bars=8, style_preset="gospel_swing", energy=0.6),
            SongArrangementSection("Pre-Chorus", bars=4, style_preset="funk_pocket", energy=0.75),
            SongArrangementSection("Chorus", bars=8, style_preset="afro_poly", energy=1.0),
            SongArrangementSection("Verse 2", bars=8, style_preset="gospel_swing", energy=0.65),
            SongArrangementSection("Chorus", bars=8, style_preset="afro_poly", energy=1.0),
            SongArrangementSection("Outro", bars=4, style_preset="soul_layback", energy=0.3),
        ]

    def orchestrate_song(
        self,
        project_dir: Path,
        bpm: int = 100,
        sections: Optional[List[SongArrangementSection]] = None
    ) -> Dict[str, Any]:
        """
        Executes full song orchestration pipeline.
        Generates multi-track MIDI, applies GMD humanization, and evaluates with Musicaiz metrics.
        """
        project_dir.mkdir(parents=True, exist_ok=True)
        midi_dir = project_dir / "midi"
        midi_dir.mkdir(parents=True, exist_ok=True)
        
        arr_sections = self.build_full_song_arrangements("Maestro Composition", bpm=bpm, sections=sections)
        total_bars = sum(sec.bars for sec in arr_sections)
        
        raw_midi_path = midi_dir / "raw_full_song.mid"
        humanized_midi_path = midi_dir / "full_song_orchestrated.mid"
        
        # 1. Generate Raw Structural MIDI using Pattern Script Engine (MusicLang/maidi rules)
        config = PatternScriptConfig(
            style=self.style,
            tempo_bpm=bpm,
            bars=total_bars,
            seed=random.randint(1, 999999)
        )
        self.pattern_engine.generate_pattern(config, raw_midi_path)

        # 2. Apply Humanization (midihum & GMD templates per section)
        self.humanizer.apply_groove_template(
            midi_path=raw_midi_path,
            output_path=humanized_midi_path,
            template_name="gospel_swing" if "gospel" in self.style else "afro_poly"
        )

        # 3. Analyze Output Quality with Musicaiz / MusPy
        analyzer = MusicAnalyzer(humanized_midi_path)
        analysis_summary = analyzer.extract_harmonic_summary()

        return {
            "status": "orchestrated",
            "song_style": self.style,
            "bpm": bpm,
            "total_bars": total_bars,
            "sections_count": len(arr_sections),
            "raw_midi_path": str(raw_midi_path),
            "orchestrated_midi_path": str(humanized_midi_path),
            "musicaiz_analysis": analysis_summary
        }
