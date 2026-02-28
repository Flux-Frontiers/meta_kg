> **Analysis Report Metadata**  
> - **Generated:** 2026-02-28T01:35:10Z  
> - **Version:** code-kg 0.3.2  
> - **Commit:** 897841a (main)  

# CodeKG Repository Analysis Report

**Generated:** 2026-02-28 01:35:10 UTC

---

## 📊 Executive Summary

This report provides a comprehensive architectural analysis of the Python repository using CodeKG's knowledge graph. The analysis covers complexity hotspots, module coupling, critical call chains, and code quality signals to guide refactoring and architecture decisions.

---

## 📈 Baseline Metrics

| Metric | Value |
|--------|-------|
| **Total Nodes** | 3136 |
| **Total Edges** | 2920 |
| **Modules** | 4 |
| **Functions** | 65 |
| **Classes** | 43 |
| **Methods** | 155 |

### Edge Distribution

| Relationship Type | Count |
|-------------------|-------|
| CALLS | 946 |
| CONTAINS | 263 |
| IMPORTS | 221 |
| ATTR_ACCESS | 875 |
| INHERITS | 10 |

---

## 🔥 Complexity Hotspots (High Fan-In)

Most-called functions are potential bottlenecks or core functionality. These functions are heavily depended upon across the codebase.

| # | Function | Module | Callers | Risk Level |
|---|----------|--------|---------|-----------|
| 1 | `stats()` | src/metakg/orchestrator.py | **4** | 🟢 LOW |
| 2 | `can_handle()` | src/metakg/parsers/kgml.py | **4** | 🟢 LOW |
| 3 | `can_handle()` | src/metakg/parsers/sbml.py | **4** | 🟢 LOW |
| 4 | `_risk()` | src/metakg/analyze.py | **1** | 🟢 LOW |
| 5 | `_analyze_args()` | src/metakg/cli.py | **1** | 🟢 LOW |
| 6 | `_mcp_args()` | src/metakg/cli.py | **1** | 🟢 LOW |
| 7 | `register_tools()` | src/metakg/mcp_tools.py | **1** | 🟢 LOW |
| 8 | `_phase2_hub_metabolites()` | src/metakg/analyze.py | **1** | 🟢 LOW |
| 9 | `analyze_main()` | src/metakg/cli.py | **0** | 🟢 LOW |
| 10 | `mcp_main()` | src/metakg/cli.py | **0** | 🟢 LOW |
| 11 | `__enter__()` | src/metakg/orchestrator.py | **0** | 🟢 LOW |
| 12 | `__repr__()` | src/metakg/orchestrator.py | **0** | 🟢 LOW |
| 13 | `__str__()` | src/metakg/orchestrator.py | **0** | 🟢 LOW |
| 14 | `supported_extensions()` | src/metakg/parsers/kgml.py | **0** | 🟢 LOW |
| 15 | `supported_extensions()` | src/metakg/parsers/sbml.py | **0** | 🟢 LOW |


**Insight:** Functions with high fan-in are either core APIs or bottlenecks. Review these for:
- Thread safety and performance
- Clear documentation and contracts
- Potential for breaking changes

---

## 🔗 High Fan-Out Functions (Orchestrators)

Functions that call many others may indicate complex orchestration logic or poor separation of concerns.

✓ No extreme high fan-out functions detected. Well-balanced architecture.

---

## 📦 Module Architecture

Top modules by dependency coupling and cohesion.

| Module | Functions | Classes | Incoming | Outgoing | Cohesion |
|--------|-----------|---------|----------|----------|----------|
| `src/metakg/parsers/base.py` | 0 | 0 | 0 | 4 | 0.83 |
| `tests/__init__.py` | 0 | 0 | 0 | 3 | 0.90 |
| `tests/test_parsers.py` | 0 | 0 | 0 | 1 | 0.67 |
| `tests/test_primitives.py` | 0 | 0 | 0 | 2 | 0.67 |

---

## 🔗 Critical Call Chains

Deepest call chains in the codebase. These represent critical execution paths.

**Chain 1** (depth: 4)

```
stats → test_stats_after_write → test_wipe_clears_data → build
```

**Chain 2** (depth: 4)

```
can_handle → test_can_handle_kgml_extension → test_cannot_handle_non_pathway_xml → test_cannot_handle_non_sbml_xml
```

**Chain 3** (depth: 4)

```
can_handle → test_can_handle_kgml_extension → test_cannot_handle_non_pathway_xml → test_cannot_handle_non_sbml_xml
```

**Chain 4** (depth: 2)

```
_risk → render_report
```

**Chain 5** (depth: 2)

```
_analyze_args → analyze_main
```

---

## 🔓 Public API Surface

Identified public APIs (module-level functions with high usage).

No public APIs identified.



---

## ⚠️  Code Quality Issues

- ⚠️  9 orphaned functions found — consider archiving or documenting

---

## ✅ Architectural Strengths

- ✓ Well-structured with 15 core functions identified
- ✓ No god objects or god functions detected

---

## 💡 Recommendations

### Immediate Actions
1. **Review high fan-in functions** - Ensure they are documented and thread-safe
2. **Examine orchestrators** - Break down high fan-out functions into smaller components
3. **Verify public APIs** - Ensure stable contracts and clear documentation

### Medium-term Refactoring
1. **Module restructuring** - Consider reshaping modules with high coupling
2. **Dead code cleanup** - Archive or document orphaned functions
3. **Test coverage** - Add tests for critical call chains

### Long-term Architecture
1. **Layer enforcement** - Prevent unexpected module dependencies
2. **API versioning** - Manage evolution of public APIs
3. **Performance monitoring** - Track hot paths identified in this analysis

---

## 📋 Appendix: Orphaned Code

Functions with zero callers (potential dead code):

| Function | Module | Lines |
|----------|--------|-------|
| `supported_extensions()` | src/metakg/parsers/base.py | 7 |
| `__repr__()` | src/metakg/orchestrator.py | 5 |
| `test_can_handle_kgml_extension()` | tests/test_parsers.py | 4 |
| `test_cannot_handle_non_pathway_xml()` | tests/test_parsers.py | 4 |
| `test_xrefs_dict_empty_when_not_set()` | tests/test_primitives.py | 2 |
| `__exit__()` | src/metakg/orchestrator.py | 1 |
| `supported_extensions()` | src/metakg/parsers/biopax.py | 1 |
| `supported_extensions()` | src/metakg/parsers/kgml.py | 1 |
| `supported_extensions()` | src/metakg/parsers/sbml.py | 1 |


---

*Report generated by CodeKG Thorough Analysis Tool*
