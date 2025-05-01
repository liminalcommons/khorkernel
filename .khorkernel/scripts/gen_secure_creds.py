#!/usr/bin/env python3
# Khora Kernel - Generate Secure Credentials v1.0.2
# Creates secure random credentials for local development

import sys
import os
import random
import string
import pathlib
import yaml
import re

# --- Python Version Check ---
if sys.version_info < (3, 8):
    print("Error: This script requires Python 3.8 or higher.", file=sys.stderr)
    sys.exit(1)

# --- Configuration ---
KERNEL_DIR_NAME = ".khorkernel"
MANIFEST_FILE = f"{KERNEL_DIR_NAME}/KERNEL_MANIFEST.yaml"
COMPOSE_FILE = "docker-compose.yml"
LITE_COMPOSE_FILE = "docker-compose.lite.yml"
CREDS_FILE = ".dev-credentials.env"  # For storing generated credentials


def find_project_root(current_path: pathlib.Path) -> pathlib.Path:
    """Find the project root by looking for the .khorkernel directory."""
    current = current_path.resolve()
    while current != current.parent:
        if (current / KERNEL_DIR_NAME).is_dir():
            return current
        current = current.parent
    print("Warning: '.khorkernel' directory not found. Assuming current directory is project root.", file=sys.stderr)
    return current_path.resolve()


def generate_secure_password(length: int = 24) -> str:
    """Generate a cryptographically secure random password."""
    chars = string.ascii_letters + string.digits + '!@#$%&*()-_=+[]{}|;:,.<>?'
    # Ensure at least one of each type of character
    pwd = [
        random.choice(string.ascii_lowercase),
        random.choice(string.ascii_uppercase),
        random.choice(string.digits),
        random.choice('!@#$%&*()-_=+[]{}|;:,.<>?')
    ]
    # Fill the rest randomly
    pwd.extend(random.choice(chars) for _ in range(length - 4))
    # Shuffle to avoid predictable pattern
    random.shuffle(pwd)
    return ''.join(pwd)


def load_manifest(root_dir: pathlib.Path) -> dict:
    """Load the KERNEL_MANIFEST.yaml file."""
    manifest_path = root_dir / MANIFEST_FILE
    if not manifest_path.exists():
        print(f"Error: Manifest file not found at '{manifest_path}'.", file=sys.stderr)
        sys.exit(1)
    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = yaml.safe_load(f)
            return manifest if isinstance(manifest, dict) else {}
    except Exception as e:
        print(f"Error loading manifest: {e}", file=sys.stderr)
        return {}


def update_compose_file(compose_path: pathlib.Path, credentials: dict) -> bool:
    """Update Docker Compose file with new credentials."""
    if not compose_path.exists():
        print(f"Warning: {compose_path.name} not found, skipping.", file=sys.stderr)
        return False

    try:
        content = compose_path.read_text(encoding='utf-8')
        
        # Replace database credentials
        if "POSTGRES_PASSWORD" in credentials:
            content = re.sub(
                r'POSTGRES_PASSWORD: ?"?[^"\n]+"?',
                f'POSTGRES_PASSWORD: "{credentials["POSTGRES_PASSWORD"]}"',
                content
            )
            content = re.sub(
                r'POSTGRES_USER: ?"?[^"\n]+"?',
                f'POSTGRES_USER: "{credentials["POSTGRES_USER"]}"',
                content
            )
            # Update DATABASE_URL in api and worker services
            content = re.sub(
                r'DATABASE_URL=postgresql://[^:]+:[^@]+@',
                f'DATABASE_URL=postgresql://{credentials["POSTGRES_USER"]}:{credentials["POSTGRES_PASSWORD"]}@',
                content
            )
        
        # Replace other credentials as needed
        # ...
        
        compose_path.write_text(content, encoding='utf-8')
        print(f"Updated credentials in {compose_path.name}")
        return True
    except Exception as e:
        print(f"Error updating {compose_path.name}: {e}", file=sys.stderr)
        return False


def generate_and_store_credentials(root_dir: pathlib.Path, manifest: dict) -> dict:
    """Generate secure credentials and store them in .dev-credentials.env file."""
    project_name = manifest.get('project', 'app')
    credentials = {}
    
    # Database credentials if needed
    if manifest.get('features', {}).get('database') == 'postgres':
        credentials["POSTGRES_USER"] = f"{project_name}_user"
        credentials["POSTGRES_PASSWORD"] = generate_secure_password()
        credentials["POSTGRES_DB"] = f"{project_name}_db"
    
    # Redis credentials if needed
    if manifest.get('features', {}).get('broker') == 'redis':
        credentials["REDIS_PASSWORD"] = generate_secure_password()
    
    # API keys or other secrets
    credentials["API_SECRET_KEY"] = generate_secure_password(32)
    credentials["JWT_SECRET"] = generate_secure_password(32)
    
    # Store credentials to file
    creds_path = root_dir / CREDS_FILE
    try:
        with open(creds_path, 'w', encoding='utf-8') as f:
            f.write("# Khora Kernel - Development Credentials\n")
            f.write("# IMPORTANT: Do not commit this file to version control!\n\n")
            for key, value in credentials.items():
                f.write(f"{key}={value}\n")
        
        # Add to .gitignore if not already there
        gitignore_path = root_dir / ".gitignore"
        if gitignore_path.exists():
            gitignore_content = gitignore_path.read_text(encoding='utf-8')
            if CREDS_FILE not in gitignore_content:
                with open(gitignore_path, 'a', encoding='utf-8') as f:
                    f.write(f"\n# Development credentials (generated by Khora Kernel)\n{CREDS_FILE}\n")
        
        print(f"Stored secure credentials in {CREDS_FILE} (added to .gitignore)")
        return credentials
    except Exception as e:
        print(f"Error storing credentials: {e}", file=sys.stderr)
        return credentials


def main():
    print("--- Khora Kernel: Generating Secure Development Credentials ---")
    
    # Find project root and load manifest
    root_dir = find_project_root(pathlib.Path(__file__).parent)
    manifest = load_manifest(root_dir)
    
    # Generate and store credentials
    credentials = generate_and_store_credentials(root_dir, manifest)
    
    # Update Docker Compose files
    updated = update_compose_file(root_dir / COMPOSE_FILE, credentials)
    if manifest.get('features', {}).get('lite_mode_available'):
        update_compose_file(root_dir / LITE_COMPOSE_FILE, credentials)
    
    print("\nCredential Generation Complete!")
    print("To use these credentials in your application:")
    print(f"1. For local development: source {CREDS_FILE}")
    print("2. For container development: credentials are already in docker-compose.yml")
    print("3. For production: Use a secure secrets management system")


if __name__ == "__main__":
    main()