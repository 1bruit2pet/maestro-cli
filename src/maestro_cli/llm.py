"""
Dual-LLM Router for Maestro CLI.

Architecture tout-local :
  1. call_compose_llm()  → llama-server port 8081 (Qwen 4B / modèle configuré)
                           Utilisé par `maestro compose` — génère du JSON structuré.
  2. call_midi_llm()     → llama-server port 8080 (MIDI-LLM, déjà en prod)
                           Utilisé par `maestro orchestrate` — génère des tokens AMT.

Les deux instances sont des serveurs llama.cpp distincts.
"""
import json
import logging
import urllib.request
import urllib.error
from typing import Optional

from maestro_cli.config import settings

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# 1. COMPOSITION LLM  (llama-server port 8081 — Qwen 4B)
# ─────────────────────────────────────────────────────────────────────────────

def call_compose_llm(
    prompt: str,
    max_tokens: int = 1024,
    temperature: float = 0.3,
    system_prompt: Optional[str] = None,
) -> str:
    """
    Appelle le LLM de composition local (modèle configuré sur port 8081).
    Utilise l'endpoint /chat/completions (OpenAI-compatible).
    Lève une exception si l'appel échoue (le caller gère le fallback).
    """
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": settings.LLM_MODEL,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

    url = f"{settings.LLM_BASE_URL}/chat/completions"
    logger.info(f"[Compose LLM] → {url}  model={settings.LLM_MODEL}")

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.LLM_API_KEY or 'local'}",
        },
    )

    with urllib.request.urlopen(req, timeout=settings.LLM_TIMEOUT) as response:
        res_data = json.loads(response.read().decode("utf-8"))
        return res_data["choices"][0]["message"]["content"].strip()


# ─────────────────────────────────────────────────────────────────────────────
# 2. MIDI LLM  (llama-server port 8080 — MIDI-LLM en prod)
# ─────────────────────────────────────────────────────────────────────────────

def call_midi_llm(
    prompt: str,
    max_tokens: int = 512,
    temperature: float = 0.7,
) -> str:
    """
    Appelle le MIDI-LLM local (port 8080) pour générer des tokens AMT.
    Bascule automatiquement sur MockMidiLLMProvider si le serveur est inaccessible.
    """
    payload = {
        "model": settings.MIDI_LLM_MODEL,
        "prompt": f"Generate MIDI: {prompt}",
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

    url = f"{settings.MIDI_LLM_BASE_URL}/completions"
    logger.info(f"[MIDI LLM] → {url}  model={settings.MIDI_LLM_MODEL}")

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.MIDI_LLM_API_KEY}",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=settings.MIDI_LLM_TIMEOUT) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            return res_data["choices"][0]["text"]
    except (urllib.error.URLError, KeyError, TimeoutError) as e:
        logger.warning(
            f"[MIDI LLM] Serveur port 8080 inaccessible ({e}) — bascule MockMidiLLMProvider"
        )
        from maestro_cli.midi_llm_provider import MockMidiLLMProvider
        return MockMidiLLMProvider().generate_midi_tokens(prompt, max_tokens, temperature)


# ─────────────────────────────────────────────────────────────────────────────
# Alias legacy (rétrocompatibilité)
# ─────────────────────────────────────────────────────────────────────────────

def call_llm(prompt: str, max_tokens: int = 1024, temperature: float = 0.3) -> str:
    """Alias legacy → call_compose_llm()."""
    try:
        return call_compose_llm(prompt, max_tokens=max_tokens, temperature=temperature)
    except Exception as e:
        logger.error(f"[call_llm] échec : {e}")
        return "{}"
