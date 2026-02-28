# Changelog

All notable changes to MetaKG are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Public Statistics API** — New `MetabolicRuntimeStats` dataclass and `MetaKG.get_stats()` method for clean, type-safe access to knowledge graph statistics
  - Encapsulates total nodes/edges, node counts by kind, edge counts by relation
  - Includes optional vector index statistics (indexed rows and embedding dimension)
  - Provides `__str__()` for nicely formatted output and `to_dict()` for serialization
  - Eliminates internal `.store` exposure in public API
  - Exported in `metakg` module for public use

- **Comprehensive Unit Tests for Orchestrator** — 14 new tests for `MetabolicRuntimeStats` and `MetaKG.get_stats()`
  - Tests basic construction, serialization, and string representation
  - Tests stats accuracy with real data (node/edge counts)
  - Tests edge cases (empty database, multiple calls consistency)
  - Tests API cleanliness (no internal implementation exposure)

- **Simulation Demo Script** — `scripts/simulation_demo.py` demonstrating metabolic pathway simulations
  - Example 1: Seeding kinetic parameters from literature (BRENDA/SABIO-RK)
  - Example 2: Flux Balance Analysis (FBA) for steady-state flux prediction
  - Example 3: FBA with custom objective reaction
  - Example 4: Kinetic ODE simulation for time-course dynamics
  - Example 5: Enzyme knockout perturbation analysis
  - Example 6: Enzyme partial inhibition (50%) perturbation analysis

### Changed

- **Article Examples API Cleanup** — Updated `scripts/article_examples.py` to use public `kg.get_stats()` instead of internal `kg.store.stats()`
  - Uses typed `MetabolicRuntimeStats` object with attribute access instead of dict access
  - Gracefully handles optional index statistics with `.get()` calls
  - Demonstrates proper API usage patterns for users

- **License Migration to Elastic License 2.0** — Updated from PolyForm Noncommercial to Elastic License 2.0 to align with sister project CodeKG
  - Updated `pyproject.toml` license field to `Elastic-2.0`
  - Added `LICENSE` file with complete Elastic License 2.0 terms
  - Updated README license badge with link to official license page

### Fixed

- **Critical Namespace Shadowing Bug** — `src/metakg/metakg.py` was shadowing the metakg package namespace, preventing imports of submodules like `graph.py` and breaking all CLI commands. Resolved by renaming to `orchestrator.py` and updating all import statements.

### Added

- **Consistent Project Badges** — Enhanced README with project status badges matching CodeKG style
  - Python version badge showing supported versions (3.10, 3.11, 3.12)
  - Version badge (0.1.0) with link to releases
  - Poetry dependency manager badge
  - Updated license badge for Elastic License 2.0

- **CodeKG Sister Project Reference** — Added prominent reference to CodeKG in README
  - Sister Project section highlighting CodeKG's role in enabling semantic analysis of MetaKG's own codebase
  - Added CodeKG to Acknowledgments section as primary enabling technology

- **Architecture Diagram in README** — Integrated visual architecture diagram (`docs/metaKG_arch.png`) into the Architecture section
  - Provides quick visual overview of system components and organization
  - Complements detailed file structure documentation

- **CodeKG Integration for Codebase Analysis** — MetaKG can now be analyzed using CodeKG's knowledge graph tools
  - Built static analysis graph (SQLite): 3,136 nodes, 2,920 edges across 27 modules
  - Built semantic vector index (LanceDB): 290 vectors with 384-dimensional embeddings
  - Configured MCP servers for Claude Code, GitHub Copilot, Kilo Code, and Cline
  - Enables tools like `query_codebase`, `pack_snippets`, `callers` for code exploration

- **Comprehensive CLI Documentation** — Added `CLAUDE.md` with complete reference for both MetaKG and CodeKG commands
  - MetaKG commands: `metakg-build`, `metakg-analyze`, `metakg-viz`, `metakg-viz3d`, `metakg-mcp`
  - CodeKG commands: `codekg-build-sqlite`, `codekg-build-lancedb`, `codekg-query`, `codekg-mcp`
  - MCP tool documentation with usage examples and query strategies
  - Typical workflows and combined MetaKG + CodeKG usage patterns
  - All examples include `poetry run` activation for virtual environment

- **MCP Server Configuration** — Added MCP server definitions for multiple clients
  - `.mcp.json` for Claude Code and Kilo Code
  - `.vscode/mcp.json` for GitHub Copilot integration

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

- **Orchestrator Class** — Renamed `MetaKG` source file from `metakg.py` to `orchestrator.py` for clarity and to eliminate namespace shadowing
- **Import Paths** — Updated all references from `metakg.metakg` to `metakg.orchestrator` in `__init__.py`, `mcp_tools.py`, and `app.py`
- **pyproject.toml** — Added optional visualization dependencies and `viz` + `viz3d` extras, plus CodeKG CLI entry points
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

[Unreleased]: https://github.com/flux-frontiers/meta_kg/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/flux-frontiers/meta_kg/releases/tag/v0.1.0
