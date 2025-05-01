# Kernel Universal Principles v1.0

These principles guide the design and evolution of the Khora Kernel. They prioritize efficiency and robustness, especially for small teams and solo developers leveraging AI.

1.  **Reproducibility First:** Every environment (dev, CI, staging, prod) and build MUST be recreatable from version-controlled code and configuration alone. No manual steps, no hidden dependencies. *(`docker-compose.yml`, CI definitions)*

2.  **Observability is Not Optional:** Foundational metrics, traces, and structured logs MUST be available from the very first commit. Debugging distributed systems without observability is prohibitively expensive. *(Pre-wired Prometheus/OTEL in Compose, JSON logging patterns encouraged)*

3.  **Security by Default:** Basic security checks (dependency vulnerabilities, leaked secrets, common code flaws) MUST run automatically and early in the development cycle ("shift-left"). *(`pip-audit`, `trufflehog`, `bandit` in CI/pre-commit)*

4.  **Traceability Everywhere:** Every code change SHOULD link clearly to a requirement (Issue), a review process (PR), and potentially the AI prompt context that influenced it. Every runtime request SHOULD be traceable across services. *(Issue/PR templates, context hash, OTEL)*

5.  **Explicit Configuration:** Project structure, features, and infrastructure choices MUST be declared explicitly in a machine-readable format. Avoid implicit conventions where possible. *(KERNEL_MANIFEST.yaml drives generation)*

6.  **AI-Ready Context:** Key project metadata (structure, features, domain concepts, rules) MUST be easily serializable and digestible by AI agents to maximize their effectiveness and minimize redundant prompting. *(`context.yaml`, `kg/*.json`)*

7.  **Minimal Footprint:** The kernel itself SHOULD remain lightweight and introduce minimal runtime dependencies. Complexity is opt-in via the manifest or plugins. *(Focus on generation, standard tools)*