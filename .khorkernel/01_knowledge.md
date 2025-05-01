# Knowledge Graph Markdown Reference v1.0

The Khora Kernel includes scripts to automatically build a simple Knowledge Graph (KG) directly from your Markdown documentation (`*.md` files, typically in the `docs_dir` specified in the manifest, or the project root). This KG feeds into the `context.yaml` file, enhancing the understanding of AI partners.

## Syntax

Use simple inline tags followed by a description using `–` (em dash or hyphen):
```markdown
This document describes the core User management system.

[concept:UserAccount] – Represents a registered user in the system. It holds authentication credentials and profile information.

[concept:UserProfile] – Contains non-authentication details about a user, like display name and bio. Linked to a UserAccount.

[rule:UniqueEmail] – Each UserAccount must have a globally unique email address. This is enforced at the database level.

[rule:PasswordComplexity] – User passwords must meet minimum complexity requirements (length, character types). Checked during signup and password change.

We also handle [concept:AuthToken] – Time-limited tokens used for session management after login.
```

## Tag Types

*   `[concept:Name]`
    *   Identifies a key noun, entity, or abstract idea within your domain.
    *   Use `CamelCase` for the `Name`.
    *   The description should explain what the concept *is*.
*   `[rule:Name]`
    *   Identifies a business rule, constraint, invariant, or operational policy.
    *   Use `CamelCase` for the `Name`.
    *   The description should explain what the rule *enforces* or *dictates*.

## How it Works

1.  **Write Docs:** Create or edit `.md` files in your project (primarily within the directory specified by `paths.docs_dir` in `KERNEL_MANIFEST.yaml`, though the script often scans the whole repo).
2.  **Add Tags:** Sprinkle `[concept:...]` and `[rule:...]` tags where relevant in your documentation.
3.  **Run Script:**
    *   The `populate_kg.py` script is automatically run by the `pre-commit` hook (if installed).
    *   You can also run it manually: `python .khorkernel/scripts/populate_kg.py`
4.  **Output:** The script generates/updates:
    *   `kg/concepts.json`: A JSON object mapping concept names to their descriptions and source file.
    *   `kg/rules.json`: A JSON object mapping rule names to their descriptions and source file.
5.  **Context Update:** The `gen_context.py` script (also run via pre-commit or manually) reads these generated files and includes a hash or summary in `.khora/context.yaml`.
6.  **Visualize:** Use `render_kg.py` to visualize your knowledge graph as a table or graphical format.

## Best Practices

*   **Be Descriptive:** Write clear, concise descriptions for each tag.
*   **Be Consistent:** Use the same name for the same concept/rule across your docs.
*   **Focus on Core Domain:** Tag the most important elements of your application's domain logic and structure.
*   **Integrate Naturally:** Place tags within your existing documentation rather than creating separate "KG files."
*   **Keep it Updated:** As your design evolves, update the tags in your Markdown files. Pre-commit hooks help enforce this.