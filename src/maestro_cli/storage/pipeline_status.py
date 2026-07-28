"""
Pipeline Status Manager
Manages the operational state of a project's pipeline execution
"""

from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime
import json

from maestro_cli.config import get_state_dir


# Pipeline step order
PIPELINE_STEPS = [
    "compose",
    "arrange",
    "orchestrate",
    "critique",
    "repair",
    "carla_load",
    "render",
    "play"
]


@dataclass
class PipelineStepStatus:
    """Status of a single pipeline step"""
    status: str = "pending"  # pending, running, completed, failed, skipped
    completed_at: Optional[str] = None
    started_at: Optional[str] = None
    run_id: Optional[str] = None
    checkpoint_id: Optional[str] = None
    artifacts: List[str] = field(default_factory=list)
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = {
            "status": self.status,
            "completed_at": self.completed_at,
            "started_at": self.started_at,
            "run_id": self.run_id,
            "checkpoint_id": self.checkpoint_id,
            "artifacts": self.artifacts,
            "error_message": self.error_message,
        }
        # Remove None values
        return {k: v for k, v in result.items() if v is not None and v != []}
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PipelineStepStatus":
        """Create from dictionary"""
        return cls(
            status=data.get("status", "pending"),
            completed_at=data.get("completed_at"),
            started_at=data.get("started_at"),
            run_id=data.get("run_id"),
            checkpoint_id=data.get("checkpoint_id"),
            artifacts=data.get("artifacts", []),
            error_message=data.get("error_message"),
        )
    
    def is_completed(self) -> bool:
        """Check if step is completed"""
        return self.status == "completed"
    
    def is_failed(self) -> bool:
        """Check if step failed"""
        return self.status == "failed"
    
    def is_pending(self) -> bool:
        """Check if step is pending"""
        return self.status == "pending"
    
    def is_running(self) -> bool:
        """Check if step is running"""
        return self.status == "running"


@dataclass
class PipelineStatus:
    """
    Operational state of a project's pipeline
    This file tracks which steps have been completed, failed, etc.
    """
    project_id: str
    active_run_id: Optional[str] = None
    current_step: Optional[str] = None
    steps: Dict[str, PipelineStepStatus] = field(default_factory=dict)
    last_checkpoint: Optional[Dict[str, Any]] = None
    last_error: Optional[str] = None
    resume_command: Optional[str] = None
    can_resume: bool = False
    can_rollback: bool = False
    rollback_to: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    @property
    def status_file(self) -> Path:
        """Path to the pipeline_status.json file"""
        return get_state_dir(self.project_id) / "pipeline_status.json"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = {
            "project_id": self.project_id,
            "active_run_id": self.active_run_id,
            "current_step": self.current_step,
            "steps": {k: v.to_dict() for k, v in self.steps.items()},
            "last_checkpoint": self.last_checkpoint,
            "last_error": self.last_error,
            "resume_command": self.resume_command,
            "can_resume": self.can_resume,
            "can_rollback": self.can_rollback,
            "rollback_to": self.rollback_to,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
        # Remove None values and empty lists
        return {k: v for k, v in result.items() if v is not None and v != {}}
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PipelineStatus":
        """Create from dictionary"""
        steps = {}
        for step_name, step_data in data.get("steps", {}).items():
            steps[step_name] = PipelineStepStatus.from_dict(step_data)
        
        return cls(
            project_id=data["project_id"],
            active_run_id=data.get("active_run_id"),
            current_step=data.get("current_step"),
            steps=steps,
            last_checkpoint=data.get("last_checkpoint"),
            last_error=data.get("last_error"),
            resume_command=data.get("resume_command"),
            can_resume=data.get("can_resume", False),
            can_rollback=data.get("can_rollback", False),
            rollback_to=data.get("rollback_to"),
            created_at=data.get("created_at", datetime.utcnow().isoformat()),
            updated_at=data.get("updated_at", datetime.utcnow().isoformat()),
        )
    
    def save(self) -> None:
        """Save to file"""
        self.status_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.status_file, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, default=str)
    
    @classmethod
    def load(cls, project_id: str) -> Optional["PipelineStatus"]:
        """Load from file"""
        status_file = get_state_dir(project_id) / "pipeline_status.json"
        if not status_file.exists():
            return None
        
        with open(status_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls.from_dict(data)
    
    @classmethod
    def get_or_create(cls, project_id: str) -> "PipelineStatus":
        """Load or create a new PipelineStatus"""
        status = cls.load(project_id)
        if status:
            return status
        return cls(project_id=project_id)
    
    def initialize_steps(self) -> None:
        """Initialize all pipeline steps as pending"""
        for step_name in PIPELINE_STEPS:
            if step_name not in self.steps:
                self.steps[step_name] = PipelineStepStatus()
    
    def update_step(
        self,
        step_name: str,
        status: str,
        run_id: Optional[str] = None,
        checkpoint_id: Optional[str] = None,
        artifacts: Optional[List[str]] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """Update the status of a step"""
        # Initialize steps if not done
        if step_name not in self.steps:
            self.steps[step_name] = PipelineStepStatus()
        
        step = self.steps[step_name]
        
        # Update step status
        if status == "running":
            step.started_at = datetime.utcnow().isoformat()
        elif status in ["completed", "failed"]:
            step.completed_at = datetime.utcnow().isoformat()
            step.run_id = run_id
            step.checkpoint_id = checkpoint_id
            if artifacts:
                step.artifacts = artifacts
            if error_message:
                step.error_message = error_message
        
        step.status = status
        
        # Update current state
        if status == "running":
            self.current_step = step_name
        
        # Update last error
        if status == "failed" and error_message:
            self.last_error = error_message
        
        # Update timestamps
        self.updated_at = datetime.utcnow().isoformat()
        
        # Update derived fields
        self._update_derived_fields()
    
    def _update_derived_fields(self) -> None:
        """Update can_resume, can_rollback, and other derived fields"""
        # Check if we can resume (there are pending or failed steps)
        has_pending = any(s.is_pending() for s in self.steps.values())
        has_failed = any(s.is_failed() for s in self.steps.values())
        self.can_resume = has_pending or has_failed
        
        # Check if we can rollback (there are completed steps)
        completed_steps = [
            (name, step) for name, step in self.steps.items()
            if step.is_completed()
        ]
        self.can_rollback = len(completed_steps) > 0
        
        # Find the last completed step for rollback
        if completed_steps:
            completed_steps.sort(key=lambda x: x[1].completed_at or "")
            last_name, last_step = completed_steps[-1]
            self.rollback_to = last_step.checkpoint_id
        else:
            self.rollback_to = None
        
        # Generate resume command
        if self.can_resume:
            if has_pending:
                # Find first pending step
                for name, step in self.steps.items():
                    if step.is_pending():
                        self.resume_command = f"maestro -p {self.project_id} {name}"
                        break
            elif has_failed:
                # Find first failed step
                for name, step in self.steps.items():
                    if step.is_failed():
                        self.resume_command = f"maestro -p {self.project_id} retry {name}"
                        break
    
    def get_next_step(self) -> Optional[str]:
        """Get the next step to execute"""
        for step_name in PIPELINE_STEPS:
            if step_name not in self.steps:
                return step_name
            step = self.steps[step_name]
            if step.is_pending() or step.is_failed():
                return step_name
        return None
    
    def get_failed_step(self) -> Optional[str]:
        """Get the first failed step"""
        for step_name in PIPELINE_STEPS:
            if step_name in self.steps and self.steps[step_name].is_failed():
                return step_name
        return None
    
    def get_last_completed_step(self) -> Optional[str]:
        """Get the last completed step"""
        completed_steps = [
            (name, step) for name, step in self.steps.items()
            if step.is_completed()
        ]
        if not completed_steps:
            return None
        
        completed_steps.sort(key=lambda x: x[1].completed_at or "")
        return completed_steps[-1][0]
    
    def is_step_completed(self, step_name: str) -> bool:
        """Check if a step is completed"""
        step = self.steps.get(step_name)
        return step is not None and step.is_completed()
    
    def is_step_failed(self, step_name: str) -> bool:
        """Check if a step failed"""
        step = self.steps.get(step_name)
        return step is not None and step.is_failed()
    
    def get_step_status(self, step_name: str) -> str:
        """Get the status of a step"""
        step = self.steps.get(step_name)
        return step.status if step else "pending"
    
    def reset(self) -> None:
        """Reset all steps to pending"""
        for step_name in self.steps:
            self.steps[step_name] = PipelineStepStatus()
        
        self.active_run_id = None
        self.current_step = None
        self.last_error = None
        self.last_checkpoint = None
        self.can_resume = False
        self.can_rollback = False
        self.rollback_to = None
        self.resume_command = None
        self.updated_at = datetime.utcnow().isoformat()
