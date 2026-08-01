"""
MIDI-LLM Provider Interface and Engine implementations.
Supports local GGUF via llama.cpp, vLLM HTTP endpoint, and Mock fallbacks.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import os
import json
from maestro_cli.amt_tokenizer import AMTTokenizer, NoteEvent


class BaseMidiLLMProvider(ABC):
    """Abstract base class for MIDI-LLM inference providers."""

    def __init__(self, tokenizer: Optional[AMTTokenizer] = None):
        self.tokenizer = tokenizer or AMTTokenizer()

    @abstractmethod
    def generate_midi_tokens(self, prompt: str, max_tokens: int = 512, temperature: float = 0.7) -> str:
        """Generate raw AMT tokens from a textual / context prompt."""
        pass

    def generate_notes(self, prompt: str, max_tokens: int = 512, temperature: float = 0.7) -> List[NoteEvent]:
        """Generate NoteEvent objects using AMT tokenization."""
        raw_tokens = self.generate_midi_tokens(prompt, max_tokens=max_tokens, temperature=temperature)
        return self.tokenizer.decode_tokens(raw_tokens)


class MockMidiLLMProvider(BaseMidiLLMProvider):
    """Mock provider generating dynamic, musically-coherent AMT tokens offline."""

    def generate_midi_tokens(self, prompt: str, max_tokens: int = 512, temperature: float = 0.7) -> str:
        # Simple string-matching/heuristic parser for dynamic local generation
        prompt_lower = prompt.lower()
        
        # 1. Detect Musical Key (Default: C major / A minor)
        key_offsets = {
            "c": 0, "c#": 1, "d": 2, "d#": 3, "e": 4, "f": 5, "f#": 6, "g": 7, "g#": 8, "a": 9, "a#": 10, "b": 11
        }
        root_offset = 0
        for k, offset in key_offsets.items():
            if f"key {k}" in prompt_lower or f"key of {k}" in prompt_lower or f"role {k}" in prompt_lower:
                root_offset = offset
                break

        # Define chords progressions based on key signature
        # Standard: I - vi - IV - V (e.g. C -> Am -> F -> G)
        scale_chords = [
            [60, 64, 67, 71],  # I maj7 (e.g. C maj7)
            [57, 60, 64, 67],  # vi min7 (e.g. A min7)
            [53, 57, 60, 64],  # IV maj7 (e.g. F maj7)
            [55, 59, 62, 65],  # V 7 (e.g. G 7)
        ]
        
        # Apply key transposition
        transposed_chords = []
        for chord in scale_chords:
            transposed_chords.append([n + root_offset for n in chord])

        tokens = []
        onset = 0
        
        # Determine track role from prompt
        is_bass = "bass" in prompt_lower
        is_drums = "drum" in prompt_lower
        is_melody = "lead" in prompt_lower or "melody" in prompt_lower
        
        # Loop over 4 bars (4 beats each)
        for bar in range(4):
            chord = transposed_chords[bar % len(transposed_chords)]
            root_note = chord[0] - 24 # 2 octaves down for bass
            
            # Default block piano chords generated for all tracks as reference
            for note in chord:
                tokens.append(f"ONSET_{onset} INST_piano PITCH_{note} DUR_480 VEL_85")

            if is_bass:
                # Bouncy baseline aligned to chords
                tokens.append(f"ONSET_{onset} INST_bass PITCH_{root_note} DUR_120 VEL_100")
                tokens.append(f"ONSET_{onset+240} INST_bass PITCH_{root_note+7} DUR_120 VEL_90")
            elif is_drums:
                # Classic 4x4 or boom-bap drum pattern
                tokens.append(f"ONSET_{onset} INST_drums PITCH_36 DUR_60 VEL_110") # Kick
                tokens.append(f"ONSET_{onset+120} INST_drums PITCH_42 DUR_40 VEL_80")  # HH
                tokens.append(f"ONSET_{onset+240} INST_drums PITCH_38 DUR_60 VEL_105") # Snare
                tokens.append(f"ONSET_{onset+360} INST_drums PITCH_42 DUR_40 VEL_85")  # HH
            elif is_melody:
                # Arpeggiate melody notes from chord
                tokens.append(f"ONSET_{onset} INST_lead PITCH_{chord[2]+12} DUR_120 VEL_95")
                tokens.append(f"ONSET_{onset+240} INST_lead PITCH_{chord[3]+12} DUR_120 VEL_90")
            
            onset += 480
            
        return " ".join(tokens)


class LlamaCppMidiProvider(BaseMidiLLMProvider):
    """Provider for local GGUF models using llama.cpp python bindings."""

    def __init__(self, model_path: str, tokenizer: Optional[AMTTokenizer] = None, n_ctx: int = 4096):
        super().__init__(tokenizer)
        self.model_path = model_path
        self.n_ctx = n_ctx
        self._llama_model = None

    def _load_model(self):
        if self._llama_model is None:
            try:
                from llama_cpp import Llama
                self._llama_model = Llama(model_path=self.model_path, n_ctx=self.n_ctx, verbose=False)
            except ImportError:
                raise RuntimeError("llama-cpp-python is not installed. Run 'pip install llama-cpp-python'.")

    def generate_midi_tokens(self, prompt: str, max_tokens: int = 512, temperature: float = 0.7) -> str:
        self._load_model()
        formatted_prompt = f"<|user|>\nGenerate MIDI sequence for: {prompt}<|end|>\n<|assistant|>\n"
        output = self._llama_model(
            formatted_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            stop=["<|end|>", "</s>"]
        )
        return output["choices"][0]["text"]


class VllmMidiProvider(BaseMidiLLMProvider):
    """Provider for vLLM / llama.cpp HTTP inference server (local or remote OpenAI-compatible API)."""

    def __init__(
        self,
        api_url: Optional[str] = None,
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
        tokenizer: Optional[AMTTokenizer] = None,
    ):
        super().__init__(tokenizer)
        from maestro_cli.config import settings  # lazy import to avoid circular deps
        self.api_url = (api_url or settings.MIDI_LLM_BASE_URL).rstrip("/")
        self.model_name = model_name or settings.MIDI_LLM_MODEL
        self.api_key = api_key or settings.MIDI_LLM_API_KEY

    def generate_midi_tokens(self, prompt: str, max_tokens: int = 512, temperature: float = 0.7) -> str:
        import urllib.request
        import urllib.error
        
        payload = {
            "model": self.model_name,
            "prompt": f"Generate MIDI: {prompt}",
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        req = urllib.request.Request(
            f"{self.api_url}/completions",
            data=json.dumps(payload).encode('utf-8'),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            }
        )
        
        try:
            with urllib.request.urlopen(req, timeout=180) as response:
                res_data = json.loads(response.read().decode('utf-8'))
                return res_data["choices"][0]["text"]
        except (urllib.error.URLError, KeyError, TimeoutError) as e:
            # Fallback to Mock in case local server is not reachable
            import logging
            logging.getLogger(__name__).warning(
                f"[VllmMidiProvider] Local MIDI-LLM server unreachable ({e}) — using MockMidiLLMProvider"
            )
            return MockMidiLLMProvider(self.tokenizer).generate_midi_tokens(prompt, max_tokens, temperature)


def get_midi_llm_provider(tokenizer: Optional[AMTTokenizer] = None) -> BaseMidiLLMProvider:
    """
    Factory: returns the best available MIDI-LLM provider.
    Priority: VllmMidiProvider (llama.cpp HTTP) → MockMidiLLMProvider (offline).
    """
    return VllmMidiProvider(tokenizer=tokenizer)
