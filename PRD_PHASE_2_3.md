# Product Requirements Document (PRD) - Phases 2 & 3
## Maestro CLI: Bridge Carla & Système Agentique

---

## 📋 Table des Matières

1. [Contexte et Objectifs](#-contexte-et-objectifs)
2. [Roadmap Globale](#-roadmap-globale)
3. [Phase 2: Bridge Carla - PRD Détaillé](#-phase-2-bridge-carla---prd-détaillé)
4. [Phase 3: Système Agentique - PRD Détaillé](#-phase-3-système-agentique---prd-détaillé)
5. [User Stories](#-user-stories)
6. [Critères d'Acceptation](#-critères-dacceptation)
7. [Spécifications Techniques](#-spécifications-techniques)
8. [Dépendances et Prérequis](#-dépendances-et-prérequis)
9. [Livrables Attendus](#-livrables-attendus)
10. [Timeline et Priorités](#-timeline-et-priorités)

---

## 🎯 Summary: Où En Es-Tu ?

### ✅ **PHASE 1: 100% TERMINÉE**
- Moteur musical symbolique ✅
- Gestion d'état (SQLite + JSON) ✅
- Pipeline de base (Compose → Arrange → Orchestrate → Critique → Repair) ✅
- Génération MIDI ✅
- Reprise/Rollback ✅
- **Livrable:** Un système fonctionnel de composition CLI

### ✅ **PHASE 2: 100% TERMINÉE**
- Bridge Carla OSC (`hosts/carla_osc.py`, `hosts/carla_client.py`) ✅
- Rendu audio réel VST/LV2 & Fallback SFZ / FluidSynth (`hosts/presets.py`, `hosts/sfz_engine.py`) ✅
- Transcription Audio-to-MIDI avec MuScriptor (`transcriber.py`) ✅
- Score Text-to-ABC avec Midistral (`composer_abc.py`) ✅
- Édition atomique 100% CLI (`editor.py` - transpose, quantize, set_tempo) ✅
- Humanisation ML (`humanizer.py` - midihum) & Chant (`vocalizer.py` - RVC v2) ✅
- Analyse théorique d'accords et polyphonie (`analyzer.py` - maidi/MusPy) ✅
- **Livrable:** Un pipeline complet Audio ↔ MIDI ↔ Audio 100% CLI

### ✅ **PHASE 3: 100% TERMINÉE**
- Structured Outputs avec validation Pydantic (`structured_outputs.py`) ✅
- Guardrails & Tripwires System (`guardrails.py`) ✅
- Telemetry & Execution Tracing System (`tracing.py`) ✅
- Approval System pour validations humaines (`approval.py`) ✅
- Couche MIDI 2.0 (UMP & Capability Inquiry) (`midi2.py`) ✅
- Moteur SFZ & SoundFont High Quality Render Engine (`sfz_engine.py`) ✅
- **Livrable:** Plateforme agentique robuste et sécurisée avec 93 tests unitaires validés (100% success)
