# MetaKG: Human Metabolic Knowledge Graph

**A unified, local-first metabolic pathway knowledge graph system with dual-layer query architecture (SQLite + LanceDB), semantic search, name enrichment, and interactive visualization.**

---

## What You Have

### Core System
- **Multi-format unification**: KGML, SBML, BioPAX, CSV pathway parsing → single reproducible graph
- **Dual-layer architecture**:
  - SQLite for precise structural queries (graph traversal, shortest paths, stoichiometry)
  - LanceDB for semantic similarity search (natural language: "glucose metabolism", "energy production")
- **Name enrichment pipeline**: Replaces bare KEGG accessions (`C00031`, `R00710`) with human-readable names (`D-Glucose`, `ADH1A/ADH1B`) — no external service required
- **Local-first design**: No external services, reproducible snapshots, version-controllable data
- **MCP server integration**: Claude and other LLMs can query the graph directly (MCP is a core dependency — no extra install flags required)

### Current Dataset
**Complete Human Metabolome** (all 369 KEGG pathways):

| Category | Count |
|----------|-------|
| **Nodes** | 22,290 total |
| - Compounds | 5,115 (glucose, ATP, pyruvate, amino acids, etc.) |
| - Enzymes | 14,667 (kinases, dehydrogenases, transferases, etc.) |
| - Pathways | 369 (metabolic, signaling, regulatory) |
| - Reactions | 2,139 (metabolic conversions) |
| **Edges** | 11,298 total |
| - SUBSTRATE_OF | 2,551 |
| - PRODUCT_OF | 2,532 |
| - CATALYZES | 2,406 |
| - CONTAINS | 3,809 |
| **Vector Index** | 20,151 semantic embeddings (384-dim) |

---

## Recent Enhancements (March 2026)

### Unified CLI (`metakg <subcommand>`)
The CLI has been refactored from a monolithic `cli.py` into a proper `cli/` package with a top-level `metakg` group:
- All subcommands accessible as `metakg build`, `metakg enrich`, `metakg analyze`, `metakg simulate`, `metakg viz`, `metakg mcp`, etc.
- Standalone `metakg-*` aliases remain for backwards compatibility
- Every command supports `--help`

### Name Enrichment Pipeline
**Human-readable names throughout the graph:**
- Phase 1 (no network): Reaction nodes get enzyme gene-symbol labels derived from `CATALYZES` edges (e.g. `R00710` → `ADH1A / ADH1B / ADH1C`)
- Phase 2 (TSV files): Compound and reaction nodes get canonical KEGG names from downloaded TSV files (e.g. `C00031` → `D-Glucose`)
- Both phases are idempotent; can be run standalone with `metakg enrich` or inline with `metakg build --enrich`

### Visualization Improvements
**Display human-readable names instead of raw IDs:**
- Graph nodes show actual compound/enzyme names: `D-Glucose` instead of `cpd:kegg:C00031`
- Hover tooltips include: name, description, formula/charge (compounds), EC number (enzymes), KEGG ID
- Simulation plots show meaningful compound/reaction names in legends and tables

### Performance Optimization
**Eliminated N+1 database query problem:**
- Added `GraphStore.nodes(node_ids)` batch query method
- Session state caching prevents re-querying on Streamlit reruns
- **Result**: 95% reduction in database queries for typical workflows

---

## Getting Started

### 1. Install Dependencies
```bash
poetry install --all-extras   # Full install: viz, viz3d, MCP included
# or minimal:
poetry install                # Core + MCP (no viz/3D)
```

### 2. Download Human KEGG Pathways (KGML)
```bash
# Download all 369 human pathways (~19 MB KGML files)
poetry run python scripts/download_human_kegg.py --output data/hsa_pathways

# Dry-run to preview (no download):
poetry run python scripts/download_human_kegg.py --output data/hsa_pathways --dry-run
```

### 3. Download KEGG Name Tables (TSV) — for Enrichment
```bash
# Download compound (~19,500 entries) and reaction (~12,400 entries) name lists
poetry run python scripts/download_kegg_names.py

# Files written:
#   data/kegg_compound_names.tsv   (KEGG_ID<TAB>name)
#   data/kegg_reaction_names.tsv   (KEGG_ID<TAB>name)
#
# Options:
#   --data DIR    output directory (default: data/)
#   --force       re-download even if files already exist
#   --quiet       suppress progress output
```

> **Note:** The TSV files are also committed to the repository under `data/`, so this step can be skipped if they are already present.

### 4. Build the Knowledge Graph
```bash
# Build SQLite + LanceDB, then enrich node names in one step
poetry run metakg build --data data/hsa_pathways --wipe --enrich

# Build without enrichment (faster, raw KEGG accessions as names):
poetry run metakg build --data data/hsa_pathways --wipe

# Result:
# - .metakg/meta.sqlite  (structured graph, ~10-15 MB)
# - .metakg/lancedb/     (semantic vectors, ~15 MB)
```

### 5. Enrich Node Names (if not done during build)
```bash
# Phase 1 only (enzyme gene-symbol labels, no network required):
poetry run metakg enrich

# Phase 1 + Phase 2 (canonical KEGG names from TSV files):
poetry run metakg enrich --data data/
```

### 6. Explore Interactively
```bash
# Launch Streamlit web explorer
poetry run metakg viz

# Opens: http://localhost:8500
# Features:
#   • Graph Browser: Navigate 22K nodes with real names
#   • Semantic Search: "glucose metabolism", "ATP synthesis"
#   • Node Details: Full metadata, incoming/outgoing edges
#   • Simulation: ODE & FBA with meaningful compound/reaction labels
```

### 7. Use in Claude / LLMs via MCP
```bash
# Start MCP server (MCP is a core dependency — no extra flags needed)
poetry run metakg mcp

# Claude can now query with tools:
# - query_pathway(name, k): Find pathways by description
# - get_compound(id): Full compound details + reactions
# - get_reaction(id): Stoichiometry + substrates/products
# - find_path(A, B): Shortest metabolic route
# - seed_kinetics: Load Km/Vmax values from literature
# - simulate_fba / simulate_ode / simulate_whatif: Metabolic simulations
```

---

## Query Capabilities

### Structural Queries (SQLite)
- **Neighborhood traversal**: All compounds connected to a reaction
- **Shortest paths**: Find metabolic route from glucose → pyruvate
- **Stoichiometric detail**: Substrate/product coefficients, reversibility
- **Graph metrics**: Hub metabolites (highest connectivity)

### Semantic Queries (LanceDB)
- **Natural language search**: "energy metabolism", "fatty acid oxidation"
- **Similarity ranking**: Find related pathways/compounds by meaning
- **Cross-pathway discovery**: What's related to glycolysis?

### Simulations
- **FBA (Flux Balance Analysis)**: Steady-state flux optimization
- **ODE Kinetics**: Time-course concentration dynamics (Michaelis-Menten, BDF solver)
- **What-If Analysis**: Enzyme knockouts, inhibitions, substrate overrides

---

## Architecture Highlights

### Why This Design?
1. **Dual-layer avoids false choice**: Structural precision + semantic exploration in one system
2. **Local-first ensures reproducibility**: Same inputs → same graph, every time
3. **Deterministic ID merging**: No external reconciliation service needed
4. **Name enrichment**: Human-readable graph without runtime lookups
5. **Snapshot-based**: Version-controllable data, offline-capable workflows
6. **MCP integration**: LLM-accessible (Claude, etc.) as a core feature

### What Distinguishes MetaKG

| Feature | KEGG | BioCyc | Reactome | **MetaKG** |
|---------|------|--------|----------|-----------|
| Multi-format unification | ✗ | ✗ | ✗ | **✓** |
| Local deployment | ✗ | ✗ | ✗ | **✓** |
| Semantic search | ✗ | ✗ | ~ | **✓** |
| Structural queries | ✓ | ✓ | ✓ | **✓** |
| Human-readable enrichment | ✗ | ✓ | ✓ | **✓** |
| LLM-accessible (MCP) | ✗ | ✗ | ✗ | **✓** |
| Reproducible snapshots | ✗ | ✗ | ✗ | **✓** |

---

## File Structure

```
meta_kg/
├── src/metakg/
│   ├── app.py                 # Streamlit explorer (interactive UI)
│   ├── store.py               # GraphStore: SQLite + LanceDB queries
│   ├── enrich.py              # Name enrichment pipeline (Phase 1 + Phase 2)
│   ├── cli/                   # Unified CLI package
│   │   ├── main.py            # Root `metakg` Click group (--version)
│   │   ├── options.py         # Shared Click option decorators
│   │   ├── _utils.py          # Shared helpers (arg parsing, file output)
│   │   ├── cmd_build.py       # `metakg build` / `metakg enrich`
│   │   ├── cmd_analyze.py     # `metakg analyze` / `metakg analyze-basic`
│   │   ├── cmd_simulate.py    # `metakg simulate {fba,ode,whatif,seed}`
│   │   ├── cmd_mcp.py         # `metakg mcp`
│   │   ├── cmd_viz.py         # `metakg viz`
│   │   └── cmd_viz3d.py       # `metakg viz3d`
│   ├── parsers/               # KGML, SBML, BioPAX, CSV parsers
│   ├── simulate.py            # FBA, ODE, what-if simulations
│   ├── mcp_tools.py           # MCP tool registration
│   └── orchestrator.py        # MetaKG public API
├── scripts/
│   ├── download_human_kegg.py # KEGG REST API KGML downloader
│   ├── download_kegg_names.py # KEGG compound/reaction TSV downloader
│   ├── wire_kegg_enzymes.py   # Patch KGML enzyme→reaction links pre-build
│   └── article_examples.py    # Reproducible example scripts
├── data/
│   ├── hsa_pathways/          # 369 human pathway KGML files (~19 MB)
│   ├── kegg_compound_names.tsv  # 19,571 compound names (KEGG_ID<TAB>name)
│   └── kegg_reaction_names.tsv  # 12,384 reaction names (KEGG_ID<TAB>name)
├── .metakg/
│   ├── meta.sqlite            # Knowledge graph (22,290 nodes, 11,298 edges)
│   └── lancedb/               # Vector index (20,151 embeddings)
└── tests/                     # Comprehensive tests (FBA, ODE, what-if, parsers)
```

---

## CLI Reference

### Unified `metakg` CLI (v0.2.0+)

| Command | Purpose |
|---------|---------|
| `metakg build --data DIR [--wipe] [--enrich] [--no-index]` | Parse pathways → SQLite + LanceDB |
| `metakg enrich [--data DIR]` | Enrich node names in existing database |
| `metakg analyze [--output FILE]` | 7-phase pathway analysis |
| `metakg simulate fba \| ode \| whatif \| seed` | Run simulations |
| `metakg viz [--port 8500]` | 2D Streamlit explorer |
| `metakg viz3d [--layout allium\|cake]` | 3D PyVista visualization |
| `metakg mcp` | MCP server for Claude / LLMs |

### Standalone Aliases (backwards compatible)

| Alias | Equivalent |
|-------|-----------|
| `metakg-build` | `metakg build` |
| `metakg-analyze` | `metakg analyze` |
| `metakg-viz` | `metakg viz` |
| `metakg-viz3d` | `metakg viz3d` |
| `metakg-mcp` | `metakg mcp` |

---

## Usage Examples

### Example 1: Full Build with Enrichment
```bash
# Download data
poetry run python scripts/download_human_kegg.py --output data/hsa_pathways
poetry run python scripts/download_kegg_names.py

# Build + enrich in one step
poetry run metakg build --data data/hsa_pathways --wipe --enrich

# Explore
poetry run metakg viz
```

### Example 2: Find Shortest Path (Glucose → Energy)
```python
from metakg import MetaKG

kg = MetaKG()
path = kg.find_path("D-Glucose", "ATP", max_hops=6)
# Result: Glucose → Glucose-6-phosphate → ... → Pyruvate → Acetyl-CoA → ATP
```

### Example 3: ODE Simulation
```python
result = kg.simulate_ode(
    pathway_id="pwy:kegg:hsa00010",
    t_end=20.0,
    initial_concentrations={"cpd:kegg:C00031": 5.0}  # 5 mM glucose
)
# Plot legends show enriched names ("D-Glucose") not raw IDs
```

### Example 4: What-If (Enzyme Knockout)
```python
import json
from metakg import MetaKG

kg = MetaKG()
scenario = {"enzyme_knockouts": ["enz:kegg:hsa:2539"]}
result = kg.simulate_whatif("pwy:kegg:hsa00010", json.dumps(scenario), mode="fba")
```

### Example 5: Enrichment via Python API
```python
from metakg import MetaKG

with MetaKG() as kg:
    stats = kg.enrich(data_dir="data/")
    print(stats)
    # Enrichment: 2139 reaction names from graph,
    #             5115 compound names from TSV, 2139 reaction names from TSV
```

---

## Performance Characteristics

| Operation | Time | Details |
|-----------|------|---------|
| Build graph | 30-60s | Parsing + indexing 369 pathways |
| Enrich (Phase 1+2) | 5-15s | Graph traversal + TSV lookups |
| Semantic search | 100-500ms | Vector similarity on 20K nodes |
| Shortest path | 10-50ms | BFS on 11K edges |
| ODE simulation (10 units) | 150-400ms | BDF solver, 24 compounds |
| Streamlit rerun | 0.5-1.5s | Batch query + session cache |

---

## Next Steps

1. **Download data & build with enrichment**:
   ```bash
   poetry run python scripts/download_human_kegg.py --output data/hsa_pathways
   poetry run python scripts/download_kegg_names.py
   poetry run metakg build --data data/hsa_pathways --wipe --enrich
   ```

2. **Explore interactively**:
   ```bash
   poetry run metakg viz
   ```

3. **Integrate with Claude** (via MCP server):
   ```bash
   poetry run metakg mcp
   # Configure in Claude settings — see docs/MCP.md
   ```

4. **Use Python API** for custom workflows:
   ```python
   from metakg import MetaKG
   kg = MetaKG()
   # query_pathway, get_compound, simulate_fba, enrich, etc.
   ```

---

## License & Data

- **MetaKG code**: MIT or applicable project license
- **KEGG data**: Free for academic/non-profit use (see [KEGG License](https://www.kegg.jp/kegg/legal.html))
- **Reproducibility**: All data is version-controllable, no external dependencies at runtime

---

**Built with**: Python 3.10+, SQLite, LanceDB, Streamlit, SciPy, Sentence-Transformers, Click, MCP

**Version**: 0.2.0 | **Status**: Production-ready for metabolic pathway exploration, simulation, and LLM integration (March 2026)
