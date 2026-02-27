#!/usr/bin/env python3
"""
viz3d.py — 3D visualization of metabolic knowledge graphs using PyVista.

Provides interactive 3D rendering of metabolic pathways, reactions, compounds,
and enzymes with selectable layout strategies (Allium or LayerCake).

Author: Eric G. Suchanek, PhD
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def launch(
    db_path: str,
    lancedb_dir: str | None = None,
    layout_name: str = "allium",
    width: int = 1400,
    height: int = 900,
    export_html: str | None = None,
    export_png: str | None = None,
) -> None:
    """
    Launch the 3D metabolic knowledge graph visualizer.

    :param db_path: Path to the MetaKG SQLite database.
    :param lancedb_dir: Path to the LanceDB directory (optional).
    :param layout_name: Layout strategy: "allium" (default) or "cake".
    :param width: Window width in pixels (default: 1400).
    :param height: Window height in pixels (default: 900).
    :param export_html: If provided, export to HTML file instead of launching GUI.
    :param export_png: If provided, export to PNG file instead of launching GUI.
    """
    try:
        import pyvista as pv
        from metakg.store import GraphStore
    except ImportError:
        import sys
        print(
            "ERROR: PyVista and related dependencies not installed.\n"
            "Install visualization support with: poetry install --extras viz3d",
            file=sys.stderr,
        )
        sys.exit(1)

    # Load the knowledge graph
    db = Path(db_path)
    if not db.exists():
        raise FileNotFoundError(f"Database not found: {db}")

    store = GraphStore(str(db))

    try:
        # Load nodes and edges
        nodes_data = store.query_nodes()
        edges_data = store.query_edges()

        if not nodes_data:
            print("WARNING: No nodes found in the database")
            store.close()
            return

        print(f"Loaded {len(nodes_data)} nodes and {len(edges_data)} edges")

        # Convert to layout nodes and edges
        from metakg.layout3d import LayoutEdge, LayoutNode

        layout_nodes = [LayoutNode.from_dict(n) for n in nodes_data]
        layout_edges = [LayoutEdge.from_dict(e) for e in edges_data]

        # Select and compute layout
        if layout_name == "cake":
            from metakg.layout3d import LayerCakeLayout

            layout = LayerCakeLayout()
        else:  # default: allium
            from metakg.layout3d import AlliumLayout

            layout = AlliumLayout()

        positions = layout.compute(layout_nodes, layout_edges)

        print(f"Using {layout_name.capitalize()} layout")

        # Create PyVista mesh
        if export_html or export_png:
            print("Creating visualization for export...")
        else:
            print("Launching interactive 3D viewer...")

        # Create plotter
        pl = pv.Plotter(window_size=(width, height))

        # Add nodes as spheres
        from metakg.primitives import KIND_COMPOUND, KIND_ENZYME, KIND_PATHWAY, KIND_REACTION

        kind_to_color = {
            KIND_PATHWAY: "blue",
            KIND_REACTION: "red",
            KIND_COMPOUND: "green",
            KIND_ENZYME: "orange",
        }

        for node in layout_nodes:
            pos = positions.get(node.id)
            if pos is None:
                continue

            color = kind_to_color.get(node.kind, "gray")
            size = 0.5  # node size

            # Add sphere for this node
            sphere = pv.Sphere(radius=size, center=pos)
            pl.add_mesh(sphere, color=color, opacity=0.8)

        # Add edges as lines
        for edge in layout_edges:
            src_pos = positions.get(edge.src)
            dst_pos = positions.get(edge.dst)
            if src_pos is None or dst_pos is None:
                continue

            # Create line
            line = pv.Line(src_pos, dst_pos)
            pl.add_mesh(line, color="gray", opacity=0.5, line_width=1)

        pl.camera_position = "xy"
        pl.reset_camera()
        pl.add_title(f"MetaKG 3D Explorer — {layout_name.capitalize()} Layout")

        if export_html:
            print(f"Exporting to HTML: {export_html}")
            pl.export_html(str(export_html))
        elif export_png:
            print(f"Exporting to PNG: {export_png}")
            pl.screenshot(str(export_png))
        else:
            pl.show()

    finally:
        store.close()
