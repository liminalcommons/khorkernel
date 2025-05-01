#!/usr/bin/env python3
# Khora Kernel - Generate Release Notes v1.0.2
# Creates a changelog based on git commit history

import sys
import os
import pathlib
import subprocess
import re
import datetime
import argparse
from typing import Dict, List, Any, Tuple, Optional

# --- Python Version Check ---
if sys.version_info < (3, 8):
    print("Error: This script requires Python 3.8 or higher.", file=sys.stderr)
    sys.exit(1)

# --- Configuration ---
KERNEL_DIR_NAME = ".khorkernel"
VERSION_FILE = f"{KERNEL_DIR_NAME}/VERSION"
CHANGELOG_FILE = "CHANGELOG.md"

# Regular expressions for conventional commits
CONVENTIONAL_COMMIT_PATTERN = re.compile(
    r'^(build|chore|ci|docs|feat|fix|perf|refactor|revert|style|test)(\([^)]+\))?:\s*(.*?)(\(\#\d+\))?$'
)

# Commit type to section mapping
SECTION_MAPPING = {
    'feat': '✨ Features',
    'fix': '🐛 Bug Fixes',
    'docs': '📚 Documentation',
    'chore': '🔧 Maintenance',
    'refactor': '♻️ Refactoring',
    'perf': '⚡ Performance',
    'test': '🧪 Tests',
    'build': '🏗️ Build System',
    'ci': '🔄 CI/CD',
    'style': '💄 Styling',
    'revert': '⏪ Reverts',
}

SECTION_ORDER = [
    '✨ Features',
    '🐛 Bug Fixes',
    '📚 Documentation',
    '♻️ Refactoring',
    '⚡ Performance',
    '🧪 Tests',
    '🔧 Maintenance',
    '🏗️ Build System',
    '🔄 CI/CD',
    '💄 Styling',
    '⏪ Reverts',
]


# --- Helper Functions ---
def find_project_root(current_path: pathlib.Path) -> pathlib.Path:
    """Find the project root by looking for git directory or .khorkernel."""
    current = current_path.resolve()
    while current != current.parent:
        if (current / ".git").is_dir() or (current / KERNEL_DIR_NAME).is_dir():
            return current
        current = current.parent
    return current_path.resolve()


def get_current_version(root_dir: pathlib.Path) -> str:
    """Get the current version from the VERSION file."""
    version_path = root_dir / VERSION_FILE
    if version_path.exists():
        return version_path.read_text().strip()
    else:
        # Try to infer from git tags
        try:
            tags = subprocess.run(
                ["git", "tag", "--sort=-v:refname"],
                capture_output=True,
                text=True,
                check=True
            ).stdout.strip().split('\n')
            
            for tag in tags:
                if tag.startswith('v') and re.match(r'v\d+\.\d+\.\d+', tag):
                    return tag.lstrip('v')
            
            return "unknown"
        except Exception:
            return "unknown"


def get_last_tag() -> Optional[str]:
    """Get the most recent git tag."""
    try:
        tag = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0"],
            capture_output=True,
            text=True,
            check=True
        ).stdout.strip()
        return tag
    except subprocess.CalledProcessError:
        # No tags found
        return None


def get_commits_since_tag(tag: Optional[str] = None) -> List[Dict[str, str]]:
    """Get all commits since the specified tag or all commits if no tag."""
    try:
        # Build the git log command
        cmd = ["git", "log", "--pretty=format:%H|||%s|||%an|||%ad|||%b", "--date=iso"]
        if tag:
            cmd.append(f"{tag}..HEAD")
        
        output = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        ).stdout.strip()
        
        if not output:
            return []
        
        commits = []
        for line in output.split('\n'):
            parts = line.split('|||')
            if len(parts) >= 5:
                commit = {
                    'hash': parts[0],
                    'subject': parts[1],
                    'author': parts[2],
                    'date': parts[3],
                    'body': parts[4]
                }
                commits.append(commit)
        
        return commits
    except subprocess.CalledProcessError as e:
        print(f"Error getting commits: {e.stderr}", file=sys.stderr)
        return []


def analyze_commit(commit: Dict[str, str]) -> Dict[str, Any]:
    """Parse a commit message and extract structured information."""
    subject = commit['subject']
    body = commit['body']
    
    # Try to parse as conventional commit
    match = CONVENTIONAL_COMMIT_PATTERN.match(subject)
    if match:
        commit_type, scope, message, issue_ref = match.groups()
        
        # Clean up values
        if scope:
            scope = scope[1:-1]  # Remove parentheses
        if issue_ref:
            issue_ref = issue_ref.strip()
        
        section = SECTION_MAPPING.get(commit_type, '🔧 Maintenance')
        
        # Extract breaking changes from body
        breaking_changes = []
        for line in body.split('\n'):
            if line.lower().startswith('breaking change:') or line.lower().startswith('breaking-change:'):
                breaking_changes.append(line)
        
        # Look for references in body text
        refs = []
        for line in body.split('\n'):
            refs.extend(re.findall(r'#(\d+)', line))
        
        return {
            'hash': commit['hash'],
            'type': commit_type,
            'scope': scope,
            'message': message,
            'section': section,
            'breaking_changes': breaking_changes,
            'refs': refs
        }
    else:
        # Non-conventional commit
        return {
            'hash': commit['hash'],
            'type': 'other',
            'scope': None,
            'message': subject,
            'section': '🔧 Maintenance',
            'breaking_changes': [],
            'refs': re.findall(r'#(\d+)', body)
        }


def group_commits_by_section(commits: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Group analyzed commits by their section."""
    sections = {section: [] for section in SECTION_ORDER}
    other_commits = []
    
    for commit in commits:
        section = commit['section']
        if section in sections:
            sections[section].append(commit)
        else:
            other_commits.append(commit)
    
    # Add any commits that didn't fit into predefined sections
    if other_commits:
        sections['🔧 Maintenance'].extend(other_commits)
    
    # Remove empty sections
    return {section: commits for section, commits in sections.items() if commits}


def format_changelog(version: str, date: str, grouped_commits: Dict[str, List[Dict[str, Any]]]) -> str:
    """Format the changelog text for the given version and commits."""
    lines = [
        f"# {version} ({date})",
        ""
    ]
    
    # Check for breaking changes across all commits
    breaking_changes = []
    for section_commits in grouped_commits.values():
        for commit in section_commits:
            if commit['breaking_changes']:
                breaking_changes.extend(commit['breaking_changes'])
    
    # Add breaking changes section if any found
    if breaking_changes:
        lines.append("## ⚠️ BREAKING CHANGES")
        lines.append("")
        for change in breaking_changes:
            lines.append(f"* {change}")
        lines.append("")
    
    # Add each section
    for section in SECTION_ORDER:
        if section in grouped_commits:
            commits = grouped_commits[section]
            lines.append(f"## {section}")
            lines.append("")
            
            for commit in commits:
                scope_text = f"**{commit['scope']}:** " if commit['scope'] else ""
                hash_short = commit['hash'][:7]
                message = commit['message']
                
                # Add references to issues
                if commit['refs']:
                    refs_text = " " + ", ".join(f"(#{ref})" for ref in commit['refs'])
                else:
                    refs_text = ""
                
                lines.append(f"* {scope_text}{message}{refs_text} ({hash_short})")
            
            lines.append("")
    
    return "\n".join(lines)


def generate_changelog(root_dir: pathlib.Path, new_version: Optional[str] = None) -> str:
    """Generate a changelog entry for the new version."""
    # Get current and previous versions
    current_version = get_current_version(root_dir)
    if new_version is None:
        new_version = current_version
    
    last_tag = get_last_tag()
    if last_tag:
        print(f"Generating changelog from {last_tag} to {new_version}")
    else:
        print("No previous tag found. Generating changelog from all commits.")
    
    # Get commits since last tag
    commits = get_commits_since_tag(last_tag)
    if not commits:
        print("No new commits found since last tag.")
        return ""
    
    # Analyze commits
    analyzed_commits = [analyze_commit(commit) for commit in commits]
    
    # Group by section
    grouped_commits = group_commits_by_section(analyzed_commits)
    
    # Generate changelog
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    return format_changelog(new_version, today, grouped_commits)


def update_changelog_file(root_dir: pathlib.Path, new_content: str, new_version: str) -> bool:
    """Update the CHANGELOG.md file with new content."""
    changelog_path = root_dir / CHANGELOG_FILE
    
    try:
        if changelog_path.exists():
            existing_content = changelog_path.read_text()
            
            # Check if version already exists in changelog
            if f"# {new_version}" in existing_content:
                print(f"Version {new_version} already exists in {CHANGELOG_FILE}")
                return False
            
            # Prepend new content to existing file
            with open(changelog_path, 'w') as f:
                f.write(new_content + "\n\n" + existing_content)
        else:
            # Create new changelog file
            with open(changelog_path, 'w') as f:
                f.write("# Changelog\n\n")
                f.write("All notable changes to this project will be documented in this file.\n\n")
                f.write(new_content)
        
        print(f"Updated {CHANGELOG_FILE} with changes for version {new_version}")
        return True
    
    except Exception as e:
        print(f"Error updating {CHANGELOG_FILE}: {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(description="Generate release notes for Khora Kernel")
    parser.add_argument(
        "--version", "-v",
        help="Version to use in the changelog (defaults to current version in VERSION file)"
    )
    parser.add_argument(
        "--output", "-o",
        help="Output file (defaults to CHANGELOG.md)",
        default=CHANGELOG_FILE
    )
    parser.add_argument(
        "--print",
        action="store_true",
        help="Print changelog to stdout instead of writing to file"
    )
    args = parser.parse_args()
    
    # Find project root
    root_dir = find_project_root(pathlib.Path(__file__).parent)
    print(f"Project root: {root_dir}")
    
    # Generate changelog
    changelog = generate_changelog(root_dir, args.version)
    if not changelog:
        print("No changelog content generated.")
        return
    
    # Output
    if args.print:
        print("\n" + changelog)
    else:
        output_path = args.output
        if not os.path.isabs(output_path):
            output_path = root_dir / output_path
        
        current_version = get_current_version(root_dir)
        version = args.version or current_version
        
        with open(output_path, 'w') as f:
            f.write(changelog)
        
        print(f"Changelog for version {version} written to {output_path}")


if __name__ == "__main__":
    main()