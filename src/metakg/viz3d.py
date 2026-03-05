#!/usr/bin/env python3
"""
viz3d.py — 3D visualization of metabolic knowledge graphs using PyVista.

Provides interactive 3D rendering of metabolic pathways, reactions, compounds,
and enzymes with selectable layout strategies (Allium or LayerCake).

Author: Eric G. Suchanek, PhD
"""

from __future__ import annotations

from pathlib import Path


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
        print("Loading nodes...", end="", flush=True)
        nodes_data = store.query_nodes()
        print(f" {len(nodes_data)} loaded")

        print("Loading edges...", end="", flush=True)
        edges_data = store.query_edges()
        print(f" {len(edges_data)} loaded")

        if not nodes_data:
            print("WARNING: No nodes found in the database")
            store.close()
            return

        # Convert to layout nodes and edges
        from metakg.layout3d import LayoutEdge, LayoutNode

        print("Converting to layout format...", end="", flush=True)
        layout_nodes = [LayoutNode.from_dict(n) for n in nodes_data]
        layout_edges = [LayoutEdge.from_dict(e) for e in edges_data]
        print(" done")

        # Select and compute layout
        from metakg.layout3d import AlliumLayout, LayerCakeLayout, Layout3D

        if layout_name == "cake":
            layout: Layout3D = LayerCakeLayout()
        else:  # default: allium
            layout = AlliumLayout()

        print(f"Computing {layout_name.capitalize()} layout positions...", end="", flush=True)
        positions = layout.compute(layout_nodes, layout_edges)
        print(" done")

        # Create PyVista mesh
        if export_html or export_png:
            print("Creating visualization for export...")
        else:
            print("Launching interactive 3D viewer...")

        # Create plotter
        pl = pv.Plotter(window_size=[width, height])

        # Add nodes as spheres
        from metakg.primitives import KIND_COMPOUND, KIND_ENZYME, KIND_PATHWAY, KIND_REACTION

        kind_to_color = {
            KIND_PATHWAY: "blue",
            KIND_REACTION: "red",
            KIND_COMPOUND: "green",
            KIND_ENZYME: "orange",
        }

        # Count nodes that will actually be added
        positioned_nodes = [n for n in layout_nodes if positions.get(n.id) is not None]
        positioned_edges = [
            e
            for e in layout_edges
            if positions.get(e.src) is not None and positions.get(e.dst) is not None
        ]

        print(f"Adding {len(positioned_nodes)} nodes to visualization...", end="", flush=True)
        node_count = 0
        progress_step = max(1, len(positioned_nodes) // 10)
        for node in positioned_nodes:
            pos = positions[node.id]
            color = kind_to_color.get(node.kind, "gray")
            size = 0.5  # node size
            sphere = pv.Sphere(radius=size, center=pos)
            pl.add_mesh(sphere, color=color, opacity=0.8)
            node_count += 1
            if progress_step > 0 and node_count % progress_step == 0:
                print(".", end="", flush=True)
        print(" done")

        # Add edges as lines
        print(f"Adding {len(positioned_edges)} edges to visualization...", end="", flush=True)
        edge_count = 0
        progress_step = max(1, len(positioned_edges) // 10)
        for edge in positioned_edges:
            src_pos = positions[edge.src]
            dst_pos = positions[edge.dst]
            line = pv.Line(src_pos, dst_pos)
            pl.add_mesh(line, color="gray", opacity=0.5, line_width=1)
            edge_count += 1
            if progress_step > 0 and edge_count % progress_step == 0:
                print(".", end="", flush=True)
        print(" done")

        print("Setting up camera and title...", end="", flush=True)
        pl.camera_position = "xy"
        pl.reset_camera()  # type: ignore[call-arg]
        pl.add_title(f"MetaKG 3D Explorer — {layout_name.capitalize()} Layout")
        print(" done")

        if export_html:
            print(f"Exporting to HTML: {export_html}...", end="", flush=True)
            pl.export_html(str(export_html))
            print(" done")
        elif export_png:
            print(f"Exporting to PNG: {export_png}...", end="", flush=True)
            pl.screenshot(str(export_png))
            print(" done")
        else:
            print("Launching interactive viewer...")
            pl.show()

    finally:
        store.close()
