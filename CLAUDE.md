# MetaKG CLI Commands Reference

**Repository:** https://github.com/Flux-Frontiers/meta_kg | **Sister:** https://github.com/Flux-Frontiers/code_kg

## CodeKG Tools (Available in Claude Code)

| Tool | Purpose |
|------|---------|
| `query_codebase(q, k=8, hop=1)` | Semantic code search |
| `pack_snippets(q, k=8, hop=1)` | Source-grounded code snippets |
| `get_node(node_id)` | Fetch node by ID (fmt: `fn:module:qualname`) |
| `callers(node_id)` | Find all callers of a function |
| `graph_stats()` | Codebase metrics |
| `/codekg-rebuild` | Rebuild after code changes |

**Workflow:** Query → read snippets → inspect node → find callers

---

## Quick Setup

```bash
poetry install --all-extras  # Full install with viz, viz3d, mcp
```

---

## MetaKG Commands

| Command | Purpose |
|---------|---------|
| `metakg-build --data DIR [--wipe]` | Parse pathways → SQLite + LanceDB |
| `metakg-analyze [--output FILE]` | 7-phase pathway analysis |
| `metakg-viz [--port 8500]` | 2D Streamlit explorer |
| `metakg-viz3d [--layout allium\|cake]` | 3D PyVista visualization |
| `metakg-mcp` | MCP server for Claude |

**Common options:**
- `--db PATH`: SQLite db (default: `.metakg/meta.sqlite`)
- `--lancedb PATH`: Vector index (default: `.metakg/lancedb`)
- `--wipe`: Clear before building
- `--no-index`: Skip LanceDB (SQLite only)

**MCP tools:** `query_pathway`, `get_compound`, `get_reaction`, `find_path`, `seed_kinetics`, `simulate_fba`, `simulate_ode`, `simulate_whatif`

### 3D Visualization (`metakg-viz3d`)

```bash
metakg-viz3d [--layout allium|cake] [--db PATH] [--width W] [--height H]
```

**Layout modes:**
- `allium` (default): Hub-spoke layout with pathways at center, reactions radially distributed
- `cake`: Concentric rings by topological distance (layer-based)

**In the UI:**
- **Pathway Filter**: Select single pathway or "(All Pathways)"
- **Layout Selector**: Switch between Allium and LayerCake (recomputes positions)
- **Visibility Toggles**: Show/hide edges, isolated nodes, labels
- **Render Graph**: Apply staged changes (filters + toggles) to the visualization

**Workflow:**
1. Start with `--layout cake` for metabolic flow visualization
2. Select a pathway (e.g., Glycolysis)
3. Adjust visibility toggles
4. Click "Render Graph" to render
5. Switch layouts dynamically from the sidebar

---

## Simulations

**ODE Default:** `ode_method="BDF"` (implicit, stiff-optimized for metabolic systems)
- Use BDF/Radau for stiff systems
- **RK45 will hang on metabolic pathways** (avoid!)

**ODE params:** `ode_rtol=1e-3`, `ode_atol=1e-5`, `ode_max_step=None`

```python
from metakg import MetaKG
kg = MetaKG()

# FBA (steady-state)
kg.simulate_fba("pwy:kegg:hsa00010", maximize=True)

# ODE (time-course)
kg.simulate_ode("pwy:kegg:hsa00010", t_end=20, t_points=50,
                initial_concentrations={"cpd:kegg:C00031": 5.0})

# What-if (perturbation)
scenario = {"enzyme_knockouts": ["enz:kegg:hsa:2539"]}
kg.simulate_whatif("pwy:kegg:hsa00010", json.dumps(scenario), mode="fba")

# Load kinetics from literature
kg.seed_kinetics()
```

---

## CodeKG Commands

| Command | Purpose |
|---------|---------|
| `codekg-build-sqlite --repo DIR [--wipe]` | Structural analysis → SQLite |
| `codekg-build-lancedb --repo DIR [--wipe]` | Embeddings → LanceDB |
| `codekg-query --q QUERY [--k 8]` | Semantic code search |
| `codekg-mcp --repo DIR` | MCP server |

**Query strategy:**
- `k=8, hop=1`: standard exploration
- `k=12, hop=2`: broad context
- `k=8, hop=2, rels=CALLS,IMPORTS`: deep dependencies

**When to rebuild:** Function/class rename/delete → `--wipe`. Minor edits → incremental.

---

## Data Download Scripts

| Script | Purpose | Output |
|--------|---------|--------|
| `scripts/download_human_kegg.py` | Download all hsa KGML pathway files | `data/hsa_pathways/*.kgml` |
| `scripts/download_kegg_names.py` | Bulk-download compound + reaction name lists | `data/kegg_compound_names.tsv`, `data/kegg_reaction_names.tsv` |
| `scripts/download_kegg_reactions.py` | Per-reaction detail: name, definition, equation, EC numbers | `data/kegg_reaction_detail.tsv` |

**Reaction detail download (EC numbers):**
```bash
# From local KGML files (faster, no extra network call for ID list):
python scripts/download_kegg_reactions.py --kgml-dir data/hsa_pathways

# From KEGG link endpoint (~2000 reactions across all hsa pathways):
python scripts/download_kegg_reactions.py

# Options: --force (re-download), --dry-run (list IDs only), --delay SECS
```

Output format (`data/kegg_reaction_detail.tsv`):
```
reaction_id  name                              definition        equation           ec_numbers
R00710       acetaldehyde:NAD+ oxidoreductase  Acetaldehyde ...  C00084 + C00003 …  1.2.1.3; 1.2.1.4
```

---

## Typical Workflow

```bash
# 1. Download pathway KGML files
python scripts/download_human_kegg.py --output data/hsa_pathways

# 2. (Optional) Download enrichment name files for compound & reaction names
python scripts/download_kegg_names.py         # compound + reaction bulk names
python scripts/download_kegg_reactions.py \   # per-reaction detail with EC numbers
  --kgml-dir data/hsa_pathways

# 3. Build & analyze pathways
poetry run metakg-build --data ./data/hsa_pathways --wipe

# 4. (Optional) Enrich DB with reaction names & EC numbers
poetry run metakg enrich --db .metakg/meta.sqlite

# 5. Analyze
poetry run metakg-analyze

# Explore (choose your view)
poetry run metakg-viz           # 2D Streamlit explorer
poetry run metakg-viz3d --layout allium    # 3D visualization (allium or cake)
poetry run metakg-mcp           # MCP server for Claude

# Optional: analyze codebase
poetry run codekg-build-sqlite --repo . --wipe
poetry run codekg-build-lancedb --repo . --wipe
poetry run codekg-query --q "orchestrator pipeline"
```

---

## Key Notes

- **Paths:** Relative to CWD
- **Embedding model:** ~100MB, downloaded once
- **ODE solvers:** Metabolic systems are stiff → use BDF (not RK45)
- **CodeKG node ID:** `fn:src/path/file.py:Class.method`
- **Rebuild:** Use `--wipe` after major refactors to avoid stale data
