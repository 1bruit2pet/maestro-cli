"""
Rack State model - Carla runtime state
"""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class PluginFormat(str, Enum):
    """Plugin formats supported by Carla"""
    VST2 = "VST2"
    VST3 = "VST3"
    LV2 = "LV2"
    LADSPA = "LADSPA"
    DSSI = "DSSI"
    SF2 = "SF2"  # SoundFont
    SFZ = "SFZ"
    INTERNAL = "internal"


class Plugin(BaseModel):
    """A plugin loaded in Carla"""
    slot: int = Field(..., ge=0, description="Plugin slot number")
    name: str = Field(..., description="Plugin name")
    format: PluginFormat = Field(..., description="Plugin format")
    path: Optional[str] = Field(
        default=None,
        description="Path to plugin file"
    )
    role: Optional[str] = Field(
        default=None,
        description="Musical role (keys, bass, etc.)"
    )
    preset: Optional[str] = Field(
        default=None,
        description="Loaded preset name"
    )
    active: bool = Field(default=True, description="Is plugin active?")
    
    class Config:
        json_schema_extra = {
            "example": {
                "slot": 1,
                "name": "EPiano",
                "format": "VST3",
                "path": "/usr/lib/vst3/EPiano.vst3",
                "role": "keys",
                "preset": "Warm Suitcase",
                "active": True
            }
        }


class Route(BaseModel):
    """MIDI/audio route in Carla"""
    track: str = Field(..., description="Track name")
    slot: int = Field(..., ge=0, description="Target plugin slot")
    midi_channel: Optional[int] = Field(
        default=None,
        ge=0, le=15,
        description="MIDI channel (0-15)"
    )
    input_port: Optional[str] = Field(
        default=None,
        description="Input port name"
    )
    output_port: Optional[str] = Field(
        default=None,
        description="Output port name"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "track": "keys_main",
                "slot": 1
            }
        }


class RackState(BaseModel):
    """
    The runtime state of Carla.
    This is a snapshot of the loaded plugins and routing.
    """
    project_id: str = Field(..., description="Project identifier")
    host: str = Field(default="carla", description="Audio host (carla, jack, etc.)")
    sample_rate: int = Field(default=48000, description="Sample rate in Hz")
    buffer_size: int = Field(default=256, description="Buffer size in samples")
    plugins: List[Plugin] = Field(
        default_factory=list,
        description="Loaded plugins"
    )
    routes: List[Route] = Field(
        default_factory=list,
        description="MIDI/audio routes"
    )
    connected: bool = Field(default=False, description="Is Carla connected?")
    status: str = Field(default="loaded", description="Pipeline status")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "project_id": "my_song",
                "host": "carla",
                "sample_rate": 48000,
                "buffer_size": 256,
                "plugins": [
                    {
                        "slot": 1,
                        "name": "EPiano",
                        "format": "VST3",
                        "role": "keys",
                        "preset": "Warm Suitcase"
                    },
                    {
                        "slot": 2,
                        "name": "BassPlugin",
                        "format": "VST3",
                        "role": "bass",
                        "preset": "Round Finger"
                    }
                ],
                "routes": [
                    {"track": "keys_main", "slot": 1},
                    {"track": "bass_main", "slot": 2}
                ],
                "connected": True,
                "status": "loaded"
            }
        }
    
    def get_plugin_by_role(self, role: str) -> Optional[Plugin]:
        """Get a plugin by its role"""
        for plugin in self.plugins:
            if plugin.role == role:
                return plugin
        return None
    
    def get_route_for_track(self, track_name: str) -> Optional[Route]:
        """Get the route for a specific track"""
        for route in self.routes:
            if route.track == track_name:
                return route
        return None
    
    def get_slot_for_track(self, track_name: str) -> Optional[int]:
        """Get the plugin slot for a track"""
        route = self.get_route_for_track(track_name)
        return route.slot if route else None
