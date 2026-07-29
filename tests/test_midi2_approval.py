import pytest
from maestro_cli.midi2 import UMPPacket, Midi2CapabilityInquiry
from maestro_cli.approval import ApprovalManager, ApprovalStatus

def test_ump_packet_generation():
    packet = UMPPacket(message_type=0x2, group=0, status=0x9, channel=0, data_1=60, data_2=100)
    words = packet.to_words()
    assert len(words) == 1
    assert (words[0] >> 28) == 0x2

def test_midi2_capability_inquiry():
    ci = Midi2CapabilityInquiry("Maestro Engine")
    capabilities = ci.inquire_capabilities("CarlaPluginHost")
    assert capabilities["protocol_negotiated"] == "MIDI 2.0 UMP"
    assert capabilities["property_exchange_supported"] is True

def test_approval_manager():
    manager = ApprovalManager()
    req = manager.create_request("render", "overwrite_master", "Overwrite existing master WAV")
    assert req.status == ApprovalStatus.PENDING
    
    success = manager.approve(req.request_id, "admin")
    assert success is True
    assert req.status == ApprovalStatus.APPROVED
    assert req.approved_by == "admin"
