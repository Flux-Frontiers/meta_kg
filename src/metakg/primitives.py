"""
primitives.py — Core data types for the MetaKG metabolic knowledge graph.

Defines MetaNode, MetaEdge dataclasses, stable node_id() constructor,
and the kind/relation constants used throughout the metakg subpackage.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Node kind constants
# ---------------------------------------------------------------------------

KIND_COMPOUND = "compound"
KIND_REACTION = "reaction"
KIND_ENZYME = "enzyme"
KIND_PATHWAY = "pathway"

ALL_KINDS = (KIND_COMPOUND, KIND_REACTION, KIND_ENZYME, KIND_PATHWAY)

# ---------------------------------------------------------------------------
# Edge relation constants
# ---------------------------------------------------------------------------

REL_SUBSTRATE_OF = "SUBSTRATE_OF"   # compound → reaction
REL_PRODUCT_OF = "PRODUCT_OF"       # reaction → compound
REL_CATALYZES = "CATALYZES"         # enzyme → reaction
REL_INHIBITS = "INHIBITS"           # compound → reaction
REL_ACTIVATES = "ACTIVATES"         # compound → reaction
REL_CONTAINS = "CONTAINS"           # pathway → reaction|compound
REL_XREF = "XREF"                   # any → any (cross-database identity)

DEFAULT_RELS: tuple[str, ...] = (
    REL_SUBSTRATE_OF,
    REL_PRODUCT_OF,
    REL_CATALYZES,
    REL_CONTAINS,
)

# ---------------------------------------------------------------------------
# Node ID construction
# ---------------------------------------------------------------------------

# Namespace prefixes for stable IDs
_NS = {
    KIND_COMPOUND: "cpd",
    KIND_REACTION: "rxn",
    KIND_ENZYME: "enz",
    KIND_PATHWAY: "pwy",
}


def node_id(kind: str, db: str, ext_id: str) -> str:
    """
    Build a stable, URI-style node identifier.

    Examples::

        node_id("compound", "kegg", "C00022")    → "cpd:kegg:C00022"
        node_id("reaction", "kegg", "R00200")    → "rxn:kegg:R00200"
        node_id("enzyme",   "ec",   "1.1.1.1")  → "enz:ec:1.1.1.1"
        node_id("pathway",  "kegg", "hsa00010")  → "pwy:kegg:hsa00010"

    :param kind: One of ``compound``, ``reaction``, ``enzyme``, ``pathway``.
    :param db: Source database namespace, e.g. ``kegg``, ``chebi``, ``uniprot``.
    :param ext_id: External identifier within that database.
    :return: Stable string identifier.
    """
    prefix = _NS.get(kind, kind)
    return f"{prefix}:{db}:{ext_id}"


def synthetic_id(kind: str, name: str) -> str:
    """
    Build a stable synthetic node ID for entities without a database identifier.

    Uses a short hash of the lowercased name so IDs are deterministic across
    parser runs on identical input.

    :param kind: Node kind.
    :param name: Display name of the entity.
    :return: Stable string identifier of the form ``<prefix>:syn:<hash8>``.
    """
    prefix = _NS.get(kind, kind)
    h = hashlib.sha1(name.lower().encode()).hexdigest()[:8]
    return f"{prefix}:syn:{h}"


# ---------------------------------------------------------------------------
# MetaNode
# ---------------------------------------------------------------------------


@dataclass
class MetaNode:
    """
    A node in the metabolic knowledge graph.

    :param id: Stable URI-style identifier (e.g. ``cpd:kegg:C00022``).
    :param kind: Node kind: ``compound``, ``reaction``, ``enzyme``, or ``pathway``.
    :param name: Primary display name.
    :param description: Free-text description used for embedding and semantic search.
    :param formula: Molecular formula (compounds only, e.g. ``C3H4O3``).
    :param charge: Net formal charge (compounds only).
    :param ec_number: EC classification number (enzymes only, e.g. ``1.1.1.1``).
    :param stoichiometry: JSON-serialised stoichiometry dict (reactions only).
        Format: ``{"substrates": [{"id": "...", "stoich": 1.0}], "products": [...]}``
    :param xrefs: JSON-serialised cross-reference dict (e.g. ``{"kegg": "C00022", "chebi": "CHEBI_15361"}``).
    :param source_format: Parser format that produced this node (``kgml``, ``biopax``, ``sbml``, ``csv``).
    :param source_file: Absolute path to the originating file.
    """

    id: str
    kind: str
    name: str
    description: str = ""
    formula: str | None = None
    charge: int | None = None
    ec_number: str | None = None
    stoichiometry: str | None = None   # JSON blob
    xrefs: str | None = None            # JSON blob
    source_format: str = ""
    source_file: str | None = None

    def xrefs_dict(self) -> dict[str, str]:
        """
        Deserialise the ``xrefs`` JSON blob to a plain dict.

        :return: Dict mapping database name to external ID, or ``{}`` if not set.
        """
        if not self.xrefs:
            return {}
        try:
            return json.loads(self.xrefs)
        except (json.JSONDecodeError, TypeError):
            return {}

    def stoichiometry_dict(self) -> dict:
        """
        Deserialise the ``stoichiometry`` JSON blob.

        :return: Stoichiometry dict with ``substrates`` and ``products`` lists,
                 or ``{}`` if not set.
        """
        if not self.stoichiometry:
            return {}
        try:
            return json.loads(self.stoichiometry)
        except (json.JSONDecodeError, TypeError):
            return {}


# ---------------------------------------------------------------------------
# MetaEdge
# ---------------------------------------------------------------------------


@dataclass
class MetaEdge:
    """
    A directed edge in the metabolic knowledge graph.

    :param src: Source node ID.
    :param rel: Relation type (e.g. ``SUBSTRATE_OF``, ``CATALYZES``).
    :param dst: Destination node ID.
    :param evidence: Optional JSON-serialised evidence dict
        (e.g. ``{"stoich": 2.0, "compartment": "cytosol"}``).
    """

    src: str
    rel: str
    dst: str
    evidence: str | None = None

    def evidence_dict(self) -> dict:
        """
        Deserialise the ``evidence`` JSON blob.

        :return: Evidence dict, or ``{}`` if not set.
        """
        if not self.evidence:
            return {}
        try:
            return json.loads(self.evidence)
        except (json.JSONDecodeError, TypeError):
            return {}
