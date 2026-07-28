"""
Audio host clients for Maestro CLI
"""

from maestro_cli.hosts.carla_osc import (
    CarlaOSCClient,
    CarlaOSCError,
    CarlaOSCTimeoutError,
    CarlaOSCConnectionError,
)
from maestro_cli.hosts.carla_client import (
    CarlaClient,
    CarlaStatus,
    CarlaError,
    CarlaNotRunningError,
    PluginNotFoundError,
    PresetNotFoundError,
    RenderError,
    RoutingError,
    fallback_to_fluidsynth,
)
from maestro_cli.hosts.presets import (
    PresetManager,
    PresetError,
    PluginMapNotFoundError,
    StyleNotFoundError,
    RoleMappingError,
)

__all__ = [
    # OSC layer
    "CarlaOSCClient",
    "CarlaOSCError",
    "CarlaOSCTimeoutError",
    "CarlaOSCConnectionError",
    # Client layer
    "CarlaClient",
    "CarlaStatus",
    "CarlaError",
    "CarlaNotRunningError",
    "PluginNotFoundError",
    "PresetNotFoundError",
    "RenderError",
    "RoutingError",
    "fallback_to_fluidsynth",
    # Presets
    "PresetManager",
    "PresetError",
    "PluginMapNotFoundError",
    "StyleNotFoundError",
    "RoleMappingError",
]
