#!/usr/bin/env python3
"""
Simple test script that doesn't import config
"""

import sys
import os
from pathlib import Path

# Ensure we're in the right directory
os.chdir(Path(__file__).parent)
sys.path.insert(0, str(Path(__file__).parent / "src"))

print("Testing storage module directly...")

# Test without importing config
try:
    # First, let's just test the database module directly
    import importlib.util
    spec = importlib.util.spec_from_file_location("database", "src/maestro_cli/storage/database.py")
    database_module = importlib.util.module_from_spec(spec)
    
    # We need to provide the dependencies manually
    sys.modules['maestro_cli.config'] = type(sys)('maestro_cli.config')
    sys.modules['maestro_cli.config'].get_project_dir = lambda p: Path("/tmp") / p
    sys.modules['maestro_cli.config'].get_state_dir = lambda p: Path("/tmp") / p / "state"
    
    spec.loader.exec_module(database_module)
    
    SQLiteDB = database_module.SQLiteDB
    
    # Create a test database
    db_path = Path("/tmp/test_maestro_simple.db")
    if db_path.exists():
        db_path.unlink()
    
    db = SQLiteDB(db_path=db_path)
    
    # Create project
    project = db.create_project(
        project_id="test_project",
        title="Test Project",
        root_path="/tmp/test",
        style="gospel"
    )
    assert project.project_id == "test_project"
    print("  ✓ Create project")
    
    # Create run
    run = db.create_run(
        project_id="test_project",
        run_id="test_run_001",
        status="running",
        current_step="compose"
    )
    assert run.run_id == "test_run_001"
    print("  ✓ Create run")
    
    # Create checkpoint
    checkpoint = db.create_checkpoint(
        run_id="test_run_001",
        project_id="test_project",
        step_name="compose",
        state_type="pipeline_state",
        state_file="/tmp/test/pipeline_status.json",
        checkpoint_id="cp_001"
    )
    assert checkpoint.checkpoint_id == "cp_001"
    print("  ✓ Create checkpoint")
    
    # Add artifact
    artifact = db.add_artifact(
        run_id="test_run_001",
        project_id="test_project",
        kind="midi",
        path="/tmp/test/song.mid"
    )
    assert artifact.kind == "midi"
    print("  ✓ Add artifact")
    
    # Add event
    event = db.add_event(
        run_id="test_run_001",
        project_id="test_project",
        step_name="compose",
        level="info",
        message="Test event"
    )
    assert event.message == "Test event"
    print("  ✓ Add event")
    
    # List projects
    projects = db.list_projects()
    assert len(projects) >= 1
    print("  ✓ List projects")
    
    # Cleanup
    db_path.unlink()
    print("  ✓ Database operations successful")
    
    print("\n✓ All database tests passed!")
    
except Exception as e:
    print(f"✗ Test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
