"""Anneal CLI — anneal init, anneal serve."""

from __future__ import annotations

import argparse
import sys


def cmd_init(args: argparse.Namespace) -> None:
    """Build codebase graph and write config."""
    from pathlib import Path
    from anneal.indexer.graph_builder import build_graph

    project_root = Path(args.path).resolve()
    if not project_root.is_dir():
        print(f"Error: {project_root} is not a directory")
        sys.exit(1)

    result = build_graph(project_root)
    print(f"Indexed {result['file_count']} files → {result['node_count']} nodes, {result['edge_count']} edges")
    print(f"Languages: {', '.join(result['languages'])}")
    print(f"Graph: {result['db_path']}")
    print(f"Config: {result['config_path']}")
    print("Ready.")


def cmd_serve(args: argparse.Namespace) -> None:
    """Start the MCP server."""
    from anneal.server import main as server_main
    server_main()


def main() -> None:
    parser = argparse.ArgumentParser(prog="anneal", description="Optimal context selection for AI coding assistants")
    sub = parser.add_subparsers(dest="command")

    init_p = sub.add_parser("init", help="Build codebase graph and config")
    init_p.add_argument("path", nargs="?", default=".", help="Project root (default: current directory)")
    init_p.set_defaults(func=cmd_init)

    serve_p = sub.add_parser("serve", help="Start MCP server")
    serve_p.set_defaults(func=cmd_serve)

    args = parser.parse_args()
    if not hasattr(args, "func"):
        parser.print_help()
        sys.exit(1)
    args.func(args)


if __name__ == "__main__":
    main()
