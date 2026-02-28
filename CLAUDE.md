# MetaKG CLI Commands Reference

**Repository:** https://github.com/Flux-Frontiers/meta_kg

**Sister Project:** https://github.com/Flux-Frontiers/code_kg (CodeKG)

This document describes all CLI commands available in the MetaKG project. Use this as a quick reference when working on the project.

MetaKG is a metabolic pathway parser and semantic knowledge graph system. It's a cousin to CodeKG, which provides similar knowledge graph capabilities for codebases.

## Prerequisites

Before using any CLI commands, ensure the project dependencies are installed:

```bash
poetry install --extras viz viz3d
# or for everything:
poetry install --all-extras
```

The main build and analyze commands only require base dependencies. The `viz` and `viz3d` extras are optional for visualization tools.

---

## Core Commands

### `metakg-build` — Build the Knowledge Graph

**Purpose:** Parse pathway files and build the MetaKG knowledge graph (SQLite + LanceDB).

**Usage:**
```bash
metakg-build --data DIRECTORY [OPTIONS]
```

**Required Arguments:**
- `--data DIRECTORY`: Directory containing pathway files (KGML, SBML, BioPAX, CSV)

**Optional Arguments:**
- `--db PATH`: Output SQLite database path (default: `.metakg/meta.sqlite`)
- `--lancedb PATH`: Output LanceDB directory (default: `.metakg/lancedb`)
- `--model NAME`: Sentence-transformer model name (default: `sentence-transformers/all-MiniLM-L6-v2`)
- `--no-index`: Skip building the LanceDB vector index (faster if you only need SQLite)
- `--wipe`: Clear existing data before building (useful for rebuilding from scratch)

**Example:**
```bash
poetry run metakg-build --data ./pathways --wipe
poetry run metakg-build --data ./pathways --no-index  # SQLite only, skip embeddings
```

**Output:**
Prints build statistics including:
- Total nodes/edges created
- Node counts by kind (compound, enzyme, pathway, reaction)
- Edge counts by relation type
- Parse errors (if any)

---

### `metakg-analyze` — Pathway Analysis Report

**Purpose:** Run a comprehensive metabolic pathway analysis and generate a detailed report.

**Usage:**
```bash
metakg-analyze [OPTIONS]
```

**Optional Arguments:**
- `--db PATH`: SQLite database path (default: `.metakg/meta.sqlite`)
- `--output FILE`, `-o FILE`: Write report to FILE (default: print to stdout)
- `--top N`: Number of items in each ranked list (default: 20)
- `--plain`: Plain-text output instead of Markdown

**Example:**
```bash
poetry run metakg-analyze  # Print report to terminal
poetry run metakg-analyze --output analysis.md  # Save as Markdown
poetry run metakg-analyze --top 50 --output report.md  # 50 items per ranking
poetry run metakg-analyze --plain --output report.txt  # Plain text
```

**Output:**
7-phase analysis report including:
1. Graph statistics (nodes, edges, pathway profiles)
2. Hub metabolites (highest connectivity)
3. Complex reactions (highest stoichiometric complexity)
4. Cross-pathway hub metabolites
5. Pathway coupling (co-occurrence patterns)
6. Topological patterns (dead-ends, isolated nodes)
7. Top enzymes by reaction coverage

---

## Visualization Commands

### `metakg-viz` — 2D Streamlit Explorer

**Purpose:** Launch an interactive Streamlit web app for exploring the knowledge graph.

**Usage:**
```bash
metakg-viz [OPTIONS]
```

**Optional Arguments:**
- `--db PATH`: SQLite database path (default: `.metakg/meta.sqlite`)
- `--lancedb PATH`: LanceDB directory (default: `.metakg/lancedb`)
- `--port PORT`: Streamlit server port (default: `8500`)
- `--no-browser`: Don't open a browser window automatically

**Example:**
```bash
poetry run metakg-viz  # Opens http://localhost:8500 in browser
poetry run metakg-viz --port 9000  # Custom port
poetry run metakg-viz --no-browser  # Headless mode
```

**Requirements:** `poetry install --extras viz`

---

### `metakg-viz3d` — 3D PyVista Visualizer

**Purpose:** Launch an interactive 3D PyVista visualization of the knowledge graph.

**Usage:**
```bash
metakg-viz3d [OPTIONS]
```

**Optional Arguments:**
- `--db PATH`: SQLite database path (default: `.metakg/meta.sqlite`)
- `--lancedb PATH`: LanceDB directory (default: `.metakg/lancedb`)
- `--layout {allium|cake}`: 3D layout strategy (default: `allium`)
  - `allium`: Each pathway rendered as a Giant Allium plant
  - `cake`: Nodes stratified by kind across Z layers
- `--width PIXELS`: Window width (default: `1400`)
- `--height PIXELS`: Window height (default: `900`)
- `--export-html PATH`: Export to HTML instead of opening interactive window

**Example:**
```bash
poetry run metakg-viz3d  # Opens interactive window (allium layout)
poetry run metakg-viz3d --layout cake  # Layer-cake layout
poetry run metakg-viz3d --export-html graph.html  # Export to HTML
poetry run metakg-viz3d --width 1920 --height 1080  # Custom window size
```

**Requirements:** `poetry install --extras viz3d`

---

## Server Commands

### `metakg-mcp` — MCP Server

**Purpose:** Start the MetaKG Model Context Protocol (MCP) server for Claude integration.

**Usage:**
```bash
metakg-mcp [OPTIONS]
```

**Optional Arguments:**
- `--db PATH`: SQLite database path (default: `.metakg/meta.sqlite`)
- `--lancedb PATH`: LanceDB directory (default: `.metakg/lancedb`)
- `--model NAME`: Sentence-transformer model name (default: `sentence-transformers/all-MiniLM-L6-v2`)
- `--transport {stdio|sse}`: MCP transport method (default: `stdio`)
  - `stdio`: Standard input/output (typical for local use)
  - `sse`: Server-sent events (for HTTP)

**Example:**
```bash
poetry run metakg-mcp  # Start server on stdio (for Claude)
poetry run metakg-mcp --transport sse --db .metakg/meta.sqlite  # HTTP transport
```

**Requirements:** `poetry install --extras mcp`

**Tools Exposed:**
- `query_pathway(name, k)`: Semantic pathway search
- `get_compound(id)`: Compound + connected reactions
- `get_reaction(id)`: Full stoichiometric detail
- `find_path(compound_a, compound_b, max_hops)`: Shortest metabolic path

---

## Typical Workflow

```bash
# 1. Build the knowledge graph from pathway files
poetry run metakg-build --data ./pathways --wipe

# 2. Analyze and examine the structure
poetry run metakg-analyze --output analysis.md

# 3. Explore interactively
poetry run metakg-viz  # Opens Streamlit explorer

# 4. (Optional) 3D visualization
poetry run metakg-viz3d --layout cake

# 5. Start MCP server for Claude integration
poetry run metakg-mcp
```

---

# CodeKG CLI Commands Reference

**Sister Project:** https://github.com/Flux-Frontiers/code_kg

CodeKG is a code knowledge graph system that analyzes Python repositories. It's installed in this project to provide codebase analysis capabilities.

## Core Commands

### `codekg-build-sqlite` — Build the Static Analysis Graph

**Purpose:** Parse Python files and build the CodeKG SQLite database (structural analysis).

**Usage:**
```bash
codekg-build-sqlite --repo DIRECTORY [OPTIONS]
```

**Required Arguments:**
- `--repo DIRECTORY`: Root directory of the Python repository to analyze

**Optional Arguments:**
- `--db PATH`: Output SQLite database path (default: `.codekg/graph.sqlite`)
- `--wipe`: Clear existing database before building (useful for rebuilding from scratch)

**Example:**
```bash
poetry run codekg-build-sqlite --repo .
poetry run codekg-build-sqlite --repo . --wipe  # Full rebuild
```

**Output:**
Prints statistics:
- Total nodes created (modules, classes, functions, methods)
- Total edges (CALLS, CONTAINS, IMPORTS, INHERITS, ATTR_ACCESS)
- Resolved references

---

### `codekg-build-lancedb` — Build the Semantic Vector Index

**Purpose:** Embed Python code elements and build the LanceDB semantic search index.

**Usage:**
```bash
codekg-build-lancedb --repo DIRECTORY [OPTIONS]
```

**Required Arguments:**
- `--repo DIRECTORY`: Root directory of the Python repository

**Optional Arguments:**
- `--sqlite PATH`: Path to SQLite database (default: `.codekg/graph.sqlite`)
- `--lancedb PATH`: Output LanceDB directory (default: `.codekg/lancedb`)
- `--model NAME`: Sentence-transformer model name (default: `sentence-transformers/all-MiniLM-L6-v2`)
- `--wipe`: Clear existing index before building

**Example:**
```bash
poetry run codekg-build-lancedb --repo .
poetry run codekg-build-lancedb --repo . --wipe  # Full rebuild
poetry run codekg-build-lancedb --repo . --model sentence-transformers/all-mpnet-base-v2
```

**Output:**
- Number of indexed vectors
- Embedding dimension (typically 384)
- Node kinds indexed (module, class, function, method)

---

### `codekg-query` — Semantic Code Search

**Purpose:** Query the knowledge graph using natural language or code patterns.

**Usage:**
```bash
codekg-query --q QUERY [OPTIONS]
```

**Required Arguments:**
- `--q QUERY`: Natural language query (e.g., "authentication flow", "database connection")

**Optional Arguments:**
- `--db PATH`: SQLite database path (default: `.codekg/graph.sqlite`)
- `--lancedb PATH`: LanceDB directory (default: `.codekg/lancedb`)
- `--k N`: Number of results to return (default: 8)
- `--hop N`: Graph expansion hops (default: 1)
- `--format {text|json}`: Output format (default: text)

**Example:**
```bash
poetry run codekg-query --q "authentication"
poetry run codekg-query --q "database connection" --k 20
poetry run codekg-query --q "error handling" --format json
```

**Output:**
Ranked list of relevant code nodes with:
- Node type (module, class, function, method)
- Qualified name and location
- Semantic similarity score

---

### `codekg-mcp` — CodeKG MCP Server

**Purpose:** Start the CodeKG Model Context Protocol server for Claude integration.

**Usage:**
```bash
codekg-mcp --repo DIRECTORY [OPTIONS]
```

**Required Arguments:**
- `--repo DIRECTORY`: Root directory of the Python repository to analyze

**Optional Arguments:**
- `--db PATH`: SQLite database path (default: `.codekg/graph.sqlite`)
- `--lancedb PATH`: LanceDB directory (default: `.codekg/lancedb`)
- `--model NAME`: Sentence-transformer model name
- `--transport {stdio|sse}`: MCP transport method (default: `stdio`)

**Example:**
```bash
poetry run codekg-mcp --repo .
poetry run codekg-mcp --repo . --transport sse
```

**Tools Exposed:**
- `graph_stats()`: Get codebase statistics (nodes, edges by type)
- `query_codebase(q, k, hop, rels)`: Semantic + structural exploration
- `pack_snippets(q, k, hop, rels)`: Source-grounded code snippets
- `get_node(node_id)`: Fetch single node metadata
- `callers(node_id)`: Find all callers of a function (cross-module resolution)

---

## MCP Tool Details

### `graph_stats()`
Returns codebase metrics:
```json
{
  "total_nodes": 3136,
  "total_edges": 2920,
  "node_counts": {"module": 27, "class": 43, "function": 65, "method": 155},
  "edge_counts": {"CALLS": 946, "CONTAINS": 263, "IMPORTS": 221, ...}
}
```

### `query_codebase(q, k=8, hop=1, rels="CONTAINS,CALLS,IMPORTS,INHERITS")`
Semantic + structural search. Returns nodes and edges:
- **q**: Natural language query or code pattern
- **k**: Number of semantic seed nodes
- **hop**: Graph expansion hops from each seed
- **rels**: Comma-separated edge types to follow

### `pack_snippets(q, k=8, hop=1, max_nodes=15, context=5)`
Returns source-grounded code snippets with line numbers:
- **q**: Natural language query
- **context**: Lines of context around each definition
- **max_lines**: Maximum lines per snippet
- Perfect for understanding implementation details

### `get_node(node_id)`
Fetch a single node by stable ID:
- ID format: `<kind>:<module_path>:<qualname>`
- Example: `fn:src/metakg/store.py:MetaStore.write`

### `callers(node_id, rel="CALLS")`
Find all callers of a function, resolving through import aliases:
- Performs reverse lookup of CALLS edges
- Handles cross-module sym: stubs (import aliases)
- Returns complete caller list with metadata

---

## Query Strategy

### Choosing `k` and `hop`

| Goal | Settings |
|------|----------|
| Narrow, precise lookup | `k=4, hop=0` |
| Standard exploration | `k=8, hop=1` (default) |
| Broad context sweep | `k=12, hop=2` |
| Deep dependency trace | `k=8, hop=2, rels="CALLS,IMPORTS"` |

### Typical Session Workflow

```python
# 1. Understand codebase
graph_stats()

# 2. Find relevant nodes
query_codebase("authentication flow", k=8, hop=1)

# 3. Read source code
pack_snippets("JWT validation", k=6, hop=1)

# 4. Get node details
get_node("fn:src/auth/jwt.py:JWTValidator.validate")

# 5. Find all callers
callers("fn:src/auth/jwt.py:JWTValidator.validate")

# 6. Deep dive into error handling
pack_snippets("error handling", k=4, hop=2, rels="CALLS")
```

---

## Rebuilding After Code Changes

The knowledge graph is a **snapshot at build time** — it doesn't auto-update.

### When to rebuild

| Change | Action |
|--------|--------|
| Added/renamed/deleted functions/classes | Full rebuild (`--wipe`) |
| Large refactor touching many files | Full rebuild (`--wipe`) |
| Minor edits within functions | Incremental rebuild (no `--wipe`) |
| New files added | Incremental rebuild |

### Full rebuild (recommended after significant changes)

```bash
poetry run codekg-build-sqlite  --repo . --wipe
poetry run codekg-build-lancedb --repo . --wipe
```

### Incremental rebuild

```bash
poetry run codekg-build-sqlite  --repo .
poetry run codekg-build-lancedb --repo .
```

---

## Combined Workflow: MetaKG + CodeKG

```bash
# Analyze the metabolic pathways
poetry run metakg-build --data ./pathways --wipe
poetry run metakg-analyze --output pathway_analysis.md

# Analyze the MetaKG codebase itself
poetry run codekg-build-sqlite --repo .
poetry run codekg-build-lancedb --repo .

# Explore MetaKG code with CodeKG
poetry run codekg-query --q "orchestrator pipeline"
poetry run codekg-query --q "parser dispatch"

# Start both MCP servers
poetry run metakg-mcp &  # Background: metabolic pathway queries
poetry run codekg-mcp --repo . &  # Background: codebase exploration
```

---

## Notes

### MetaKG
- **Database paths** are relative to the current working directory
- **Embedding model** is downloaded on first use; uses about 100MB disk space
- **LanceDB** is automatically created if the directory doesn't exist
- **Parse errors** are reported at the end of `metakg-build`; non-fatal files are skipped
- Use `--wipe` carefully; it deletes the entire database before rebuilding

### CodeKG
- **Node ID format**: `<kind>:<module_path>:<qualname>` (e.g., `fn:src/metakg/orchestrator.py:MetaKG.build`)
- **Kinds**: `mod` (module), `cls` (class), `fn` (function), `m` (method), `sym` (external symbol)
- **Relations**: `CALLS`, `CONTAINS`, `IMPORTS`, `INHERITS`, `ATTR_ACCESS`, `RESOLVES_TO`
- **Always use absolute paths** in MCP configs — relative paths won't resolve correctly
- **Stale data risk**: Run `--wipe` after major refactors to avoid phantom entries
