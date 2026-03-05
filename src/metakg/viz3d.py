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

    Optimized for large graphs using:
    - MultiBlock batching for efficient rendering
    - Adaptive geometry (cubes for 500+ nodes)
    - Efficient edge rendering (skip for 5000+ edges)
    - Proper 3D lighting and anti-aliasing

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

        # Create plotter with optimized settings
        pl = pv.Plotter(window_size=[width, height])
        pl.clear_actors()
        pl.remove_all_lights()
        pl.enable_anti_aliasing("msaa")

        # Setup 3D lighting (key, fill, back lights)
        key_light = pv.Light(
            position=(0, 0, 100), color="white", light_type="scene light"
        )
        fill_light = pv.Light(
            position=(0, 100, 0), color="white", light_type="scene light"
        )
        back_light = pv.Light(
            position=(0, 0, -100), color="white", light_type="scene light"
        )
        pl.add_light(key_light)
        pl.add_light(fill_light)
        pl.add_light(back_light)

        # Node kind to color mapping
        from metakg.primitives import (
            KIND_COMPOUND,
            KIND_ENZYME,
            KIND_PATHWAY,
            KIND_REACTION,
        )

        kind_to_color = {
            KIND_PATHWAY: "blue",
            KIND_REACTION: "red",
            KIND_COMPOUND: "green",
            KIND_ENZYME: "orange",
        }

        # Filter nodes/edges that have positions
        positioned_nodes = [n for n in layout_nodes if positions.get(n.id) is not None]
        positioned_edges = [
            e
            for e in layout_edges
            if positions.get(e.src) is not None and positions.get(e.dst) is not None
        ]

        n_nodes = len(positioned_nodes)
        n_edges = len(positioned_edges)

        # Adaptive rendering: use geometry appropriate to graph size
        use_cubes = n_nodes > 500
        render_edges = n_edges < 5000  # Skip edges for extremely dense graphs
        node_size = 0.3 if use_cubes else 0.5

        print(
            f"Batching {n_nodes} nodes to visualization (adaptive: {'cubes' if use_cubes else 'spheres'})...",
            end="",
            flush=True,
        )

        # Create MultiBlocks grouped by node kind for efficient batching
        node_blocks = {}
        for kind in [KIND_PATHWAY, KIND_REACTION, KIND_COMPOUND, KIND_ENZYME]:
            node_blocks[kind] = pv.MultiBlock()

        # Add nodes to their respective MultiBlocks
        node_count = 0
        progress_step = max(1, n_nodes // 10)
        for node in positioned_nodes:
            pos = positions[node.id]

            # Create geometry (cube or sphere)
            if use_cubes:
                mesh = pv.Cube(
                    center=pos,
                    x_length=node_size,
                    y_length=node_size,
                    z_length=node_size,
                )
            else:
                mesh = pv.Sphere(radius=node_size, center=pos)

            node_blocks[node.kind].append(mesh)
            node_count += 1

            if progress_step > 0 and node_count % progress_step == 0:
                print(".", end="", flush=True)

        # Add all node blocks to plotter (one call per kind)
        for kind, block in node_blocks.items():
            if block.n_blocks > 0:
                color = kind_to_color.get(kind, "gray")
                pl.add_mesh(
                    block,
                    color=color,
                    opacity=0.85,
                    smooth_shading=not use_cubes,
                    show_edges=False,
                    name=f"nodes_{kind}",
                )

        print(" done")

        # Add edges (skip for very dense graphs)
        if render_edges:
            print(f"Batching {n_edges} edges to visualization...", end="", flush=True)

            edge_block = pv.MultiBlock()
            edge_count = 0
            progress_step = max(1, n_edges // 10)

            for edge in positioned_edges:
                src_pos = positions[edge.src]
                dst_pos = positions[edge.dst]

                # Use lines for edges (more efficient than tubes for large counts)
                line = pv.Line(src_pos, dst_pos)
                edge_block.append(line)

                edge_count += 1
                if progress_step > 0 and edge_count % progress_step == 0:
                    print(".", end="", flush=True)

            if edge_block.n_blocks > 0:
                pl.add_mesh(
                    edge_block,
                    color="gray",
                    opacity=0.4,
                    line_width=1,
                    name="edges",
                )

            print(" done")
        else:
            print(f"Skipping {n_edges} edges (graph too dense for readable rendering)")

        print("Setting up camera and rendering...", end="", flush=True)
        pl.reset_camera()
        pl.view_xy()
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
