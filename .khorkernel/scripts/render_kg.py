#!/usr/bin/env python3
# Khora Kernel - Render Knowledge Graph v1.0.2
# Visualizes the knowledge graph in various formats

import sys
import pathlib
import json
import argparse
from typing import Dict, Any, List, Optional, Tuple

# --- Python Version Check ---
if sys.version_info < (3, 8):
    print("Error: This script requires Python 3.8 or higher.", file=sys.stderr)
    sys.exit(1)

# --- Check for optional dependencies ---
RICH_AVAILABLE = False
GRAPHVIZ_AVAILABLE = False

try:
    import rich
    from rich.console import Console
    from rich.table import Table
    RICH_AVAILABLE = True
except ImportError:
    pass

try:
    import graphviz
    GRAPHVIZ_AVAILABLE = True
except ImportError:
    pass

# --- Configuration ---
KG_DIR = "kg"
CONCEPTS_FILE = "concepts.json"
RULES_FILE = "rules.json"
OUTPUT_DIR = "kg/visualizations"

# --- Helper Functions ---
def find_project_root(current_path: pathlib.Path) -> pathlib.Path:
    """Find the project root by looking for the kg directory or working backwards."""
    current = current_path.resolve()
    while current != current.parent:
        if (current / KG_DIR).is_dir():
            return current
        current = current.parent
    return current_path.resolve()


def load_knowledge_graph(root_dir: pathlib.Path) -> Tuple[Dict[str, Dict[str, str]], Dict[str, Dict[str, str]]]:
    """Load the concepts and rules from the KG files."""
    concepts_path = root_dir / KG_DIR / CONCEPTS_FILE
    rules_path = root_dir / KG_DIR / RULES_FILE
    
    concepts = {}
    rules = {}
    
    if concepts_path.exists():
        try:
            with open(concepts_path, 'r', encoding='utf-8') as f:
                concepts = json.load(f)
        except Exception as e:
            print(f"Error loading concepts: {e}", file=sys.stderr)
    else:
        print(f"Warning: Concepts file not found at {concepts_path}", file=sys.stderr)
    
    if rules_path.exists():
        try:
            with open(rules_path, 'r', encoding='utf-8') as f:
                rules = json.load(f)
        except Exception as e:
            print(f"Error loading rules: {e}", file=sys.stderr)
    else:
        print(f"Warning: Rules file not found at {rules_path}", file=sys.stderr)
    
    return concepts, rules


def render_as_table(concepts: Dict[str, Dict[str, str]], rules: Dict[str, Dict[str, str]]) -> None:
    """Render the knowledge graph as tables using rich if available, otherwise plain text."""
    if RICH_AVAILABLE:
        console = Console()
        
        # Concepts table
        if concepts:
            concepts_table = Table(title="Domain Concepts")
            concepts_table.add_column("Concept Name", style="cyan")
            concepts_table.add_column("Description", style="green")
            concepts_table.add_column("Source", style="dim")
            
            for name, data in sorted(concepts.items()):
                concepts_table.add_row(name, data.get('desc', ''), data.get('source', ''))
            
            console.print(concepts_table)
            console.print()
        else:
            console.print("No concepts found in the knowledge graph.", style="yellow")
        
        # Rules table
        if rules:
            rules_table = Table(title="Domain Rules")
            rules_table.add_column("Rule Name", style="magenta")
            rules_table.add_column("Description", style="green")
            rules_table.add_column("Source", style="dim")
            
            for name, data in sorted(rules.items()):
                rules_table.add_row(name, data.get('desc', ''), data.get('source', ''))
            
            console.print(rules_table)
        else:
            console.print("No rules found in the knowledge graph.", style="yellow")
    
    else:
        # Fallback to plain text rendering
        print("\n=== Domain Concepts ===\n")
        if concepts:
            max_name_len = max(len(name) for name in concepts.keys())
            for name, data in sorted(concepts.items()):
                print(f"{name.ljust(max_name_len)} - {data.get('desc', '')}")
                print(f"{' ' * max_name_len}   Source: {data.get('source', '')}")
                print()
        else:
            print("No concepts found in the knowledge graph.")
        
        print("\n=== Domain Rules ===\n")
        if rules:
            max_name_len = max(len(name) for name in rules.keys())
            for name, data in sorted(rules.items()):
                print(f"{name.ljust(max_name_len)} - {data.get('desc', '')}")
                print(f"{' ' * max_name_len}   Source: {data.get('source', '')}")
                print()
        else:
            print("No rules found in the knowledge graph.")


def render_as_graph(concepts: Dict[str, Dict[str, str]], rules: Dict[str, Dict[str, str]], 
                   output_dir: pathlib.Path, format: str = 'png') -> None:
    """Render the knowledge graph as a graphviz visualization."""
    if not GRAPHVIZ_AVAILABLE:
        print("Error: graphviz Python package is not installed. Install with 'pip install graphviz'.", file=sys.stderr)
        print("Note: This requires the Graphviz executable to be installed on your system as well.", file=sys.stderr)
        return
    
    try:
        # Create output directory if it doesn't exist
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create a new digraph
        dot = graphviz.Digraph('Knowledge_Graph', format=format)
        dot.attr('node', shape='box', style='filled', fontname='Arial')
        dot.attr('edge', fontname='Arial')
        dot.attr('graph', rankdir='TB')
        
        # Add concepts as nodes
        for name, data in concepts.items():
            # Truncate description if too long
            desc = data.get('desc', '')
            if len(desc) > 60:
                desc = desc[:57] + '...'
                
            label = f"{name}\n{desc}"
            dot.node(name, label=label, fillcolor='lightblue')
        
        # Add rules as nodes
        for name, data in rules.items():
            # Truncate description if too long
            desc = data.get('desc', '')
            if len(desc) > 60:
                desc = desc[:57] + '...'
                
            label = f"{name}\n{desc}"
            dot.node(name, label=label, fillcolor='lightpink')
        
        # Try to infer relationships between concepts and rules
        for rule_name, rule_data in rules.items():
            rule_desc = rule_data.get('desc', '').lower()
            
            # Link rule to concepts mentioned in its description
            for concept_name in concepts.keys():
                # Simple heuristic: if concept name (lowercased) is in rule description
                if concept_name.lower() in rule_desc:
                    dot.edge(rule_name, concept_name, label='applies to')
        
        # Render and save the graph
        output_path = output_dir / f"knowledge_graph"
        dot.render(output_path, view=False, cleanup=True)
        print(f"Graph visualization saved to {output_path}.{format}")
        
        # On some platforms, attempt to open the file
        try:
            import os
            import platform
            
            if platform.system() == 'Darwin':  # macOS
                os.system(f'open {output_path}.{format}')
            elif platform.system() == 'Windows':
                os.system(f'start {output_path}.{format}')
            elif platform.system() == 'Linux':
                os.system(f'xdg-open {output_path}.{format}')
        except Exception:
            pass
        
    except Exception as e:
        print(f"Error generating graph visualization: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()


def main():
    parser = argparse.ArgumentParser(description="Khora Kernel Knowledge Graph Visualizer")
    parser.add_argument(
        "--format", "-f",
        choices=["table", "graph"],
        default="table",
        help="Output format (table or graph)"
    )
    parser.add_argument(
        "--graph-format",
        choices=["png", "svg", "pdf"],
        default="png",
        help="Graph output format (png, svg, pdf) - only used with --format=graph"
    )
    parser.add_argument(
        "--output-dir", "-o",
        help="Output directory for graph visualizations",
        default=None
    )
    args = parser.parse_args()
    
    # Find project root and load knowledge graph
    root_dir = find_project_root(pathlib.Path(__file__).parent)
    concepts, rules = load_knowledge_graph(root_dir)
    
    if not concepts and not rules:
        print("No knowledge graph content found. Add [concept:Name] and [rule:Name] tags to your markdown files.")
        return
    
    # Set output directory
    if args.output_dir:
        output_dir = pathlib.Path(args.output_dir)
    else:
        output_dir = root_dir / OUTPUT_DIR
    
    # Render based on selected format
    if args.format == "table":
        if not RICH_AVAILABLE:
            print("Warning: rich package not installed. Falling back to plain text table.", file=sys.stderr)
            print("For prettier tables, install 'pip install rich'", file=sys.stderr)
        render_as_table(concepts, rules)
    elif args.format == "graph":
        if not GRAPHVIZ_AVAILABLE:
            print("Error: graphviz package not installed. Cannot generate graph visualization.", file=sys.stderr)
            print("For graph visualization, install both:")
            print("1. The Graphviz software: https://graphviz.org/download/")
            print("2. The Python package: pip install graphviz")
            print("Falling back to table format...")
            render_as_table(concepts, rules)
        else:
            render_as_graph(concepts, rules, output_dir, args.graph_format)


if __name__ == "__main__":
    main()