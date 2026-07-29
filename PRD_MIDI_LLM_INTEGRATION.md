# PRD : Intégration de l'Architecture MIDI-LLM & Modèle Hybride dans Maestro CLI

> **Document de Spécifications Produit (PRD)**  
> **Projet** : Maestro CLI — AI-Assisted Music Production CLI  
> **Feature** : Intégration de MIDI-LLM (Llama 3.2 1B + AMT) & Architecture Hybride (Desktop & Mobile)  
> **Date** : 2026-07-29  

---

## 1. Vision & Objectifs

L'objectif principal est de transformer **Maestro CLI** en une plateforme de production musicale assistée par IA de pointe en intégrant l'architecture **MIDI-LLM** ([slSeanWU/MIDI-LLM](https://github.com/slSeanWU/MIDI-LLM)). 

En remplaçant la dépendance aux seuls LLM textuels génériques par une **architecture hybride double-modèle**, Maestro CLI sera capable de :
1. **Générer directement de la musique symbolique polyphonique (Text-to-MIDI)** avec une cohérence rythmique et harmonique supérieure grâce à l'encodage **AMT (Anticipatory Music Transformer)**.
2. **Réparer et compléter intelligemment les morceaux (*Infilling*)** : Générer une ligne de basse manquante, insérer un solo entre deux sections ou corriger des fautes de conduite de voix.
3. **Exécuter l'inférence en local sur Desktop & Smartphone** grâce à des modèles ultra-légers (Llama 3.2 1B quantifié 4-bit) via `vLLM`, `llama.cpp` (GGUF) et **Meta ExecuTorch**.

---

## 2. Architecture Hybride Double-Modèle

```
+-----------------------------------------------------------------------------------+
|                           ENTRÉE UTILISATEUR (CLI / Prompt)                       |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
| 1. COUCHE PLANIFICATION (Planner Provider - ex: Qwen 2.5 1.5B / Llama 3.2 3B)     |
| • Analyse du prompt & Génération du Brief (`brief.md`, `song.json`)                |
| • Structuration des sections & Grilles d'accords (`sections.json`)                 |
| • Configuration des VST & Racks Carla (`rack_state.json`)                          |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
| 2. COUCHE GÉNÉRATION & INFILLING MIDI (MIDI-LLM Provider - Llama 3.2 1B + AMT)    |
| • Encodage / Décodage AMT (Onsets, Durations, Instrument-Pitch pairs)             |
| • Génération symbolique multi-pistes (`maestro orchestrate`)                      |
| • Infilling & Auto-complétion de pistes/mesures (`maestro infill`, `repair`)      |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
| 3. COUCHE EXECUTION & RENDU (Moteur Carla OSC / VST Synthesizers)                |
| • Export MIDI 2.0 / UMP & Rendu Audio WAV (`maestro render`)                      |
+-----------------------------------------------------------------------------------+
```

---

## 3. Spécifications Fonctionnelles

### F1. Module de Tokenization & Format Pivot AMT
* Implémentation du décodeur/encodeur AMT pour convertir les événements MIDI standard (`mido` / `pretty_midi`) en tokens AMT et réciproquement.
* Support du vocabulaire de 55 030 tokens MIDI complémentaires de Llama 3.2 1B.

### F2. Provider d'Inférence MIDI-LLM
* Abstraction `MidiLLMProvider` supportant :
  * Backend local `llama.cpp` (Fichiers `.gguf` quantifiés Q4_K_M).
  * Backend haute performance `vLLM` (API serveur local / distante).
  * Backend natif mobile **ExecuTorch** pour Android/iOS.
  * Backend Hugging Face `transformers` (Inférence standard PyTorch).

### F3. Commande `maestro infill` (Nouvelle Fonctionnalité)
* Permet de compléter une zone vide ou une piste spécifique dans un projet :
  * `--track <name>` : Générer ou compléter une piste spécifique (ex: basse) basée sur les autres pistes.
  * `--bars <start>-<end>` : Compléter une section temporelle précise (inbetweening).

### F4. Amélioration de `maestro repair`
* Utilisation de l'infilling MIDI-LLM pour corriger dynamiquement les erreurs détectées lors de la critique (notes hors-gamme, collisions de fréquences, trous rythmiques).

### F5. Suivi de Progression & Versionnement Git Intégré
* Rapport d'avancement automatique dans `PROGRESS_MIDI_LLM.md`.
* Validation et `git commit` systématique à chaque fin de phase.

---

## 4. Exigences Non-Fonctionnelles & Performance

* **Consommation RAM (Mobile)** : < 1.0 Go de RAM en quantification 4-bit (Q4_K_M).
* **Vitesse d'Inférence** : > 25 tokens/s sur CPU mobile moderne (Snapdragon / Apple Silicon) et > 100 tokens/s avec GPU/vLLM.
* **Compatibilité** : Python 3.10+, Linux, macOS, Android (via Termux/ExecuTorch).
