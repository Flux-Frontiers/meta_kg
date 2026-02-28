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
