"""
mcp_tools.py — MCP tool registrations for MetaKG.

Exposes four tools on a FastMCP instance:

    query_pathway(name, k)                      — semantic pathway search
    get_compound(id)                            — compound + connected reactions
    get_reaction(id)                            — full stoichiometric detail
    find_path(compound_a, compound_b, max_hops) — shortest metabolic path

Register via::

    from metakg import MetaKG
    from metakg.mcp_tools import create_server

    mcp = create_server(MetaKG(db_path=".metakg/meta.sqlite"))
    mcp.run()

Or mount onto an existing FastMCP instance::

    from metakg.mcp_tools import register_tools
    register_tools(mcp, metakg)
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from metakg.metakg import MetaKG


def register_tools(mcp, metakg: MetaKG) -> None:
    """
    Register all MetaKG MCP tools on *mcp*.

    :param mcp: A ``FastMCP`` instance (from ``mcp.server.fastmcp``).
    :param metakg: Initialised :class:`~metakg.metakg.MetaKG` instance.
    """

    @mcp.tool()
    def query_pathway(name: str, k: int = 8) -> str:
        """
        Find metabolic pathways by name or description using semantic search.

        :param name: Pathway name or description, e.g. ``"glycolysis"`` or
            ``"fatty acid beta oxidation"``.
        :param k: Maximum results to return (default 8).
        :return: JSON list of matching pathway nodes with ``member_count`` field.
        """
        result = metakg.query_pathway(name, k=k)
        return result.to_json()

    @mcp.tool()
    def get_compound(id: str) -> str:
        """
        Retrieve a compound node by its internal ID or external database ID.

        Accepts internal IDs (``cpd:kegg:C00022``), shorthand (``kegg:C00022``),
        or a compound name (case-insensitive).

        :param id: Compound identifier in any supported format.
        :return: JSON object with compound fields and a ``reactions`` list.
        """
        node = metakg.get_compound(id)
        if node is None:
            return json.dumps({"error": f"compound not found: {id!r}"})
        return json.dumps(node, indent=2, default=str)

    @mcp.tool()
    def get_reaction(id: str) -> str:
        """
        Retrieve a reaction node with its full substrate/product/enzyme context.

        :param id: Reaction node ID (e.g. ``rxn:kegg:R00200``) or shorthand
            (e.g. ``kegg:R00200``).
        :return: JSON object with ``substrates``, ``products``, and ``enzymes`` lists.
        """
        detail = metakg.get_reaction(id)
        if detail is None:
            return json.dumps({"error": f"reaction not found: {id!r}"})
        return json.dumps(detail, indent=2, default=str)

    @mcp.tool()
    def find_path(compound_a: str, compound_b: str, max_hops: int = 6) -> str:
        """
        Find the shortest metabolic path between two compounds.

        Uses bidirectional BFS through ``SUBSTRATE_OF`` and ``PRODUCT_OF`` edges.

        :param compound_a: Source compound ID, shorthand, or name.
        :param compound_b: Target compound ID, shorthand, or name.
        :param max_hops: Maximum reaction steps (default 6).
        :return: JSON with ``path``, ``hops``, ``edges``, or ``{"error": ...}``.
        """
        result = metakg.find_path(compound_a, compound_b, max_hops=max_hops)
        return json.dumps(result, indent=2, default=str)


def create_server(metakg: MetaKG, *, name: str = "metakg"):
    """
    Create a standalone FastMCP server with all MetaKG tools registered.

    :param metakg: Initialised :class:`~metakg.metakg.MetaKG` instance.
    :param name: Server name advertised to MCP clients.
    :return: Configured ``FastMCP`` instance ready to ``.run()``.
    """
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:
        raise ImportError(
            "mcp package not found. Install it with: pip install mcp"
        ) from exc

    server = FastMCP(
        name,
        instructions=(
            "MetaKG gives you semantic access to a metabolic pathway knowledge graph. "
            "Use query_pathway to find pathways, get_compound/get_reaction for entity "
            "detail, and find_path to trace biochemical routes between compounds."
        ),
    )
    register_tools(server, metakg)
    return server
