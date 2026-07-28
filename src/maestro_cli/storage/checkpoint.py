"""
Checkpoint Manager
Creates, restores, and manages checkpoints for pipeline steps
"""

from pathlib import Path
from typing import Optional, Dict, Any, List
import json
import hashlib
import shutil
from datetime import datetime

from maestro_cli.config import get_state_dir


class CheckpointManager:
    """
    Manages checkpoints for pipeline steps.
    A checkpoint is a snapshot of the state files at a specific point in time.
    """
    
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.state_dir = get_state_dir(project_id)
        self.checkpoint_dir = self.state_dir / "checkpoints"
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
    
    def create(
        self,
        step_name: str,
        state_files: Optional[Dict[str, Path]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a checkpoint for the current state.
        
        Args:
            step_name: Name of the pipeline step
            state_files: Dictionary of filename -> Path (if None, uses all state/*.json)
            metadata: Additional metadata to store
            
        Returns:
            checkpoint_id: Unique identifier for the checkpoint
        """
        checkpoint_id = f"cp_{int(datetime.utcnow().timestamp())}_{step_name}"
        
        # If no state files specified, use all JSON files in state dir
        if state_files is None:
            state_files = {}
            for filepath in self.state_dir.glob("*.json"):
                if filepath.name != "pipeline_status.json":
                    state_files[filepath.name] = filepath
        
        # Create checkpoint directory
        checkpoint_path = self.checkpoint_dir / checkpoint_id
        checkpoint_path.mkdir(parents=True, exist_ok=True)
        
        # Copy state files to checkpoint directory
        saved_files = {}
        for filename, filepath in state_files.items():
            dest = checkpoint_path / filename
            shutil.copy2(filepath, dest)
            saved_files[filename] = str(dest.relative_to(checkpoint_path))
        
        # Calculate fingerprint (hash of all files)
        fingerprint = self._calculate_fingerprint(checkpoint_path)
        
        # Create manifest
        manifest = {
            "checkpoint_id": checkpoint_id,
            "project_id": self.project_id,
            "step_name": step_name,
            "created_at": datetime.utcnow().isoformat(),
            "files": saved_files,
            "fingerprint": fingerprint,
            "metadata": metadata or {}
        }
        
        # Save manifest
        manifest_path = checkpoint_path / "manifest.json"
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2)
        
        return checkpoint_id
    
    def _calculate_fingerprint(self, checkpoint_path: Path) -> str:
        """Calculate a fingerprint (hash) for all files in the checkpoint"""
        hasher = hashlib.sha256()
        
        for filepath in sorted(checkpoint_path.glob("*.json")):
            if filepath.name == "manifest.json":
                continue
            try:
                hasher.update(filepath.read_bytes())
            except (IOError, OSError):
                pass
        
        return hasher.hexdigest()
    
    def restore(self, checkpoint_id: str) -> bool:
        """
        Restore a checkpoint to the current state directory.
        
        Args:
            checkpoint_id: The checkpoint to restore
            
        Returns:
            True if successful, False otherwise
        """
        checkpoint_path = self.checkpoint_dir / checkpoint_id
        if not checkpoint_path.exists():
            return False
        
        # Load manifest
        manifest_path = checkpoint_path / "manifest.json"
        if not manifest_path.exists():
            return False
        
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
        
        # Restore each file
        for filename, relative_path in manifest.get("files", {}).items():
            src = checkpoint_path / relative_path
            dest = self.state_dir / filename
            
            try:
                shutil.copy2(src, dest)
            except (IOError, OSError):
                return False
        
        return True
    
    def delete(self, checkpoint_id: str) -> bool:
        """Delete a checkpoint"""
        checkpoint_path = self.checkpoint_dir / checkpoint_id
        if checkpoint_path.exists():
            shutil.rmtree(checkpoint_path)
            return True
        return False
    
    def list(self) -> List[str]:
        """List all checkpoint IDs"""
        if not self.checkpoint_dir.exists():
            return []
        
        checkpoints = []
        for item in self.checkpoint_dir.iterdir():
            if item.is_dir():
                checkpoints.append(item.name)
        
        return sorted(checkpoints, reverse=True)
    
    def get_info(self, checkpoint_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a checkpoint"""
        checkpoint_path = self.checkpoint_dir / checkpoint_id
        if not checkpoint_path.exists():
            return None
        
        manifest_path = checkpoint_path / "manifest.json"
        if not manifest_path.exists():
            return None
        
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
        
        # Add file list
        files = list(checkpoint_path.glob("*.json"))
        manifest["file_count"] = len([f for f in files if f.name != "manifest.json"])
        
        return manifest
    
    def get_latest(self, step_name: Optional[str] = None) -> Optional[str]:
        """Get the latest checkpoint, optionally filtered by step name"""
        checkpoints = self.list()
        if not checkpoints:
            return None
        
        for cp_id in checkpoints:
            info = self.get_info(cp_id)
            if info is None:
                continue
            if step_name is None or info.get("step_name") == step_name:
                return cp_id
        
        return None
    
    def get_all_info(self) -> List[Dict[str, Any]]:
        """Get information about all checkpoints"""
        checkpoints = self.list()
        return [self.get_info(cp) for cp in checkpoints if self.get_info(cp)]
    
    def cleanup(self, max_checkpoints: int = 10) -> int:
        """
        Clean up old checkpoints, keeping only the most recent.
        
        Args:
            max_checkpoints: Maximum number of checkpoints to keep
            
        Returns:
            Number of checkpoints deleted
        """
        checkpoints = self.list()
        if len(checkpoints) <= max_checkpoints:
            return 0
        
        # Sort and delete old checkpoints
        checkpoints.sort(reverse=True)
        to_delete = checkpoints[max_checkpoints:]
        
        for cp_id in to_delete:
            self.delete(cp_id)
        
        return len(to_delete)
