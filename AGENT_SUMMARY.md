# MetaKG Agent Handoff Summary
**Date:** 2026-03-03
**Branch:** develop (created from main)
**Full analysis:** `metakg-codekg-analysis-2026-03-03.md`

---

## Codebase at a Glance

- **5,127 nodes / 4,902 edges** in CodeKG graph
- **36 modules** · 54 classes · 134 functions · 198 methods
- **10 INHERITS edges** — strongly composition-based design

## Architecture (5 Layers, Clean)

```
cli.py / mcp_tools.py / app.py         ← Interfaces
orchestrator.py (MetaKG)                ← Thin orchestration
simulate.py / kinetics_fetch.py         ← Simulation & Kinetics
store.py (MetaStore) / index.py         ← Dual-layer storage
graph.py + parsers/ + primitives.py     ← Ingestion
```

**Entry point:** `MetaKG` class (`src/metakg/orchestrator.py:159`) — the single public API.
All CLI commands, MCP tools, and tests route through it (except one, see risks below).

## Key Files

| File | Lines | Purpose |
|------|-------|---------|
| `src/metakg/orchestrator.py` | 677 | MetaKG top-level API |
| `src/metakg/store.py` | ~888 | MetaStore (SQLite) + GraphStore (viz) |
| `src/metakg/simulate.py` | ~909 | FBA/ODE/what-if + result renderers |
| `src/metakg/mcp_tools.py` | ~462 | MCP server (register_tools 383L) |
| `src/metakg/cli.py` | 605 | 8 CLI entry points |
| `src/metakg/kinetics_fetch.py` | ~693 | Literature kinetics seeding |
| `src/metakg/app.py` | ~833 | Streamlit 2D viz |

## Active Bugs / Risks

### 1. `simulate_main` bypasses the orchestrator (MEDIUM)
**File:** `src/metakg/cli.py:491`
```python
# Current — wrong: directly instantiates MetaStore
store = MetaStore(args.db)
simulator = MetabolicSimulator(store)

# Fix: route through MetaKG like every other CLI command
with MetaKG(db_path=args.db) as kg:
    result = kg.simulate_fba(pathway_id=args.pathway)
```

### 2. `GraphStore.query_semantic` is a text-filter stub (LOW)
**File:** `src/metakg/store.py:861`
The Streamlit "Semantic Search" tab calls this, but it does substring matching, not vector search.
Fix: wire to `MetaIndex.search()`, or rename to `query_text`.

### 3. `register_tools` is a 383-line closure factory (MEDIUM)
**File:** `src/metakg/mcp_tools.py:49`
8 MCP tool handlers are nested closures — can't be unit-tested in isolation.
Fix: extract each handler to a module-level function taking `metakg` explicitly.

### 4. `scripts/wire_enzymes.py` appears redundant
Older version of `scripts/wire_kegg_enzymes.py`. Candidate for deletion.

## Design Strengths (Don't Break These)

- `PathwayParser` ABC — stateless, pure, deterministic; adding a new format = one new file
- `MetaKG` lazy properties (`.store`, `.index`, `.simulator`) — cheap construction
- BDF solver default in `simulate.py` — correct for stiff metabolic systems (RK45 hangs)
- `KineticParam` provenance fields (source, organism, confidence) — important for reproducibility
- Context manager on `MetaKG` — ensures SQLite connection cleanup

## Refactoring Opportunities

1. **Extract renderers from `simulate.py`** → new `render.py`
   Functions: `render_fba_result`, `render_ode_result`, `render_whatif_result`
   No behavior change — pure code organization.

2. **Document `MetaStore` sections** (686-line class)
   Add section comments or split into `NodeStore`, `EdgeStore`, `PathFinder`.
   Biggest comprehension bottleneck in the codebase.

3. **`simulate_main` → use `MetaKG`** (see bug #1 above)

## Test Suite State

97 tests total (last known passing state).
Key test files:
- `tests/test_simulation.py` — 21 tests (FBA, ODE, what-if, kinetics, regression guards)
- `tests/test_store.py` — store CRUD, xref, path-finding
- `tests/test_orchestrator.py` — MetaKG API
- `tests/test_parsers.py` — KGML/SBML parser tests

Regression guards:
- `test_ode_bdf_performance` — BDF completes in <2s (catches hang regression)
- `test_ode_no_hardcoded_max_step_hang` — `ode_max_step=None` doesn't hang

## CLI Commands

```bash
metakg-build --data DIR [--wipe]         # Parse → SQLite + LanceDB
metakg-analyze [--output FILE]           # 7-phase pathway analysis report
metakg-analyze-basic [--output FILE]     # Structured facts report
metakg-simulate --pathway ID [--mode fba|ode|whatif]
metakg-mcp                               # MCP server for Claude
metakg-viz [--port 8500]                 # Streamlit 2D explorer
metakg-viz3d [--layout allium|cake]      # PyVista 3D visualization
```

## ODE Solver (Important)

Default: **BDF** (implicit, stiff-optimized). Do NOT revert to RK45.
Config in `SimulationConfig`: `ode_method="BDF"`, `ode_rtol=1e-3`, `ode_atol=1e-5`, `ode_max_step=None`

---

*See `metakg-codekg-analysis-2026-03-03.md` for the full report with line-number references.*
