"""
cli.py — Command-line entry points for MetaKG.

Commands
--------
metakg-build     Build the knowledge graph from a directory of pathway files.
metakg-mcp       Start the MCP server.
metakg-analyze   Run the thorough pathway analysis report.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from metakg.embed import DEFAULT_MODEL


# ---------------------------------------------------------------------------
# metakg-build
# ---------------------------------------------------------------------------


def _build_args(argv: list | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="metakg-build",
        description="Build the MetaKG metabolic knowledge graph from pathway files.",
    )
    p.add_argument(
        "--data", required=True,
        help="Directory containing pathway files (KGML, SBML, BioPAX, CSV)",
    )
    p.add_argument(
        "--db", default=".metakg/meta.sqlite",
        help="Output SQLite database path (default: .metakg/meta.sqlite)",
    )
    p.add_argument(
        "--lancedb", default=".metakg/lancedb",
        help="Output LanceDB directory (default: .metakg/lancedb)",
    )
    p.add_argument(
        "--model", default=DEFAULT_MODEL,
        help=f"Sentence-transformer model name (default: {DEFAULT_MODEL})",
    )
    p.add_argument(
        "--no-index", action="store_true",
        help="Skip building the LanceDB vector index",
    )
    p.add_argument(
        "--wipe", action="store_true",
        help="Wipe existing data before building",
    )
    return p.parse_args(argv)


def build_main(argv: list | None = None) -> None:
    """
    CLI entry point: ``metakg-build``.

    :param argv: Argument list; defaults to ``sys.argv[1:]``.
    """
    args = _build_args(argv)
    data_dir = Path(args.data).resolve()
    if not data_dir.exists():
        print(f"ERROR: data directory not found: {data_dir}", file=sys.stderr)
        sys.exit(1)

    from metakg import MetaKG

    kg = MetaKG(db_path=args.db, lancedb_dir=args.lancedb, model=args.model)
    print(f"Building MetaKG from {data_dir}...", file=sys.stderr)
    stats = kg.build(data_dir=data_dir, wipe=args.wipe, build_index=not args.no_index)
    print(stats, file=sys.stderr)

    if stats.parse_errors:
        print(f"\n{len(stats.parse_errors)} file(s) failed to parse:", file=sys.stderr)
        for err in stats.parse_errors:
            print(f"  {err['file']}: {err['error']}", file=sys.stderr)

    kg.close()


# ---------------------------------------------------------------------------
# metakg-mcp
# ---------------------------------------------------------------------------


def _mcp_args(argv: list | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="metakg-mcp",
        description="Start the MetaKG MCP server.",
    )
    p.add_argument(
        "--db", default=".metakg/meta.sqlite",
        help="Path to MetaKG SQLite database (default: .metakg/meta.sqlite)",
    )
    p.add_argument(
        "--lancedb", default=".metakg/lancedb",
        help="Path to LanceDB directory (default: .metakg/lancedb)",
    )
    p.add_argument(
        "--model", default=DEFAULT_MODEL,
        help=f"Sentence-transformer model name (default: {DEFAULT_MODEL})",
    )
    p.add_argument(
        "--transport", choices=["stdio", "sse"], default="stdio",
        help="MCP transport: stdio (default) or sse (HTTP)",
    )
    return p.parse_args(argv)


def mcp_main(argv: list | None = None) -> None:
    """
    CLI entry point: ``metakg-mcp``.

    :param argv: Argument list; defaults to ``sys.argv[1:]``.
    """
    args = _mcp_args(argv)

    from metakg import MetaKG
    from metakg.mcp_tools import create_server

    db = Path(args.db)
    if not db.exists():
        print(
            f"WARNING: database not found at '{db}'.\n"
            "Run 'metakg-build' first.",
            file=sys.stderr,
        )

    print(
        f"MetaKG MCP server starting\n"
        f"  db       : {db}\n"
        f"  lancedb  : {args.lancedb}\n"
        f"  model    : {args.model}\n"
        f"  transport: {args.transport}",
        file=sys.stderr,
    )

    kg = MetaKG(db_path=db, lancedb_dir=args.lancedb, model=args.model)
    server = create_server(kg)
    server.run(transport=args.transport)


# ---------------------------------------------------------------------------
# metakg-viz
# ---------------------------------------------------------------------------


def viz_main() -> None:
    """
    CLI entry point: ``metakg-viz``.

    Launches the Streamlit metabolic knowledge-graph explorer. Argument parsing
    is handled by :mod:`metakg.metakg_viz`.
    """
    from metakg.metakg_viz import main as viz_main_func

    viz_main_func()


# ---------------------------------------------------------------------------
# metakg-viz3d
# ---------------------------------------------------------------------------


def viz3d_main() -> None:
    """
    CLI entry point: ``metakg-viz3d``.

    Launches the 3D PyVista metabolic knowledge-graph visualizer. Argument parsing
    is handled by :mod:`metakg.metakg_viz3d`.
    """
    from metakg.metakg_viz3d import main as viz3d_main_func

    viz3d_main_func()


# ---------------------------------------------------------------------------
# metakg-analyze
# ---------------------------------------------------------------------------


def _analyze_args(argv: list | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="metakg-analyze",
        description=(
            "Thorough metabolic pathway analysis for a MetaKG database. "
            "Identifies hub metabolites, complex reactions, cross-pathway connections, "
            "pathway coupling, dead-end metabolites, and top enzymes."
        ),
    )
    p.add_argument(
        "--db", default=".metakg/meta.sqlite",
        help="Path to MetaKG SQLite database (default: .metakg/meta.sqlite)",
    )
    p.add_argument(
        "--output", "-o", default=None,
        metavar="FILE",
        help="Write the Markdown report to FILE (default: print to stdout)",
    )
    p.add_argument(
        "--top", type=int, default=20,
        metavar="N",
        help="Number of items in each ranked list (default: 20)",
    )
    p.add_argument(
        "--plain", action="store_true",
        help="Plain-text output instead of Markdown",
    )
    return p.parse_args(argv)


def analyze_main(argv: list | None = None) -> None:
    """
    CLI entry point: ``metakg-analyze``.

    :param argv: Argument list; defaults to ``sys.argv[1:]``.
    """
    args = _analyze_args(argv)
    db_path = Path(args.db)

    if not db_path.exists():
        print(
            f"ERROR: database not found: {db_path}\n"
            "Run 'metakg-build' first.",
            file=sys.stderr,
        )
        sys.exit(1)

    from metakg.analyze import PathwayAnalyzer, render_report

    print(f"Analysing {db_path} ...", file=sys.stderr)
    with PathwayAnalyzer(db_path, top_n=args.top) as analyzer:
        report = analyzer.run()

    text = render_report(report, markdown=not args.plain)

    if args.output:
        out_path = Path(args.output)
        out_path.write_text(text, encoding="utf-8")
        print(f"Report written to {out_path}", file=sys.stderr)
    else:
        print(text)


# ---------------------------------------------------------------------------
# metakg-simulate
# ---------------------------------------------------------------------------


def _simulate_args(argv: list | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="metakg-simulate",
        description=(
            "Metabolic simulation for MetaKG: FBA, ODE kinetics, and what-if analysis.\n\n"
            "Subcommands:\n"
            "  fba       Flux Balance Analysis (steady-state optimal flux distribution)\n"
            "  ode       ODE kinetic simulation (concentration time-courses)\n"
            "  whatif    Perturbation analysis (baseline vs. modified scenario)\n"
            "  seed      Seed kinetic parameters from curated literature values"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--db", default=".metakg/meta.sqlite",
        help="Path to MetaKG SQLite database (default: .metakg/meta.sqlite)",
    )
    p.add_argument(
        "--output", "-o", default=None, metavar="FILE",
        help="Write Markdown report to FILE (default: print to stdout)",
    )
    p.add_argument(
        "--plain", action="store_true",
        help="Plain-text output instead of Markdown",
    )
    p.add_argument(
        "--top", type=int, default=25, metavar="N",
        help="Maximum items to list in each table (default: 25)",
    )

    sub = p.add_subparsers(dest="subcommand", required=True)

    # --- fba ---
    fba_p = sub.add_parser("fba", help="Flux Balance Analysis")
    fba_p.add_argument(
        "--pathway", "-p", default=None,
        help="Pathway node ID or name (e.g. pwy:kegg:hsa00010 or 'Glycolysis')",
    )
    fba_p.add_argument(
        "--objective", default=None, metavar="RXN_ID",
        help="Reaction ID to optimise (default: maximise total forward flux)",
    )
    fba_p.add_argument(
        "--minimize", action="store_true",
        help="Minimise rather than maximise the objective",
    )

    # --- ode ---
    ode_p = sub.add_parser("ode", help="ODE kinetic simulation")
    ode_p.add_argument(
        "--pathway", "-p", default=None,
        help="Pathway node ID or name",
    )
    ode_p.add_argument(
        "--time", "-t", type=float, default=100.0,
        help="Simulation end time (arbitrary units, default 100)",
    )
    ode_p.add_argument(
        "--points", type=int, default=500,
        help="Number of time points to sample (default 500)",
    )
    ode_p.add_argument(
        "--conc", action="append", default=[], metavar="ID:VALUE",
        help=(
            "Set initial concentration for a compound: e.g. "
            "--conc cpd:kegg:C00031:5.0  (can repeat)"
        ),
    )
    ode_p.add_argument(
        "--default-conc", type=float, default=1.0, metavar="MM",
        help="Default initial concentration in mM for all compounds (default 1.0)",
    )

    # --- whatif ---
    wi_p = sub.add_parser("whatif", help="Perturbation / what-if analysis")
    wi_p.add_argument(
        "--pathway", "-p", default=None,
        help="Pathway node ID or name",
    )
    wi_p.add_argument(
        "--mode", choices=["fba", "ode"], default="fba",
        help="Simulation mode (default: fba)",
    )
    wi_p.add_argument(
        "--knockout", action="append", default=[], metavar="ENZ_ID",
        help="Enzyme node ID to knock out (can repeat)",
    )
    wi_p.add_argument(
        "--factor", action="append", default=[], metavar="ENZ_ID:FACTOR",
        help=(
            "Scale enzyme activity: e.g. --factor enz:kegg:hsa:2538:0.5  "
            "halves activity (can repeat)"
        ),
    )
    wi_p.add_argument(
        "--conc", action="append", default=[], metavar="ID:VALUE",
        help="Override initial compound concentration (ODE mode): ID:mM (can repeat)",
    )
    wi_p.add_argument(
        "--name", default="whatif_scenario",
        help="Scenario label for the report (default: whatif_scenario)",
    )
    wi_p.add_argument(
        "--time", "-t", type=float, default=100.0,
        help="ODE end time (ignored for FBA, default 100)",
    )

    # --- seed ---
    seed_p = sub.add_parser("seed", help="Seed kinetic parameters from literature")
    seed_p.add_argument(
        "--force", action="store_true",
        help="Overwrite existing kinetic parameter rows",
    )

    return p.parse_args(argv)


def _parse_conc_args(conc_args: list[str]) -> dict[str, float]:
    """Parse ``ID:VALUE`` strings into a dict. Last colon-sep token is the value."""
    result: dict[str, float] = {}
    for item in conc_args:
        parts = item.rsplit(":", 1)
        if len(parts) == 2:
            try:
                result[parts[0]] = float(parts[1])
            except ValueError:
                print(f"WARNING: ignoring bad --conc value: {item!r}", file=sys.stderr)
    return result


def _parse_factor_args(factor_args: list[str]) -> dict[str, float]:
    """Parse ``ENZ_ID:FACTOR`` strings. Last colon-sep token is the factor."""
    return _parse_conc_args(factor_args)


def simulate_main(argv: list | None = None) -> None:
    """
    CLI entry point: ``metakg-simulate``.

    :param argv: Argument list; defaults to ``sys.argv[1:]``.
    """
    args = _simulate_args(argv)
    db_path = Path(args.db)

    if args.subcommand == "seed":
        if not db_path.exists():
            print(
                f"ERROR: database not found: {db_path}\nRun 'metakg-build' first.",
                file=sys.stderr,
            )
            sys.exit(1)
        from metakg.kinetics_fetch import seed_kinetics
        from metakg.store import MetaStore

        print(f"Seeding kinetic parameters into {db_path}...", file=sys.stderr)
        with MetaStore(db_path) as store:
            n_kp, n_ri = seed_kinetics(store, force=args.force)
        print(
            f"Done. Wrote {n_kp} kinetic parameter row(s) and "
            f"{n_ri} regulatory interaction row(s).",
            file=sys.stderr,
        )
        return

    if not db_path.exists():
        print(
            f"ERROR: database not found: {db_path}\nRun 'metakg-build' first.",
            file=sys.stderr,
        )
        sys.exit(1)

    from metakg.simulate import (
        MetabolicSimulator,
        SimulationConfig,
        WhatIfScenario,
        render_fba_result,
        render_ode_result,
        render_whatif_result,
    )
    from metakg.store import MetaStore

    markdown = not args.plain

    with MetaStore(db_path) as store:
        sim = MetabolicSimulator(store)

        if args.subcommand == "fba":
            pathway_id = store.resolve_id(args.pathway) if args.pathway else None
            config = SimulationConfig(
                pathway_id=pathway_id,
                objective_reaction=args.objective,
                maximize=not args.minimize,
            )
            print("Running FBA...", file=sys.stderr)
            result = sim.run_fba(config)
            text = render_fba_result(result, store, top_n=args.top, markdown=markdown)

        elif args.subcommand == "ode":
            pathway_id = store.resolve_id(args.pathway) if args.pathway else None
            config = SimulationConfig(
                pathway_id=pathway_id,
                t_end=args.time,
                t_points=args.points,
                initial_concentrations=_parse_conc_args(args.conc),
                default_concentration=args.default_conc,
            )
            print(f"Running ODE (t=0..{args.time}, {args.points} pts)...", file=sys.stderr)
            result = sim.run_ode(config)
            text = render_ode_result(result, store, top_n=args.top, markdown=markdown)

        elif args.subcommand == "whatif":
            pathway_id = store.resolve_id(args.pathway) if args.pathway else None
            config = SimulationConfig(
                pathway_id=pathway_id,
                t_end=args.time,
            )
            scenario = WhatIfScenario(
                name=args.name,
                enzyme_knockouts=[
                    store.resolve_id(e) or e for e in args.knockout
                ],
                enzyme_factors=_parse_factor_args(args.factor),
                initial_conc_overrides=_parse_conc_args(args.conc),
            )
            print(
                f"Running what-if '{args.name}' ({args.mode.upper()})...",
                file=sys.stderr,
            )
            result = sim.run_whatif(config, scenario, mode=args.mode)
            text = render_whatif_result(result, store, top_n=args.top, markdown=markdown)

        else:
            print(f"Unknown subcommand: {args.subcommand}", file=sys.stderr)
            sys.exit(1)

    if args.output:
        out_path = Path(args.output)
        out_path.write_text(text, encoding="utf-8")
        print(f"Report written to {out_path}", file=sys.stderr)
    else:
        print(text)


# ---------------------------------------------------------------------------
# Aliases for pyproject.toml [tool.poetry.scripts]
# ---------------------------------------------------------------------------

main = build_main  # metakg-build points here
