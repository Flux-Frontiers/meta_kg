"""
metakg.py — MetaKG: top-level orchestrator for the metabolic knowledge graph.

Owns the full pipeline:
    data_dir → MetabolicGraph → MetaStore → MetaIndex → query results
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from metakg.graph import MetabolicGraph
from metakg.index import MetaIndex
from metakg.store import MetaStore
from metakg.simulate import MetabolicSimulator, SimulationConfig, WhatIfScenario
from metakg.kinetics_fetch import seed_kinetics as _seed_kinetics

# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass
class MetabolicBuildStats:
    """
    Statistics returned by :meth:`MetaKG.build`.

    :param data_root: Data directory that was parsed.
    :param db_path: Path to the SQLite database.
    :param total_nodes: Total nodes written to SQLite.
    :param total_edges: Total edges written to SQLite.
    :param node_counts: Node counts by kind.
    :param edge_counts: Edge counts by relation.
    :param xref_rows: Number of xref index entries built.
    :param indexed_rows: Number of nodes embedded into LanceDB.
    :param index_dim: Embedding dimension.
    :param parse_errors: List of files that failed to parse.
    """

    data_root: str
    db_path: str
    total_nodes: int
    total_edges: int
    node_counts: dict[str, int]
    edge_counts: dict[str, int]
    xref_rows: int = 0
    indexed_rows: int | None = None
    index_dim: int | None = None
    parse_errors: list[dict] | None = None

    def to_dict(self) -> dict:
        """Serialise to a plain dict."""
        return {
            "data_root": self.data_root,
            "db_path": self.db_path,
            "total_nodes": self.total_nodes,
            "total_edges": self.total_edges,
            "node_counts": self.node_counts,
            "edge_counts": self.edge_counts,
            "xref_rows": self.xref_rows,
            "indexed_rows": self.indexed_rows,
            "index_dim": self.index_dim,
            "parse_errors": self.parse_errors or [],
        }

    def __str__(self) -> str:
        lines = [
            f"data_root   : {self.data_root}",
            f"db_path     : {self.db_path}",
            f"nodes       : {self.total_nodes}  {self.node_counts}",
            f"edges       : {self.total_edges}  {self.edge_counts}",
            f"xref_rows   : {self.xref_rows}",
        ]
        if self.indexed_rows is not None:
            lines.append(f"indexed     : {self.indexed_rows} vectors  dim={self.index_dim}")
        if self.parse_errors:
            lines.append(f"parse_errors: {len(self.parse_errors)}")
        return "\n".join(lines)


@dataclass
class MetabolicRuntimeStats:
    """
    Statistics for the current state of the knowledge graph.

    :param total_nodes: Total nodes in the database.
    :param total_edges: Total edges in the database.
    :param node_counts: Node counts by kind.
    :param edge_counts: Edge counts by relation.
    :param indexed_rows: Number of nodes embedded in the vector index (if built).
    :param index_dim: Embedding dimension (if index exists).
    """

    total_nodes: int
    total_edges: int
    node_counts: dict[str, int]
    edge_counts: dict[str, int]
    indexed_rows: int | None = None
    index_dim: int | None = None

    def to_dict(self) -> dict:
        """Serialise to a plain dict."""
        return {
            "total_nodes": self.total_nodes,
            "total_edges": self.total_edges,
            "node_counts": self.node_counts,
            "edge_counts": self.edge_counts,
            "indexed_rows": self.indexed_rows,
            "index_dim": self.index_dim,
        }

    def __str__(self) -> str:
        node_str = ", ".join(f"{k}={v}" for k, v in sorted(self.node_counts.items()))
        edge_str = ", ".join(f"{k}={v}" for k, v in sorted(self.edge_counts.items()))
        lines = [
            f"nodes       : {self.total_nodes}  ({node_str})",
            f"edges       : {self.total_edges}  ({edge_str})",
        ]
        if self.indexed_rows is not None:
            lines.append(f"indexed     : {self.indexed_rows} vectors  dim={self.index_dim}")
        return "\n".join(lines)


@dataclass
class MetabolicQueryResult:
    """
    Result of a :meth:`MetaKG.query_pathway` search.

    :param query: Original query string.
    :param hits: Matching node dicts from LanceDB + SQLite.
    """

    query: str
    hits: list[dict]

    def to_json(self, *, indent: int = 2) -> str:
        """Serialise to JSON string."""
        return json.dumps({"query": self.query, "hits": self.hits}, indent=indent)


# ---------------------------------------------------------------------------
# MetaKG — orchestrator
# ---------------------------------------------------------------------------


class MetaKG:
    """
    Top-level orchestrator for the metabolic knowledge graph.

    Coordinates:

    * :class:`~metakg.graph.MetabolicGraph` — file parsing
    * :class:`~metakg.store.MetaStore` — SQLite persistence
    * :class:`~metakg.index.MetaIndex` — LanceDB vector index

    Typical usage::

        kg = MetaKG(db_path=".metakg/meta.sqlite")
        stats = kg.build(data_dir="./pathway_files", wipe=True)
        print(stats)

        result = kg.query_pathway("glycolysis")
        print(result.to_json())

        rxn = kg.get_reaction("rxn:kegg:R00200")
        print(rxn)

    :param db_path: Path to the SQLite database.
    :param lancedb_dir: Path to the LanceDB directory.
    :param model: Sentence-transformer model name for embeddings.
    :param table: LanceDB table name.
    """

    def __init__(
        self,
        db_path: str | Path | None = None,
        lancedb_dir: str | Path | None = None,
        *,
        model: str | None = None,
        table: str = "metakg_nodes",
    ) -> None:
        """
        Initialise MetaKG and resolve paths.

        :param db_path: SQLite database path.  Defaults to ``.metakg/meta.sqlite``.
        :param lancedb_dir: LanceDB directory.  Defaults to ``.metakg/lancedb``.
        :param model: Sentence-transformer model name.
        :param table: LanceDB table name.
        """
        from metakg.embed import DEFAULT_MODEL

        base = Path.cwd() / ".metakg"
        self.db_path = Path(db_path) if db_path else base / "meta.sqlite"
        self.lancedb_dir = Path(lancedb_dir) if lancedb_dir else base / "lancedb"
        self.model_name = model or DEFAULT_MODEL
        self.table_name = table

        self._store: MetaStore | None = None
        self._index: MetaIndex | None = None
        self._simulator: MetabolicSimulator | None = None

    # ------------------------------------------------------------------
    # Layer accessors (lazy)
    # ------------------------------------------------------------------

    @property
    def store(self) -> MetaStore:
        """SQLite persistence layer (lazy)."""
        if self._store is None:
            self._store = MetaStore(self.db_path)
        return self._store

    @property
    def index(self) -> MetaIndex:
        """LanceDB semantic index (lazy)."""
        if self._index is None:
            from metakg.embed import SentenceTransformerEmbedder
            embedder = SentenceTransformerEmbedder(self.model_name)
            self._index = MetaIndex(
                self.lancedb_dir,
                embedder=embedder,
                table=self.table_name,
            )
        return self._index

    @property
    def simulator(self) -> MetabolicSimulator:
        """Metabolic simulation engine (lazy)."""
        if self._simulator is None:
            self._simulator = MetabolicSimulator(self.store)
        return self._simulator

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def build(
        self,
        data_dir: str | Path | None = None,
        *,
        wipe: bool = False,
        build_index: bool = True,
    ) -> MetabolicBuildStats:
        """
        Full pipeline: parse → SQLite → LanceDB.

        :param data_dir: Directory of pathway files.  If omitted, only the
            SQLite → LanceDB step is run (useful for re-indexing existing data).
        :param wipe: Clear existing data before writing.
        :param build_index: Whether to build the LanceDB vector index.
        :return: :class:`MetabolicBuildStats`.
        """
        parse_errors: list[dict] = []

        if data_dir is not None:
            graph = MetabolicGraph(data_dir)
            graph.extract(force=wipe)
            nodes, edges = graph.result()
            parse_errors = graph.parse_errors
            self.store.write(nodes, edges, wipe=wipe)

        xref_rows = self.store.build_xref_index()
        s = self.store.stats()

        idx_rows: int | None = None
        idx_dim: int | None = None
        if build_index:
            idx_stats = self.index.build(self.store, wipe=wipe)
            idx_rows = idx_stats["indexed_rows"]
            idx_dim = idx_stats["dim"]

        return MetabolicBuildStats(
            data_root=str(data_dir) if data_dir else "",
            db_path=str(self.db_path),
            total_nodes=s["total_nodes"],
            total_edges=s["total_edges"],
            node_counts=s["node_counts"],
            edge_counts=s["edge_counts"],
            xref_rows=xref_rows,
            indexed_rows=idx_rows,
            index_dim=idx_dim,
            parse_errors=parse_errors,
        )

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def query_pathway(self, name: str, *, k: int = 8) -> MetabolicQueryResult:
        """
        Find metabolic pathways by name or description using semantic search.

        :param name: Pathway name or description (e.g. ``"glycolysis"``).
        :param k: Maximum results to return.
        :return: :class:`MetabolicQueryResult` with matching pathway nodes.
        """
        hits = self.index.search(name, k=k)
        results: list[dict] = []
        for h in hits:
            node = self.store.node(h.id)
            if node and node["kind"] == "pathway":
                cur = self.store._conn.execute(
                    "SELECT COUNT(*) FROM meta_edges WHERE src=? AND rel='CONTAINS'", (h.id,)
                )
                member_count = cur.fetchone()[0]
                results.append({**node, "_distance": h.distance, "member_count": member_count})
        return MetabolicQueryResult(query=name, hits=results)

    def get_compound(self, id: str) -> dict | None:
        """
        Retrieve a compound node by internal or external ID.

        Accepts ``cpd:kegg:C00022``, shorthand ``kegg:C00022``, or a plain name.

        :param id: Compound identifier.
        :return: Compound node dict with connected reactions, or ``None`` if not found.
        """
        nid = self.store.resolve_id(id)
        if not nid:
            return None
        node = self.store.node(nid)
        if not node:
            return None

        reactions: list[dict] = []
        for edge in self.store.edges_of(nid):
            if edge["rel"] in ("SUBSTRATE_OF", "PRODUCT_OF"):
                rxn_id = edge["dst"] if edge["rel"] == "SUBSTRATE_OF" else edge["src"]
                rxn = self.store.node(rxn_id)
                if rxn:
                    reactions.append({**rxn, "role": edge["rel"]})

        return {**node, "reactions": reactions}

    def get_reaction(self, id: str) -> dict | None:
        """
        Retrieve a reaction node with full substrate/product/enzyme context.

        :param id: Reaction node ID or shorthand external ID.
        :return: Reaction detail dict or ``None`` if not found.
        """
        nid = self.store.resolve_id(id)
        if not nid:
            return None
        return self.store.reaction_detail(nid)

    def find_path(
        self, compound_a: str, compound_b: str, *, max_hops: int = 6
    ) -> dict:
        """
        Find the shortest metabolic path between two compound nodes.

        :param compound_a: Source compound ID, shorthand, or name.
        :param compound_b: Target compound ID, shorthand, or name.
        :param max_hops: Maximum reaction steps (default 6).
        :return: Dict with ``path``, ``hops``, and ``edges`` keys,
                 or ``{"error": ..., "searched_hops": n}``.
        """
        a_id = self.store.resolve_id(compound_a)
        b_id = self.store.resolve_id(compound_b)
        if not a_id:
            return {"error": f"compound not found: {compound_a!r}"}
        if not b_id:
            return {"error": f"compound not found: {compound_b!r}"}
        return self.store.find_shortest_path(a_id, b_id, max_hops=max_hops)

    # ------------------------------------------------------------------
    # Simulation
    # ------------------------------------------------------------------

    def seed_kinetics(self, force: bool = False) -> dict:
        """
        Seed the database with curated kinetic parameters from literature.

        Populates ``kinetic_parameters`` and ``regulatory_interactions`` tables
        with values from BRENDA, SABIO-RK, and published metabolic models.

        :param force: If ``True``, overwrite existing kinetic parameter rows.
        :return: Dict with ``kinetic_params_written`` and
            ``regulatory_interactions_written`` counts.
        """
        kp_count, ri_count = _seed_kinetics(self.store, force=force)
        return {
            "kinetic_params_written": kp_count,
            "regulatory_interactions_written": ri_count,
        }

    def simulate_fba(
        self,
        pathway_id: str | None = None,
        reaction_ids: list[str] | None = None,
        *,
        t_end: float = 100.0,
        t_points: int = 500,
        initial_concentrations: dict[str, float] | None = None,
        default_concentration: float = 1.0,
        objective_reaction: str | None = None,
        maximize: bool = True,
        flux_bounds: dict[str, tuple[float, float]] | None = None,
        vmax_overrides: dict[str, float] | None = None,
        vmax_factors: dict[str, float] | None = None,
    ) -> dict:
        """
        Run Flux Balance Analysis on the reactions in a pathway.

        :param pathway_id: Pathway node ID to scope reactions (e.g. ``"pwy:kegg:hsa00010"``).
        :param reaction_ids: Explicit list of reaction node IDs to include.
        :param objective_reaction: Reaction ID to optimise in FBA.  ``None`` maximises
            the sum of all fluxes (biomass proxy).
        :param maximize: If ``True`` (default) maximise the objective; else minimise.
        :param flux_bounds: Override reaction flux bounds ``{reaction_id: (lb, ub)}``.
        :return: Dict with ``status``, ``objective_value``, ``fluxes``, ``shadow_prices``, and ``message``.
        """
        config = SimulationConfig(
            pathway_id=pathway_id,
            reaction_ids=reaction_ids,
            t_end=t_end,
            t_points=t_points,
            initial_concentrations=initial_concentrations or {},
            default_concentration=default_concentration,
            objective_reaction=objective_reaction,
            maximize=maximize,
            flux_bounds=flux_bounds or {},
            vmax_overrides=vmax_overrides or {},
            vmax_factors=vmax_factors or {},
        )
        result = self.simulator.run_fba(config)
        return {
            "status": result.status,
            "objective_value": result.objective_value,
            "fluxes": result.fluxes,
            "shadow_prices": result.shadow_prices,
            "message": result.message,
        }

    def simulate_ode(
        self,
        pathway_id: str | None = None,
        reaction_ids: list[str] | None = None,
        *,
        t_end: float = 100.0,
        t_points: int = 500,
        initial_concentrations: dict[str, float] | None = None,
        default_concentration: float = 1.0,
        initial_concentrations_json: str | None = None,
        vmax_overrides: dict[str, float] | None = None,
        vmax_factors: dict[str, float] | None = None,
    ) -> dict:
        """
        Run kinetic ODE simulation using Michaelis-Menten rate equations.

        :param pathway_id: Pathway node ID to scope reactions.
        :param reaction_ids: Explicit list of reaction node IDs to include.
        :param t_end: End time for ODE integration (arbitrary time units, default 100).
        :param t_points: Number of time points to sample in ODE output (default 500).
        :param initial_concentrations: Map of ``{compound_id: mM}`` for ODE initial conditions.
        :param default_concentration: Default initial concentration (mM) for ODE runs (default 1.0).
        :param initial_concentrations_json: JSON string of ``{compound_id: mM}`` (alternative to dict).
        :param vmax_overrides: Override Vmax for specific reactions.
        :param vmax_factors: Multiply stored (or default) Vmax by a factor.
        :return: Dict with ``status``, ``t``, ``concentrations``, and ``message``.
        """
        # Parse JSON if provided
        if initial_concentrations_json:
            initial_concentrations = json.loads(initial_concentrations_json)

        config = SimulationConfig(
            pathway_id=pathway_id,
            reaction_ids=reaction_ids,
            t_end=t_end,
            t_points=t_points,
            initial_concentrations=initial_concentrations or {},
            default_concentration=default_concentration,
            vmax_overrides=vmax_overrides or {},
            vmax_factors=vmax_factors or {},
        )
        result = self.simulator.run_ode(config)
        return {
            "status": result.status,
            "t": result.t,
            "concentrations": result.concentrations,
            "message": result.message,
        }

    def simulate_whatif(
        self,
        scenario_json: str,
        pathway_id: str | None = None,
        reaction_ids: list[str] | None = None,
        *,
        mode: str = "fba",
        initial_concentrations: dict[str, float] | None = None,
        default_concentration: float = 1.0,
        t_end: float = 100.0,
        t_points: int = 500,
    ) -> dict:
        """
        Run baseline and perturbed simulations and return the difference.

        The scenario is a JSON object with optional keys:

        - ``name`` (str): Label for the scenario.
        - ``enzyme_knockouts`` (list[str]): Enzyme node IDs to silence.
        - ``enzyme_factors`` (dict[str, float]): Map enzyme ID → activity multiplier.
        - ``initial_conc_overrides`` (dict[str, float]): Override compound initial
          concentrations in mM (ODE mode only).

        :param scenario_json: JSON-encoded scenario object (see above).
        :param pathway_id: Pathway node ID to scope reactions.
        :param reaction_ids: Explicit list of reaction node IDs to include.
        :param mode: ``"fba"`` (default) or ``"ode"``.
        :param initial_concentrations: Map of ``{compound_id: mM}`` for ODE initial conditions.
        :param default_concentration: Default initial concentration (mM) for ODE runs (default 1.0).
        :param t_end: End time for ODE integration (default 100).
        :param t_points: Number of time points to sample (default 500).
        :return: Dict with ``baseline``, ``perturbed``, ``delta_fluxes``, ``delta_final_conc``, and ``mode``.
        :raises ValueError: If *mode* is not ``"fba"`` or ``"ode"``.
        """
        if mode not in ("fba", "ode"):
            raise ValueError(f"mode must be 'fba' or 'ode', got {mode!r}")

        scenario_data = json.loads(scenario_json)
        scenario = WhatIfScenario(
            name=scenario_data.get("name", "unnamed"),
            enzyme_knockouts=scenario_data.get("enzyme_knockouts", []),
            enzyme_factors=scenario_data.get("enzyme_factors", {}),
            initial_conc_overrides=scenario_data.get("initial_conc_overrides", {}),
        )

        config = SimulationConfig(
            pathway_id=pathway_id,
            reaction_ids=reaction_ids,
            t_end=t_end,
            t_points=t_points,
            initial_concentrations=initial_concentrations or {},
            default_concentration=default_concentration,
        )

        result = self.simulator.run_whatif(config, scenario, mode=mode)

        # Convert result to dict
        baseline_dict = {}
        perturbed_dict = {}

        if mode == "fba":
            baseline_dict = {
                "status": result.baseline.status,
                "objective_value": result.baseline.objective_value,
                "fluxes": result.baseline.fluxes,
                "shadow_prices": result.baseline.shadow_prices,
                "message": result.baseline.message,
            }
            perturbed_dict = {
                "status": result.perturbed.status,
                "objective_value": result.perturbed.objective_value,
                "fluxes": result.perturbed.fluxes,
                "shadow_prices": result.perturbed.shadow_prices,
                "message": result.perturbed.message,
            }
        else:  # mode == "ode"
            baseline_dict = {
                "status": result.baseline.status,
                "t": result.baseline.t,
                "concentrations": result.baseline.concentrations,
                "message": result.baseline.message,
            }
            perturbed_dict = {
                "status": result.perturbed.status,
                "t": result.perturbed.t,
                "concentrations": result.perturbed.concentrations,
                "message": result.perturbed.message,
            }

        return {
            "scenario_name": result.scenario_name,
            "baseline": baseline_dict,
            "perturbed": perturbed_dict,
            "delta_fluxes": result.delta_fluxes,
            "delta_final_conc": result.delta_final_conc,
            "mode": result.mode,
        }

    def get_stats(self) -> MetabolicRuntimeStats:
        """
        Get current knowledge graph statistics.

        :return: :class:`MetabolicRuntimeStats` with node/edge/index counts.
        """
        s = self.store.stats()

        indexed_rows: int | None = None
        index_dim: int | None = None

        # Get index stats if available
        if self._index is not None or (self.lancedb_dir / "data" / "index" / ".lance").exists():
            try:
                idx_stats = self.index.stats()
                indexed_rows = idx_stats.get("indexed_rows")
                index_dim = idx_stats.get("dim")
            except Exception:
                pass  # Index not available or error reading stats

        return MetabolicRuntimeStats(
            total_nodes=s["total_nodes"],
            total_edges=s["total_edges"],
            node_counts=s["node_counts"],
            edge_counts=s["edge_counts"],
            indexed_rows=indexed_rows,
            index_dim=index_dim,
        )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Close the underlying SQLite connection."""
        if self._store is not None:
            self._store.close()

    def __enter__(self) -> MetaKG:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def __repr__(self) -> str:
        return (
            f"MetaKG(db_path={self.db_path!r}, "
            f"lancedb_dir={self.lancedb_dir!r}, "
            f"model={self.model_name!r})"
        )
