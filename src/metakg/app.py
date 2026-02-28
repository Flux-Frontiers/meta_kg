#!/usr/bin/env python3
"""
app.py — MetaKG Streamlit Metabolic Knowledge Graph Explorer

Interactive metabolic pathway explorer with:
  • Sidebar: configure database paths and query parameters
  • Graph tab: pyvis interactive graph of pathways, reactions, compounds, enzymes
  • Query tab: semantic and structural search with ranked results
  • Details tab: comprehensive node information

Run with:
    poetry run metakg-viz
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import streamlit as st
from pyvis.network import Network

from metakg.store import GraphStore

# ---------------------------------------------------------------------------
# Constants — colours and shapes per node kind
# ---------------------------------------------------------------------------

_KIND_COLOR: dict[str, str] = {
    "pathway": "#3498DB",    # blue
    "reaction": "#E74C3C",   # red
    "compound": "#27AE60",   # green
    "enzyme": "#F39C12",     # orange
}

_KIND_SHAPE: dict[str, str] = {
    "pathway": "box",
    "reaction": "diamond",
    "compound": "dot",
    "enzyme": "triangle",
}

_REL_COLOR: dict[str, str] = {
    "CONTAINS": "#BDC3C7",       # grey
    "SUBSTRATE_OF": "#3498DB",   # blue
    "PRODUCT_OF": "#27AE60",     # green
    "CATALYZES": "#F39C12",      # orange
    "INHIBITS": "#E74C3C",       # red
    "ACTIVATES": "#F1C40F",      # yellow
    "XREF": "#95A5A6",           # dark grey
}

# Honour the METAKG_DB env var for Docker deployment
_DEFAULT_DB = os.environ.get("METAKG_DB", ".metakg/meta.sqlite")
_DEFAULT_LANCEDB = os.environ.get("METAKG_LANCEDB", ".metakg/lancedb")

# ---------------------------------------------------------------------------
# Page config (must be first Streamlit call)
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="MetaKG Explorer",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Minimal CSS tweaks
# ---------------------------------------------------------------------------

st.markdown(
    """
    <style>
    .stTabs [data-baseweb="tab-list"] { gap: 12px; }
    .stTabs [data-baseweb="tab"] { font-size: 1rem; padding: 6px 18px; }
    .node-card {
        background: #1e1e2e;
        border-left: 4px solid #3498DB;
        border-radius: 6px;
        padding: 10px 14px;
        margin-bottom: 8px;
        font-family: monospace;
        font-size: 0.85rem;
    }
    .edge-row { font-family: monospace; font-size: 0.82rem; color: #aaa; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Session-state initialisation
# ---------------------------------------------------------------------------


def _init_state() -> None:
    """
    Initialize Streamlit session state with default values.
    """
    defaults = {
        "db_path": _DEFAULT_DB,
        "lancedb_dir": _DEFAULT_LANCEDB,
        "store": None,
        "store_loaded_path": None,
        "query_result": None,
        "graph_nodes": None,
        "graph_edges": None,
        "selected_node_id": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


# ---------------------------------------------------------------------------
# Store helpers
# ---------------------------------------------------------------------------


@st.cache_resource(show_spinner="Opening SQLite store…")
def _load_store(db_path: str) -> GraphStore | None:
    """
    Load and cache a GraphStore from the given SQLite database path.

    :param db_path: Filesystem path to the SQLite database file.
    :return: A connected ``GraphStore`` instance, or ``None`` if the file is absent.
    """
    p = Path(db_path)
    if not p.exists():
        return None
    return GraphStore(db_path)


def _get_store() -> GraphStore | None:
    """Retrieve the current GraphStore, loading it if the database path has changed."""
    current_path = st.session_state.get("db_path")
    loaded_path = st.session_state.get("store_loaded_path")

    if current_path != loaded_path:
        st.session_state["store"] = _load_store(current_path)
        st.session_state["store_loaded_path"] = current_path

    return st.session_state.get("store")


# ---------------------------------------------------------------------------
# UI: Legend
# ---------------------------------------------------------------------------


def _render_legend() -> None:
    """Display a legend of node kinds and edge relations."""
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Node Kinds:**")
        for kind, color in _KIND_COLOR.items():
            st.markdown(
                f'<span style="color:{color}">●</span> {kind.capitalize()}',
                unsafe_allow_html=True,
            )

    with col2:
        st.markdown("**Edge Relations:**")
        for rel, color in _REL_COLOR.items():
            st.markdown(
                f'<span style="color:{color}">→</span> {rel}',
                unsafe_allow_html=True,
            )


# ---------------------------------------------------------------------------
# Pyvis graph rendering
# ---------------------------------------------------------------------------


def _build_pyvis(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    height: str = "750px",
    physics_on: bool = False,
) -> str:
    """
    Build an interactive pyvis graph from nodes and edges.

    :param nodes: List of node dicts.
    :param edges: List of edge dicts.
    :param height: Height of the graph widget.
    :param physics_on: Whether to enable physics simulation.
    :return: HTML string for embedding in Streamlit.
    """
    net = Network(directed=True, height=height)

    for node in nodes:
        node_id = node["id"]
        kind = node.get("kind", "")
        label = node.get("name", node_id)
        color = _KIND_COLOR.get(kind, "#95A5A6")
        shape = _KIND_SHAPE.get(kind, "dot")
        net.add_node(node_id, label=label, color=color, shape=shape, title=label)

    for edge in edges:
        src = edge["src"]
        dst = edge["dst"]
        rel = edge["rel"]
        color = _REL_COLOR.get(rel, "#95A5A6")
        net.add_edge(src, dst, label=rel, color=color)

    net.toggle_physics(physics_on)
    net.show(f"temp_{id(net)}.html")
    with open(f"temp_{id(net)}.html") as f:
        return f.read()


# ---------------------------------------------------------------------------
# UI: Sidebar configuration
# ---------------------------------------------------------------------------


def _render_sidebar() -> dict[str, Any]:
    """
    Render sidebar controls and return a configuration dict.

    :return: Dict with keys: ``db_path``, ``lancedb_dir``, ``max_nodes``,
             ``physics_on``, ``node_kinds_filter``, ``edge_rels_filter``.
    """
    st.sidebar.markdown("## Configuration")

    db_path = st.sidebar.text_input(
        "SQLite Database Path",
        value=st.session_state.get("db_path", _DEFAULT_DB),
        help="Path to the MetaKG SQLite database",
    )
    st.session_state["db_path"] = db_path

    lancedb_dir = st.sidebar.text_input(
        "LanceDB Directory",
        value=st.session_state.get("lancedb_dir", _DEFAULT_LANCEDB),
        help="Path to the LanceDB vector database directory",
    )
    st.session_state["lancedb_dir"] = lancedb_dir

    max_nodes = st.sidebar.number_input(
        "Max nodes to display",
        min_value=10,
        max_value=1000,
        value=200,
        step=10,
    )

    physics_on = st.sidebar.checkbox(
        "Enable physics simulation",
        value=False,
        help="Slow down the graph but may provide better layout",
    )

    st.sidebar.markdown("---")
    st.sidebar.markdown("## Filters")

    node_kinds_filter = st.sidebar.multiselect(
        "Filter by node kind",
        options=list(_KIND_COLOR.keys()),
        default=list(_KIND_COLOR.keys()),
    )

    edge_rels_filter = st.sidebar.multiselect(
        "Filter by edge relation",
        options=list(_REL_COLOR.keys()),
        default=list(_REL_COLOR.keys()),
    )

    return {
        "db_path": db_path,
        "lancedb_dir": lancedb_dir,
        "max_nodes": max_nodes,
        "physics_on": physics_on,
        "node_kinds_filter": node_kinds_filter,
        "edge_rels_filter": edge_rels_filter,
    }


# ---------------------------------------------------------------------------
# Tab: Graph Browser
# ---------------------------------------------------------------------------


def _tab_graph(cfg: dict[str, Any]) -> None:
    """Render the Graph Browser tab."""
    st.subheader("🗺️ Graph Browser")

    store = _get_store()
    if store is None:
        st.error(
            f"❌ Database not found at `{cfg['db_path']}`\n\n"
            "Please run `metakg-build` to create the database first."
        )
        return

    # Load full graph
    try:
        all_nodes = store.query_nodes()
        all_edges = store.query_edges()
    except Exception as e:
        st.error(f"Error loading graph: {e}")
        return

    # Filter by kind and relation
    filtered_nodes = [
        n for n in all_nodes if n.get("kind") in cfg["node_kinds_filter"]
    ]
    filtered_edges = [
        e for e in all_edges
        if e.get("rel") in cfg["edge_rels_filter"]
        and e.get("src") in {n["id"] for n in filtered_nodes}
        and e.get("dst") in {n["id"] for n in filtered_nodes}
    ]

    # Limit nodes
    if len(filtered_nodes) > cfg["max_nodes"]:
        filtered_nodes = filtered_nodes[: cfg["max_nodes"]]
        node_ids = {n["id"] for n in filtered_nodes}
        filtered_edges = [
            e for e in filtered_edges
            if e.get("src") in node_ids and e.get("dst") in node_ids
        ]

    st.caption(
        f"Showing {len(filtered_nodes)} nodes and {len(filtered_edges)} edges"
    )

    _render_legend()
    html = _build_pyvis(filtered_nodes, filtered_edges, physics_on=cfg["physics_on"])
    st.components.v1.html(html, height=750, scrolling=False)

    # Node list
    with st.expander(f"📋 Nodes ({len(filtered_nodes)})", expanded=False):
        import pandas as pd

        ndf = pd.DataFrame(
            [
                {
                    "ID": n["id"],
                    "Kind": n.get("kind", ""),
                    "Name": n.get("name", ""),
                    "Description": (n.get("description", "") or "")[:80],
                }
                for n in filtered_nodes
            ]
        )
        st.dataframe(ndf, use_container_width=True, hide_index=True)

    # Edges list
    with st.expander(f"🔗 Edges ({len(filtered_edges)})", expanded=False):
        import pandas as pd

        edf = pd.DataFrame(
            [
                {"Source": e["src"], "Relation": e["rel"], "Target": e["dst"]}
                for e in sorted(filtered_edges, key=lambda x: (x["rel"], x["src"]))
            ]
        )
        st.dataframe(edf, use_container_width=True, hide_index=True)


# ---------------------------------------------------------------------------
# Tab: Semantic Search
# ---------------------------------------------------------------------------


def _tab_search(cfg: dict[str, Any]) -> None:
    """Render the Semantic Search tab."""
    st.subheader("🔍 Semantic Search")

    store = _get_store()
    if store is None:
        st.error(f"❌ Database not found at `{cfg['db_path']}`")
        return

    query_text = st.text_area(
        "Enter a query",
        placeholder="e.g., 'glucose metabolism' or 'ATP synthase'",
        height=80,
    )

    if query_text:
        k = st.slider("Number of results", min_value=1, max_value=50, value=10)

        try:
            results = store.query_semantic(query_text, k=k)
            st.success(f"Found {len(results)} results")

            for i, result in enumerate(results, 1):
                node_id = result.get("id")
                kind = result.get("kind", "")
                name = result.get("name", "")
                description = result.get("description", "")
                color = _KIND_COLOR.get(kind, "#95A5A6")

                st.markdown(
                    f'<div class="node-card" style="border-left-color:{color}">'
                    f'<b>{i}. {name}</b> <code style="color:{color}">{kind}</code><br>'
                    f'<small>{node_id}</small><br>'
                    f'<small>{description[:200]}</small>'
                    f"</div>",
                    unsafe_allow_html=True,
                )
        except Exception as e:
            st.error(f"Query failed: {e}")


# ---------------------------------------------------------------------------
# Tab: Node Details
# ---------------------------------------------------------------------------


def _tab_details(cfg: dict[str, Any]) -> None:
    """Render the Node Details tab."""
    st.subheader("📋 Node Details")

    store = _get_store()
    if store is None:
        st.error(f"❌ Database not found at `{cfg['db_path']}`")
        return

    node_id = st.text_input(
        "Enter node ID", placeholder="e.g., cpd:kegg:C00022"
    )

    if node_id:
        try:
            node = store.get_node(node_id)
            if node is None:
                st.warning(f"Node `{node_id}` not found")
                return

            kind = node.get("kind", "")
            color = _KIND_COLOR.get(kind, "#95A5A6")

            st.markdown(
                f'<div style="border-left:4px solid {color};padding-left:10px;">'
                f'<code style="color:{color};font-size:1.2em">{kind}</code> '
                f'<b style="font-size:1.2em">{node.get("name", node_id)}</b><br>'
                f'<small><code>{node_id}</code></small>'
                f"</div>",
                unsafe_allow_html=True,
            )

            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**Basic Info**")
                st.write(f"**Name:** {node.get('name', 'N/A')}")
                st.write(f"**Kind:** {kind}")
                st.write(f"**Description:** {node.get('description', 'N/A')}")

            with col2:
                st.markdown("**Additional Data**")
                if kind == "compound":
                    st.write(f"**Formula:** {node.get('formula', 'N/A')}")
                    st.write(f"**Charge:** {node.get('charge', 'N/A')}")
                elif kind == "enzyme":
                    st.write(f"**EC Number:** {node.get('ec_number', 'N/A')}")

            # Xrefs
            xrefs = node.get("xrefs")
            if xrefs:
                try:
                    xrefs_dict = json.loads(xrefs) if isinstance(xrefs, str) else xrefs
                    st.markdown("**Cross-references**")
                    for db, ext_id in xrefs_dict.items():
                        st.write(f"  {db}: `{ext_id}`")
                except (json.JSONDecodeError, TypeError):
                    pass

            # Edges
            st.markdown("---")
            try:
                incoming_edges = store.query_edges(dst=node_id)
                outgoing_edges = store.query_edges(src=node_id)

                if incoming_edges or outgoing_edges:
                    col1, col2 = st.columns(2)
                    with col1:
                        if outgoing_edges:
                            st.markdown(f"**Outgoing ({len(outgoing_edges)})**")
                            for e in outgoing_edges:
                                dst_name = store.get_node(e["dst"]).get(
                                    "name", e["dst"]
                                ) if store.get_node(e["dst"]) else e["dst"]
                                color = _REL_COLOR.get(e["rel"], "#95A5A6")
                                st.markdown(
                                    f'<span style="color:{color}">→</span> '
                                    f'<b>{e["rel"]}</b> {dst_name}',
                                    unsafe_allow_html=True,
                                )

                    with col2:
                        if incoming_edges:
                            st.markdown(f"**Incoming ({len(incoming_edges)})**")
                            for e in incoming_edges:
                                src_name = store.get_node(e["src"]).get(
                                    "name", e["src"]
                                ) if store.get_node(e["src"]) else e["src"]
                                color = _REL_COLOR.get(e["rel"], "#95A5A6")
                                st.markdown(
                                    f'<span style="color:{color}">←</span> '
                                    f'{src_name} <b>{e["rel"]}</b>',
                                    unsafe_allow_html=True,
                                )
            except Exception as e:
                st.warning(f"Could not load edges: {e}")

        except Exception as e:
            st.error(f"Error loading node: {e}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    """
    Application entry point for the MetaKG Streamlit visualizer.

    Initialises session state, renders the sidebar, and dispatches to the
    three tab renderers: Graph Browser, Semantic Search, and Node Details.
    """
    _init_state()
    cfg = _render_sidebar()

    st.title("🧬 MetaKG Explorer")
    st.caption(
        "Interactive metabolic knowledge-graph explorer. "
        "Built with [MetaKG](https://github.com/Suchanek/meta_kg) · "
        "Powered by Streamlit + pyvis."
    )

    tab1, tab2, tab3 = st.tabs(
        [
            "🗺️ Graph Browser",
            "🔍 Semantic Search",
            "📋 Node Details",
        ]
    )

    with tab1:
        _tab_graph(cfg)

    with tab2:
        _tab_search(cfg)

    with tab3:
        _tab_details(cfg)


if __name__ == "__main__":
    main()
