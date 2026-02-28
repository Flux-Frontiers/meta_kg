#!/usr/bin/env python3
"""
wire_enzymes.py — Add enzyme="N" attributes to <reaction> elements in KGML files.

Links each reaction to its catalysing gene entry by adding the MetaKG-extension
``enzyme`` attribute, which the KGMLParser uses to emit CATALYZES edges.

Mapping format:
    ENZYME_MAPS[filename][reaction_id] = gene_entry_id

Run from the repo root:
    python scripts/wire_enzymes.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Reaction-id → gene-entry-id mappings for each KGML file
# ---------------------------------------------------------------------------

ENZYME_MAPS: dict[str, dict[str, str]] = {
    "hsa00010.xml": {
        "51": "31",  # R00299 hexokinase/glucokinase  → HK1, HK2, GCK
        "52": "32",  # R00771 phosphoglucose isomerase → GPI
        "53": "33",  # R00756 phosphofructokinase      → PFKL, PFKM, PFKP
        "54": "34",  # R01068 aldolase                → ALDOA, ALDOB, ALDOC
        "55": "35",  # R01015 triose-phosphate isomer. → TPI1
        "56": "36",  # R01061 GAPDH                   → GAPDH, GAPDHS
        "57": "37",  # R01512 phosphoglycerate kinase  → PGK1, PGK2
        "58": "38",  # R01518 phosphoglycerate mutase  → PGAM1, PGAM2
        "59": "39",  # R00430 enolase                 → ENO1, ENO2, ENO3
        "60": "40",  # R00200 pyruvate kinase          → PKLR, PKM
        "61": "42",  # R00703 lactate dehydrogenase    → LDHA, LDHB, LDHC
        "63": "41",  # R00754 alcohol dehydrogenase    → AKR1A1
        "64": "43",  # R00352 PEPCK                   → PCK1
        "65": "44",  # R00431 pyruvate carboxylase     → PC
        "66": "45",  # R00841 fructose-1,6-bisphosphatase → FBP1
        "67": "46",  # R00306 glucose-6-phosphatase    → G6PC1
    },
    "hsa00020.xml": {
        "51": "39",  # R00209 pyruvate dehydrogenase   → PDHA1, PDHB, DLAT
        "52": "31",  # R00351 citrate synthase          → CS
        "53": "32",  # R01325 aconitase                → ACO2
        "54": "32",  # R01900 aconitase                → ACO2
        "55": "33",  # R00709 isocitrate dehydrogenase → IDH1, IDH2, IDH3A
        "56": "34",  # R08549 2-oxoglutarate dehydrog. → DLST, DLD, OGDH
        "57": "35",  # R00405 succinyl-CoA synthetase  → SUCLA2, SUCLG1
        "58": "36",  # R02164 succinate dehydrogenase  → SDHA, SDHB, SDHC
        "59": "37",  # R01082 fumarase                 → FH
        "60": "38",  # R00342 malate dehydrogenase     → MDH2
    },
    "hsa00030.xml": {
        "51": "31",  # R00835 glucose-6-P dehydrog.    → G6PD
        "52": "33",  # R02035 gluconolactonase          → PGLS
        "53": "34",  # R01528 6-phosphogluconate dehyd. → PGD
        "54": "35",  # R01056 ribose-5-P isomerase      → RPIA
        "55": "36",  # R01529 ribulose-5-P epimerase    → RPE
        "56": "37",  # R01641 transketolase             → TKT, TKTL1
        "57": "38",  # R01830 transaldolase             → TALDO1
        "58": "37",  # R01829 transketolase             → TKT, TKTL1
        "59": "39",  # R00756 phosphofructokinase       → PFKL
    },
    "hsa00071.xml": {
        "51": "31",  # R01280 long-chain acyl-CoA synt. → ACSL1, ACSL4
        "52": "32",  # R04224 acyl-CoA dehydrogenase   → ACADM, ACADL
        "53": "33",  # R04739 enoyl-CoA hydratase      → HADH, HADHB
        "54": "34",  # R04737 3-hydroxyacyl-CoA dehyd. → HADHB
        "55": "34",  # R00238 thiolase                 → HADHB
        "58": "37",  # R01292 methylmalonyl-CoA mutase → MUT
    },
    "hsa00190.xml": {
        "51": "31",  # R02161 NADH dehydrogenase (Complex I)       → ND subunits
        "52": "32",  # R02164 succinate dehydrogenase (Complex II) → SDH subunits
        "53": "33",  # R02163 cytochrome bc1 (Complex III)         → UQCR subunits
        "54": "34",  # R00081 cytochrome c oxidase (Complex IV)    → COX subunits
        "55": "35",  # R00086 ATP synthase (Complex V)             → ATP5 subunits
        "56": "31",  # R03958 NADH dehydrogenase alt.              → ND subunits
    },
    "hsa00230.xml": {
        "53": "31",  # R01556 AMP deaminase              → AMPD1
        "57": "37",  # R01875 adenine phosphoribosyltransferase → APRT
        "58": "36",  # R01956 hypoxanthine-guanine PRPP-transferase → HPRT1
        "59": "32",  # R01981 adenosine deaminase         → ADA
        "60": "39",  # R00310 purine-nucleoside phosphorylase → NP
        "61": "35",  # R02103 xanthine oxidase            → XDH
        "62": "35",  # R02105 xanthine oxidase            → XDH
        "63": "38",  # R04566 glutamine phosphoribosyl-PP amidotransferase → PPAT
    },
    "hsa00250.xml": {
        "51": "31",  # R00258 alanine aminotransferase    → GPT, GPT2
        "52": "32",  # R00355 aspartate aminotransferase  → GOT1, GOT2
        "55": "34",  # R00253 glutamine synthetase        → GLUL
        "56": "33",  # R00256 glutaminase                 → GLS
        "57": "37",  # R01540 aspartate transcarbamylase  → CAD
        "58": "36",  # R03878 adenylosuccinate lyase       → ADSL
    },
    "hsa00260.xml": {
        "51": "31",  # R02973 phosphoglycerate dehydrogenase → PHGDH
        "52": "33",  # R04347 phosphoserine phosphatase      → PSPH
        "53": "34",  # R00372 serine hydroxymethyltransferase → SHMT1
        "54": "35",  # R01221 glycine decarboxylase complex   → GLDC
        "55": "36",  # R01434 threonine aldolase              → GCAT
        "56": "36",  # R01432 threonine dehydrogenase         → GCAT
        "57": "37",  # R00220 serine/threonine dehydratase    → SDS
    },
    "hsa00480.xml": {
        "51": "31",  # R00899 glutamate-cysteine ligase  → GCLC
        "52": "32",  # R00894 glutathione synthetase     → GSS
        "53": "34",  # R00274 glutathione peroxidase     → GPX1, GPX4
        "54": "33",  # R00195 glutathione reductase      → GSR
        "55": "35",  # R02740 glutathione S-transferase  → GSTA/GSTM/GSTP
        "57": "36",  # R00578 5-oxoprolinase             → OPLAH
    },
    "hsa00620.xml": {
        "51": "31",  # R00703 lactate dehydrogenase      → LDHA, LDHB
        "52": "32",  # R00209 pyruvate dehydrogenase     → PDHA1, PDHB
        "56": "34",  # R00352 PEPCK                     → PCK1, PCK2
        "57": "35",  # R00342 malate dehydrogenase       → MDH2
        "58": "37",  # R00431 pyruvate carboxylase       → PC
        "59": "36",  # R00200 pyruvate kinase            → PKLR
        "60": "38",  # R00216 malic enzyme               → ME1, ME2
    },
    "hsa00650.xml": {
        "51": "31",  # R00238 acetyl-CoA acetyltransferase → ACAT1
        "52": "34",  # R01975 acetoacetyl-CoA hydrolase    → ACSS2/AACS
        "54": "35",  # R01367 3-hydroxybutyrate dehydrog. → BDH1
        "55": "32",  # R00239 HMG-CoA synthase            → HMGCS1, HMGCS2
        "56": "33",  # R00241 HMG-CoA lyase               → HMGCL
        "57": "36",  # R01176 butanoate-CoA ligase         → ACSS2
    },
}

# ---------------------------------------------------------------------------
# Patcher
# ---------------------------------------------------------------------------


def patch_file(path: Path, enzyme_map: dict[str, str]) -> int:
    """
    Add ``enzyme="N"`` attribute to each <reaction id="M"> element where
    M appears in *enzyme_map*.  Returns the number of reactions patched.
    """
    content = path.read_text(encoding="utf-8")
    patched = 0

    for rxn_id, enz_entry_id in enzyme_map.items():
        # Match <reaction id="N" ...> — capture tag open and closing >
        # Make sure we don't add the attribute twice
        pattern = rf'(<reaction\s+id="{re.escape(rxn_id)}"(?![^>]*\benzyme\b)[^>]*)(>)'
        replacement = rf'\1 enzyme="{enz_entry_id}"\2'
        new_content, n = re.subn(pattern, replacement, content)
        if n:
            content = new_content
            patched += n

    path.write_text(content, encoding="utf-8")
    return patched


def main() -> int:
    pathways_dir = Path("pathways")
    total_patched = 0

    for filename, enzyme_map in ENZYME_MAPS.items():
        path = pathways_dir / filename
        if not path.exists():
            print(f"  SKIP  {filename}  (file not found)")
            continue
        n = patch_file(path, enzyme_map)
        total_patched += n
        print(f"  OK    {filename}  — {n} reactions wired")

    print(f"\nTotal: {total_patched} enzyme–reaction links added across {len(ENZYME_MAPS)} files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
