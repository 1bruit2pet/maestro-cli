"""
SQLite database for Maestro CLI state management
Provides transactional persistence for projects, runs, checkpoints, artifacts, and events
"""

import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime
import json
import uuid
import os

# Default database path
DEFAULT_DB_DIR = Path.home() / ".maestro"
DEFAULT_DB_PATH = DEFAULT_DB_DIR / "state.db"


class DatabaseError(Exception):
    """Database error exception"""
    pass


@dataclass
class Project:
    """A music project"""
    project_id: str
    title: str
    root_path: str
    style: Optional[str] = None
    created_at: str = ""
    updated_at: str = ""
    is_active: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "title": self.title,
            "root_path": self.root_path,
            "style": self.style,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "is_active": self.is_active,
        }


@dataclass
class Run:
    """An execution run of the pipeline"""
    run_id: str
    project_id: str
    trace_id: Optional[str] = None
    status: str = "pending"  # pending, running, completed, failed, cancelled
    current_step: Optional[str] = None
    started_at: str = ""
    finished_at: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "project_id": self.project_id,
            "trace_id": self.trace_id,
            "status": self.status,
            "current_step": self.current_step,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "error_message": self.error_message,
            "metadata": self.metadata,
        }


@dataclass
class Checkpoint:
    """A checkpoint in the pipeline"""
    checkpoint_id: str
    run_id: str
    project_id: str
    step_name: str
    state_type: str
    state_file: str
    fingerprint: Optional[str] = None
    created_at: str = ""
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "run_id": self.run_id,
            "project_id": self.project_id,
            "step_name": self.step_name,
            "state_type": self.state_type,
            "state_file": self.state_file,
            "fingerprint": self.fingerprint,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }


@dataclass 
class Artifact:
    """A generated artifact (MIDI file, WAV file, etc.)"""
    artifact_id: str
    run_id: str
    project_id: str
    kind: str  # midi, audio, preset, etc.
    path: str
    size_bytes: Optional[int] = None
    fingerprint: Optional[str] = None
    created_at: str = ""
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "run_id": self.run_id,
            "project_id": self.project_id,
            "kind": self.kind,
            "path": self.path,
            "size_bytes": self.size_bytes,
            "fingerprint": self.fingerprint,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }


@dataclass
class Event:
    """A log event"""
    event_id: int
    run_id: str
    project_id: str
    step_name: str
    level: str  # debug, info, warning, error
    message: str
    data: Optional[Dict[str, Any]] = None
    created_at: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "run_id": self.run_id,
            "project_id": self.project_id,
            "step_name": self.step_name,
            "level": self.level,
            "message": self.message,
            "data": self.data,
            "created_at": self.created_at,
        }


@dataclass
class Lock:
    """A resource lock"""
    lock_id: str
    resource_type: str
    resource_id: str
    owner: str
    acquired_at: str = ""
    expires_at: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "lock_id": self.lock_id,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "owner": self.owner,
            "acquired_at": self.acquired_at,
            "expires_at": self.expires_at,
        }


class SQLiteDB:
    """
    SQLite database manager for Maestro CLI
    Handles projects, runs, checkpoints, artifacts, and events
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialize database tables"""
        with self._get_connection() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=5000")
            conn.execute("PRAGMA foreign_keys=ON")
            
            conn.executescript(self._get_schema_sql())
    
    def _get_schema_sql(self) -> str:
        """Get the SQL schema"""
        return """
            CREATE TABLE IF NOT EXISTS projects (
                project_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                root_path TEXT NOT NULL,
                style TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                is_active BOOLEAN DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                trace_id TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                current_step TEXT,
                started_at TEXT NOT NULL DEFAULT (datetime('now')),
                finished_at TEXT,
                error_message TEXT,
                metadata JSON,
                FOREIGN KEY(project_id) REFERENCES projects(project_id)
            );

            CREATE TABLE IF NOT EXISTS checkpoints (
                checkpoint_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                step_name TEXT NOT NULL,
                state_type TEXT NOT NULL,
                state_file TEXT NOT NULL,
                fingerprint TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                metadata JSON,
                FOREIGN KEY(run_id) REFERENCES runs(run_id),
                FOREIGN KEY(project_id) REFERENCES projects(project_id)
            );

            CREATE TABLE IF NOT EXISTS artifacts (
                artifact_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                kind TEXT NOT NULL,
                path TEXT NOT NULL,
                size_bytes INTEGER,
                fingerprint TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                metadata JSON,
                FOREIGN KEY(run_id) REFERENCES runs(run_id),
                FOREIGN KEY(project_id) REFERENCES projects(project_id)
            );

            CREATE TABLE IF NOT EXISTS events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                step_name TEXT NOT NULL,
                level TEXT NOT NULL,
                message TEXT NOT NULL,
                data JSON,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY(run_id) REFERENCES runs(run_id),
                FOREIGN KEY(project_id) REFERENCES projects(project_id)
            );

            CREATE TABLE IF NOT EXISTS locks (
                lock_id TEXT PRIMARY KEY,
                resource_type TEXT NOT NULL,
                resource_id TEXT NOT NULL,
                owner TEXT NOT NULL,
                acquired_at TEXT NOT NULL DEFAULT (datetime('now')),
                expires_at TEXT NOT NULL,
                UNIQUE(resource_type, resource_id)
            );

            CREATE INDEX IF NOT EXISTS idx_runs_project ON runs(project_id);
            CREATE INDEX IF NOT EXISTS idx_runs_status ON runs(status);
            CREATE INDEX IF NOT EXISTS idx_runs_started ON runs(started_at);
            CREATE INDEX IF NOT EXISTS idx_checkpoints_run ON checkpoints(run_id);
            CREATE INDEX IF NOT EXISTS idx_checkpoints_project ON checkpoints(project_id);
            CREATE INDEX IF NOT EXISTS idx_artifacts_run ON artifacts(run_id);
            CREATE INDEX IF NOT EXISTS idx_artifacts_project ON artifacts(project_id);
            CREATE INDEX IF NOT EXISTS idx_events_run ON events(run_id);
            CREATE INDEX IF NOT EXISTS idx_events_project ON events(project_id);
            CREATE INDEX IF NOT EXISTS idx_events_created ON events(created_at);
        """
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection with Row factory"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn
    
    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Convert row to dict"""
        return {col: row[col] for col in row.keys()}
    
    def _load_json(self, row: sqlite3.Row, key: str) -> Optional[Dict]:
        """Load JSON field"""
        data = row[key]
        return json.loads(data) if data else None
    
    def _make_obj(self, row: sqlite3.Row, dataclass_type, json_fields: list = None):
        """Create a dataclass object from a row, handling JSON fields"""
        json_fields = json_fields or []
        row_dict = self._row_to_dict(row)
        # Remove JSON fields from dict as they need special handling
        for field in json_fields:
            row_dict.pop(field, None)
        # Add back as parsed JSON
        for field in json_fields:
            row_dict[field] = self._load_json(row, field)
        return dataclass_type(**row_dict)

    # ========== PROJECTS ==========

    def create_project(
        self,
        project_id: str,
        title: str,
        root_path: str,
        style: Optional[str] = None
    ) -> Project:
        """Create a new project"""
        with self._get_connection() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO projects (project_id, title, root_path, style) VALUES (?, ?, ?, ?)",
                (project_id, title, root_path, style)
            )
        return self.get_project(project_id)

    def get_project(self, project_id: str) -> Optional[Project]:
        """Get a project by ID"""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM projects WHERE project_id = ?",
                (project_id,)
            ).fetchone()
            if row:
                return Project(**self._row_to_dict(row))
        return None

    def update_project(self, project_id: str, **kwargs) -> Optional[Project]:
        """Update a project"""
        if "updated_at" not in kwargs:
            kwargs["updated_at"] = datetime.utcnow().isoformat()
        
        with self._get_connection() as conn:
            set_clause = ", ".join(f"{k} = ?" for k in kwargs.keys())
            values = list(kwargs.values()) + [project_id]
            
            conn.execute(
                f"UPDATE projects SET {set_clause} WHERE project_id = ?",
                values
            )
        return self.get_project(project_id)

    def list_projects(self, active_only: bool = False) -> List[Project]:
        """List all projects"""
        with self._get_connection() as conn:
            query = "SELECT * FROM projects"
            if active_only:
                query += " WHERE is_active = 1"
            query += " ORDER BY updated_at DESC"
            
            rows = conn.execute(query).fetchall()
            return [Project(**self._row_to_dict(row)) for row in rows]

    def deactivate_project(self, project_id: str) -> bool:
        """Deactivate a project"""
        result = self.update_project(project_id, is_active=False)
        return result is not None

    # ========== RUNS ==========

    def create_run(
        self,
        project_id: str,
        run_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        status: str = "pending",
        current_step: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Run:
        """Create a new run"""
        run_id = run_id or f"run_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        started_at = datetime.utcnow().isoformat()
        
        with self._get_connection() as conn:
            conn.execute(
                """INSERT INTO runs 
                   (run_id, project_id, trace_id, status, current_step, started_at, metadata)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (run_id, project_id, trace_id, status, current_step, started_at, json.dumps(metadata))
            )
        return self.get_run(run_id)

    def get_run(self, run_id: str) -> Optional[Run]:
        """Get a run by ID"""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM runs WHERE run_id = ?",
                (run_id,)
            ).fetchone()
            if row:
                return self._make_obj(row, Run, ["metadata"])
        return None

    def get_incomplete_run(self, project_id: str) -> Optional[Run]:
        """Get the incomplete run for a project"""
        with self._get_connection() as conn:
            row = conn.execute(
                """SELECT * FROM runs 
                   WHERE project_id = ? AND status IN ('pending', 'running')
                   ORDER BY started_at DESC LIMIT 1""",
                (project_id,)
            ).fetchone()
            if row:
                return self._make_obj(row, Run, ["metadata"])
        return None

    def get_last_run(self, project_id: str) -> Optional[Run]:
        """Get the last run for a project"""
        with self._get_connection() as conn:
            row = conn.execute(
                """SELECT * FROM runs 
                   WHERE project_id = ?
                   ORDER BY started_at DESC LIMIT 1""",
                (project_id,)
            ).fetchone()
            if row:
                return self._make_obj(row, Run, ["metadata"])
        return None

    def update_run(self, run_id: str, **kwargs) -> Optional[Run]:
        """Update a run"""
        if "finished_at" not in kwargs and kwargs.get("status") in ["completed", "failed", "cancelled"]:
            kwargs["finished_at"] = datetime.utcnow().isoformat()
        
        with self._get_connection() as conn:
            set_clause = ", ".join(f"{k} = ?" for k in kwargs.keys())
            values = list(kwargs.values()) + [run_id]
            
            conn.execute(
                f"UPDATE runs SET {set_clause} WHERE run_id = ?",
                values
            )
        return self.get_run(run_id)

    def list_runs(self, project_id: str, limit: int = 10) -> List[Run]:
        """List runs for a project"""
        with self._get_connection() as conn:
            rows = conn.execute(
                """SELECT * FROM runs 
                   WHERE project_id = ?
                   ORDER BY started_at DESC LIMIT ?""",
                (project_id, limit)
            ).fetchall()
            return [
                self._make_obj(row, Run, ["metadata"])
                for row in rows
            ]

    # ========== CHECKPOINTS ==========

    def create_checkpoint(
        self,
        run_id: str,
        project_id: str,
        step_name: str,
        state_type: str,
        state_file: str,
        checkpoint_id: Optional[str] = None,
        fingerprint: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Checkpoint:
        """Create a checkpoint"""
        checkpoint_id = checkpoint_id or f"cp_{int(datetime.utcnow().timestamp())}_{step_name}"
        created_at = datetime.utcnow().isoformat()
        
        with self._get_connection() as conn:
            conn.execute(
                """INSERT INTO checkpoints 
                   (checkpoint_id, run_id, project_id, step_name, state_type, state_file, fingerprint, created_at, metadata)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (checkpoint_id, run_id, project_id, step_name, state_type, state_file, fingerprint, created_at, json.dumps(metadata))
            )
        return self.get_checkpoint(checkpoint_id)

    def get_checkpoint(self, checkpoint_id: str) -> Optional[Checkpoint]:
        """Get a checkpoint by ID"""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM checkpoints WHERE checkpoint_id = ?",
                (checkpoint_id,)
            ).fetchone()
            if row:
                return self._make_obj(row, Checkpoint, ["metadata"])
        return None

    def get_checkpoint_for_run(self, run_id: str, step_name: str) -> Optional[Checkpoint]:
        """Get the checkpoint for a run and step"""
        with self._get_connection() as conn:
            row = conn.execute(
                """SELECT * FROM checkpoints 
                   WHERE run_id = ? AND step_name = ?
                   ORDER BY created_at DESC LIMIT 1""",
                (run_id, step_name)
            ).fetchone()
            if row:
                return self._make_obj(row, Checkpoint, ["metadata"])
        return None

    def list_checkpoints(self, project_id: Optional[str] = None, run_id: Optional[str] = None) -> List[Checkpoint]:
        """List checkpoints"""
        with self._get_connection() as conn:
            if run_id:
                rows = conn.execute(
                    "SELECT * FROM checkpoints WHERE run_id = ? ORDER BY created_at DESC",
                    (run_id,)
                ).fetchall()
            elif project_id:
                rows = conn.execute(
                    "SELECT * FROM checkpoints WHERE project_id = ? ORDER BY created_at DESC",
                    (project_id,)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM checkpoints ORDER BY created_at DESC LIMIT 100"
                ).fetchall()
            
            return [
                self._make_obj(row, Checkpoint, ["metadata"])
                for row in rows
            ]

    # ========== ARTIFACTS ==========

    def add_artifact(
        self,
        run_id: str,
        project_id: str,
        kind: str,
        path: str,
        size_bytes: Optional[int] = None,
        fingerprint: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Artifact:
        """Add a generated artifact"""
        artifact_id = str(uuid.uuid4())
        created_at = datetime.utcnow().isoformat()
        
        with self._get_connection() as conn:
            conn.execute(
                """INSERT INTO artifacts 
                   (artifact_id, run_id, project_id, kind, path, size_bytes, fingerprint, created_at, metadata)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (artifact_id, run_id, project_id, kind, path, size_bytes, fingerprint, created_at, json.dumps(metadata))
            )
        return self.get_artifact(artifact_id)

    def get_artifact(self, artifact_id: str) -> Optional[Artifact]:
        """Get an artifact by ID"""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM artifacts WHERE artifact_id = ?",
                (artifact_id,)
            ).fetchone()
            if row:
                return self._make_obj(row, Artifact, ["metadata"])
        return None

    def list_artifacts(self, project_id: Optional[str] = None, run_id: Optional[str] = None) -> List[Artifact]:
        """List artifacts"""
        with self._get_connection() as conn:
            if run_id:
                rows = conn.execute(
                    "SELECT * FROM artifacts WHERE run_id = ? ORDER BY created_at DESC",
                    (run_id,)
                ).fetchall()
            elif project_id:
                rows = conn.execute(
                    "SELECT * FROM artifacts WHERE project_id = ? ORDER BY created_at DESC",
                    (project_id,)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM artifacts ORDER BY created_at DESC LIMIT 100"
                ).fetchall()
            
            return [
                self._make_obj(row, Artifact, ["metadata"])
                for row in rows
            ]

    # ========== EVENTS ==========

    def add_event(
        self,
        run_id: str,
        project_id: str,
        step_name: str,
        level: str,
        message: str,
        data: Optional[Dict] = None
    ) -> Event:
        """Add an event to the log"""
        created_at = datetime.utcnow().isoformat()
        
        with self._get_connection() as conn:
            cursor = conn.execute(
                """INSERT INTO events 
                   (run_id, project_id, step_name, level, message, data, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (run_id, project_id, step_name, level, message, json.dumps(data), created_at)
            )
            event_id = cursor.lastrowid
        
        return Event(
            event_id=event_id,
            run_id=run_id,
            project_id=project_id,
            step_name=step_name,
            level=level,
            message=message,
            data=data,
            created_at=created_at
        )

    def get_events(
        self,
        run_id: Optional[str] = None,
        project_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Event]:
        """Get events"""
        with self._get_connection() as conn:
            if run_id:
                rows = conn.execute(
                    "SELECT * FROM events WHERE run_id = ? ORDER BY created_at DESC LIMIT ?",
                    (run_id, limit)
                ).fetchall()
            elif project_id:
                rows = conn.execute(
                    "SELECT * FROM events WHERE project_id = ? ORDER BY created_at DESC LIMIT ?",
                    (project_id, limit)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM events ORDER BY created_at DESC LIMIT ?",
                    (limit,)
                ).fetchall()
            
            return [
                Event(
                    event_id=row["event_id"],
                    run_id=row["run_id"],
                    project_id=row["project_id"],
                    step_name=row["step_name"],
                    level=row["level"],
                    message=row["message"],
                    data=json.loads(row["data"]) if row["data"] else None,
                    created_at=row["created_at"]
                )
                for row in rows
            ]

    # ========== LOCKS ==========

    def acquire_lock(self, resource_type: str, resource_id: str, owner: str, ttl_seconds: int = 60) -> bool:
        """Acquire a lock on a resource"""
        lock_id = f"{resource_type}:{resource_id}"
        acquired_at = datetime.utcnow().isoformat()
        
        with self._get_connection() as conn:
            # Check if lock exists and is not expired
            row = conn.execute(
                """SELECT * FROM locks 
                   WHERE resource_type = ? AND resource_id = ? AND expires_at > ?""",
                (resource_type, resource_id, datetime.utcnow().isoformat())
            ).fetchone()
            
            if row:
                return False
            
            # Create lock
            conn.execute(
                """INSERT OR REPLACE INTO locks 
                   (lock_id, resource_type, resource_id, owner, acquired_at, expires_at)
                   VALUES (?, ?, ?, ?, ?, datetime(?))""",
                (lock_id, resource_type, resource_id, owner, acquired_at, f"{ttl_seconds} seconds")
            )
        return True

    def release_lock(self, resource_type: str, resource_id: str, owner: str) -> bool:
        """Release a lock"""
        with self._get_connection() as conn:
            result = conn.execute(
                """DELETE FROM locks 
                   WHERE resource_type = ? AND resource_id = ? AND owner = ?""",
                (resource_type, resource_id, owner)
            )
            return result.rowcount > 0

    def has_lock(self, resource_type: str, resource_id: str) -> bool:
        """Check if a resource is locked"""
        with self._get_connection() as conn:
            row = conn.execute(
                """SELECT 1 FROM locks 
                   WHERE resource_type = ? AND resource_id = ? AND expires_at > ?""",
                (resource_type, resource_id, datetime.utcnow().isoformat())
            ).fetchone()
            return row is not None

    def cleanup_expired_locks(self) -> int:
        """Remove expired locks"""
        with self._get_connection() as conn:
            result = conn.execute(
                "DELETE FROM locks WHERE expires_at < datetime('now')"
            )
            return result.rowcount
