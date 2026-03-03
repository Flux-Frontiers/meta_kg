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

## Typical Workflow

```bash
# Build & analyze pathways
poetry run metakg-build --data ./pathways --wipe
poetry run metakg-analyze

# Explore
poetry run metakg-viz           # Web explorer
poetry run metakg-mcp           # MCP server

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
