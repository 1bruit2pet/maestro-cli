# Plan d'Exécution : Intégration MIDI-LLM & Modèle Hybride dans Maestro CLI

> **Plan de Développement Feuille de Route (Plan)**  
> **Méthodologie** : Développement par phases avec suivi d'avancement LLM (`PROGRESS_MIDI_LLM.md`) et versionnement Git automatique (`git commit`).

---

## 📊 Tableau de Bord du Projet (Phase Status)

| Phase | Description | Statut | Commit Git |
| :--- | :--- | :--- | :--- |
| **Phase 1** | Module de Encodage/Décodage AMT & Types MIDI | ⏳ En attente | - |
| **Phase 2** | Providers d'Inférence Hybride (vLLM / llama.cpp / HF) | ⏳ En attente | - |
| **Phase 3** | Intégration du Pipeline (`compose` & `orchestrate`) | ⏳ En attente | - |
| **Phase 4** | Feature `maestro infill` & Réparation Générative | ⏳ En attente | - |
| **Phase 5** | Quantification Mobile (GGUF/ExecuTorch) & Tests | ⏳ En attente | - |

---

## 🛠️ DÉTAIL DES PHASES D'EXÉCUTION

### Phase 1 : Core AMT Tokenization & Types (`src/maestro/core/amt.py`)
- [ ] Créer le tokenizer/detokenizer AMT (`AMTTokenizer`) pour convertir entre structures MIDI (`mido` / `pretty_midi`) et tokens de vocabulaire AMT.
- [ ] Gérer le vocabulaire des 55 030 tokens MIDI complémentaires de Llama 3.2.
- [ ] Ajouter les tests unitaires dans `tests/test_amt.py`.
- [ ] **Commit Git** : `feat(core): Add AMT tokenization and MIDI conversion module`

### Phase 2 : Providers LLM Hybrides (`src/maestro/providers/`)
- [ ] Définir l'interface abstraite `MidiLLMProvider` dans `src/maestro/providers/midi_llm_provider.py`.
- [ ] Implémenter le backend `LlamaCppMidiProvider` (Support GGUF local 4-bit).
- [ ] Implémenter le backend `VllmMidiProvider` (API serveur local vLLM).
- [ ] Mettre à jour `configs/app.toml` pour gérer la configuration des modèles hybrides (Planner + MIDI-LLM).
- [ ] **Commit Git** : `feat(providers): Add MIDI-LLM inference providers (llama.cpp, vLLM)`

### Phase 3 : Raccordement du Pipeline Principal (`src/maestro/commands/`)
- [ ] Raccorder `maestro orchestrate` au provider `MidiLLMProvider` pour la génération symbolique directe multi-pistes.
- [ ] Raccorder `maestro compose` au modèle Planner pour la création du projet et la structure d'accords.
- [ ] Ajouter des tests d'intégration dans `tests/test_midi_llm_pipeline.py`.
- [ ] **Commit Git** : `feat(pipeline): Integrate MIDI-LLM into compose and orchestrate CLI workflows`

### Phase 4 : Commande `maestro infill` & Réparation Intelligente
- [ ] Créer la nouvelle commande `maestro infill` dans `src/maestro/commands/infill.py`.
- [ ] Mettre à jour `maestro repair` pour utiliser l'infilling MIDI-LLM sur les pistes présentant des erreurs.
- [ ] Enregistrer la commande dans la CLI principale (`src/maestro/cli.py`).
- [ ] **Commit Git** : `feat(infill): Add maestro infill command and AI-driven song repair`

### Phase 5 : Export Mobile & Benchmarking
- [ ] Créer un script d'export/quantification vers GGUF Q4_K_M (`scripts/export_gguf.py`).
- [ ] Rédiger le guide d'optimisation et déploiement mobile (ExecuTorch / Android / iOS).
- [ ] Effectuer la validation globale et mettre à jour le rapport d'avancement final.
- [ ] **Commit Git** : `docs(mobile): Add GGUF export tools and mobile benchmark specs`

---

## 🤖 Protocole de Rapportation LLM

À la fin de chaque Phase :
1. Mise à jour de `PROGRESS_MIDI_LLM.md` avec le résumé des accomplissements et tests exécutés.
2. Exécution du commit Git structuré.
3. Notification claire dans le terminal / réponse utilisateur.
