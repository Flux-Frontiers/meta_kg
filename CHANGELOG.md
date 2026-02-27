# Changelog

All notable changes to MetaKG are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Interactive Web Visualization** — Streamlit-based metabolic knowledge graph explorer
  - Graph Browser tab for visualizing pathways, reactions, compounds, and enzymes
  - Semantic Search tab for querying nodes by description and keywords
  - Node Details tab for exploring comprehensive node information
  - Pyvis-based interactive graph rendering with filtering and legend controls

- **3D Metabolic Pathway Visualization** — PyVista-powered 3D interactive visualizer
  - Allium layout strategy: each pathway rendered as a "Giant Allium plant" with reactions/compounds as the spherical head
  - LayerCake layout strategy: vertical stratification by node kind with golden-angle spiral distribution
  - Interactive 3D rendering with color coding by metabolic entity type
  - Export to HTML and PNG formats

- **Layout Algorithms** (`src/metakg/layout3d.py`)
  - Fibonacci spatial utilities for uniform point distribution on spheres and annuli
  - AlliumLayout class for plant-inspired botanical visualization
  - LayerCakeLayout class for stratified hierarchical visualization
  - Extensible Layout3D abstract base class for custom layout implementations

- **CLI Commands**
  - `metakg-viz` — Launch Streamlit web explorer with database and port configuration
  - `metakg-viz3d` — Launch 3D PyVista visualizer with layout and export options

- **GraphStore Wrapper** (`src/metakg/store.py`)
  - Convenience compatibility layer wrapping MetaStore with visualization-friendly methods
  - `query_nodes()` — Query nodes with optional kind filtering
  - `query_edges()` — Query edges with optional source/destination filtering
  - `query_semantic()` — Text-based semantic search (extensible for embeddings)
  - `get_node()` — Fetch individual nodes by ID

- **Dependencies**
  - Optional visualization extras: `viz` (Streamlit + pyvis), `viz3d` (PyVista + PyQt5)
  - Updated pyproject.toml with streamlit, pyvis, pyvista, pyvistaqt, PyQt5, and param dependencies

- **Documentation**
  - Comprehensive README.md with quick start, architecture, commands, and API examples
  - Detailed feature descriptions and usage patterns
  - Performance characteristics and installation variants

### Changed

- **pyproject.toml** — Added optional visualization dependencies and `viz` + `viz3d` extras
- **src/metakg/cli.py** — Added `viz_main()` and `viz3d_main()` entry points for new CLI commands
- **src/metakg/store.py** — Extended with GraphStore compatibility wrapper class

### Technical Details

- **Visualization Scope** — Adapted from flux-frontiers/code_kg with metabolic pathway domain-specific customizations
- **Node Types** — Supports compound, reaction, enzyme, and pathway nodes
- **Edge Relations** — SUBSTRATE_OF, PRODUCT_OF, CATALYZES, INHIBITS, ACTIVATES, CONTAINS, XREF
- **Embedding Model** — Integrates with sentence-transformers via LanceDB for semantic search
- **Database** — SQLite persistence with indexed queries for graph operations

## [0.1.0] — 2024-02-27

### Added

- Initial standalone MetaKG package release
- Metabolic pathway parser supporting KGML, SBML, BioPAX, and CSV formats
- Semantic knowledge graph with LanceDB vector indexing
- MCP (Model Context Protocol) server integration
- Core CLI: `metakg-build` and `metakg-mcp` commands
- SQLite-based graph persistence layer
- Cross-reference resolution and pathway unification

---

[Unreleased]: https://github.com/Suchanek/meta_kg/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Suchanek/meta_kg/releases/tag/v0.1.0
