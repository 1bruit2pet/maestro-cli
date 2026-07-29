import pytest
from maestro_cli.guardrails import GuardrailValidator, GuardrailViolationError
from maestro_cli.tracing import TraceLogger

def test_guardrail_pitch_validation():
    validator = GuardrailValidator()
    assert validator.validate_pitch(60, "piano") is True
    
    with pytest.raises(GuardrailViolationError):
        validator.validate_pitch(15, "piano")  # Below A0 (21)

def test_guardrail_velocity_validation():
    validator = GuardrailValidator()
    assert validator.validate_velocity(100, "drums") is True
    
    with pytest.raises(GuardrailViolationError):
        validator.validate_velocity(150, "drums")  # Above 127

def test_trace_logger(tmp_path):
    logger = TraceLogger(tmp_path)
    logger.log_step("compose", "SUCCESS", {"prompt": "gospel test"})
    
    traces = logger.get_traces()
    assert len(traces) == 1
    assert traces[0]["step"] == "compose"
    assert traces[0]["status"] == "SUCCESS"
