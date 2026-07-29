"""
Execution Tracing & Telemetry System for Maestro CLI (Phase 3 PRD)
Tracks step execution, state transitions, and performance metrics.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
import json


class TraceLogger:
    """
    Records deterministic step traces and execution metrics into log JSON files.
    """

    def __init__(self, log_dir: Path):
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.trace_file = self.log_dir / "execution_trace.jsonl"

    def log_step(self, step_name: str, status: str, details: Optional[Dict[str, Any]] = None):
        """Append a trace event to the trace log file."""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "step": step_name,
            "status": status,
            "details": details or {}
        }
        with open(self.trace_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    def get_traces(self) -> List[Dict[str, Any]]:
        """Retrieve all recorded trace events."""
        if not self.trace_file.exists():
            return []
        traces = []
        with open(self.trace_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    traces.append(json.loads(line.strip()))
        return traces
