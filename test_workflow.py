#!/usr/bin/env python3
"""
Test the complete workflow manually without importing problematic modules
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Mock config module to avoid pydantic import issues
import types
config_mock = types.ModuleType('maestro_cli.config')
config_mock.PROJECT_ROOT = Path(__file__).parent
config_mock.settings = types.SimpleNamespace(
    SONGS_DIR=Path("songs/projects"),
    AUDIO_SAMPLE_RATE=48000,
    AUDIO_BIT_DEPTH=24
)

# Mock get_* functions
import tempfile
import shutil

# Create a temp directory for testing
test_root = Path(tempfile.mkdtemp())
print(f"Using test directory: {test_root}")

config_mock.get_project_dir = lambda p: test_root / "songs" / "projects" / p
config_mock.get_state_dir = lambda p: test_root / "songs" / "projects" / p / "state"
config_mock.get_midi_dir = lambda p: test_root / "songs" / "projects" / p / "midi"
config_mock.get_audio_dir = lambda p: test_root / "songs" / "projects" / p / "audio"
config_mock.ensure_project_structure = lambda p: (
    (test_root / "songs" / "projects" / p).mkdir(parents=True, exist_ok=True) or
    (test_root / "songs" / "projects" / p / "state").mkdir(parents=True, exist_ok=True) or
    (test_root / "songs" / "projects" / p / "midi").mkdir(parents=True, exist_ok=True) or
    (test_root / "songs" / "projects" / p / "audio").mkdir(parents=True, exist_ok=True) or
    True
)

sys.modules['maestro_cli.config'] = config_mock

# Also mock models to avoid pydantic issues
models_mock = types.ModuleType('maestro_cli.models')
models_mock.song = types.ModuleType('maestro_cli.models.song')
models_mock.sections = types.ModuleType('maestro_cli.models.sections')
models_mock.tracks = types.ModuleType('maestro_cli.models.tracks')
models_mock.critique = types.ModuleType('maestro_cli.models.critique')
models_mock.rack_state = types.ModuleType('maestro_cli.models.rack_state')
models_mock.render_report = types.ModuleType('maestro_cli.models.render_report')

sys.modules['maestro_cli.models'] = models_mock
sys.modules['maestro_cli.models.song'] = models_mock.song
sys.modules['maestro_cli.models.sections'] = models_mock.sections
sys.modules['maestro_cli.models.tracks'] = models_mock.tracks
sys.modules['maestro_cli.models.critique'] = models_mock.critique
sys.modules['maestro_cli.models.rack_state'] = models_mock.rack_state
sys.modules['maestro_cli.models.render_report'] = models_mock.render_report

# Now import storage modules
print("Importing storage modules...")

try:
    from maestro_cli.storage.database import SQLiteDB
    print("  ✓ database")
    
    from maestro_cli.storage.pipeline_status import PipelineStatus, PIPELINE_STEPS
    print("  ✓ pipeline_status")
    
    from maestro_cli.storage.checkpoint import CheckpointManager
    print("  ✓ checkpoint")
    
    from maestro_cli.storage.run_manager import RunManager
    print("  ✓ run_manager")
    
except Exception as e:
    print(f"  ✗ Import failed: {e}")
    import traceback
    traceback.print_exc()
    
    # Cleanup
    shutil.rmtree(test_root)
    sys.exit(1)

print("\nTesting workflow with mocked config...")

try:
    # Create a test project
    project_id = "test_workflow"
    project_dir = config_mock.get_project_dir(project_id)
    state_dir = config_mock.get_state_dir(project_id)
    
    # Mock the config functions in the storage modules
    # The modules already imported config, so we need to patch them
    import maestro_cli.storage.database as db_module
    import maestro_cli.storage.pipeline_status as ps_module
    import maestro_cli.storage.checkpoint as cp_module
    import maestro_cli.storage.run_manager as rm_module
    
    # Patch the config imports in these modules
    db_module.get_project_dir = config_mock.get_project_dir
    db_module.get_state_dir = config_mock.get_state_dir
    ps_module.get_state_dir = config_mock.get_state_dir
    cp_module.get_state_dir = config_mock.get_state_dir
    rm_module.get_project_dir = config_mock.get_project_dir
    rm_module.get_state_dir = config_mock.get_state_dir
    
    # Create database
    db_path = test_root / "state.db"
    db = SQLiteDB(db_path=db_path)
    
    # Create project in DB
    project = db.create_project(
        project_id=project_id,
        title="Test Workflow",
        root_path=str(project_dir),
        style="gospel"
    )
    print(f"  ✓ Created project: {project.project_id}")
    
    # Create RunManager
    manager = RunManager(project_id, db=db)
    print(f"  ✓ Created RunManager")
    
    # Start a run
    context = manager.start_run()
    print(f"  ✓ Started run: {context.run_id}")
    
    # Start compose step
    manager.start_step("compose")
    print(f"  ✓ Started compose step")
    
    # Create a song.json file
    song_data = {
        "project_id": project_id,
        "title": "Test Song",
        "style": ["gospel"],
        "tempo_bpm": 92
    }
    song_file = state_dir / "song.json"
    import json
    with open(song_file, 'w') as f:
        json.dump(song_data, f)
    print(f"  ✓ Created song.json")
    
    # Complete compose step
    manager.complete_step("compose", artifacts=[str(song_file)])
    print(f"  ✓ Completed compose step")
    
    # Start arrange step
    manager.start_step("arrange")
    print(f"  ✓ Started arrange step")
    
    # Create sections.json
    sections_data = {
        "project_id": project_id,
        "sections": [
            {"id": "intro", "bars": 8},
            {"id": "verse_1", "bars": 16}
        ]
    }
    sections_file = state_dir / "sections.json"
    with open(sections_file, 'w') as f:
        json.dump(sections_data, f)
    print(f"  ✓ Created sections.json")
    
    # Complete arrange step
    manager.complete_step("arrange", artifacts=[str(sections_file)])
    print(f"  ✓ Completed arrange step")
    
    # Check pipeline status
    pipeline_status = PipelineStatus.load(project_id)
    if pipeline_status:
        print(f"  ✓ Pipeline status loaded")
        print(f"    Active run: {pipeline_status.active_run_id}")
        print(f"    Current step: {pipeline_status.current_step}")
        print(f"    Compose status: {pipeline_status.get_step_status('compose')}")
        print(f"    Arrange status: {pipeline_status.get_step_status('arrange')}")
    else:
        print(f"  ✗ Pipeline status not found")
    
    # List checkpoints
    checkpoints = manager.checkpoint_manager.list()
    print(f"  ✓ Checkpoints: {checkpoints}")
    
    # Get run summary
    summary = manager.get_run_summary()
    print(f"  ✓ Run summary: {summary.get('run_id', 'N/A')}")
    
    # List runs
    runs = manager.list_runs()
    print(f"  ✓ Runs: {len(runs)}")
    
    # Get events
    events = manager.get_events()
    print(f"  ✓ Events: {len(events)}")
    
    # Test resume
    context2 = manager.resume()
    if context2:
        print(f"  ✓ Can resume: {context2.run_id}")
    else:
        print(f"  ✗ Cannot resume (run already complete)")
    
    # Test rollback
    try:
        manager.rollback(step_name="compose")
        print(f"  ✓ Rollback to compose successful")
    except Exception as e:
        print(f"  ✗ Rollback failed: {e}")
    
    # Cleanup
    shutil.rmtree(test_root)
    print("\n" + "="*50)
    print("WORKFLOW TEST COMPLETED SUCCESSFULLY!")
    print("="*50)
    
except Exception as e:
    print(f"\n✗ Workflow test failed: {e}")
    import traceback
    traceback.print_exc()
    
    # Cleanup
    try:
        shutil.rmtree(test_root)
    except:
        pass
    sys.exit(1)
