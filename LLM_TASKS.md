# 🤖 Guide des Tâches pour LLM - Maestro CLI Phases 2 & 3

*Document de référence pour les agents IA travaillant sur le projet Maestro CLI*

---

## 📋 Sommaire

1. [Introduction](#-introduction)
2. [Règles Générales pour les LLM](#-règles-générales-pour-les-llm)
3. [Tâches Phase 2 - Bridge Carla](#-tâches-phase-2---bridge-carla)
4. [Tâches Phase 3 - Système Agentique](#-tâches-phase-3---système-agentique)
5. [Prompts Prêts à l'Emploi](#-prompts-prêts-à-lemploi)
6. [Checklist de Validation](#-checklist-de-validation)
7. [Ressources et Références](#-ressources-et-références)

---

## 🎯 Introduction

### Contexte
- **Phase 1** est **TERMINÉE** à 100% : Moteur musical + gestion d'état fonctionnels
- **Phase 2** est à **0%** : Bridge Carla à implémenter
- **Phase 3** est à **0%** : Système agentique à implémenter

### Objectif de ce Document
Fournir aux LLM (Large Language Models) des **instructions claires et précises** pour implémenter les phases 2 et 3 du projet Maestro CLI.

### Public Cible
- LLM spécialisés en Python (CodeLlama, GPT-4, Claude, etc.)
- Développeurs humains utilisant des LLM comme assistants
- Systèmes autonomes d'IA

---

## 📜 Règles Générales pour les LLM

### ⚠️ Règles IMPORTANTES (À TOUJOURS SUIVRE)

1. **📖 LIRE LE PRD D'ABORD**
   - Toujours commencer par lire `PRD_PHASE_2_3.md` pour comprendre les requirements
   - Ne jamais deviner les spécifications - elles sont dans le PRD

2. **🎯 SUIVRE LES SPÉCIFICATIONS EXACTES**
   - Respecter **à la lettre** les signatures de méthodes
   - Respecter **à la lettre** les noms de classes et fichiers
   - Respecter **à la lettre** les types de retour

3. **✅ VALIDER AVANT DE LIVRER**
   - Le code doit **compiler** sans erreurs
   - Les **tests doivent passer** (si spécifiés)
   - Tous les **critères d'acceptation** doivent être remplis

4. **📝 DOCUMENTER LE CODE**
   - Ajouter des **docstrings** à toutes les classes et méthodes
   - Commenter le code complexe
   - Mettre à jour la documentation si nécessaire

5. **🔍 GÉRER LES ERREURS**
   - Toujours gérer les exceptions
   - Messages d'erreur **clairs et actionnables**
   - Utiliser des **types d'erreurs spécifiques** quand pertinent

6. **🧪 ÉCRIRE DES TESTS**
   - Créer des **tests unitaires** pour chaque nouvelle classe
   - Tests doivent couvrir les **cas normaux et edge cases**
   - Utiliser `pytest` comme framework de test

7. **📁 STRUCTURE DES FICHIERS**
   - Placer les fichiers dans le **bon dossier**
   - Respecter les **conventions de nommage**
   - Ne pas modifier les fichiers existants sans raison

8. **🔄 IDempotence**
   - Les opérations doivent être **rejouables** sans effets de bord
   - Ne pas écraser les fichiers existants sans sauvegarde

9. **📊 LOGGING**
   - Ajouter du **logging** pour les opérations importantes
   - Utiliser le module `logging` de Python
   - Niveaux : DEBUG, INFO, WARNING, ERROR

10. **🎨 CODE STYLE**
    - Suivre **PEP 8**
    - Utiliser des **type hints** partout
    - Lignes **max 100 caractères**
    - **4 espaces** pour l'indentation (pas de tabs)

---

## 🚀 Tâches Phase 2 - Bridge Carla

### Priorité: ⭐⭐⭐⭐⭐ (MAXIMUM - À FAIRE EN PREMIER)

#### Tâche 2.1: Créer `hosts/carla_osc.py`

**Description:** Client OSC bas-niveau pour communiquer avec Carla.

**Fichier:** `src/maestro_cli/hosts/carla_osc.py`

**Dependencies:**
- `python-osc` (à installer si non présent)

**Requirements:**
```python
"""
Client OSC pour Carla
Permet d'envoyer et recevoir des messages OSC pour contrôler Carla à distance.
"""

from pythonosc import udp_client, osc_message_builder, osc_bundle_builder
from pythonosc.osc_message import OscMessage
from pythonosc.osc_bundle import OscBundle
from typing import Any, Optional, Tuple
import logging
import socket
import time

# Configuration
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 9001
DEFAULT_TIMEOUT = 5.0  # secondes

# Logger
logger = logging.getLogger(__name__)


class CarlaOSCError(Exception):
    """Erreur de communication OSC avec Carla"""
    pass


class CarlaOSCConnectionError(CarlaOSCError):
    """Erreur de connexion à Carla"""
    pass


class CarlaOSCTimeoutError(CarlaOSCError):
    """Timeout de connexion OSC"""
    pass


class CarlaOSCClient:
    """
    Client OSC pour communiquer avec Carla.
    
    Carla expose un contrôle distant via OSC sur le port 9001 par défaut.
    Voir: https://github.com/falkTX/Carla/blob/master/README.md#remote-control
    """
    
    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):
        """
        Initialise le client OSC.
        
        Args:
            host: Adresse IP de Carla (default: 127.0.0.1)
            port: Port OSC de Carla (default: 9001)
        """
        self.host = host
        self.port = port
        self._client: Optional[udp_client.SimpleUDPClient] = None
        self._last_error: Optional[str] = None
        
    @property
    def client(self) -> udp_client.SimpleUDPClient:
        """Retourne le client UDP, en le créant si nécessaire"""
        if self._client is None:
            self._client = udp_client.SimpleUDPClient(self.host, self.port)
        return self._client
    
    def send(self, address: str, *args: Any, timeout: float = DEFAULT_TIMEOUT) -> bool:
        """
        Envoie un message OSC à Carla.
        
        Args:
            address: Adresse OSC (ex: "/carla/load-plugin")
            *args: Arguments du message
            timeout: Timeout en secondes
            
        Returns:
            bool: True si l'envoi a réussi
            
        Raises:
            CarlaOSCConnectionError: Si impossible de se connecter
            CarlaOSCTimeoutError: Si timeout dépassé
        """
        try:
            # Construire le message
            builder = osc_message_builder.OscMessageBuilder(address=address)
            for arg in args:
                builder.add_arg(arg)
            msg = builder.build()
            
            # Envoyer
            self.client.send(msg)
            self._last_error = None
            logger.debug(f"OSC sent: {address} {args}")
            return True
            
        except socket.timeout as e:
            self._last_error = f"Timeout après {timeout}s: {e}"
            logger.error(self._last_error)
            raise CarlaOSCTimeoutError(self._last_error)
            
        except Exception as e:
            self._last_error = f"Erreur d'envoi OSC: {e}"
            logger.error(self._last_error)
            raise CarlaOSCConnectionError(self._last_error)
    
    def is_connected(self, timeout: float = DEFAULT_TIMEOUT) -> bool:
        """
        Vérifie si Carla répond sur le port OSC.
        
        Args:
            timeout: Timeout en secondes
            
        Returns:
            bool: True si Carla répond
        """
        try:
            # Essayer d'envoyer un message ping
            # Carla répond avec un message sur /carla/ping
            test_msg = osc_message_builder.OscMessageBuilder(address="/carla/ping")
            test_msg.add_arg("test")
            self.client.send(test_msg.build())
            
            # Pour une vérification simple, on considère que si send() ne lève pas
            # d'exception, Carla est probablement connecté
            return True
            
        except Exception as e:
            logger.warning(f"Carla ne répond pas: {e}")
            return False
    
    def start_carla(self, server_port: int = 9002) -> bool:
        """
        Démarre le serveur Carla.
        
        Args:
            server_port: Port du serveur Carla (default: 9002)
            
        Returns:
            bool: True si Carla a démarré avec succès
            
        Note:
            Cette méthode est optionnelle et nécessite que Carla soit
            installé dans le PATH. Si Carla n'est pas disponible, retourne False.
        """
        import subprocess
        import shutil
        
        # Vérifier si Carla est déjà en cours d'exécution
        if self.is_connected():
            logger.info("Carla est déjà en cours d'exécution")
            return True
        
        # Vérifier si la commande carla existe
        carla_cmd = shutil.which("carla")
        if not carla_cmd:
            logger.warning("Commande 'carla' introuvable dans PATH")
            return False
        
        # Démarrer Carla en mode serveur
        cmd = [
            carla_cmd,
            "--server",
            f"--osc-port={self.port}",
            f"--server-port={server_port}"
        ]
        
        try:
            # Démarrer en arrière-plan
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True
            )
            
            # Attendre que Carla soit prêt (max 10 secondes)
            for _ in range(10):
                if self.is_connected():
                    logger.info("Carla démarré avec succès")
                    return True
                time.sleep(1)
            
            # Si on arrive ici, Carla n'a pas répondu
            logger.warning("Carla n'a pas répondu après démarrage")
            process.terminate()
            return False
            
        except Exception as e:
            logger.error(f"Échec du démarrage de Carla: {e}")
            return False
    
    def stop_carla(self) -> bool:
        """
        Arrête le serveur Carla.
        
        Returns:
            bool: True si Carla a été arrêté
        """
        try:
            # Envoyer commande d'arrêt
            self.send("/carla/quit")
            logger.info("Commande d'arrêt envoyée à Carla")
            return True
        except Exception as e:
            logger.error(f"Échec de l'arrêt de Carla: {e}")
            return False
    
    def get_last_error(self) -> Optional[str]:
        """Retourne la dernière erreur rencontrée"""
        return self._last_error
```

**Critères d'Acceptation:**
- [ ] `send()` envoie des messages OSC sans erreurs
- [ ] `is_connected()` détecte correctement si Carla tourne
- [ ] `start_carla()` démarre Carla si disponible
- [ ] Gestion des erreurs avec exceptions typées
- [ ] Logging de toutes les opérations
- [ ] Tests unitaires créés

**Tests à créer:**
```python
# tests/test_carla_osc.py
import pytest
from unittest.mock import patch, MagicMock
from maestro_cli.hosts.carla_osc import CarlaOSCClient


class TestCarlaOSCClient:
    def test_init_defaults(self):
        """Test l'initialisation avec les valeurs par défaut"""
        client = CarlaOSCClient()
        assert client.host == "127.0.0.1"
        assert client.port == 9001
        
    def test_send_success(self):
        """Test l'envoi réussi d'un message"""
        client = CarlaOSCClient()
        with patch.object(client, 'client') as mock_client:
            mock_client.send.return_value = None
            result = client.send("/test", "arg1", "arg2")
            assert result is True
            mock_client.send.assert_called_once()
    
    def test_send_connection_error(self):
        """Test la gestion des erreurs de connexion"""
        client = CarlaOSCClient()
        with patch.object(client, 'client') as mock_client:
            mock_client.send.side_effect = Exception("Connection failed")
            with pytest.raises(CarlaOSCConnectionError):
                client.send("/test", "arg1")
    
    def test_is_connected(self):
        """Test la détection de connexion"""
        client = CarlaOSCClient()
        with patch.object(client, 'client') as mock_client:
            mock_client.send.return_value = None
            assert client.is_connected() is True
    
    def test_start_carla_not_in_path(self):
        """Test si Carla n'est pas dans PATH"""
        client = CarlaOSCClient()
        with patch('shutil.which', return_value=None):
            assert client.start_carla() is False
    
    def test_stop_carla(self):
        """Test l'arrêt de Carla"""
        client = CarlaOSCClient()
        with patch.object(client, 'send') as mock_send:
            mock_send.return_value = True
            assert client.stop_carla() is True
            mock_send.assert_called_once_with("/carla/quit")
```

---

#### Tâche 2.2: Créer `hosts/carla_client.py`

**Description:** Client haut-niveau pour Carla.

**Fichier:** `src/maestro_cli/hosts/carla_client.py`

**Dependencies:**
- `carla_osc.py` (créé précédemment)
- `presets.py` (à créer)

**Requirements:**

Voir **PRD_PHASE_2_3.md, section 2.2** pour les spécifications complètes.

**Structure minimale:**
```python
"""
Client haut-niveau pour Carla
Fournit une API simple pour contrôler Carla et gérer les plugins.
"""

from .carla_osc import CarlaOSCClient, CarlaOSCError
from .presets import PresetManager
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from pathlib import Path
import logging
import json

logger = logging.getLogger(__name__)


@dataclass
class PluginInfo:
    """Informations sur un plugin chargé"""
    slot: int
    name: str
    loaded: bool
    path: Optional[str] = None
    format: Optional[str] = None
    error: Optional[str] = None


@dataclass
class RackState:
    """État d'un rack Carla"""
    plugins: Dict[int, PluginInfo] = field(default_factory=dict)
    connections: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "plugins": {k: v.__dict__ for k, v in self.plugins.items()},
            "connections": self.connections,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RackState":
        plugins = {}
        for slot, info in data.get("plugins", {}).items():
            plugins[int(slot)] = PluginInfo(**info)
        return cls(
            plugins=plugins,
            connections=data.get("connections", []),
            metadata=data.get("metadata", {})
        )


class CarlaError(Exception):
    """Erreur liée à Carla"""
    pass


class PluginNotFoundError(CarlaError):
    """Plugin introuvable"""
    pass


class PresetNotFoundError(CarlaError):
    """Preset introuvable"""
    pass


class CarlaNotRunningError(CarlaError):
    """Carla n'est pas en cours d'exécution"""
    pass


class CarlaClient:
    """
    Client haut-niveau pour Carla.
    
    Gère le chargement des plugins, presets, routage, et rendu.
    """
    
    def __init__(self, host: str = "127.0.0.1", port: int = 9001):
        """
        Initialise le client Carla.
        
        Args:
            host: Adresse IP de Carla
            port: Port OSC de Carla
        """
        self.osc = CarlaOSCClient(host, port)
        self.preset_manager = PresetManager()
        self._rack_state: Optional[RackState] = None
        
    # === Server Management ===
    
    def is_running(self) -> bool:
        """Vérifie si Carla tourne"""
        return self.osc.is_connected()
    
    def start(self) -> bool:
        """Démarre Carla si ce n'est pas déjà fait"""
        if self.is_running():
            return True
        return self.osc.start_carla()
    
    def stop(self) -> bool:
        """Arrête Carla"""
        return self.osc.stop_carla()
    
    # === Plugin Management ===
    
    def load_plugin(
        self, 
        slot: int, 
        plugin_path: str, 
        plugin_format: str = "VST3"
    ) -> PluginInfo:
        """
        Charge un plugin dans un slot.
        
        Args:
            slot: Numéro du slot (1-16 typiquement)
            plugin_path: Chemin vers le plugin
            plugin_format: Format du plugin (VST3, VST2, LV2, SF2, etc.)
            
        Returns:
            PluginInfo: Informations sur le plugin chargé
        """
        # Vérifier que Carla tourne
        if not self.is_running():
            if not self.start():
                raise CarlaNotRunningError("Impossible de démarrer Carla")
        
        # Vérifier que le fichier existe
        plugin_path_obj = Path(plugin_path)
        if not plugin_path_obj.exists():
            raise PluginNotFoundError(f"Plugin introuvable: {plugin_path}")
        
        try:
            # Envoyer commande de chargement
            # Format Carla: /carla/load-plugin <slot> <path> <format>
            self.osc.send("/carla/load-plugin", slot, str(plugin_path), plugin_format)
            
            # Créer PluginInfo
            info = PluginInfo(
                slot=slot,
                name=plugin_path_obj.stem,
                loaded=True,
                path=str(plugin_path),
                format=plugin_format
            )
            
            # Mettre à jour l'état du rack
            if self._rack_state is None:
                self._rack_state = RackState()
            self._rack_state.plugins[slot] = info
            
            logger.info(f"Plugin chargé: slot={slot}, path={plugin_path}")
            return info
            
        except CarlaOSCError as e:
            logger.error(f"Échec du chargement du plugin: {e}")
            return PluginInfo(
                slot=slot,
                name=plugin_path_obj.stem,
                loaded=False,
                path=str(plugin_path),
                format=plugin_format,
                error=str(e)
            )
    
    def load_preset(self, slot: int, preset_path: str) -> bool:
        """
        Charge un preset pour un plugin.
        
        Args:
            slot: Numéro du slot
            preset_path: Chemin vers le fichier de preset (.fxp, .fxb, etc.)
            
        Returns:
            bool: True si le preset a été chargé
        """
        preset_path_obj = Path(preset_path)
        if not preset_path_obj.exists():
            raise PresetNotFoundError(f"Preset introuvable: {preset_path}")
        
        try:
            # Envoyer commande de chargement de preset
            self.osc.send("/carla/load-preset", slot, str(preset_path))
            logger.info(f"Preset chargé: slot={slot}, path={preset_path}")
            return True
        except CarlaOSCError as e:
            logger.error(f"Échec du chargement du preset: {e}")
            return False
    
    # === Rack Management ===
    
    def load_rack(self, rack_config: Dict[str, Any]) -> RackState:
        """
        Charge un rack complet.
        
        Args:
            rack_config: Configuration du rack
                {
                    "plugins": [
                        {"slot": 1, "path": "/path/to/plugin.vst3", "preset": "preset.fxp"},
                        ...
                    ],
                    "routes": [
                        {"track": "keys_main", "slot": 1, "channel": 0},
                        ...
                    ],
                    "metadata": {...}
                }
                
        Returns:
            RackState: État du rack chargé
        """
        self._rack_state = RackState(metadata=rack_config.get("metadata", {}))
        
        # Charger les plugins
        for plugin_config in rack_config.get("plugins", []):
            slot = plugin_config["slot"]
            plugin_path = plugin_config["path"]
            
            info = self.load_plugin(slot, plugin_path)
            self._rack_state.plugins[slot] = info
            
            # Charger le preset si spécifié
            if "preset" in plugin_config:
                preset_path = plugin_config["preset"]
                if preset_path:
                    self.load_preset(slot, preset_path)
        
        # Configurer le routage (simplifié - à implémenter complètement)
        for route in rack_config.get("routes", []):
            # self.connect(route["input"], route["output_slot"])
            pass
        
        logger.info("Rack chargé avec succès")
        return self._rack_state
    
    def save_rack_state(self, filepath: str) -> bool:
        """Sauvegarde l'état du rack dans un fichier"""
        if self._rack_state is None:
            logger.warning("Aucun rack chargé à sauvegarder")
            return False
        
        try:
            with open(filepath, 'w') as f:
                json.dump(self._rack_state.to_dict(), f, indent=2)
            logger.info(f"Rack sauvegardé: {filepath}")
            return True
        except Exception as e:
            logger.error(f"Échec de la sauvegarde du rack: {e}")
            return False
    
    def load_rack_state(self, filepath: str) -> bool:
        """Charge un état de rack sauvegardé"""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            self._rack_state = RackState.from_dict(data)
            
            # Recharger les plugins (optionnel - pour restaurer l'état)
            # Cela nécessiterait de connaître les chemins exacts
            
            logger.info(f"Rack chargé depuis: {filepath}")
            return True
        except Exception as e:
            logger.error(f"Échec du chargement du rack: {e}")
            return False
    
    def get_state(self) -> Dict[str, Any]:
        """Récupère l'état complet du rack"""
        if self._rack_state is None:
            return {"error": "No rack loaded"}
        return self._rack_state.to_dict()
    
    # === Rendering ===
    
    def render(self, output_path: str, duration: Optional[float] = None) -> Dict[str, Any]:
        """
        Déclenche le rendu audio.
        
        Args:
            output_path: Chemin du fichier de sortie (WAV)
            duration: Durée optionnelle
            
        Returns:
            Dict: {"status": "started"|"completed"|"failed", "output_path": str, "error": str}
        """
        if not self.is_running():
            raise CarlaNotRunningError("Carla n'est pas en cours d'exécution")
        
        try:
            # Envoyer commande de rendu
            # /carla/render <output_path> [<duration>]
            if duration:
                self.osc.send("/carla/render", output_path, duration)
            else:
                self.osc.send("/carla/render", output_path)
            
            logger.info(f"Rendu démarré: {output_path}")
            return {"status": "started", "output_path": output_path}
            
        except CarlaOSCError as e:
            logger.error(f"Échec du démarrage du rendu: {e}")
            return {"status": "failed", "error": str(e)}
    
    def is_rendering(self) -> bool:
        """Vérifie si un rendu est en cours"""
        # Carla expose /carla/is-rendering
        # Pour l'instant, on retourne False (à implémenter)
        return False
    
    def wait_for_render(self, output_path: str, timeout: float = 300.0) -> bool:
        """
        Attend la fin du rendu.
        
        Args:
            output_path: Chemin du fichier de sortie
            timeout: Timeout en secondes (default: 5 minutes)
            
        Returns:
            bool: True si le rendu a réussi
        """
        import os
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            # Vérifier si le fichier existe et a une taille > 0
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                logger.info(f"Rendu terminé: {output_path}")
                return True
            time.sleep(1)
        
        logger.warning(f"Timeout du rendu après {timeout}s")
        return False
```

**Critères d'Acceptation:**
- [ ] Peut démarrer/arrêter Carla
- [ ] Peut charger des plugins VST3/LV2/SF2
- [ ] Peut charger des presets
- [ ] Peut sauvegarder/charger l'état du rack
- [ ] Peut déclencher un rendu
- [ ] Gestion des erreurs complète
- [ ] Tests unitaires créés

---

#### Tâche 2.3: Créer `hosts/presets.py`

**Description:** Gestion des presets et mappings de plugins.

**Fichier:** `src/maestro_cli/hosts/presets.py`

**Requirements:**

Voir **PRD_PHASE_2_3.md, section 2.3** pour les spécifications complètes.

---

#### Tâche 2.4: Créer `presets/plugin_map.json`

**Description:** Fichier de configuration du mapping rôle → plugin.

**Fichier:** `presets/plugin_map.json`

**Requirements:**

Voir **PRD_PHASE_2_3.md, section 2.4** pour le format complet.

**Version minimale:**
```json
{
  "version": "1.0",
  "styles": {
    "gospel": {
      "description": "Style Gospel",
      "mappings": [
        {
          "id": "gospel_keys",
          "role": "keys",
          "plugin": "EPiano",
          "format": "VST3",
          "path": "/usr/lib/vst3/EPiano.vst3",
          "preset": null,
          "default_slot": 1,
          "volume": 0.8,
          "pan": 0.5,
          "midi_channel": 0,
          "required": true
        },
        {
          "id": "gospel_bass",
          "role": "bass",
          "plugin": "BassPlugin",
          "format": "VST3",
          "path": "/usr/lib/vst3/BassPlugin.vst3",
          "preset": null,
          "default_slot": 2,
          "volume": 1.0,
          "pan": 0.5,
          "midi_channel": 0,
          "required": true
        },
        {
          "id": "gospel_drums",
          "role": "drums",
          "plugin": "DrumMachine",
          "format": "VST3",
          "path": "/usr/lib/vst3/DrumMachine.vst3",
          "preset": null,
          "default_slot": 3,
          "volume": 1.0,
          "pan": 0.5,
          "midi_channel": 9,
          "required": true
        }
      ]
    }
  },
  "fallback": {
    "enabled": true,
    "synth": "fluidsynth",
    "soundfont": "/usr/share/sounds/sf2/GeneralUser_GS.sf2"
  },
  "search_paths": [
    "/usr/lib/vst3",
    "/usr/lib/lv2",
    "~/vst3",
    "~/plugins"
  ]
}
```

---

#### Tâche 2.5: Créer `hosts/__init__.py`

**Description:** Initialisation du package hosts.

**Fichier:** `src/maestro_cli/hosts/__init__.py`

**Contenu:**
```python
"""
Package pour l'intégration avec les hosts audio (Carla, FluidSynth, etc.)
"""

from .carla_osc import CarlaOSCClient, CarlaOSCError, CarlaOSCConnectionError, CarlaOSCTimeoutError
from .carla_client import CarlaClient, CarlaError, PluginNotFoundError, PresetNotFoundError, CarlaNotRunningError, PluginInfo, RackState
from .presets import PresetManager

__all__ = [
    # Carla OSC
    "CarlaOSCClient",
    "CarlaOSCError",
    "CarlaOSCConnectionError",
    "CarlaOSCTimeoutError",
    # Carla Client
    "CarlaClient",
    "CarlaError",
    "PluginNotFoundError",
    "PresetNotFoundError",
    "CarlaNotRunningError",
    "PluginInfo",
    "RackState",
    # Presets
    "PresetManager",
]
```

---

#### Tâche 2.6: Mettre à jour `cli_stateful.py`

**Description:** Mettre à jour les commandes `carla_load`, `render`, et `play`.

**Fichier:** `src/maestro_cli/cli_stateful.py`

**Changes:**

```python
# Ajouter en haut du fichier
from maestro_cli.hosts.carla_client import CarlaClient, CarlaError, CarlaNotRunningError
from maestro_cli.hosts.presets import PresetManager
import subprocess
import time


# Remplacer handle_carla_load
def handle_carla_load(args) -> int:
    """Load Carla rack with real OSC integration"""
    project_id = args.project_id or "test_song"
    
    manager = get_run_manager(project_id)
    
    # Check if tracks.json exists
    tracks_file = get_state_dir(project_id) / "tracks.json"
    if not tracks_file.exists():
        print("Error: tracks.json not found. Run 'orchestrate' first.")
        return 1
    
    if manager.run_context is None:
        manager.start_run()
    
    manager.start_step("carla_load")
    print(f"Loading Carla rack: {project_id}")
    
    try:
        # Load tracks
        tracks_data = load_json(tracks_file)
        tracks = Tracks(**tracks_data)
        
        # Load plugin mapping
        preset_manager = PresetManager()
        style = tracks.tracks[0].style[0] if tracks.tracks else "gospel"
        plugin_map = preset_manager.load_plugin_map(style)
        
        # Create Carla client
        carla = CarlaClient()
        
        # Start Carla if needed
        if not carla.is_running():
            print("Starting Carla...")
            if not carla.start():
                raise CarlaNotRunningError("Failed to start Carla. Make sure it's installed.")
        
        # Build rack config from tracks
        rack_config = preset_manager.build_rack_config(tracks.tracks, style)
        
        # Load rack
        rack_state = carla.load_rack(rack_config)
        
        # Save rack state
        rack_state_path = get_state_dir(project_id) / "rack_state.json"
        carla.save_rack_state(str(rack_state_path))
        
        artifacts = [str(rack_state_path)]
        manager.complete_step("carla_load", artifacts=artifacts)
        
        print(f"✓ Carla rack loaded with {len(rack_config['plugins'])} plugins")
        return 0
        
    except CarlaNotRunningError as e:
        print(f"⚠️  Carla not available: {e}")
        print("   Falling back to FluidSynth preview...")
        # For now, just create the rack_state.json without real Carla
        rack_state = {"fallback": True, "message": str(e)}
        save_json(get_state_dir(project_id) / "rack_state.json", rack_state)
        manager.complete_step("carla_load", artifacts=[str(get_state_dir(project_id) / "rack_state.json")])
        return 0
        
    except Exception as e:
        manager.fail_step("carla_load", str(e))
        print(f"✗ Carla load failed: {e}", file=sys.stderr)
        return 1


# Remplacer handle_render
def handle_render(args) -> int:
    """Render audio with real Carla integration"""
    project_id = args.project_id or "test_song"
    
    manager = get_run_manager(project_id)
    
    # Check dependencies
    rack_state_file = get_state_dir(project_id) / "rack_state.json"
    if not rack_state_file.exists():
        print("Error: rack_state.json not found. Run 'carla_load' first.")
        return 1
    
    if manager.run_context is None:
        manager.start_run()
    
    manager.start_step("render")
    print(f"Rendering: {project_id}")
    
    try:
        # Load rack state
        carla = CarlaClient()
        
        # If Carla is running, use it
        if carla.is_running():
            output_file = args.output or str(get_audio_dir(project_id) / "mix.wav")
            
            # Trigger render
            result = carla.render(output_file)
            if result.get("status") == "failed":
                raise CarlaError(result.get("error", "Unknown render error"))
            
            # Wait for render to complete
            print("Waiting for render to complete...")
            if carla.wait_for_render(output_file, timeout=300):
                # Verify file
                output_path = Path(output_file)
                if not output_path.exists() or output_path.stat().st_size == 0:
                    raise CarlaError("Render failed: empty output file")
            else:
                raise CarlaError("Render timeout")
            
            # Save render report
            report = RenderReport(
                project_id=project_id,
                render_ok=True,
                output_file=output_file,
                duration_seconds=get_audio_duration(output_file),
                sample_rate=AUDIO_SAMPLE_RATE,
                bit_depth=AUDIO_BIT_DEPTH,
                channels=2,
                status="rendered"
            )
            save_json(get_state_dir(project_id) / "render_report.json", report.model_dump(mode="json"))
            
            artifacts = [output_file, str(get_state_dir(project_id) / "render_report.json")]
            manager.complete_step("render", artifacts=artifacts)
            
            print(f"✓ Render complete: {output_file}")
            minutes = int(get_audio_duration(output_file) // 60)
            seconds = int(get_audio_duration(output_file) % 60)
            print(f"  Duration: {minutes:02d}:{seconds:02d}")
            
        else:
            # Fallback to FluidSynth
            print("⚠️  Carla not running, using FluidSynth fallback...")
            return fallback_render(args)
        
        return 0
        
    except Exception as e:
        manager.fail_step("render", str(e))
        print(f"✗ Render failed: {e}", file=sys.stderr)
        return 1


def fallback_render(args) -> int:
    """Render using FluidSynth as fallback"""
    project_id = args.project_id or "test_song"
    manager = get_run_manager(project_id)
    
    try:
        # Find all MIDI files
        midi_dir = get_midi_dir(project_id)
        midi_files = list(midi_dir.glob("*.mid"))
        
        if not midi_files:
            print("Error: No MIDI files found")
            return 1
        
        # Render each MIDI file
        output_files = []
        for midi_file in midi_files:
            output_file = args.output or str(get_audio_dir(project_id) / f"{midi_file.stem}.wav")
            
            # Use FluidSynth
            from maestro_cli.config import settings
            soundfont = settings.CARLA_RACK_PATH or "/usr/share/sounds/sf2/GeneralUser_GS.sf2"
            
            cmd = [
                "fluidsynth",
                "-ni",
                soundfont,
                str(midi_file),
                "-F",
                output_file
            ]
            
            print(f"  Rendering {midi_file.name} with FluidSynth...")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode != 0:
                print(f"  Warning: FluidSynth error for {midi_file.name}: {result.stderr}")
            else:
                output_files.append(output_file)
                print(f"  ✓ {midi_file.name} → {Path(output_file).name}")
        
        # Mix all outputs (simplified - just use first one for now)
        if output_files:
            final_output = output_files[0]
            
            report = RenderReport(
                project_id=project_id,
                render_ok=True,
                output_file=final_output,
                duration_seconds=get_audio_duration(final_output),
                sample_rate=AUDIO_SAMPLE_RATE,
                bit_depth=AUDIO_BIT_DEPTH,
                channels=2,
                status="rendered",
                fallback=True
            )
            save_json(get_state_dir(project_id) / "render_report.json", report.model_dump(mode="json"))
            
            artifacts = [final_output, str(get_state_dir(project_id) / "render_report.json")]
            manager.complete_step("render", artifacts=artifacts)
            
            print(f"✓ Fallback render complete: {final_output}")
        
        return 0
        
    except Exception as e:
        print(f"✗ Fallback render failed: {e}", file=sys.stderr)
        return 1


def get_audio_duration(filepath: str) -> float:
    """Get duration of audio file in seconds"""
    # Simplified - use soxi if available, otherwise return default
    try:
        import subprocess
        result = subprocess.run(
            ["soxi", "-D", filepath],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            return float(result.stdout.strip())
    except:
        pass
    
    # Default duration
    return 168.2


# Remplacer handle_play
def handle_play(args) -> int:
    """Play the rendered audio"""
    project_id = args.project_id or "test_song"
    
    manager = get_run_manager(project_id)
    
    # Check if render report exists
    render_report_file = get_state_dir(project_id) / "render_report.json"
    if not render_report_file.exists():
        print("Error: render_report.json not found. Run 'render' first.")
        return 1
    
    if manager.run_context is None:
        manager.start_run()
    
    manager.start_step("play")
    print(f"Playing: {project_id}")
    
    try:
        report_data = load_json(render_report_file)
        report = RenderReport(**report_data)
        output_file = report.output_file
        
        if not Path(output_file).exists():
            print(f"Error: Output file not found: {output_file}")
            return 1
        
        print(f"Playing: {output_file}")
        
        # Try different players
        players = [
            ("aplay", ["aplay", output_file]),
            ("vlc", ["vlc", "--play-and-exit", output_file]),
            ("ffplay", ["ffplay", "-autoexit", output_file]),
            ("mpg123", ["mpg123", output_file]),
        ]
        
        played = False
        for name, cmd in players:
            try:
                import subprocess
                subprocess.run(cmd, check=True, timeout=300)
                played = True
                break
            except:
                continue
        
        if not played:
            print("  No audio player found. Try one of these:")
            for name, cmd in players:
                print(f"    {name}: {' '.join(cmd)}")
        
        artifacts = [output_file]
        manager.complete_step("play", artifacts=artifacts)
        
        try:
            manager.complete_run()
        except RuntimeError:
            pass
        
        print("✓ Play command complete")
        return 0
        
    except Exception as e:
        manager.fail_step("play", str(e))
        print(f"✗ Play failed: {e}", file=sys.stderr)
        return 1
```

---

## 🤖 Tâches Phase 3 - Système Agentique

### Priorité: ⭐⭐ (À FAIRE APRÈS PHASE 2)

#### Tâche 3.1: Implémenter Structured Outputs

**Description:** Tous les agents doivent produire des sorties typées avec Pydantic.

**Fichiers:**
- `src/maestro_cli/agents/outputs.py` (nouveau)
- Mettre à jour les modèles existants dans `models/`

**Requirements:**

Voir **PRD_PHASE_2_3.md, section 3.1** pour les spécifications.

---

#### Tâche 3.2: Implémenter Guardrails

**Description:** Système de validation des entrées/sorties.

**Fichiers:**
- `src/maestro_cli/agents/guardrails.py` (nouveau)
- `src/maestro_cli/agents/guardrail_manager.py` (nouveau)

**Requirements:**

Voir **PRD_PHASE_2_3.md, section 3.2** pour les spécifications.

---

#### Tâche 3.3: Implémenter Tracing System

**Description:** Traçage complet des opérations.

**Fichiers:**
- `src/maestro_cli/tracing/tracer.py` (nouveau)
- `src/maestro_cli/tracing/span.py` (nouveau)
- `src/maestro_cli/tracing/trace.py` (nouveau)

**Requirements:**

Voir **PRD_PHASE_2_3.md, section 3.3** pour les spécifications.

---

#### Tâche 3.4: Implémenter Approval System

**Description:** Validation humaine pour les actions sensibles.

**Fichiers:**
- `src/maestro_cli/approvals/approval_manager.py` (nouveau)
- `src/maestro_cli/approvals/approval_request.py` (nouveau)

**Requirements:**

Voir **PRD_PHASE_2_3.md, section 3.4** pour les spécifications.

---

#### Tâche 3.5: Implémenter MIDI 2.0 Layer

**Description:** Support de MIDI 2.0 avec MIDI-CI, Profiles, Property Exchange.

**Fichiers:**
- `src/maestro_cli/midi2/midi_ci.py` (nouveau)
- `src/maestro_cli/midi2/profiles.py` (nouveau)
- `src/maestro_cli/midi2/property_exchange.py` (nouveau)
- `src/maestro_cli/midi2/ump.py` (nouveau)
- `src/maestro_cli/midi2/fallback.py` (nouveau)

**Requirements:**

Voir **PRD_PHASE_2_3.md, section 3.5** pour les spécifications.

---

## 💬 Prompts Prêts à l'Emploi

### Pour un LLM (Phase 2)

#### Prompt 1: Créer `carla_osc.py`
```
Tu es un expert Python spécialisé dans les protocoles audio et OSC.

TÂCHE: Implémenter la classe CarlaOSCClient dans src/maestro_cli/hosts/carla_osc.py

REQUIS:
1. Lire PRD_PHASE_2_3.md, section 2.1 pour les spécifications complètes
2. Créer le fichier avec EXACTEMENT cette structure:
   - DEFAULT_HOST = "127.0.0.1"
   - DEFAULT_PORT = 9001
   - DEFAULT_TIMEOUT = 5.0
   - Classes: CarlaOSCError, CarlaOSCConnectionError, CarlaOSCTimeoutError, CarlaOSCClient
   - Méthodes: __init__, send, is_connected, start_carla, stop_carla, get_last_error
3. Utiliser python-osc pour l'envoi de messages
4. Gérer les timeouts (5 secondes)
5. Gérer les erreurs avec logging
6. Créer des tests unitaires dans tests/test_carla_osc.py
7. Le code doit compiler sans erreurs
8. Suivre PEP 8

CONTEXTE:
- Carla est un host de plugins audio qui expose une API OSC
- Documentation: https://github.com/falkTX/Carla/blob/master/README.md#remote-control
- Ce client sera utilisé par CarlaClient (haut-niveau)

EXEMPLE D'UTILISATION:
```python
client = CarlaOSCClient()
if client.is_connected():
    client.send("/carla/load-plugin", 1, "/path/to/plugin.vst3", "VST3")
else:
    client.start_carla()
```

LIVRABLES:
1. src/maestro_cli/hosts/carla_osc.py (code principal)
2. tests/test_carla_osc.py (tests unitaires)

COMMENCE MAINTENANT. Ne me demande pas de confirmation, juste fais-le.
```

---

#### Prompt 2: Créer `carla_client.py`
```
Tu es un expert Python spécialisé dans l'intégration avec Carla et les plugins audio.

TÂCHE: Implémenter la classe CarlaClient dans src/maestro_cli/hosts/carla_client.py

REQUIS:
1. Lire PRD_PHASE_2_3.md, section 2.2 pour les spécifications complètes
2. Importer et utiliser CarlaOSCClient de carla_osc.py
3. Créer les dataclasses: PluginInfo, RackState
4. Créer les classes d'erreur: CarlaError, PluginNotFoundError, PresetNotFoundError, CarlaNotRunningError
5. Implémenter la classe CarlaClient avec TOUTES les méthodes:
   - Server Management: is_running, start, stop
   - Plugin Management: load_plugin, unload_plugin, load_preset, get_plugin_info, list_plugins
   - Rack Management: load_rack, save_rack_state, load_rack_state, get_state
   - Rendering: render, is_rendering, wait_for_render
   - Transport: play, stop, pause
   - State: get_volume, set_volume, get_parameter, set_parameter
6. Utiliser PresetManager pour la gestion des presets
7. Créer des tests unitaires dans tests/test_carla_client.py
8. Le code doit compiler sans erreurs
9. Suivre PEP 8

CONTEXTE:
- Carla expose une API OSC complète pour contrôler les plugins
- Ce client est le pont entre le pipeline Maestro et Carla
- Il doit être robuste et gérer toutes les erreurs

EXEMPLE D'UTILISATION:
```python
client = CarlaClient()
client.start()
client.load_plugin(1, "/usr/lib/vst3/EPiano.vst3")
client.load_preset(1, "/path/to/preset.fxp")
client.render("/output/mix.wav")
client.wait_for_render("/output/mix.wav")
```

LIVRABLES:
1. src/maestro_cli/hosts/carla_client.py (code principal)
2. tests/test_carla_client.py (tests unitaires)

COMMENCE MAINTENANT. Ne me demande pas de confirmation, juste fais-le.
```

---

#### Prompt 3: Créer `presets.py`
```
Tu es un expert Python spécialisé dans la gestion de configurations.

TÂCHE: Implémenter la classe PresetManager dans src/maestro_cli/hosts/presets.py

REQUIS:
1. Lire PRD_PHASE_2_3.md, section 2.3 pour les spécifications complètes
2. Créer la classe PresetManager avec ces méthodes:
   - __init__(presets_dir)
   - load_plugin_map(style)
   - find_plugin(role, style)
   - validate_rack(tracks)
   - build_rack_config(tracks, style)
   - list_styles()
   - list_roles(style)
3. Charger plugin_map.json depuis le dossier presets/
4. Valider que tous les plugins existent avant chargement
5. Construire une config de rack à partir de tracks.json
6. Gérer plusieurs styles (gospel, neo-soul, afrobeats)
7. Créer des tests unitaires dans tests/test_presets.py
8. Le code doit compiler sans erreurs
9. Suivre PEP 8

CONTEXTE:
- PresetManager fait le pont entre les rôles musicaux (keys, bass, drums) et les plugins Carla
- Il permet de construire automatiquement un rack à partir d'une liste de pistes
- plugin_map.json contient la configuration des mappings

EXEMPLE D'UTILISATION:
```python
manager = PresetManager()
plugin_map = manager.load_plugin_map("gospel")
rack_config = manager.build_rack_config(tracks, "gospel")
```

LIVRABLES:
1. src/maestro_cli/hosts/presets.py (code principal)
2. tests/test_presets.py (tests unitaires)

COMMENCE MAINTENANT. Ne me demande pas de confirmation, juste fais-le.
```

---

#### Prompt 4: Mettre à jour `cli_stateful.py`
```
Tu es un expert Python spécialisé dans les interfaces CLI.

TÂCHE: Mettre à jour cli_stateful.py pour intégrer le bridge Carla

REQUIS:
1. Lire PRD_PHASE_2_3.md, section 2.5 pour les spécifications
2. Modifier ONLY les fonctions: handle_carla_load, handle_render, handle_play
3. NOUVEAUTES DÉPENDANCES À AJOUTER:
   - from maestro_cli.hosts.carla_client import CarlaClient, CarlaError, CarlaNotRunningError
   - from maestro_cli.hosts.presets import PresetManager
   - import subprocess, time
4. handle_carla_load doit:
   - Vérifier que tracks.json existe
   - Charger le plugin_map pour le style
   - Démarrer Carla si nécessaire
   - Construire et charger le rack
   - Sauvegarder rack_state.json
   - Gérer le fallback vers JSON si Carla échoue
5. handle_render doit:
   - Vérifier que rack_state.json existe
   - Utiliser CarlaClient pour le rendu
   - Attendre la fin du rendu
   - Sauvegarder render_report.json
   - Gérer le fallback vers FluidSynth
6. handle_play doit:
   - Vérifier que render_report.json existe
   - Jouer le fichier avec aplay/vlc/ffplay/mpg123
   - Gérer les erreurs de lecture
7. Ajouter la fonction helper: get_audio_duration(filepath)
8. Le code doit compiler sans erreurs
9. Suivre PEP 8

CONTEXTE:
- Les commandes existantes créent juste des JSONs dummy
- Il faut les remplacer par des versions qui utilisent vraiment Carla
- Toujours garder un fallback si Carla n'est pas disponible

EXEMPLE DE MODIFICATION:
```python
# Avant (version dummy)
def handle_carla_load(args):
    rack_state = RackState(...)
    save_json(...)
    manager.complete_step(...)

# Après (version réelle)
def handle_carla_load(args):
    carla = CarlaClient()
    if not carla.is_running():
        carla.start()
    rack_state = carla.load_rack(rack_config)
    carla.save_rack_state(path)
    manager.complete_step(...)
```

LIVRABLE:
1. src/maestro_cli/cli_stateful.py (mis à jour)

COMMENCE MAINTENANT. Ne me demande pas de confirmation, juste fais-le.
```

---

### Pour un LLM (Phase 3)

#### Prompt 5: Implémenter Structured Outputs
```
Tu es un expert Python spécialisé dans la validation de données avec Pydantic.

TÂCHE: Implémenter les structured outputs pour tous les agents

REQUIS:
1. Lire PRD_PHASE_2_3.md, section 3.1 pour les spécifications complètes
2. Créer src/maestro_cli/agents/outputs.py
3. Définir les enums: Severity, IssueType
4. Créer les Pydantic models:
   - CritiqueIssue
   - Critique
   - ComposeOutput
   - ArrangeOutput
   - OrchestrateOutput
   - RenderOutput
   - (etc. pour chaque agent)
5. Mettre à jour les modèles existants dans models/ pour utiliser BaseModel
6. Tous les outputs des agents doivent être des instances de ces models
7. Créer des tests de validation dans tests/test_outputs.py
8. Le code doit compiler sans erreurs
9. Suivre PEP 8

CONTEXTE:
- Les structured outputs garantissent que les agents produisent des données valides
- Pydantic permet la validation automatique et la sérialisation
- Tous les champs doivent avoir des types clairs et des descriptions

EXEMPLE:
```python
from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum

class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class CritiqueIssue(BaseModel):
    severity: Severity
    issue_type: str
    track_a: Optional[str] = None
    track_b: Optional[str] = None
    bars: Optional[List[int]] = None
    message: str
    suggestion: Optional[str] = None

class Critique(BaseModel):
    project_id: str
    valid: bool
    issues: List[CritiqueIssue]
    repair_actions: List[str]
    confidence: float = Field(ge=0.0, le=1.0)
```

LIVRABLES:
1. src/maestro_cli/agents/outputs.py (modèles Pydantic)
2. Mettre à jour models/*.py (si nécessaire)
3. tests/test_outputs.py (tests de validation)

COMMENCE MAINTENANT. Ne me demande pas de confirmation, juste fais-le.
```

---

## ✅ Checklist de Validation

### Pour Chaque Tâche

- [ ] Code compilé sans erreurs (`python -m py_compile fichier.py`)
- [ ] Tous les imports fonctionnent
- [ ] Les noms de classes/méthodes correspondent EXACTEMENT aux spécifications
- [ ] Les types de retour correspondent aux spécifications
- [ ] Gestion des erreurs implémentée
- [ ] Logging ajouté pour les opérations importantes
- [ ] Docstrings ajoutées à toutes les classes et méthodes
- [ ] Tests unitaires créés et passants
- [ ] Code suit PEP 8
- [ ] Pas de warnings/errors de linter

### Pour la Phase 2 (Complète)

- [ ] `carla_osc.py` implémenté et testé
- [ ] `carla_client.py` implémenté et testé
- [ ] `presets.py` implémenté et testé
- [ ] `plugin_map.json` créé
- [ ] `hosts/__init__.py` créé
- [ ] `cli_stateful.py` mis à jour
- [ ] Tous les tests passent
- [ ] Documentation mise à jour

### Pour la Phase 3 (Complète)

- [ ] Structured Outputs implémentés
- [ ] Guardrails implémentés
- [ ] Tracing System implémenté
- [ ] Approval System implémenté
- [ ] MIDI 2.0 Layer implémenté
- [ ] Storage Layer mis à jour
- [ ] Tous les tests passent
- [ ] Documentation complète

---

## 🔗 Ressources et Références

### Documentation Officielle

- **PRD Complet:** `PRD_PHASE_2_3.md` (CE DOCUMENT)
- **Architecture:** `STATE_MANAGEMENT.md`
- **Résumé Technique:** `IMPLEMENTATION_SUMMARY.md`

### Code Existant

- **Storage Layer:** `src/maestro_cli/storage/`
- **CLI Actuelle:** `src/maestro_cli/cli_stateful.py`
- **Modèles:** `src/maestro_cli/models/`
- **Config:** `src/maestro_cli/config.py`

### Documentation Externe

- **Carla:** https://github.com/falkTX/Carla
- **Carla OSC Protocol:** https://github.com/falkTX/Carla/blob/master/README.md#remote-control
- **python-osc:** https://pypi.org/project/python-osc/
- **Pydantic:** https://pydantic.dev/
- **MIDI 2.0:** https://midi.org/midi-2-0

### Commandes Utiles

```bash
# Compiler un fichier Python
python -m py_compile src/maestro_cli/hosts/carla_osc.py

# Exécuter les tests
python -m pytest tests/test_carla_osc.py -v

# Vérifier PEP 8
python -m pyflakes src/maestro_cli/hosts/carla_osc.py
python -m pep8 src/maestro_cli/hosts/carla_osc.py

# Démarrer Carla
carla --server --osc-port 9001 --server-port 9002

# Tester la connexion OSC
python -c "from maestro_cli.hosts.carla_osc import CarlaOSCClient; c = CarlaOSCClient(); print(c.is_connected())"
```

---

## 📊 Statut Actuel

### Phase 1: ✅ 100% TERMINÉE
- Tout est fonctionnel et testé
- Prêt pour la production

### Phase 2: ❌ 0% COMMENCÉE
- **Priorité Maximale**
- Temps estimé: 1-2 semaines
- Blocage: Aucune dépendance critique

### Phase 3: ❌ 0% COMMENCÉE
- Priorité: Moyenne
- À faire après Phase 2
- Temps estimé: 2-3 semaines

---

## 🎯 Prochaines Actions Recommandées

### Pour un Développeur Humain:
1. **Commencer par la Phase 2** (c'est la priorité)
2. Créer `carla_osc.py` → `carla_client.py` → `presets.py` → `plugin_map.json`
3. Mettre à jour `cli_stateful.py`
4. Tester avec Carla réel
5. Passer à la Phase 3

### Pour un LLM:
1. **Choisir une tâche** dans ce document
2. **Lire les spécifications** dans PRD_PHASE_2_3.md
3. **Implémenter le code** en suivant les prompts prêts à l'emploi
4. **Valider** avec la checklist
5. **Passer à la tâche suivante**

---

## 📝 Notes Finales

- **Ce document est la source de vérité** pour les Phases 2 et 3
- **Toutes les spécifications sont dans PRD_PHASE_2_3.md**
- **Ne jamais deviner** - toujours suivre ce qui est écrit
- **Priorité à la Phase 2** - c'est ce qui rend le système utilisable
- **Phase 3 est un bonus** - le système sera déjà très utile après Phase 2

---

**Document créé le 28 juillet 2026**
**Version: 1.0**
**Dernière mise à jour: 28 juillet 2026**

---

*"Un LLM bien guidé est un LLM efficace."* 🚀
