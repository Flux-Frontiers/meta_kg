"""
Tests for code_kg.metakg.store — MetaStore SQLite persistence layer.
"""

import json
import tempfile
from pathlib import Path

import pytest

from metakg.primitives import (
    KIND_COMPOUND,
    KIND_ENZYME,
    KIND_PATHWAY,
    KIND_REACTION,
    MetaEdge,
    MetaNode,
    node_id,
)
from metakg.store import MetaStore


@pytest.fixture()
def store(tmp_path):
    s = MetaStore(tmp_path / "test.sqlite")
    yield s
    s.close()


def _make_nodes():
    glucose = MetaNode(
        id=node_id(KIND_COMPOUND, "kegg", "C00031"),
        kind=KIND_COMPOUND, name="D-Glucose",
        description="Hexose sugar", formula="C6H12O6",
        xrefs='{"kegg": "C00031", "chebi": "CHEBI_4167"}',
        source_format="csv",
    )
    pyruvate = MetaNode(
        id=node_id(KIND_COMPOUND, "kegg", "C00022"),
        kind=KIND_COMPOUND, name="Pyruvate",
        description="End product of glycolysis", formula="C3H4O3",
        xrefs='{"kegg": "C00022"}',
        source_format="csv",
    )
    rxn = MetaNode(
        id=node_id(KIND_REACTION, "kegg", "R00200"),
        kind=KIND_REACTION, name="Glycolysis reaction",
        stoichiometry=json.dumps({
            "substrates": [{"id": node_id(KIND_COMPOUND, "kegg", "C00031"), "stoich": 1.0}],
            "products": [{"id": node_id(KIND_COMPOUND, "kegg", "C00022"), "stoich": 2.0}],
        }),
        xrefs='{"kegg": "R00200"}',
        source_format="csv",
    )
    pwy = MetaNode(
        id=node_id(KIND_PATHWAY, "kegg", "hsa00010"),
        kind=KIND_PATHWAY, name="Glycolysis / Gluconeogenesis",
        source_format="csv",
    )
    enz = MetaNode(
        id=node_id(KIND_ENZYME, "ec", "2.7.1.1"),
        kind=KIND_ENZYME, name="Hexokinase",
        ec_number="2.7.1.1",
        xrefs='{"ec": "2.7.1.1"}',
        source_format="csv",
    )
    return [glucose, pyruvate, rxn, pwy, enz]


def _make_edges():
    glucose_id = node_id(KIND_COMPOUND, "kegg", "C00031")
    pyruvate_id = node_id(KIND_COMPOUND, "kegg", "C00022")
    rxn_id = node_id(KIND_REACTION, "kegg", "R00200")
    pwy_id = node_id(KIND_PATHWAY, "kegg", "hsa00010")
    enz_id = node_id(KIND_ENZYME, "ec", "2.7.1.1")
    return [
        MetaEdge(src=glucose_id, rel="SUBSTRATE_OF", dst=rxn_id,
                 evidence='{"stoich": 1.0}'),
        MetaEdge(src=rxn_id, rel="PRODUCT_OF", dst=pyruvate_id,
                 evidence='{"stoich": 2.0}'),
        MetaEdge(src=enz_id, rel="CATALYZES", dst=rxn_id),
        MetaEdge(src=pwy_id, rel="CONTAINS", dst=rxn_id),
    ]


class TestMetaStoreBasic:
    def test_write_and_read_node(self, store):
        nodes = _make_nodes()
        store.write(nodes, [])
        n = store.node(node_id(KIND_COMPOUND, "kegg", "C00031"))
        assert n is not None
        assert n["name"] == "D-Glucose"
        assert n["formula"] == "C6H12O6"

    def test_stats_after_write(self, store):
        store.write(_make_nodes(), _make_edges())
        s = store.stats()
        assert s["total_nodes"] == 5
        assert s["total_edges"] == 4
        assert s["node_counts"]["compound"] == 2
        assert s["node_counts"]["reaction"] == 1

    def test_wipe_clears_data(self, store):
        store.write(_make_nodes(), _make_edges())
        store.write([], [], wipe=True)
        assert store.stats()["total_nodes"] == 0

    def test_node_returns_none_for_missing(self, store):
        assert store.node("nonexistent:id") is None

    def test_edges_of_node(self, store):
        store.write(_make_nodes(), _make_edges())
        rxn_id = node_id(KIND_REACTION, "kegg", "R00200")
        edges = store.edges_of(rxn_id)
        rels = {e["rel"] for e in edges}
        assert "SUBSTRATE_OF" in rels
        assert "PRODUCT_OF" in rels

    def test_edges_within(self, store):
        store.write(_make_nodes(), _make_edges())
        rxn_id = node_id(KIND_REACTION, "kegg", "R00200")
        glucose_id = node_id(KIND_COMPOUND, "kegg", "C00031")
        edges = store.edges_within({rxn_id, glucose_id})
        assert len(edges) == 1
        assert edges[0]["rel"] == "SUBSTRATE_OF"


class TestXrefIndex:
    def test_build_xref_index(self, store):
        store.write(_make_nodes(), [])
        count = store.build_xref_index()
        assert count > 0

    def test_node_by_xref(self, store):
        store.write(_make_nodes(), [])
        store.build_xref_index()
        n = store.node_by_xref("kegg", "C00031")
        assert n is not None
        assert n["name"] == "D-Glucose"

    def test_resolve_id_internal(self, store):
        store.write(_make_nodes(), [])
        nid = node_id(KIND_COMPOUND, "kegg", "C00031")
        assert store.resolve_id(nid) == nid

    def test_resolve_id_shorthand(self, store):
        store.write(_make_nodes(), [])
        store.build_xref_index()
        nid = store.resolve_id("kegg:C00031")
        assert nid == node_id(KIND_COMPOUND, "kegg", "C00031")

    def test_resolve_id_by_name(self, store):
        store.write(_make_nodes(), [])
        nid = store.resolve_id("D-Glucose")
        assert nid == node_id(KIND_COMPOUND, "kegg", "C00031")

    def test_resolve_id_unknown_returns_none(self, store):
        store.write(_make_nodes(), [])
        assert store.resolve_id("nonexistent") is None


class TestReactionDetail:
    def test_reaction_detail(self, store):
        store.write(_make_nodes(), _make_edges())
        rxn_id = node_id(KIND_REACTION, "kegg", "R00200")
        detail = store.reaction_detail(rxn_id)
        assert detail is not None
        assert detail["name"] == "Glycolysis reaction"
        assert len(detail["substrates"]) == 1
        assert len(detail["products"]) == 1
        assert detail["substrates"][0]["stoich"] == 1.0
        assert len(detail["enzymes"]) == 1
        assert detail["enzymes"][0]["role"] == "CATALYZES"

    def test_reaction_detail_missing(self, store):
        assert store.reaction_detail("rxn:kegg:MISSING") is None


class TestFindPath:
    def test_direct_path_two_hops(self, store):
        store.write(_make_nodes(), _make_edges())
        glucose_id = node_id(KIND_COMPOUND, "kegg", "C00031")
        pyruvate_id = node_id(KIND_COMPOUND, "kegg", "C00022")
        result = store.find_shortest_path(glucose_id, pyruvate_id)
        assert "error" not in result
        assert result["hops"] == 1
        ids_in_path = [n["id"] for n in result["path"]]
        assert glucose_id in ids_in_path
        assert pyruvate_id in ids_in_path

    def test_same_compound_zero_hops(self, store):
        store.write(_make_nodes(), [])
        nid = node_id(KIND_COMPOUND, "kegg", "C00031")
        result = store.find_shortest_path(nid, nid)
        assert result["hops"] == 0

    def test_no_path_returns_error(self, store):
        store.write(_make_nodes(), _make_edges())
        glucose_id = node_id(KIND_COMPOUND, "kegg", "C00031")
        pwy_id = node_id(KIND_PATHWAY, "kegg", "hsa00010")
        result = store.find_shortest_path(glucose_id, pwy_id, max_hops=2)
        assert "error" in result
