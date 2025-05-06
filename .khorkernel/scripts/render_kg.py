#!/usr/bin/env python3
"""
Khora Kernel – KG renderer (v1.0.2)

Usage:
  python .khorkernel/scripts/render_kg.py --format table
  python .khorkernel/scripts/render_kg.py --format graph
"""
import argparse, json, pathlib, sys
from rich.console import Console
from rich.table import Table

ROOT = pathlib.Path(__file__).resolve().parents[2]
KG_DIR = ROOT / "kg"

def load(path: pathlib.Path):
    try:
        return json.loads(path.read_text("utf-8"))
    except FileNotFoundError:
        print(f"[!] {path} not found", file=sys.stderr)
        return {}

def render_table():
    concepts = load(KG_DIR / "concepts.json")
    rules    = load(KG_DIR / "rules.json")

    console = Console()
    table = Table(title="Knowledge Graph – Concepts / Rules", show_lines=True)
    table.add_column("Type", style="cyan", no_wrap=True)
    table.add_column("Name", style="bold")
    table.add_column("Description", style="")
    table.add_column("Source", style="dim")

    for name, meta in concepts.items():
        table.add_row("concept", name, meta["desc"], meta["source"])
    for name, meta in rules.items():
        table.add_row("rule", name, meta["desc"], meta["source"])

    console.print(table)

def render_graph():
    """Render knowledge graph in DOT format using graphviz if available."""
    # Try to import graphviz, print a friendly message if not installed
    try:
        import graphviz
    except ImportError:
        print("Graphviz Python library not installed. Install it with:")
        print("  pip install graphviz")
        print("Note: You also need the Graphviz binary (https://graphviz.org/download/) for rendering.")
        return

    # Load concepts and rules
    concepts = load(KG_DIR / "concepts.json")
    rules = load(KG_DIR / "rules.json")
    
    if not concepts and not rules:
        print("No concepts or rules found in knowledge graph.")
        return

    # Create a new graph
    g = graphviz.Digraph(comment='Knowledge Graph')
    
    # Add concept nodes (boxes)
    for name in concepts:
        g.node(name, shape="box")
    
    # Add rule nodes (ellipses)
    for name in rules:
        g.node(name, shape="ellipse")
    
    # Print the DOT source
    print(g.source)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--format", choices=["table", "graph"], default="table")
    args = ap.parse_args()

    if args.format == "table":
        render_table()
    else:
        render_graph()
