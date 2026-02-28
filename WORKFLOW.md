# MetaKG Workflow

End-to-end guide from raw pathway data to running simulations and serving an MCP agent.

---

## Overview

```
KEGG REST API
     │
     ▼
collect_pathway_data.py        ← optional; pathways/ already committed
     │  downloads hsa*.xml
     ▼
pathways/*.xml  (KGML)
     │
     ▼
wire_enzymes.py                ← one-time; already applied to committed files
     │  injects enzyme="N" into <reaction> elements
     ▼
pathways/*.xml  (patched)
     │
     ▼
metakg-build --data pathways/  ← run once (or --wipe to rebuild)
     │  KGMLParser → MetaNode/MetaEdge
     ├──► .metakg/meta.sqlite   (SQLite knowledge graph)
     └──► .metakg/lancedb/      (vector index for semantic search)
     │
     ▼
metakg-simulate seed           ← run once after build
     │  kinetics_fetch.py → kinetic_parameters + regulatory_interactions
     ▼
.metakg/meta.sqlite  (complete)
     │
     ├── metakg-analyze         → Markdown pathway analysis report
     ├── metakg-simulate fba    → flux distribution
     ├── metakg-simulate ode    → concentration time-courses
     ├── metakg-simulate whatif → perturbation analysis
     ├── metakg-mcp             → MCP server (for Claude)
     └── metakg-viz / viz3d     → interactive visualisers
```

---

## Phase 1 — Get Pathway Data

The 11 KGML files in `pathways/` are **already committed** to the repo.
Skip this phase unless you want to expand the dataset or refresh from KEGG.

```bash
# See all 30 curated pathways without downloading
python scripts/collect_pathway_data.py --list

# Download all 30 pathways (1 s polite delay between KEGG API calls)
python scripts/collect_pathway_data.py --out pathways/

# Download only one metabolic category
python scripts/collect_pathway_data.py --category energy
python scripts/collect_pathway_data.py --category lipid
python scripts/collect_pathway_data.py --category amino_acid

# Force re-download even if files already exist
python scripts/collect_pathway_data.py --force
```

**Available categories:** `energy`, `lipid`, `amino_acid`, `nucleotide`, `cofactor`, `carbohydrate`

After downloading fresh KGML files, re-run the enzyme wiring step:

```bash
# Inject enzyme="N" attributes so the parser can emit CATALYZES edges
python scripts/wire_enzymes.py
```

`wire_enzymes.py` is a one-time data-preparation tool.  It adds a MetaKG
extension attribute (`enzyme="N"`) to each `<reaction>` element, linking it
to the catalysing gene entry by KGML integer ID.  The patch has already been
applied to all files currently in `pathways/` — only re-run it when ingesting
newly downloaded or refreshed KGML files.

---

## Phase 2 — Build Both Databases

```bash
# First build (creates .metakg/ automatically)
metakg-build --data pathways/

# Rebuild from scratch (drops existing data)
metakg-build --data pathways/ --wipe

# Build without the LanceDB vector index (faster, no semantic search)
metakg-build --data pathways/ --no-index

# Custom paths or embedding model
metakg-build --data pathways/ \
             --db .metakg/meta.sqlite \
             --lancedb .metakg/lancedb \
             --model all-MiniLM-L6-v2
```

Both the SQLite graph and LanceDB vector index are built by default.
The build prints a stat block on completion:

```
nodes: 342 (compound: 198, reaction: 87, enzyme: 41, pathway: 16)
edges: 891 (SUBSTRATE_OF: 234, PRODUCT_OF: 234, CATALYZES: 87, CONTAINS: 336)
xref_index: 621 rows
lancedb: 255 rows indexed (dim=384)
parse_errors: 0
```

---

## Phase 3 — Seed Kinetic Parameters

```bash
# Populate from curated literature values (safe to run multiple times)
metakg-simulate seed

# Overwrite existing rows (use after updating kinetics_fetch.py)
metakg-simulate seed --force
```

This populates two tables in the SQLite database:

| Table | Content |
|-------|---------|
| `kinetic_parameters` | Km, kcat, Vmax, Ki, ΔG°', Keq for 26 key reactions |
| `regulatory_interactions` | 13 allosteric rules (PFK, PK, HK, CS, IDH, G6PD) |

Run once after every `metakg-build --wipe`.

---

## Phase 4 — Analyse and Simulate

### Structural pathway analysis

```bash
# Print Markdown report to stdout
metakg-analyze

# Write to file
metakg-analyze --output analysis.md

# Plain text, top 30 items per section
metakg-analyze --output analysis.txt --plain --top 30
```

Covers: graph statistics, hub metabolites, complex reactions,
cross-pathway hubs, pathway coupling, dead-end metabolites, top enzymes.

---

### Flux Balance Analysis (FBA)

```bash
# Maximise total forward flux across a pathway
metakg-simulate fba --pathway hsa00010

# Optimise a specific reaction (e.g. pyruvate kinase)
metakg-simulate fba --pathway hsa00010 \
    --objective rxn:kegg:R00196 \
    --output fba_glycolysis.md

# Minimise instead of maximise
metakg-simulate fba --pathway hsa00020 --minimize

# All pathways in the graph (no --pathway filter)
metakg-simulate fba --output fba_all.md
```

---

### ODE Kinetic Simulation

```bash
# Default: 100 time units, 500 points, 1 mM initial concentration for all compounds
metakg-simulate ode --pathway hsa00010

# Custom time range and initial conditions
metakg-simulate ode --pathway hsa00010 \
    --time 200 --points 1000 \
    --conc cpd:kegg:C00031:5.0 \
    --conc cpd:kegg:C00002:3.0 \
    --default-conc 0.5 \
    --output ode_glycolysis.md
```

Uses Michaelis-Menten kinetics (seeded Km/Vmax values, or defaults of
Km = 0.5 mM / Vmax = 1.0 mM/s when parameters are absent).

---

### What-If Perturbation Analysis

```bash
# Enzyme knockout via FBA
metakg-simulate whatif --pathway hsa00010 \
    --mode fba \
    --knockout enz:kegg:hsa:2538 \
    --name HK_knockout \
    --output whatif_hk.md

# Partial inhibition (50%) of two enzymes via ODE
metakg-simulate whatif --pathway hsa00010 \
    --mode ode \
    --factor enz:kegg:hsa:5211:0.5 \
    --factor enz:kegg:hsa:5213:0.5 \
    --name PFK_inhibition \
    --output whatif_pfk.md

# Substrate pulse with FBA
metakg-simulate whatif --pathway hsa00010 \
    --mode ode \
    --conc cpd:kegg:C00031:10.0 \
    --name glucose_pulse \
    --output whatif_glucose.md
```

Reports the delta flux (FBA) or delta final concentration (ODE)
for every affected reaction or compound, sorted by magnitude.

---

## Phase 5 — Serve via MCP (for Claude)

```bash
# stdio transport (Claude Desktop / Claude Code)
metakg-mcp

# SSE transport (HTTP, for custom integrations)
metakg-mcp --transport sse
```

Exposes 9 tools to the connected agent:

| Tool | Purpose |
|------|---------|
| `query_pathway` | Semantic search for pathways |
| `get_compound` | Compound detail + connected reactions |
| `get_reaction` | Full stoichiometry + enzymes |
| `find_path` | Shortest metabolic route between two compounds |
| `seed_kinetics` | Populate kinetic parameters from literature |
| `get_kinetic_params` | Retrieve Km/Vmax/regulatory data for a reaction |
| `simulate_fba` | Flux Balance Analysis |
| `simulate_ode` | ODE kinetic time-course |
| `simulate_whatif` | Perturbation analysis |

---

## Quick-Start (from scratch)

```bash
pip install metakg[simulate,mcp]

# pathways/ already in repo — skip collect/wire if using committed files
metakg-build --data pathways/ --wipe
metakg-simulate seed
metakg-analyze --output analysis.md
metakg-simulate fba --pathway hsa00010 --output fba.md
metakg-mcp
```
