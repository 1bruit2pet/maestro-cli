"""
Preset Manager - Plugin mapping, validation, and rack configuration builder.
Loads plugin_map.json and converts tracks into Carla rack configurations.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from maestro_cli.config import settings

logger = logging.getLogger(__name__)

DEFAULT_PLUGIN_MAP = settings.PROJECT_ROOT / "presets" / "plugin_map.json"

SOUNDFONT_PROFILES = {
    "generaluser": {
        "name": "GeneralUser GS",
        "author": "S. Christian Collins",
        "url": "https://www.schristiancollins.com/generaluser",
        "filename": "GeneralUser_GS.sf2",
        "style_recommendation": "gospel, neo_soul, jazz"
    },
    "musescore": {
        "name": "MuseScore General",
        "author": "MuseScore Team",
        "url": "https://ftp.osuosl.org/pub/musescore/soundfont/MuseScore_General/MuseScore_General.sf3",
        "filename": "MuseScore_General.sf3",
        "style_recommendation": "orchestral, classical, cinematic"
    },
    "sgm": {
        "name": "Shan's General MIDI V2.01",
        "author": "Shan",
        "url": "https://archive.org/details/SGM-V2.01",
        "filename": "SGM-V2.01.sf2",
        "style_recommendation": "rock, pop, afrobeats"
    }
}


class PresetError(Exception):
    """Base error for preset operations"""
    pass


class PluginMapNotFoundError(PresetError):
    """Plugin map file not found"""
    pass


class StyleNotFoundError(PresetError):
    """Requested style not found in plugin map"""
    pass


class RoleMappingError(PresetError):
    """No plugin mapping found for a required role"""
    pass


class PresetManager:
    """
    Manages plugin presets and rack configurations.

    Responsibilities:
    - Load and cache plugin_map.json
    - Find plugins for given roles/styles
    - Validate rack configurations
    - Build rack configs from track lists
    """

    def __init__(self, presets_dir: Optional[str] = None):
        """
        Initialize the preset manager.

        Args:
            presets_dir: Directory containing plugin_map.json.
                         Defaults to project root /presets/
        """
        if presets_dir:
            self._presets_dir = Path(presets_dir)
        else:
            self._presets_dir = DEFAULT_PLUGIN_MAP.parent

        self._plugin_map: Optional[Dict[str, Any]] = None
        logger.info("PresetManager initialized: presets_dir=%s", self._presets_dir)

    @property
    def plugin_map(self) -> Dict[str, Any]:
        """Get the plugin map, loading from disk if needed"""
        if self._plugin_map is None:
            self._plugin_map = self._load_plugin_map_file()
        return self._plugin_map

    def _load_plugin_map_file(self) -> Dict[str, Any]:
        """Load plugin_map.json from disk"""
        map_file = self._presets_dir / "plugin_map.json"
        if not map_file.exists():
            raise PluginMapNotFoundError(f"Plugin map not found: {map_file}")

        try:
            with open(map_file, "r") as f:
                data = json.load(f)
            logger.info("Loaded plugin map v%s from %s", data.get("version", "?"), map_file)
            return data
        except json.JSONDecodeError as e:
            raise PresetError(f"Invalid JSON in plugin map: {e}")

    def reload(self) -> None:
        """Force reload of plugin_map.json"""
        self._plugin_map = None
        _ = self.plugin_map
        logger.info("Plugin map reloaded")

    # ========== QUERY METHODS ==========

    def load_plugin_map(self, style: str = "gospel") -> Dict[str, Any]:
        """
        Load the plugin mappings for a given style.

        Args:
            style: Musical style (gospel, neo_soul, afrobeats)

        Returns:
            Dict with "mappings" list and "fallback" config
        """
        styles = self.plugin_map.get("styles", {})
        if style not in styles:
            raise StyleNotFoundError(
                f"Style '{style}' not found. Available: {list(styles.keys())}"
            )

        style_data = styles[style]
        return {
            "mappings": style_data.get("mappings", []),
            "fallback": self.plugin_map.get("fallback", {}),
        }

    def find_plugin(self, role: str, style: str = "gospel") -> Optional[Dict[str, Any]]:
        """
        Find a plugin mapping for a given role and style.

        Args:
            role: Musical role (keys, bass, drums, pad, lead)
            style: Musical style

        Returns:
            Plugin mapping dict or None if not found
        """
        style_map = self.load_plugin_map(style)
        for mapping in style_map["mappings"]:
            if mapping.get("role") == role:
                return mapping
        return None

    def list_styles(self) -> List[str]:
        """List all available styles"""
        return list(self.plugin_map.get("styles", {}).keys())

    def list_roles(self, style: str = "gospel") -> List[str]:
        """List all roles defined for a style"""
        style_map = self.load_plugin_map(style)
        return [m["role"] for m in style_map["mappings"]]

    def get_fallback_config(self) -> Dict[str, Any]:
        """Get the FluidSynth fallback configuration"""
        return self.plugin_map.get("fallback", {
            "enabled": False,
            "synth": "fluidsynth",
            "soundfont": "/usr/share/sounds/sf2/GeneralUser_GS.sf2",
        })

    def get_search_paths(self) -> List[str]:
        """Get configured plugin search paths"""
        return self.plugin_map.get("search_paths", [])

    # ========== VALIDATION ==========

    def validate_rack(self, tracks: List[Dict[str, Any]], style: str = "gospel") -> Tuple[bool, List[str]]:
        """
        Validate that a rack can be built for the given tracks.

        Checks:
        - All required roles have plugin mappings
        - Plugin paths exist (if check_paths=True)
        - No slot conflicts

        Args:
            tracks: List of track dicts with at least "name" and "role"
            style: Musical style to use

        Returns:
            (is_valid, list_of_errors)
        """
        errors: List[str] = []
        used_slots: Dict[int, str] = {}

        try:
            style_map = self.load_plugin_map(style)
        except StyleNotFoundError as e:
            return False, [str(e)]

        for track in tracks:
            track_name = track.get("name", "unknown")
            role = track.get("role", "")

            # Check role has a mapping
            mapping = self.find_plugin(role, style)
            if mapping is None:
                if self._is_role_required(role, style):
                    errors.append(
                        f"Track '{track_name}': no plugin mapping for required role '{role}' "
                        f"in style '{style}'"
                    )
                else:
                    logger.warning(
                        "Track '%s': no mapping for optional role '%s', will use fallback",
                        track_name, role,
                    )
                continue

            # Check slot conflicts
            slot = mapping.get("default_slot", 0)
            if slot in used_slots:
                errors.append(
                    f"Slot conflict: slot {slot} used by both "
                    f"'{used_slots[slot]}' and '{track_name}'"
                )
            else:
                used_slots[slot] = track_name

        is_valid = len(errors) == 0
        if is_valid:
            logger.info("Rack validation passed for %d tracks", len(tracks))
        else:
            logger.warning("Rack validation failed: %s", errors)

        return is_valid, errors

    def _is_role_required(self, role: str, style: str) -> bool:
        """Check if a role is marked as required in the style config"""
        mapping = self.find_plugin(role, style)
        if mapping is None:
            # If no mapping exists at all, it's required only if it's a core role
            return role in ("keys", "bass", "drums")
        return mapping.get("required", False)

    def validate_plugin_paths(self, style: str = "gospel") -> Tuple[bool, List[str]]:
        """
        Validate that plugin files exist at their configured paths.

        Args:
            style: Musical style

        Returns:
            (all_exist, list_of_missing_paths)
        """
        style_map = self.load_plugin_map(style)
        missing: List[str] = []

        for mapping in style_map["mappings"]:
            plugin_path = Path(mapping.get("path", ""))
            if not plugin_path.exists():
                missing.append(
                    f"{mapping['role']} ({mapping['plugin']}): {plugin_path}"
                )

        return len(missing) == 0, missing

    # ========== RACK BUILDING ==========

    def build_rack_config(
        self,
        tracks: List[Dict[str, Any]],
        style: str = "gospel",
        project_id: str = "",
    ) -> Dict[str, Any]:
        """
        Build a complete rack configuration from a list of tracks.

        Converts track data (from tracks.json) into a rack config
        that CarlaClient.load_rack() can consume.

        Args:
            tracks: List of track dicts: [{"name": "keys_main", "role": "keys", "midi_file": "..."}]
            style: Musical style
            project_id: Project identifier

        Returns:
            Rack config dict with plugins, routes, and metadata
        """
        plugins: List[Dict[str, Any]] = []
        routes: List[Dict[str, Any]] = []
        warnings: List[str] = []

        for track in tracks:
            track_name = track.get("name", "unknown")
            role = track.get("role", "")
            midi_file = track.get("midi_file", "")

            mapping = self.find_plugin(role, style)
            if mapping is None:
                warnings.append(f"No plugin mapping for role '{role}' (track: {track_name})")
                continue

            # Build plugin entry
            plugin_entry = {
                "slot": mapping["default_slot"],
                "name": mapping["plugin"],
                "format": mapping["format"],
                "path": mapping["path"],
                "preset": mapping.get("preset"),
                "role": role,
                "volume": track.get("volume", mapping.get("volume", 0.8)),
                "pan": track.get("pan", mapping.get("pan", 0.5)),
            }
            plugins.append(plugin_entry)

            # Build route entry
            route_entry = {
                "track": track_name,
                "slot": mapping["default_slot"],
                "midi_channel": mapping.get("midi_channel", 0),
                "midi_file": midi_file,
            }
            routes.append(route_entry)

        rack_config = {
            "plugins": plugins,
            "routes": routes,
            "metadata": {
                "style": style,
                "project_id": project_id,
                "track_count": len(tracks),
                "plugin_count": len(plugins),
                "warnings": warnings,
            },
        }

        logger.info(
            "Built rack config: %d plugins, %d routes, %d warnings",
            len(plugins), len(routes), len(warnings),
        )

        return rack_config
