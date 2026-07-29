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
    """Mock provider for unit testing and offline development."""

    def generate_midi_tokens(self, prompt: str, max_tokens: int = 512, temperature: float = 0.7) -> str:
        # Generate a deterministic sequence of AMT tokens representing a simple chord progression
        tokens = [
            "ONSET_0 INST_piano PITCH_60 DUR_50 VEL_90",
            "ONSET_0 INST_piano PITCH_64 DUR_50 VEL_85",
            "ONSET_0 INST_piano PITCH_67 DUR_50 VEL_85",
            "ONSET_100 INST_bass PITCH_36 DUR_100 VEL_95",
            "ONSET_100 INST_piano PITCH_62 DUR_50 VEL_88",
            "ONSET_100 INST_piano PITCH_65 DUR_50 VEL_85",
            "ONSET_100 INST_piano PITCH_69 DUR_50 VEL_85",
        ]
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
    """Provider for vLLM inference server (local or remote HTTP API)."""

    def __init__(self, api_url: str = "http://localhost:8000/v1", model_name: str = "MIDI-LLM-1B", tokenizer: Optional[AMTTokenizer] = None):
        super().__init__(tokenizer)
        self.api_url = api_url.rstrip("/")
        self.model_name = model_name

    def generate_midi_tokens(self, prompt: str, max_tokens: int = 512, temperature: float = 0.7) -> str:
        import urllib.request
        
        payload = {
            "model": self.model_name,
            "prompt": f"Generate MIDI: {prompt}",
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        req = urllib.request.Request(
            f"{self.api_url}/completions",
            data=json.dumps(payload).encode('utf-8'),
            headers={"Content-Type": "application/json"}
        )
        
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                res_data = json.loads(response.read().decode('utf-8'))
                return res_data["choices"][0]["text"]
        except Exception as e:
            # Fallback to Mock in case local server is not reachable
            return MockMidiLLMProvider(self.tokenizer).generate_midi_tokens(prompt, max_tokens, temperature)
