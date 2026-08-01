"""
Main entry point for maestro CLI
Allows running with: python -m maestro_cli
"""

import sys

# Try to use the full CLI with typer/rich first (fully supports Claw-DAW rendering)
try:
    from maestro_cli.cli import app
    app()
except ImportError:
    try:
        from maestro_cli.cli_stateful import main as stateful_main
        sys.exit(stateful_main())
    except ImportError:
        try:
            # Fall back to CLI with argparse + rich
            from maestro_cli.cli_simple import main
            import sys
            sys.exit(main())
        except ImportError:
            # Minimal version with only standard library + pydantic
            from maestro_cli.cli_minimal import main
            import sys
            sys.exit(main())
