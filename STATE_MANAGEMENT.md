# State Management System for Maestro CLI

This document describes the state management architecture implemented for Maestro CLI, which provides **pipeline resumption, checkpointing, rollback, and idempotent operations** between CLI executions.

## Architecture Overview

The system uses a **hybrid JSON + SQLite approach**:

- **JSON files**: Human-readable state for creative data (song structure, sections, tracks, etc.)
- **SQLite database** (`~/.maestro/state.db`): Transactional metadata for runs, checkpoints, artifacts, and events
- **pipeline_status.json**: Operational state for pipeline execution tracking

### Directory Structure

```
songs/projects/my_song/
├── brief.md                    # Human-readable brief
├── state/
│   ├── song.json               # Song structure (Pydantic model)
│   ├── sections.json           # Arranged sections
│   ├── tracks.json             # Orchestrated tracks
│   ├── critique.json           # Critique results
│   ├── rack_state.json         # Carla rack state
│   ├── render_report.json      # Render results
│   ├── pipeline_status.json    # Pipeline operational state
│   └── checkpoints/            # State snapshots
│       ├── cp_12345678_compose/
│       │   ├── manifest.json
│       │   ├── song.json
│       │   └── ...
│       └── cp_87654321_arrange/
│           ├── manifest.json
│           └── ...
├── midi/
│   ├── keys.mid
│   ├── bass.mid
│   └── drums.mid
├── audio/
│   └── mix.wav
└── presets/
    └── carla_rack.json
```

## Core Components

### 1. SQLite Database (`database.py`)

Manages persistent storage for:
- **Projects**: Project metadata and directory paths
- **Runs**: Execution runs with status, steps, timestamps
- **Checkpoints**: Snapshots of state at specific steps
- **Artifacts**: Generated files (MIDI, WAV, etc.)
- **Events**: Detailed log of all operations
- **Locks**: Resource locking for concurrent access

**Key Tables:**
```sql
- projects (project_id, title, root_path, style, created_at, updated_at)
- runs (run_id, project_id, status, current_step, started_at, finished_at)
- checkpoints (checkpoint_id, run_id, project_id, step_name, state_file)
- artifacts (artifact_id, run_id, project_id, kind, path)
- events (event_id, run_id, project_id, step_name, level, message)
```

### 2. Pipeline Status (`pipeline_status.py`)

Tracks the operational state of the pipeline execution:
- Which steps are completed/pending/failed
- Current active run
- Last checkpoint information
- Resume command generation
- Rollback capability

**Pipeline Steps:**
```python
PIPELINE_STEPS = [
    "compose",      # Generate song structure
    "arrange",      # Arrange into sections
    "orchestrate",  # Orchestrate into tracks
    "critique",     # Critique the orchestration
    "repair",       # Repair issues
    "carla_load",   # Load Carla rack
    "render",       # Render audio
    "play"          # Play the result
]
```

### 3. Checkpoint Manager (`checkpoint.py`)

Creates and restores state snapshots:
- Creates checkpoint directories with timestamps
- Copies all state files to checkpoint directory
- Calculates fingerprints for integrity verification
- Provides restore functionality

### 4. Run Manager (`run_manager.py`)

Orchestrates the complete workflow:
- Starts new runs or resumes existing ones
- Tracks step execution
- Creates checkpoints automatically
- Manages run lifecycle (start, complete, cancel)
- Provides rollback functionality
- Logs all events to SQLite

## Usage Examples

### Basic Workflow

```bash
# Initialize a project (creates project in DB and JSON files)
maestro init my_song --title "My Gospel Song" --bpm 92

# Run the pipeline
maestro -p my_song compose
maestro -p my_song arrange
maestro -p my_song orchestrate

# Check status
maestro -p my_song status

# Continue pipeline
maestro -p my_song critique
maestro -p my_song repair
maestro -p my_song carla_load
maestro -p my_song render
maestro -p my_song play
```

### State Management Commands

```bash
# Show pipeline status with step completion
maestro -p my_song status

# Resume an incomplete run
maestro -p my_song resume

# Rollback to a specific step
maestro -p my_song rollback --step orchestrate

# Rollback to a specific checkpoint
maestro -p my_song rollback --checkpoint cp_12345678_compose

# Show run history
maestro -p my_song history

# Show event log
maestro -p my_song events

# List all projects
maestro projects

# Clean up old runs and checkpoints
maestro -p my_song cleanup --max-runs 5 --max-checkpoints 5
```

### Viewing Run Details

```bash
# Get detailed summary of current run
maestro -p my_song status

# Output includes:
# - Active run ID
# - Current step
# - Step completion status for all steps
# - Checkpoints available
# - Artifacts generated
# - Events logged
```

## Resumption Flow

When a run is interrupted (e.g., CLI crash, user cancellation):

1. **Detection**: `RunManager.resume()` checks for incomplete runs in SQLite
2. **State Loading**: Pipeline status and checkpoints are reloaded
3. **Context Restoration**: Run context is recreated with the last step
4. **User Guidance**: System provides next step suggestion

Example:
```bash
$ maestro -p my_song compose
$ maestro -p my_song arrange
# User interrupts here (Ctrl+C)

$ maestro -p my_song resume
Resumed run: run_20260728_120000_abc123
  Current step: arrange

To continue: maestro -p my_song orchestrate
```

## Rollback Flow

To revert to a previous state:

1. **Identify Target**: Specify checkpoint ID or step name
2. **State Restoration**: Checkpoint files are copied back to state directory
3. **Pipeline Reset**: Steps after the target are reset to pending
4. **Run Reactivation**: Run is marked as running again

Example:
```bash
$ maestro -p my_song rollback --step orchestrate
Rolled back successfully

New pipeline status:
  [DONE] compose
  [DONE] arrange
  [PEND] orchestrate
  [PEND] critique
  ...
```

## Idempotency

Each pipeline step follows these principles:

1. **Check Prerequisites**: Verify required files exist
2. **Start Step**: Mark step as running in both DB and JSON
3. **Execute**: Perform the actual work
4. **Create Checkpoint**: Snapshot state before finalizing
5. **Complete Step**: Mark step as completed with artifacts
6. **Error Handling**: On failure, mark step as failed with error message

This ensures:
- Steps can be safely retried
- Partial failures don't corrupt state
- Resumption always picks up from the right point

## Database Schema

```sql
-- Projects table
CREATE TABLE projects (
    project_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    root_path TEXT NOT NULL,
    style TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    is_active BOOLEAN DEFAULT 1
);

-- Runs table
CREATE TABLE runs (
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

-- Checkpoints table
CREATE TABLE checkpoints (
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

-- Artifacts table
CREATE TABLE artifacts (
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

-- Events table
CREATE TABLE events (
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
```

## JSON Schemas

### pipeline_status.json

```json
{
  "project_id": "my_song",
  "active_run_id": "run_20260728_120000_abc123",
  "current_step": "arrange",
  "steps": {
    "compose": {
      "status": "completed",
      "completed_at": "2026-07-28T12:00:00",
      "run_id": "run_20260728_120000_abc123",
      "checkpoint_id": "cp_12345678_compose",
      "artifacts": ["songs/projects/my_song/state/song.json"]
    },
    "arrange": {
      "status": "running",
      "started_at": "2026-07-28T12:05:00",
      "run_id": "run_20260728_120000_abc123"
    },
    "orchestrate": {
      "status": "pending"
    },
    ...
  },
  "last_checkpoint": {
    "checkpoint_id": "cp_12345678_compose",
    "step_name": "compose",
    "created_at": "2026-07-28T12:00:00"
  },
  "can_resume": true,
  "can_rollback": true,
  "rollback_to": "cp_12345678_compose",
  "resume_command": "maestro -p my_song orchestrate",
  "created_at": "2026-07-28T12:00:00",
  "updated_at": "2026-07-28T12:05:00"
}
```

### Checkpoint Manifest (checkpoints/<checkpoint_id>/manifest.json)

```json
{
  "checkpoint_id": "cp_12345678_compose",
  "project_id": "my_song",
  "step_name": "compose",
  "created_at": "2026-07-28T12:00:00",
  "files": {
    "song.json": "song.json"
  },
  "fingerprint": "a1b2c3d4e5f6...",
  "metadata": {}
}
```

## Python API

### Database Operations

```python
from maestro_cli.storage.database import SQLiteDB

db = SQLiteDB()

# Projects
db.create_project("my_song", "My Song", "/path/to/project")
db.get_project("my_song")
db.list_projects()

# Runs
db.create_run("run_001", "my_song", status="running")
db.get_run("run_001")
db.get_incomplete_run("my_song")  # For resume
db.list_runs("my_song")

# Checkpoints
db.create_checkpoint("cp_001", "run_001", "my_song", "compose", "pipeline", "/path/to/state.json")
db.get_checkpoint("cp_001")
db.list_checkpoints(project_id="my_song")

# Artifacts
db.add_artifact("run_001", "my_song", "midi", "/path/to/song.mid")
db.list_artifacts(project_id="my_song")

# Events
db.add_event("run_001", "my_song", "compose", "info", "Step started")
db.get_events(project_id="my_song")
```

### Pipeline Status

```python
from maestro_cli.storage.pipeline_status import PipelineStatus

# Load or create
status = PipelineStatus.get_or_create("my_song")

# Initialize steps
status.initialize_steps()

# Update step status
status.update_step("compose", "completed", run_id="run_001", artifacts=["song.json"])

# Check status
status.is_step_completed("compose")  # True
status.get_next_step()  # "arrange"
status.get_failed_step()  # None or first failed step
status.get_last_completed_step()  # "compose"

# Save
status.save()
```

### Checkpoint Manager

```python
from maestro_cli.storage.checkpoint import CheckpointManager

cm = CheckpointManager("my_song")

# Create checkpoint
checkpoint_id = cm.create("compose", metadata={"note": "After composition"})

# Restore checkpoint
cm.restore(checkpoint_id)

# List checkpoints
cm.list()

# Get info
cm.get_info(checkpoint_id)

# Cleanup
cm.cleanup(max_checkpoints=10)
```

### Run Manager (High-Level API)

```python
from maestro_cli.storage.run_manager import RunManager

manager = RunManager("my_song")

# Start a new run
context = manager.start_run()

# Execute steps
manager.start_step("compose")
# ... do work ...
manager.complete_step("compose", artifacts=["song.json"])

manager.start_step("arrange")
# ... do work ...
manager.complete_step("arrange", artifacts=["sections.json"])

# Complete the entire run
manager.complete_run()

# Or resume a previous run
context = manager.resume()
if context:
    next_step = manager.pipeline_status.get_next_step()
    manager.start_step(next_step)
    # ... continue work ...

# Rollback
manager.rollback(step_name="compose")  # Rollback to last checkpoint for compose

# Get run information
summary = manager.get_run_summary()
runs = manager.list_runs()
events = manager.get_events()
```

## Error Handling

The system automatically tracks errors:

```python
try:
    manager.start_step("compose")
    # ... work that fails ...
except Exception as e:
    manager.fail_step("compose", str(e))
    # Step is marked as failed
    # Error is logged to events
    # Pipeline status updated
    # Can be retried later
```

## Best Practices

1. **Always use RunManager** for pipeline execution - it handles all state tracking automatically
2. **Create checkpoints** after significant work, not just at step completion
3. **Validate prerequisites** before starting a step
4. **Log events** for important operations using `db.add_event()`
5. **Keep state files small** - they should be human-readable JSON
6. **Use artifacts table** to track all generated files
7. **Clean up regularly** with `manager.cleanup()` to avoid database bloat

## Testing

Run the test suite:

```bash
# Test database operations
python test_simple.py

# Test complete workflow
python test_workflow.py
```

## Future Enhancements

- [ ] Add remote database support (PostgreSQL, MySQL)
- [ ] Add state synchronization across devices
- [ ] Add visualization dashboard for pipeline status
- [ ] Add automatic cleanup of old runs
- [ ] Add support for branching workflows
- [ ] Add undo/redo functionality

## Migration Notes

This system is designed to be backward compatible:

- Existing projects without SQLite will work (new DB entries are created on first use)
- JSON files remain the source of truth for creative state
- SQLite only tracks metadata and execution history
- Can be disabled by not importing storage modules

## References

- [SQLite Documentation](https://www.sqlite.org/docs.html)
- [Python sqlite3 Module](https://docs.python.org/3/library/sqlite3.html)
- [Pydantic Documentation](https://pydantic.dev/)
