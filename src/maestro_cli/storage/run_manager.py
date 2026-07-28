"""
Run Manager
Manages execution runs for the pipeline, coordinating SQLite persistence and pipeline status
"""

from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime
import uuid
import json

from maestro_cli.storage.database import SQLiteDB, Run, Project
from maestro_cli.storage.pipeline_status import PipelineStatus, PIPELINE_STEPS, PipelineStepStatus
from maestro_cli.storage.checkpoint import CheckpointManager
from maestro_cli.config import get_project_dir, get_state_dir, ensure_project_structure


@dataclass
class RunContext:
    """Context for a single pipeline run"""
    project_id: str
    run_id: str
    trace_id: Optional[str] = None
    step_name: Optional[str] = None
    is_resume: bool = False
    
    # References to managers
    db: Optional[SQLiteDB] = None
    pipeline_status: Optional[PipelineStatus] = None
    checkpoint_manager: Optional[CheckpointManager] = None
    
    def __post_init__(self):
        if self.db is None:
            self.db = SQLiteDB()
        if self.pipeline_status is None:
            self.pipeline_status = PipelineStatus.get_or_create(self.project_id)
        if self.checkpoint_manager is None:
            self.checkpoint_manager = CheckpointManager(self.project_id)


class RunManager:
    """
    Manages the lifecycle of pipeline execution runs.
    Coordinates between SQLite (for transactional history) and JSON files (for state).
    """
    
    def __init__(self, project_id: str, db: Optional[SQLiteDB] = None):
        self.project_id = project_id
        self.db = db or SQLiteDB()
        self.pipeline_status = PipelineStatus.get_or_create(project_id)
        self.checkpoint_manager = CheckpointManager(project_id)
        self.run_context: Optional[RunContext] = None
        
        # Ensure project exists in DB
        self._ensure_project()
    
    def _ensure_project(self) -> Project:
        """Ensure project exists in database"""
        project_dir = get_project_dir(self.project_id)
        project = self.db.get_project(self.project_id)
        if project is None:
            project = self.db.create_project(
                project_id=self.project_id,
                title=self.project_id,
                root_path=str(project_dir)
            )
        return project
    
    def start_run(
        self,
        trace_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> RunContext:
        """
        Start a new execution run.
        Creates a new run record in SQLite and initializes pipeline status.
        """
        # Generate run ID
        run_id = f"run_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        
        # Check for incomplete run to resume
        incomplete_run = self.db.get_incomplete_run(self.project_id)
        is_resume = incomplete_run is not None
        
        # If we have an incomplete run, use it
        if is_resume and incomplete_run:
            run_id = incomplete_run.run_id
            trace_id = incomplete_run.trace_id or trace_id
        else:
            # Create new run
            run = self.db.create_run(
                run_id=run_id,
                project_id=self.project_id,
                trace_id=trace_id,
                status="running",
                current_step=None,
                metadata=metadata
            )
            trace_id = run.trace_id
        
        # Initialize or update pipeline status
        if self.pipeline_status.active_run_id is None:
            self.pipeline_status.active_run_id = run_id
        self.pipeline_status.current_step = None
        self.pipeline_status.last_error = None
        self.pipeline_status.updated_at = datetime.utcnow().isoformat()
        
        # Initialize steps if not done
        self.pipeline_status.initialize_steps()
        
        # Create context
        context = RunContext(
            project_id=self.project_id,
            run_id=run_id,
            trace_id=trace_id,
            step_name=None,
            is_resume=is_resume,
            db=self.db,
            pipeline_status=self.pipeline_status,
            checkpoint_manager=self.checkpoint_manager
        )
        
        self.run_context = context
        self.pipeline_status.save()
        
        return context
    
    def start_step(self, step_name: str) -> bool:
        """
        Start executing a specific step.
        Updates both SQLite run record and pipeline status JSON.
        """
        if self.run_context is None:
            self.start_run()
        
        context = self.run_context
        
        # Validate step name
        if step_name not in PIPELINE_STEPS:
            raise ValueError(f"Unknown step: {step_name}. Valid steps: {PIPELINE_STEPS}")
        
        # Update run in SQLite
        self.db.update_run(
            context.run_id,
            current_step=step_name,
            status="running"
        )
        
        # Update pipeline status
        self.pipeline_status.update_step(
            step_name=step_name,
            status="running",
            run_id=context.run_id
        )
        self.pipeline_status.current_step = step_name
        self.pipeline_status.save()
        
        context.step_name = step_name
        
        # Log event
        self.db.add_event(
            run_id=context.run_id,
            project_id=self.project_id,
            step_name=step_name,
            level="info",
            message=f"Started step: {step_name}"
        )
        
        return True
    
    def complete_step(
        self,
        step_name: str,
        checkpoint_id: Optional[str] = None,
        artifacts: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Mark a step as successfully completed.
        Creates a checkpoint and updates all state.
        """
        if self.run_context is None:
            raise RuntimeError("No active run. Call start_run() first.")
        
        context = self.run_context
        
        # Create checkpoint for state files
        checkpoint_id = checkpoint_id or self.checkpoint_manager.create(
            step_name=step_name,
            metadata=metadata
        )
        
        # Update SQLite run
        self.db.update_run(
            context.run_id,
            current_step=step_name,
            status="running"  # Still running until all steps done
        )
        
        # Update pipeline status
        self.pipeline_status.update_step(
            step_name=step_name,
            status="completed",
            run_id=context.run_id,
            checkpoint_id=checkpoint_id,
            artifacts=artifacts or []
        )
        self.pipeline_status.save()
        
        # Record checkpoint in SQLite
        state_dir = get_state_dir(self.project_id)
        self.db.create_checkpoint(
            checkpoint_id=checkpoint_id,
            run_id=context.run_id,
            project_id=self.project_id,
            step_name=step_name,
            state_type="pipeline_state",
            state_file=str(state_dir / "pipeline_status.json"),
            fingerprint=None,
            metadata={"artifacts": artifacts}
        )
        
        # Log event
        self.db.add_event(
            run_id=context.run_id,
            project_id=self.project_id,
            step_name=step_name,
            level="info",
            message=f"Completed step: {step_name}",
            data={"checkpoint_id": checkpoint_id, "artifacts": artifacts}
        )
        
        # Update last checkpoint reference
        self.pipeline_status.last_checkpoint = {
            "checkpoint_id": checkpoint_id,
            "step_name": step_name,
            "created_at": datetime.utcnow().isoformat()
        }
        self.pipeline_status.save()
        
        return True
    
    def fail_step(
        self,
        step_name: str,
        error_message: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Mark a step as failed.
        Updates state to allow for retry.
        """
        if self.run_context is None:
            raise RuntimeError("No active run. Call start_run() first.")
        
        context = self.run_context
        
        # Update SQLite run
        self.db.update_run(
            context.run_id,
            current_step=step_name,
            status="failed",
            error_message=error_message
        )
        
        # Update pipeline status
        self.pipeline_status.update_step(
            step_name=step_name,
            status="failed",
            run_id=context.run_id,
            error_message=error_message
        )
        self.pipeline_status.last_error = error_message
        self.pipeline_status.save()
        
        # Log error event
        self.db.add_event(
            run_id=context.run_id,
            project_id=self.project_id,
            step_name=step_name,
            level="error",
            message=f"Failed step: {step_name}",
            data={"error": error_message, "metadata": metadata}
        )
        
        return True
    
    def complete_run(self, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Mark the entire run as completed.
        All steps should be done.
        """
        if self.run_context is None:
            raise RuntimeError("No active run. Call start_run() first.")
        
        context = self.run_context
        
        # Check if all steps are completed
        all_completed = all(
            self.pipeline_status.is_step_completed(step)
            for step in PIPELINE_STEPS
        )
        
        if not all_completed:
            pending = [s for s in PIPELINE_STEPS if not self.pipeline_status.is_step_completed(s)]
            raise RuntimeError(f"Cannot complete run: pending steps: {pending}")
        
        # Update SQLite run
        self.db.update_run(
            context.run_id,
            status="completed",
            finished_at=datetime.utcnow().isoformat(),
            metadata=metadata
        )
        
        # Update pipeline status
        self.pipeline_status.current_step = None
        self.pipeline_status.active_run_id = context.run_id  # Keep reference to last run
        self.pipeline_status.updated_at = datetime.utcnow().isoformat()
        self.pipeline_status.save()
        
        # Log event
        self.db.add_event(
            run_id=context.run_id,
            project_id=self.project_id,
            step_name="pipeline",
            level="info",
            message="Pipeline run completed successfully",
            data=metadata
        )
        
        # Clean up context
        self.run_context = None
        
        return True
    
    def cancel_run(self, error_message: Optional[str] = None) -> bool:
        """
        Cancel the current run.
        """
        if self.run_context is None:
            raise RuntimeError("No active run. Call start_run() first.")
        
        context = self.run_context
        
        # Update SQLite run
        self.db.update_run(
            context.run_id,
            status="cancelled",
            finished_at=datetime.utcnow().isoformat(),
            error_message=error_message
        )
        
        # Update pipeline status
        if context.step_name:
            self.pipeline_status.update_step(
                step_name=context.step_name,
                status="pending",  # Reset to pending for retry
                run_id=None,
                checkpoint_id=None
            )
        
        self.pipeline_status.last_error = error_message or "Run cancelled"
        self.pipeline_status.current_step = None
        self.pipeline_status.updated_at = datetime.utcnow().isoformat()
        self.pipeline_status.save()
        
        # Log event
        self.db.add_event(
            run_id=context.run_id,
            project_id=self.project_id,
            step_name="pipeline",
            level="warning",
            message="Pipeline run cancelled",
            data={"error": error_message}
        )
        
        # Clean up context
        self.run_context = None
        
        return True
    
    def get_current_run(self) -> Optional[Run]:
        """Get the current active run"""
        return self.db.get_incomplete_run(self.project_id)
    
    def get_last_run(self) -> Optional[Run]:
        """Get the last run for this project"""
        return self.db.get_last_run(self.project_id)
    
    def list_runs(self, limit: int = 10) -> List[Run]:
        """List runs for this project"""
        return self.db.list_runs(self.project_id, limit=limit)
    
    def get_events(self, run_id: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """Get events for this project or run"""
        events = self.db.get_events(run_id=run_id, project_id=self.project_id, limit=limit)
        return [e.to_dict() for e in events]
    
    def resume(self) -> Optional[RunContext]:
        """
        Resume an incomplete run.
        Returns context if there's a run to resume, None otherwise.
        """
        incomplete_run = self.db.get_incomplete_run(self.project_id)
        
        if incomplete_run is None:
            return None
        
        # Reload pipeline status
        self.pipeline_status = PipelineStatus.get_or_create(self.project_id)
        
        # Create context for resume
        context = RunContext(
            project_id=self.project_id,
            run_id=incomplete_run.run_id,
            trace_id=incomplete_run.trace_id,
            step_name=incomplete_run.current_step,
            is_resume=True,
            db=self.db,
            pipeline_status=self.pipeline_status,
            checkpoint_manager=self.checkpoint_manager
        )
        
        # Find the failed or pending step to resume from
        failed_step = self.pipeline_status.get_failed_step()
        if failed_step:
            context.step_name = failed_step
        else:
            next_step = self.pipeline_status.get_next_step()
            if next_step:
                context.step_name = next_step
        
        self.run_context = context
        
        return context
    
    def rollback(self, checkpoint_id: Optional[str] = None, step_name: Optional[str] = None) -> bool:
        """
        Rollback to a specific checkpoint or step.
        Restores state files and updates pipeline status.
        """
        # Find checkpoint
        if checkpoint_id:
            checkpoint = self.db.get_checkpoint(checkpoint_id)
            if checkpoint is None:
                raise ValueError(f"Checkpoint not found: {checkpoint_id}")
            target_step = checkpoint.step_name
        elif step_name:
            # Find latest checkpoint for this step
            latest_cp = self.checkpoint_manager.get_latest(step_name)
            if latest_cp is None:
                raise ValueError(f"No checkpoint found for step: {step_name}")
            
            info = self.checkpoint_manager.get_info(latest_cp)
            if info is None:
                raise ValueError(f"Checkpoint info not found: {latest_cp}")
            
            target_step = info.get("step_name")
            checkpoint_id = latest_cp
        else:
            # Rollback to last completed step
            last_completed = self.pipeline_status.get_last_completed_step()
            if last_completed is None:
                raise ValueError("No completed steps to rollback to")
            
            latest_cp = self.checkpoint_manager.get_latest(last_completed)
            if latest_cp is None:
                raise ValueError(f"No checkpoint found for last completed step: {last_completed}")
            
            info = self.checkpoint_manager.get_info(latest_cp)
            if info is None:
                raise ValueError(f"Checkpoint info not found: {latest_cp}")
            
            target_step = info.get("step_name")
            checkpoint_id = latest_cp
        
        # Restore from checkpoint
        if checkpoint_id:
            success = self.checkpoint_manager.restore(checkpoint_id)
            if not success:
                raise RuntimeError(f"Failed to restore checkpoint: {checkpoint_id}")
        
        # Reset steps after the target step to pending
        found_target = False
        for step in PIPELINE_STEPS:
            if step == target_step:
                found_target = True
                continue
            if found_target:
                self.pipeline_status.update_step(step, "pending")
        
        # Update current step
        self.pipeline_status.current_step = target_step
        self.pipeline_status.last_error = None
        self.pipeline_status.updated_at = datetime.utcnow().isoformat()
        self.pipeline_status.save()
        
        # Mark run as running again if it was incomplete
        current_run = self.db.get_incomplete_run(self.project_id)
        if current_run:
            self.db.update_run(
                current_run.run_id,
                current_step=target_step,
                status="running",
                error_message=None
            )
        
        # Log rollback event
        run = self.db.get_incomplete_run(self.project_id)
        if run:
            self.db.add_event(
                run_id=run.run_id,
                project_id=self.project_id,
                step_name="pipeline",
                level="warning",
                message=f"Rolled back to step: {target_step}",
                data={"checkpoint_id": checkpoint_id}
            )
        
        return True
    
    def get_run_summary(self, run_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get a summary of a run or the current run.
        """
        if run_id is None:
            current_run = self.get_current_run()
            if current_run:
                run_id = current_run.run_id
            else:
                last_run = self.get_last_run()
                if last_run:
                    run_id = last_run.run_id
                else:
                    return {"error": "No runs found for project"}
        
        run = self.db.get_run(run_id)
        if run is None:
            return {"error": f"Run not found: {run_id}"}
        
        # Get checkpoints for this run
        checkpoints = self.db.list_checkpoints(run_id=run.run_id)
        
        # Get artifacts for this run
        artifacts = self.db.list_artifacts(run_id=run.run_id)
        
        # Get events for this run
        events = self.db.get_events(run_id=run.run_id, limit=50)
        
        return {
            "run_id": run.run_id,
            "project_id": run.project_id,
            "status": run.status,
            "current_step": run.current_step,
            "started_at": run.started_at,
            "finished_at": run.finished_at,
            "error_message": run.error_message,
            "checkpoints": [cp.to_dict() for cp in checkpoints],
            "artifacts": [a.to_dict() for a in artifacts],
            "events": [e.to_dict() for e in events],
            "pipeline_status": self.pipeline_status.to_dict()
        }
    
    def cleanup(self, max_runs: int = 10, max_checkpoints: int = 10) -> Dict[str, int]:
        """
        Clean up old runs and checkpoints.
        Returns count of deleted items.
        """
        deleted = {"runs": 0, "checkpoints": 0}
        
        # Clean up old runs (keep last max_runs)
        runs = self.db.list_runs(self.project_id, limit=1000)
        if len(runs) > max_runs:
            old_runs = runs[max_runs:]
            for run in old_runs:
                # Delete run and its children
                self.db._get_connection().execute(
                    "DELETE FROM events WHERE run_id = ?", (run.run_id,)
                )
                self.db._get_connection().execute(
                    "DELETE FROM checkpoints WHERE run_id = ?", (run.run_id,)
                )
                self.db._get_connection().execute(
                    "DELETE FROM artifacts WHERE run_id = ?", (run.run_id,)
                )
                self.db._get_connection().execute(
                    "DELETE FROM runs WHERE run_id = ?", (run.run_id,)
                )
                deleted["runs"] += 1
        
        # Clean up checkpoints via CheckpointManager
        deleted["checkpoints"] = self.checkpoint_manager.cleanup(max_checkpoints)
        
        return deleted
    
    def add_artifact(
        self,
        kind: str,
        path: Path,
        size_bytes: Optional[int] = None,
        fingerprint: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Add a generated artifact to the current run.
        """
        if self.run_context is None:
            # Create a run if none exists
            self.start_run()
        
        context = self.run_context
        
        artifact = self.db.add_artifact(
            run_id=context.run_id,
            project_id=self.project_id,
            kind=kind,
            path=str(path),
            size_bytes=size_bytes,
            fingerprint=fingerprint,
            metadata=metadata
        )
        
        return artifact.artifact_id
