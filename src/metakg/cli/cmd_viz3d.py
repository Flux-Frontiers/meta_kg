"""
cmd_viz3d.py — viz3d subcommand.

Registers:
  metakg viz3d  — launch the 3D PyVista visualizer
"""

from __future__ import annotations

from metakg.cli.main import cli


@cli.command("viz3d")
def viz3d() -> None:
    """Launch the 3D PyVista metabolic knowledge-graph visualizer.

    Argument parsing is handled by :mod:`metakg.metakg_viz3d`.
    """
    from metakg.metakg_viz3d import main as viz3d_main_func

    viz3d_main_func()


# ---------------------------------------------------------------------------
# Standalone entry-point alias
# ---------------------------------------------------------------------------

viz3d_main = viz3d
