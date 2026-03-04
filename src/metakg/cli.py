"""
cli.py — Command-line entry points for MetaKG.

Commands
--------
metakg-build          Build the knowledge graph from a directory of pathway files.
metakg-mcp            Start the MCP server.
metakg-analyze        Run the thorough pathway analysis report.
metakg-analyze-basic  Run the basic structured analysis report.
metakg-simulate       Metabolic simulation (fba / ode / whatif / seed).
metakg-viz            Launch the 2D Streamlit explorer.
metakg-viz3d          Launch the 3D PyVista visualizer.

Author: Eric G. Suchanek, PhD
Last Revision: 2026-03-03

"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import click

from metakg.embed import DEFAULT_MODEL

# ---------------------------------------------------------------------------
# Shared utilities
# ---------------------------------------------------------------------------


def _timestamped_filename(basename: str = "metakg-analysis", ext: str = ".md") -> str:
    """Generate a timestamped filename: metakg-analysis-2026-03-01-143022.md"""
    ts = datetime.now().strftime("%Y-%m-%d-%H%M%S")
    return f"{basename}-{ts}{ext}"


def _parse_conc_args(conc_args: tuple[str, ...] | list[str]) -> dict[str, float]:
    """Parse ``ID:VALUE`` strings into a dict. Last colon-sep token is the value."""
    result: dict[str, float] = {}
    for item in conc_args:
        parts = item.rsplit(":", 1)
        if len(parts) == 2:
            try:
                result[parts[0]] = float(parts[1])
            except ValueError:
                click.echo(f"WARNING: ignoring bad --conc value: {item!r}", err=True)
    return result


def _parse_factor_args(factor_args: tuple[str, ...] | list[str]) -> dict[str, float]:
    """Parse ``ENZ_ID:FACTOR`` strings. Last colon-sep token is the factor."""
    return _parse_conc_args(factor_args)


# ---------------------------------------------------------------------------
# metakg-build
# ---------------------------------------------------------------------------


@click.command("metakg-build")
@click.option(
    "--data",
    required=True,
    help="Directory containing pathway files (KGML, SBML, BioPAX, CSV)",
)
@click.option(
    "--db",
    default=".metakg/meta.sqlite",
    show_default=True,
    help="Output SQLite database path",
)
@click.option(
    "--lancedb",
    default=".metakg/lancedb",
    show_default=True,
    help="Output LanceDB directory",
)
@click.option(
    "--model",
    default=DEFAULT_MODEL,
    show_default=True,
    help="Sentence-transformer model name",
)
@click.option("--no-index", is_flag=True, help="Skip building the LanceDB vector index")
@click.option("--wipe", is_flag=True, help="Wipe existing data before building")
@click.option(
    "--enrich",
    is_flag=True,
    help="Run name enrichment after building (Phase 1: always; Phase 2: if KEGG TSV files present)",
)
@click.option(
    "--enrich-data",
    default=None,
    metavar="DIR",
    help="Directory containing kegg_compound_names.tsv / kegg_reaction_names.tsv (default: data/)",
)
def build_main(
    data: str,
    db: str,
    lancedb: str,
    model: str,
    no_index: bool,
    wipe: bool,
    enrich: bool,
    enrich_data: str | None,
) -> None:
    """
    Build the MetaKG metabolic knowledge graph from pathway files.
    """
    data_dir = Path(data).resolve()
    if not data_dir.exists():
        raise click.ClickException(f"data directory not found: {data_dir}")

    from metakg import MetaKG

    kg = MetaKG(db_path=db, lancedb_dir=lancedb, model=model)
    click.echo(f"Building MetaKG from {data_dir}...", err=True)
    stats = kg.build(
        data_dir=data_dir,
        wipe=wipe,
        build_index=not no_index,
        enrich=enrich,
        enrich_data_dir=enrich_data,
    )
    click.echo(str(stats), err=True)

    if stats.parse_errors:
        click.echo(f"\n{len(stats.parse_errors)} file(s) failed to parse:", err=True)
        for err in stats.parse_errors:
            click.echo(f"  {err['file']}: {err['error']}", err=True)

    kg.close()


# ---------------------------------------------------------------------------
# metakg-mcp
# ---------------------------------------------------------------------------


@click.command("metakg-mcp")
@click.option(
    "--db",
    default=".metakg/meta.sqlite",
    show_default=True,
    help="Path to MetaKG SQLite database",
)
@click.option(
    "--lancedb",
    default=".metakg/lancedb",
    show_default=True,
    help="Path to LanceDB directory",
)
@click.option(
    "--model",
    default=DEFAULT_MODEL,
    show_default=True,
    help="Sentence-transformer model name",
)
@click.option(
    "--transport",
    default="stdio",
    show_default=True,
    type=click.Choice(["stdio", "sse"]),
    help="MCP transport: stdio or sse (HTTP)",
)
def mcp_main(db: str, lancedb: str, model: str, transport: str) -> None:
    """
    Start the MetaKG MCP server.
    """
    from metakg import MetaKG
    from metakg.mcp_tools import create_server

    db_path = Path(db)
    if not db_path.exists():
        click.echo(
            f"WARNING: database not found at '{db_path}'.\nRun 'metakg-build' first.",
            err=True,
        )

    click.echo(
        f"MetaKG MCP server starting\n"
        f"  db       : {db_path}\n"
        f"  lancedb  : {lancedb}\n"
        f"  model    : {model}\n"
        f"  transport: {transport}",
        err=True,
    )

    kg = MetaKG(db_path=db_path, lancedb_dir=lancedb, model=model)
    server = create_server(kg)
    server.run(transport=transport)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# metakg-enrich
# ---------------------------------------------------------------------------


@click.command("metakg-enrich")
@click.option(
    "--db",
    default=".metakg/meta.sqlite",
    show_default=True,
    help="Path to MetaKG SQLite database",
)
@click.option(
    "--data",
    default=None,
    metavar="DIR",
    help="Directory containing kegg_compound_names.tsv / kegg_reaction_names.tsv (default: data/)",
)
def enrich_main(db: str, data: str | None) -> None:
    """
    Enrich node names in an existing MetaKG database.

    Phase 1 (always): set reaction names from catalysing enzyme gene symbols
    using CATALYZES edges already in the graph — no network required.

    Phase 2 (when TSV files present): replace bare KEGG accessions with
    human-readable names from kegg_compound_names.tsv and
    kegg_reaction_names.tsv.  Download those files first with:

        python scripts/download_kegg_names.py
    """
    db_path = Path(db)
    if not db_path.exists():
        raise click.ClickException(f"database not found: {db_path}\nRun 'metakg-build' first.")

    from metakg import MetaKG

    click.echo(f"Enriching node names in {db_path}...", err=True)
    with MetaKG(db_path=db_path) as kg:
        stats = kg.enrich(data_dir=data)
    click.echo(str(stats), err=True)


# ---------------------------------------------------------------------------
# metakg-viz
# ---------------------------------------------------------------------------


@click.command("metakg-viz")
def viz_main() -> None:
    """
    Launch the Streamlit 2D metabolic knowledge-graph explorer.

    Argument parsing is handled by :mod:`metakg.metakg_viz`.
    """
    from metakg.metakg_viz import main as viz_main_func

    viz_main_func()


# ---------------------------------------------------------------------------
# metakg-viz3d
# ---------------------------------------------------------------------------


@click.command("metakg-viz3d")
def viz3d_main() -> None:
    """
    Launch the 3D PyVista metabolic knowledge-graph visualizer.

    Argument parsing is handled by :mod:`metakg.metakg_viz3d`.
    """
    from metakg.metakg_viz3d import main as viz3d_main_func

    viz3d_main_func()


# ---------------------------------------------------------------------------
# metakg-analyze
# ---------------------------------------------------------------------------


@click.command("metakg-analyze")
@click.option(
    "--db",
    default=".metakg/meta.sqlite",
    show_default=True,
    help="Path to MetaKG SQLite database",
)
@click.option(
    "--output",
    "-o",
    default=None,
    metavar="FILE",
    help="Write Markdown report to FILE (default: timestamped filename)",
)
@click.option(
    "--top",
    default=20,
    show_default=True,
    type=int,
    metavar="N",
    help="Number of items in each ranked list",
)
@click.option("--plain", is_flag=True, help="Plain-text output instead of Markdown")
def analyze_main(db: str, output: str | None, top: int, plain: bool) -> None:
    """
    Thorough metabolic pathway analysis report.

    Identifies hub metabolites, complex reactions, cross-pathway connections,
    pathway coupling, dead-end metabolites, and top enzymes.
    Writes to a timestamped file by default (e.g. metakg-analysis-2026-03-01-143022.md).
    """
    db_path = Path(db)
    if not db_path.exists():
        raise click.ClickException(f"database not found: {db_path}\nRun 'metakg-build' first.")

    from metakg.analyze import PathwayAnalyzer
    from metakg.thorough_analysis import render_thorough_report

    click.echo(f"Analysing {db_path} ...", err=True)
    with PathwayAnalyzer(db_path, top_n=top) as analyzer:
        report = analyzer.run()

    text = render_thorough_report(report, markdown=not plain)

    out_path = Path(output or _timestamped_filename("metakg-analysis"))
    out_path.write_text(text, encoding="utf-8")
    click.echo(f"Report written to {out_path}", err=True)


@click.command("metakg-analyze-basic")
@click.option(
    "--db",
    default=".metakg/meta.sqlite",
    show_default=True,
    help="Path to MetaKG SQLite database",
)
@click.option(
    "--output",
    "-o",
    default=None,
    metavar="FILE",
    help="Write Markdown report to FILE (default: timestamped filename)",
)
@click.option(
    "--top",
    default=20,
    show_default=True,
    type=int,
    metavar="N",
    help="Number of items in each ranked list",
)
@click.option("--plain", is_flag=True, help="Plain-text output instead of Markdown")
def analyze_basic_main(db: str, output: str | None, top: int, plain: bool) -> None:
    """
    Basic structured analysis report: facts, ranked lists, minimal narrative.

    Writes to a timestamped file by default (e.g. metakg-analysis-basic-2026-03-01-143022.md).
    """
    db_path = Path(db)
    if not db_path.exists():
        raise click.ClickException(f"database not found: {db_path}\nRun 'metakg-build' first.")

    from metakg.analyze import PathwayAnalyzer, render_report

    click.echo(f"Analysing {db_path} ...", err=True)
    with PathwayAnalyzer(db_path, top_n=top) as analyzer:
        report = analyzer.run()

    text = render_report(report, markdown=not plain)

    out_path = Path(output or _timestamped_filename("metakg-analysis-basic"))
    out_path.write_text(text, encoding="utf-8")
    click.echo(f"Report written to {out_path}", err=True)


# ---------------------------------------------------------------------------
# metakg-simulate  (Click group with fba / ode / whatif / seed subcommands)
# ---------------------------------------------------------------------------


@click.group("metakg-simulate")
@click.option(
    "--db",
    default=".metakg/meta.sqlite",
    show_default=True,
    help="Path to MetaKG SQLite database",
)
@click.option(
    "--output",
    "-o",
    default=None,
    metavar="FILE",
    help="Write Markdown report to FILE (default: timestamped filename)",
)
@click.option("--plain", is_flag=True, help="Plain-text output instead of Markdown")
@click.option(
    "--top",
    default=25,
    show_default=True,
    type=int,
    metavar="N",
    help="Maximum items to list in each table",
)
@click.pass_context
def simulate_main(ctx: click.Context, db: str, output: str | None, plain: bool, top: int) -> None:
    """
    Metabolic simulation for MetaKG: FBA, ODE kinetics, and what-if analysis.
    """
    ctx.ensure_object(dict)
    ctx.obj.update({"db": db, "output": output, "plain": plain, "top": top})


@simulate_main.command("fba")
@click.option(
    "--pathway",
    "-p",
    default=None,
    help="Pathway node ID or name (e.g. pwy:kegg:hsa00010 or 'Glycolysis')",
)
@click.option(
    "--objective",
    default=None,
    metavar="RXN_ID",
    help="Reaction ID to optimise (default: maximise total forward flux)",
)
@click.option("--minimize", is_flag=True, help="Minimise rather than maximise the objective")
@click.pass_obj
def simulate_fba(obj: dict, pathway: str | None, objective: str | None, minimize: bool) -> None:
    """
    Flux Balance Analysis — steady-state optimal flux distribution.
    """
    db_path = Path(obj["db"])
    if not db_path.exists():
        raise click.ClickException(f"database not found: {db_path}\nRun 'metakg-build' first.")

    from metakg import MetaKG
    from metakg.simulate import SimulationConfig, render_fba_result

    with MetaKG(db_path=db_path) as kg:
        store = kg.store
        pathway_id = store.resolve_id(pathway) if pathway else None
        config = SimulationConfig(
            pathway_id=pathway_id,
            objective_reaction=objective,
            maximize=not minimize,
        )
        click.echo("Running FBA...", err=True)
        result = kg.simulator.run_fba(config)
        text = render_fba_result(result, store, top_n=obj["top"], markdown=not obj["plain"])

    _write_output(text, obj["output"], "metakg-simulate-fba")


@simulate_main.command("ode")
@click.option(
    "--pathway",
    "-p",
    default=None,
    help="Pathway node ID or name",
)
@click.option(
    "--time",
    "-t",
    default=100.0,
    show_default=True,
    type=float,
    help="Simulation end time (arbitrary units)",
)
@click.option(
    "--points",
    default=500,
    show_default=True,
    type=int,
    help="Number of time points to sample",
)
@click.option(
    "--conc",
    multiple=True,
    metavar="ID:VALUE",
    help="Set initial concentration for a compound: e.g. --conc cpd:kegg:C00031:5.0  (repeatable)",
)
@click.option(
    "--default-conc",
    default=1.0,
    show_default=True,
    type=float,
    metavar="MM",
    help="Default initial concentration in mM for all compounds",
)
@click.pass_obj
def simulate_ode(
    obj: dict,
    pathway: str | None,
    time: float,
    points: int,
    conc: tuple[str, ...],
    default_conc: float,
) -> None:
    """
    ODE kinetic simulation — concentration time-courses via Michaelis-Menten.
    """
    db_path = Path(obj["db"])
    if not db_path.exists():
        raise click.ClickException(f"database not found: {db_path}\nRun 'metakg-build' first.")

    from metakg import MetaKG
    from metakg.simulate import SimulationConfig, render_ode_result

    with MetaKG(db_path=db_path) as kg:
        store = kg.store
        pathway_id = store.resolve_id(pathway) if pathway else None
        config = SimulationConfig(
            pathway_id=pathway_id,
            t_end=time,
            t_points=points,
            initial_concentrations=_parse_conc_args(conc),
            default_concentration=default_conc,
        )
        click.echo(f"Running ODE (t=0..{time}, {points} pts)...", err=True)
        result = kg.simulator.run_ode(config)
        text = render_ode_result(result, store, top_n=obj["top"], markdown=not obj["plain"])

    _write_output(text, obj["output"], "metakg-simulate-ode")


@simulate_main.command("whatif")
@click.option("--pathway", "-p", default=None, help="Pathway node ID or name")
@click.option(
    "--mode",
    default="fba",
    show_default=True,
    type=click.Choice(["fba", "ode"]),
    help="Simulation mode",
)
@click.option(
    "--knockout",
    multiple=True,
    metavar="ENZ_ID",
    help="Enzyme node ID to knock out (repeatable)",
)
@click.option(
    "--factor",
    multiple=True,
    metavar="ENZ_ID:FACTOR",
    help="Scale enzyme activity: e.g. --factor enz:kegg:hsa:2538:0.5  (repeatable)",
)
@click.option(
    "--conc",
    multiple=True,
    metavar="ID:VALUE",
    help="Override initial compound concentration for ODE mode: ID:mM (repeatable)",
)
@click.option(
    "--name",
    default="whatif_scenario",
    show_default=True,
    help="Scenario label for the report",
)
@click.option(
    "--time",
    "-t",
    default=100.0,
    show_default=True,
    type=float,
    help="ODE end time (ignored for FBA)",
)
@click.pass_obj
def simulate_whatif(
    obj: dict,
    pathway: str | None,
    mode: str,
    knockout: tuple[str, ...],
    factor: tuple[str, ...],
    conc: tuple[str, ...],
    name: str,
    time: float,
) -> None:
    """
    Perturbation / what-if analysis — baseline vs. modified scenario.
    """
    db_path = Path(obj["db"])
    if not db_path.exists():
        raise click.ClickException(f"database not found: {db_path}\nRun 'metakg-build' first.")

    from metakg import MetaKG
    from metakg.simulate import SimulationConfig, WhatIfScenario, render_whatif_result

    with MetaKG(db_path=db_path) as kg:
        store = kg.store
        pathway_id = store.resolve_id(pathway) if pathway else None
        config = SimulationConfig(pathway_id=pathway_id, t_end=time)
        scenario = WhatIfScenario(
            name=name,
            enzyme_knockouts=[store.resolve_id(e) or e for e in knockout],
            enzyme_factors=_parse_factor_args(factor),
            initial_conc_overrides=_parse_conc_args(conc),
        )
        click.echo(f"Running what-if '{name}' ({mode.upper()})...", err=True)
        result = kg.simulator.run_whatif(config, scenario, mode=mode)
        text = render_whatif_result(result, store, top_n=obj["top"], markdown=not obj["plain"])

    _write_output(text, obj["output"], "metakg-simulate-whatif")


@simulate_main.command("seed")
@click.option("--force", is_flag=True, help="Overwrite existing kinetic parameter rows")
@click.pass_obj
def simulate_seed(obj: dict, force: bool) -> None:
    """
    Seed kinetic parameters from curated literature values (BRENDA, SABIO-RK).
    """
    db_path = Path(obj["db"])
    if not db_path.exists():
        raise click.ClickException(f"database not found: {db_path}\nRun 'metakg-build' first.")

    from metakg import MetaKG

    click.echo(f"Seeding kinetic parameters into {db_path}...", err=True)
    with MetaKG(db_path=db_path) as kg:
        result = kg.seed_kinetics(force=force)
    n_kp = result["kinetic_params_written"]
    n_ri = result["regulatory_interactions_written"]
    click.echo(
        f"Done. Wrote {n_kp} kinetic parameter row(s) and {n_ri} regulatory interaction row(s).",
        err=True,
    )


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------


def _write_output(text: str, output: str | None, basename: str) -> None:
    """Write *text* to *output* path (or a timestamped default) and report to stderr."""
    out_path = Path(output or _timestamped_filename(basename))
    out_path.write_text(text, encoding="utf-8")
    click.echo(f"Report written to {out_path}", err=True)


# ---------------------------------------------------------------------------
# Aliases for pyproject.toml [tool.poetry.scripts]
# ---------------------------------------------------------------------------

main = build_main  # metakg-build points here
