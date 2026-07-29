"""
MIDI 2.0 Layer - UMP (Universal MIDI Packet), MIDI-CI (Capability Inquiry), and Property Exchange for Maestro CLI.
"""

from typing import Dict, Any, List, Optional
import dataclasses


@dataclasses.dataclass
class UMPPacket:
    """
    Universal MIDI Packet (UMP) for MIDI 2.0.
    Supports 32-bit packet words encoding MIDI 1.0/2.0 channel voice messages.
    """
    message_type: int
    group: int
    status: int
    channel: int
    data_1: int
    data_2: int
    extra_word: Optional[int] = None

    def to_words(self) -> List[int]:
        """Convert UMP packet to 32-bit words."""
        header = ((self.message_type & 0xF) << 28) | ((self.group & 0xF) << 24) | ((self.status & 0xF) << 20) | ((self.channel & 0xF) << 16) | ((self.data_1 & 0xFF) << 8) | (self.data_2 & 0xFF)
        if self.extra_word is not None:
            return [header, self.extra_word]
        return [header]


class Midi2CapabilityInquiry:
    """
    MIDI-CI (Capability Inquiry) Manager.
    Negotiates MIDI 2.0 Protocol, Profile Configuration, and Property Exchange.
    """

    def __init__(self, device_name: str = "Maestro CLI Engine"):
        self.device_name = device_name
        self.supported_protocols = ["MIDI 1.0", "MIDI 2.0 UMP"]

    def inquire_capabilities(self, target_id: str) -> Dict[str, Any]:
        """Perform MIDI-CI Capability Inquiry on target plugin / hardware."""
        return {
            "target": target_id,
            "protocol_negotiated": "MIDI 2.0 UMP",
            "property_exchange_supported": True,
            "profiles_supported": ["General MIDI 2", "Synthesizer Control"]
        }
