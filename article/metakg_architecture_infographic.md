# MetaKG — Architecture & Data Flow

> A local-first metabolic knowledge graph with dual-layer query architecture.
> 369 KEGG pathways · 22,290 nodes · 11,298 edges · 20,151 embeddings

---

## The Problem

Existing tools force a false choice:

| Structural databases | Vector databases |
|---|---|
| Exact graph queries | Natural-language search |
| No semantic search | No graph structure |
| Web-only, no API | Discards stoichiometry |

**MetaKG eliminates this choice.**

---

## Data Flow Pipeline

```
INPUT: Pathway files
┌─────────────────────────────────┐
│  KGML · SBML · BioPAX · CSV    │
└──────────────┬──────────────────┘
               │
               v
┌─────────────────────────────────┐
│         MetabolicGraph          │
│  Format detection + dispatch    │
│  Stateless, deterministic parse │
└──────────────┬──────────────────┘
               │
               v
┌─────────────────────────────────┐
│     MetaNode / MetaEdge         │
│  Merged by stable ID            │
│  cpd:kegg:C00022  ·  rxn:...   │
└────────┬──────────────┬─────────┘
         │              │
         v              v
┌─────────────┐  ┌──────────────┐
│  MetaStore  │  │  MetaIndex   │
│   SQLite    │  │   LanceDB    │
│  Structure  │  │  Semantics   │
└─────────────┘  └──────────────┘
         │              │
         └──────┬───────┘
                v
┌─────────────────────────────────┐
│     Unified Query Interface     │
│   Python API · CLI · MCP        │
└─────────────────────────────────┘
```

---

## Dual-Layer Storage

### Layer 1 — SQLite (Structural)

- Stores the property graph: compounds, reactions, enzymes, pathways
- Three tables: `meta_nodes`, `meta_edges`, `xref_index`
- Queries via SQL joins — fast, ACID, no server
- Use for: graph traversal, stoichiometry, shortest paths

### Layer 2 — LanceDB (Semantic)

- 384-dimensional embeddings via `all-MiniLM-L6-v2`
- Approximate nearest-neighbour search over node descriptions
- Use for: natural-language queries, synonym resolution, exploratory search
- ~100 MB model, downloaded once, runs offline

---

## Four Query Modalities

```
1. SEMANTIC SEARCH
   "fatty acid beta-oxidation"
   → vector similarity over 20K embeddings
   → ranked pathway results in 100–500 ms

2. NEIGHBOURHOOD TRAVERSAL
   get_compound("cpd:kegg:C00022")
   → all connected reactions via SQL JOIN
   → results in 10–50 ms

3. SHORTEST PATH
   find_path("D-Glucose", "Pyruvate", max_hops=12)
   → BFS over compound–reaction bipartite graph
   → 9-step glycolytic route in 10–50 ms

4. STOICHIOMETRIC DETAIL
   get_reaction("rxn:kegg:R00200")
   → substrates · products · enzymes · inhibitors
   → multi-table JOIN with JSON decode in <10 ms
```

---

## Three Simulation Modalities

```
FBA (Flux Balance Analysis)
  Steady-state optimisation
  → flux distribution over all reactions

ODE Integration
  Michaelis-Menten kinetics · BDF solver (stiff)
  → time-course concentrations for all compounds
  → 150–400 ms for a 24-compound pathway

What-If Perturbation
  Enzyme knockouts · inhibition · substrate overrides
  → baseline vs. perturbed comparison
  → FBA or ODE mode
```

---

## Stable Identifier Scheme

Every node gets a deterministic, URI-style ID:

```
cpd:kegg:C00022    →  Pyruvate
rxn:kegg:R00200    →  Pyruvate decarboxylation
enz:ec:1.2.4.1     →  Pyruvate dehydrogenase
pwy:kegg:hsa00010  →  Glycolysis / Gluconeogenesis
cpd:syn:a4f2b8c1   →  Unnamed compound (SHA-1 hash)
```

Same input → same IDs → reproducible, version-controllable graphs.

---

## Graph Schema

**Node kinds:** `compound` · `reaction` · `enzyme` · `pathway`

**Edge types:**

```
SUBSTRATE_OF   compound  →  reaction
PRODUCT_OF     reaction  →  compound
CATALYZES      enzyme    →  reaction
INHIBITS       compound  →  reaction
ACTIVATES      compound  →  reaction
CONTAINS       pathway   →  reaction
XREF           any       →  any
```

---

## Access Interfaces

| Interface | Use case |
|---|---|
| Python API | Scripting, ML pipelines, programmatic analysis |
| CLI (`metakg-build`, `metakg-analyze`, `metakg-viz`) | Interactive exploration, batch workflows |
| MCP server (`metakg-mcp`) | AI assistants (Claude, ChatGPT, etc.) |
| Streamlit 2D browser | Interactive graph + semantic search in browser |
| PyVista 3D viewer | Publication figures, 3D pathway layouts |

---

## Performance at Scale (22K nodes · 11K edges)

| Operation | Time |
|---|---|
| Build full graph (369 pathways) | 30–60 s |
| Semantic search | 100–500 ms |
| Shortest-path query | 10–50 ms |
| ODE simulation | 150–400 ms |
| Stoichiometric detail lookup | < 10 ms |

*Measured on 2024 MacBook Pro, Apple M3 Max, 36 GB RAM.*

---

## Design Principles

1. **Dual-layer query** — structural precision AND semantic expressivity, not a choice between them
2. **Deterministic merging** — same inputs always produce the same graph; no external reconciliation service
3. **Local-first** — no database server, no cloud, no network after setup; runs on a laptop

---

## Quick Start

```bash
git clone https://github.com/Flux-Frontiers/meta_kg
cd meta_kg
poetry install --extras all

# Build the knowledge graph
metakg-build --data ./data/hsa_pathways --wipe

# Query via Python
python -c "
from metakg import MetaKG
kg = MetaKG()
results = kg.query_pathway('fatty acid beta-oxidation', k=5)
for h in results.hits: print(h['name'], h['_distance'])
"

# Start MCP server for AI assistants
metakg-mcp --db .metakg/meta.sqlite --transport stdio
```
