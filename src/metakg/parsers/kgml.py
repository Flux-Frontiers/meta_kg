"""
kgml.py — KEGG KGML (XML) pathway parser.

KGML is the native XML format exported by the KEGG PATHWAY database.
Each file describes one pathway map with:
  - <entry> elements: compounds (type="compound"), genes/enzymes (type="gene",
    "ortholog"), and other entities (type="map", "group").
  - <reaction> elements: biochemical reactions with <substrate> and <product>
    child elements.
  - <relation> elements: protein interactions (not parsed here).

Reference: https://www.genome.jp/kegg/xml/docs/

KGML detection heuristic: the root element tag is ``{...}pathway`` or
``pathway`` (no namespace), which distinguishes it from SBML's ``<sbml>`` root.
"""

from __future__ import annotations

import json
from pathlib import Path
from xml.etree import ElementTree as ET

from metakg.parsers.base import PathwayParser
from metakg.primitives import (
    KIND_COMPOUND,
    KIND_ENZYME,
    KIND_PATHWAY,
    KIND_REACTION,
    REL_CATALYZES,
    REL_CONTAINS,
    REL_PRODUCT_OF,
    REL_SUBSTRATE_OF,
    MetaEdge,
    MetaNode,
    node_id,
    synthetic_id,
)


class KGMLParser(PathwayParser):
    """
    Parser for KEGG KGML (XML) pathway files.

    Handles ``.xml`` and ``.kgml`` files whose root element is ``<pathway>``.
    Uses only stdlib ``xml.etree.ElementTree`` — no additional dependencies.
    """

    @property
    def supported_extensions(self) -> tuple[str, ...]:
        return (".xml", ".kgml")

    def can_handle(self, path: Path) -> bool:
        if path.suffix.lower() not in self.supported_extensions:
            return False
        try:
            for _evt, elem in ET.iterparse(path, events=("start",)):
                tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
                return tag == "pathway"
        except ET.ParseError:
            return False
        return False

    def parse(self, path: Path) -> tuple[list[MetaNode], list[MetaEdge]]:
        """
        Parse a KGML file into MetaNode and MetaEdge objects.

        :param path: Path to the ``.kgml`` or ``.xml`` file.
        :return: ``(nodes, edges)`` tuple.
        :raises ValueError: If the file is not valid KGML.
        """
        try:
            tree = ET.parse(path)
        except ET.ParseError as exc:
            raise ValueError(f"Invalid XML in {path}: {exc}") from exc

        root = tree.getroot()
        tag = root.tag.split("}")[-1] if "}" in root.tag else root.tag
        if tag != "pathway":
            raise ValueError(f"Root element is <{tag}>, expected <pathway>")

        nodes: dict[str, MetaNode] = {}
        edges: list[MetaEdge] = []

        pathway_kegg_id = root.attrib.get("name", "").replace("path:", "").strip()
        pathway_title = root.attrib.get("title", pathway_kegg_id)
        org = root.attrib.get("org", "")

        # Pathway container node
        pwy_id = node_id(KIND_PATHWAY, "kegg", pathway_kegg_id) if pathway_kegg_id else synthetic_id(KIND_PATHWAY, pathway_title)
        pwy_node = MetaNode(
            id=pwy_id,
            kind=KIND_PATHWAY,
            name=pathway_title,
            description=f"KEGG pathway {pathway_kegg_id} ({org}): {pathway_title}",
            xrefs=json.dumps({"kegg": pathway_kegg_id}) if pathway_kegg_id else None,
            source_format="kgml",
            source_file=str(path),
        )
        nodes[pwy_id] = pwy_node

        # Map KGML entry id (integer) → MetaNode id for reaction wiring
        entry_map: dict[str, str] = {}

        # --- Entries ---
        for entry in root.findall("entry"):
            etype = entry.attrib.get("type", "")
            enames = entry.attrib.get("name", "")
            entry_id = entry.attrib.get("id", "")

            if etype == "compound":
                for raw_name in enames.split():
                    kegg_cid = raw_name.replace("cpd:", "").strip()
                    nid = node_id(KIND_COMPOUND, "kegg", kegg_cid)
                    if nid not in nodes:
                        graphics = entry.find("graphics")
                        label = graphics.attrib.get("name", kegg_cid) if graphics is not None else kegg_cid
                        nodes[nid] = MetaNode(
                            id=nid,
                            kind=KIND_COMPOUND,
                            name=label,
                            description=f"KEGG compound {kegg_cid}",
                            xrefs=json.dumps({"kegg": kegg_cid}),
                            source_format="kgml",
                            source_file=str(path),
                        )
                    entry_map[entry_id] = nid
                    # One entry typically has one compound; use last if multiple
            elif etype in ("gene", "ortholog"):
                for raw_name in enames.split():
                    kegg_gene = raw_name.replace("hsa:", "").replace("ko:", "").strip()
                    nid = node_id(KIND_ENZYME, "kegg", kegg_gene)
                    if nid not in nodes:
                        graphics = entry.find("graphics")
                        label = graphics.attrib.get("name", kegg_gene) if graphics is not None else kegg_gene
                        nodes[nid] = MetaNode(
                            id=nid,
                            kind=KIND_ENZYME,
                            name=label,
                            description=f"KEGG gene/enzyme {kegg_gene}",
                            xrefs=json.dumps({"kegg": kegg_gene}),
                            source_format="kgml",
                            source_file=str(path),
                        )
                    entry_map[entry_id] = nid

        # --- Reactions ---
        for rxn_elem in root.findall("reaction"):
            rxn_kegg_id = rxn_elem.attrib.get("name", "").replace("rn:", "").strip()
            rxn_type = rxn_elem.attrib.get("type", "irreversible")  # reversible|irreversible

            substrates: list[dict] = []
            products: list[dict] = []

            for sub in rxn_elem.findall("substrate"):
                sub_name = sub.attrib.get("name", "").replace("cpd:", "").strip()
                substrates.append({"id": node_id(KIND_COMPOUND, "kegg", sub_name), "stoich": 1.0})

            for prod in rxn_elem.findall("product"):
                prod_name = prod.attrib.get("name", "").replace("cpd:", "").strip()
                products.append({"id": node_id(KIND_COMPOUND, "kegg", prod_name), "stoich": 1.0})

            stoich_blob = json.dumps({"substrates": substrates, "products": products, "direction": rxn_type})
            rxn_id = node_id(KIND_REACTION, "kegg", rxn_kegg_id) if rxn_kegg_id else synthetic_id(KIND_REACTION, rxn_elem.attrib.get("id", ""))
            rxn_name = rxn_kegg_id or rxn_elem.attrib.get("id", "unknown")

            if rxn_id not in nodes:
                nodes[rxn_id] = MetaNode(
                    id=rxn_id,
                    kind=KIND_REACTION,
                    name=rxn_name,
                    description=f"KEGG reaction {rxn_kegg_id} ({rxn_type})",
                    stoichiometry=stoich_blob,
                    xrefs=json.dumps({"kegg": rxn_kegg_id}) if rxn_kegg_id else None,
                    source_format="kgml",
                    source_file=str(path),
                )

            # Pathway CONTAINS reaction
            edges.append(MetaEdge(src=pwy_id, rel=REL_CONTAINS, dst=rxn_id))

            # Substrate edges
            for s in substrates:
                cid = s["id"]
                # Ensure compound node exists (may not be in entries if only in reaction)
                if cid not in nodes:
                    kegg_cid = cid.split(":")[-1]
                    nodes[cid] = MetaNode(
                        id=cid, kind=KIND_COMPOUND, name=kegg_cid,
                        description=f"KEGG compound {kegg_cid}",
                        xrefs=json.dumps({"kegg": kegg_cid}),
                        source_format="kgml", source_file=str(path),
                    )
                edges.append(MetaEdge(
                    src=cid, rel=REL_SUBSTRATE_OF, dst=rxn_id,
                    evidence=json.dumps({"stoich": s["stoich"]}),
                ))

            # Product edges
            for p in products:
                cid = p["id"]
                if cid not in nodes:
                    kegg_cid = cid.split(":")[-1]
                    nodes[cid] = MetaNode(
                        id=cid, kind=KIND_COMPOUND, name=kegg_cid,
                        description=f"KEGG compound {kegg_cid}",
                        xrefs=json.dumps({"kegg": kegg_cid}),
                        source_format="kgml", source_file=str(path),
                    )
                edges.append(MetaEdge(
                    src=rxn_id, rel=REL_PRODUCT_OF, dst=cid,
                    evidence=json.dumps({"stoich": p["stoich"]}),
                ))

        # --- Wire enzymes to reactions via entry map ---
        # KGML doesn't explicitly link genes to reactions via child elements;
        # the convention is that gene entries listed adjacent to a reaction in
        # the same pathway are its catalysts. We emit CATALYZES edges for gene
        # entries whose id appears in the reaction's entry attribute (not standard)
        # or simply leave enzyme wiring to be done by the user's dataset.
        # Standard KGML does not have a direct gene→reaction link in the XML.

        return list(nodes.values()), edges
