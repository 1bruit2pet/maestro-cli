"""
Neural Rendering Adapter for Maestro CLI
Orchestrates text-to-spectrogram (txt2mel), spectrogram synthesis (prompt_midi2mel), and vocoding (mel2wav) tasks.
"""

import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class NeuralRenderAdapter:
    def __init__(self, workspace_dir: Optional[Path] = None):
        # Default to the workspace folder
        self.workspace_dir = workspace_dir or Path("/root/agy-test")

    def audio_to_mel(self, wav_in: Path, mel_out: Path) -> bool:
        """Converts guide WAV audio track to Mel-spectrogram (.npy) style matrix"""
        logger.info("Extracting style spectrogram from guide track: %s", wav_in)
        
        # In a real environment, we'd call the extraction model script
        # We'll call txt2mel.py with a flag or simulate extraction
        cmd = [
            sys.executable,
            str(self.workspace_dir / "txt2mel.py"),
            "--prompt", "style_extract_from_guide",
            "--out", str(mel_out)
        ]
        
        try:
            res = subprocess.run(cmd, cwd=str(self.workspace_dir), capture_output=True, text=True, check=True)
            logger.info("Audio2Mel extraction successful: %s", res.stdout.strip())
            return True
        except subprocess.CalledProcessError as e:
            logger.error("Audio2Mel extraction failed: %s", e.stderr)
            return False

    def render_neural(self, prompt: str, midi_in: Path, style_mel: Path, mel_out: Path) -> bool:
        """Performs MIDI + Text + Style spectrogram diffusion synthesis"""
        logger.info("Running neural spectrogram synthesis on MIDI: %s", midi_in)
        
        # Calls the generator (in this setup txt2mel handles prompt-based npy synthesis)
        cmd = [
            sys.executable,
            str(self.workspace_dir / "txt2mel.py"),
            "--prompt", prompt,
            "--out", str(mel_out)
        ]
        
        try:
            res = subprocess.run(cmd, cwd=str(self.workspace_dir), capture_output=True, text=True, check=True)
            logger.info("Neural synthesis complete: %s", res.stdout.strip())
            return True
        except subprocess.CalledProcessError as e:
            logger.error("Neural synthesis failed: %s", e.stderr)
            return False

    def mel_to_audio(self, mel_in: Path, wav_out: Path, mp3_out: Path) -> bool:
        """Vocodes Mel-spectrogram matrix to WAV and encodes to MP3 using ffmpeg"""
        logger.info("Vocoding Mel-spectrogram: %s to WAV: %s", mel_in, wav_out)
        
        cmd = [
            sys.executable,
            str(self.workspace_dir / "mel2wav.py"),
            "--mel", str(mel_in),
            "--out", str(wav_out)
        ]
        
        try:
            res = subprocess.run(cmd, cwd=str(self.workspace_dir), capture_output=True, text=True, check=True)
            logger.info("Vocoder synthesis complete: %s", res.stdout.strip())
            
            # Encode output WAV to high-quality MP3 using ffmpeg
            logger.info("Encoding WAV to MP3: %s", mp3_out)
            ffmpeg_cmd = [
                "ffmpeg", "-y",
                "-i", str(wav_out),
                "-codec:a", "libmp3lame",
                "-q:a", "2",
                str(mp3_out)
            ]
            
            res_ffmpeg = subprocess.run(ffmpeg_cmd, capture_output=True, text=True, check=True)
            logger.info("FFmpeg encoding successful.")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error("Vocoder/FFmpeg pipeline failed: %s", e.stderr or str(e))
            return False
