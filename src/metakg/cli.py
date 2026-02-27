"""
cli.py — Command-line entry points for MetaKG.

Commands
--------
metakg-build   Build the knowledge graph from a directory of pathway files.
metakg-mcp     Start the MCP server.
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
# Aliases for pyproject.toml [tool.poetry.scripts]
# ---------------------------------------------------------------------------

main = build_main  # metakg-build points here
