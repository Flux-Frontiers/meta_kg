"""
metakg.parsers — Format-specific metabolic pathway parsers.

Each parser implements the PathwayParser ABC and returns
(list[MetaNode], list[MetaEdge]) for a single input file.
"""

from metakg.parsers.base import PathwayParser
from metakg.parsers.kgml import KGMLParser
from metakg.parsers.sbml import SBMLParser
from metakg.parsers.biopax import BioPAXParser
from metakg.parsers.csv_tsv import CSVParser, CSVParserConfig

__all__ = [
    "PathwayParser",
    "KGMLParser",
    "SBMLParser",
    "BioPAXParser",
    "CSVParser",
    "CSVParserConfig",
]
