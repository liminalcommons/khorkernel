# Khora Kernel v1.0.2 – reproducible · secure · AI-ready

<p align="center">
  <!-- Optional: <img width="140" src="URL_TO_YOUR_LOGO.svg" alt="Khora Kernel Logo"> -->
</p>

**One copy → one command → one green CI pipeline.**

`Khora-Kernel` is a drop-in folder that instantly scaffolds a new project with best practices, designed for solo developers working alongside AI partners. Get **Sprint-0 backlog, green CI, a Docker stack, security gates, and a machine-readable context graph** – all in under **5 minutes**.

**Requires Python >= 3.8.**

---

## 🔥 Why you'll love it

| ✅ Out-of-the-box                     | 🔧 Toggle via `KERNEL_MANIFEST.yaml` |
| :------------------------------------ | :------------------------------------- |
| GitHub Issue & PR templates           | Broker: `redis` / `listen_notify` / `none` |
| CI: Lint, Typecheck, Security Scans   | Database: `postgres` / `sqlite` / `none` |
| Docker Compose Stack (API/Worker/DB/...) | Observability: `true` / `false`        |
| Knowledge Graph Generator (`kg/*.json`) | API/Worker code paths & ports        |
| AI Context File (`.khora/context.yaml`) | Bounded Contexts list                |
| Pre-commit Hooks (formatting, KG)     | Plugins: `terraform`, `playwright`, etc. |
| Lite-Mode for Laptop Development     | Security Gates: `true` / `false`       |

---

## 🚀 Quick Start

**Inside a fresh repository:**

1.  **Get the Kernel:**
    *   **Option A (Clone):**
        ```bash
        # Clone the kernel source repo (replace URL)
        git clone https://github.com/your-org/khora-kernel.git khora-kernel-source
        # Copy the kernel folder into your new project
        cp -R khora-kernel-source/.khorkernel ./your-new-project/.khorkernel
        cd ./your-new-project
        ```
    *   **Option B (Submodule - Advanced):**
        ```bash
        cd ./your-new-project
        git submodule add https://github.com/your-org/khora-kernel.git .khorkernel
        git submodule update --init --recursive
        ```
    *   **Option C (Download/Extract):** Download the `.zip` or `.tar.gz` from the kernel repository's releases page and extract the `.khorkernel` folder into your project root.

2.  **(Optional) Configure:**
    ```bash
    # Review and adjust features for your project
    vim .khorkernel/KERNEL_MANIFEST.yaml
    ```

3.  **Bootstrap:**
    ```bash
    # Install kernel dependencies (recommended)
    pip install -r .khorkernel/requirements-kernel.txt
    
    # Installs hooks, renders templates, creates Sprint-0 issues, makes initial commit
    python .khorkernel/scripts/bootstrap_backlog.py
    ```
    *   **Requirements:** `git`, `python3 >= 3.8`, `pip`.
    *   **Required Python packages:** See `requirements-kernel.txt`. The bootstrap script will attempt to install these if missing.
    *   **Required CLI tools:** `gh` (GitHub CLI) - **must be installed and authenticated (`gh auth login`)**.
    *   The script will attempt to install `pre-commit` via pip if not found.

4.  **Install Pre-commit Hooks (if not done by bootstrap):**
    ```bash
    # Ensure pre-commit is installed (pip install pre-commit)
    pre-commit install
    ```

5.  **Push:**
    ```bash
    git push origin main # Or your default branch
    ```

**Outcome:**

*   ✅ **Sprint-0 Issues** created in your GitHub repository.
*   ✅ **CI Pipeline** triggered (`.github/workflows/`), building images, running checks, and uploading `context.yaml`.
    *   The `context-delta.yml` workflow detects and comments on changes to the AI context in PRs.
*   ✅ **`.khora/context.yaml`** generated and committed, ready for AI ingestion.
*   ✅ **`docker-compose.yml`** generated based on your manifest.
*   ✅ **Local environment** ready:
    * `docker compose up` for full stack 
    * `docker compose --profile lite up` for lightweight development
    * **⚠️ Security Note:** The generated `docker-compose.yml` uses plain text passwords for local development convenience. Use `scripts/gen_secure_creds.py` to generate better local development credentials, and always use secrets management in production.
*   ✅ **`.gitignore`** updated with `.khora/` and `kg/`.

---

## 🧠 How AI Sees Your Project

The kernel automatically generates and maintains context files crucial for AI partners:

`.khora/context.yaml`   ← **Primary:** Machine-readable project capsule (features, infra, paths, contexts).  
`kg/concepts.json`      ← Domain vocabulary extracted from your Markdown ([concept:...]).  
`kg/rules.json`         ← Business rules extracted from your Markdown ([rule:...]).  
`docker-compose.yml`    ← Runtime service graph.  
`.github/workflows/*`   ← CI rules & process definitions.  

An LLM agent can load `.khora/context.yaml` to instantly understand the project's structure, features, and conventions without parsing vast amounts of code or documentation. See `01_knowledge.md` for how to populate the Knowledge Graph.

You can visualize your knowledge graph anytime with:
```bash
python .khorkernel/scripts/render_kg.py --format table  # Or --format graph
```

---

## 🛠 Customizing After Bootstrap

*   **Change Features:** Edit `.khorkernel/KERNEL_MANIFEST.yaml`.
*   **Re-render Templates:** Run `python .khorkernel/scripts/bootstrap_backlog.py --regenerate-only`. This updates `docker-compose.yml` and CI workflows without touching issues or commits.
*   **Update Knowledge Graph:** Edit your Markdown files (`*.md` in `docs_dir` or project root) and run `pre-commit run populate-kg -a` or `python .khorkernel/scripts/populate_kg.py`.
*   **Update Context:** Run `python .khorkernel/scripts/gen_context.py` after KG or manifest changes.
*   **Generate Secure Credentials:** Run `python .khorkernel/scripts/gen_secure_creds.py` to create safer dev credentials.
*   **Self-Test Kernel Integrity:** Run `python .khorkernel/scripts/self_test.py` to verify kernel files.
*   **Generate Release Notes:** Run `python .khorkernel/scripts/gen_release_notes.py` to create a changelog.

---

## 🔌 Plugins

Extend kernel functionality by adding modules to the `.khorkernel/plugins/` directory and listing them in `KERNEL_MANIFEST.yaml`. Available plugins:

* **terraform**: Scaffolds basic Terraform infrastructure (AWS ECS + RDS)
* **playwright**: Adds browser testing capabilities and GitHub workflows

See `.khorkernel/plugins/README.md` for details on available plugins or how to create your own.

---

## 🧭 Core Principles

See `00_principles.md` for the guiding philosophy behind the Kernel.

---

## 🤝 Contributing to the Kernel

(Instructions for improving the kernel *itself*)

1.  Open an Issue in the Kernel's source repository tagged `type:kernel`.
2.  Make changes **only inside the `.khorkernel/` directory** of the source repo.
3.  Test changes thoroughly (e.g., using the `self_test.py` script).
4.  Submit a Pull Request.

---

## 📄 License

MIT License – Use freely, modify, distribute. Attribution appreciated but not required.

---

> *Built for developers who'd rather ship features than configure boilerplate.*