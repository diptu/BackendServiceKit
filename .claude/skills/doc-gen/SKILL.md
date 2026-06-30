---
name: doc-gen
description: This protocol defines the standardized procedure for generating, managing, and maintaining documentation for services using the Docs-as-Code approach with MkDocs. It enforces a strict separation between internal engineering intelligence (ADRs, infrastructure) and public-facing product documentation.
---

# Enterprise Doc-Gen Protocol

## Execution
Run the following command in the service root:
`python3 scripts/doc-gen.py <service_name> --scope <internal|public>`

## Constraints & Rules
1. **Boundary**: Never scan or document files outside the `services/<service_name>/` directory.
2. **Security**: Internal-only content (ADRs, infrastructure diagrams, security specs) must reside in `/internal/` directories.
3. **Format**: Use Markdown. Diagrams must be authored in **Mermaid.js** format to ensure version-controlled diffs.
4. **Source of Truth**: The generated documentation in the `docs/` folder is the official documentation; local `README.md` files should act only as gateways linking to the central portal.

## Workflow Steps

### 1. Ingestion
- Scan `services/<service_name>/app/api/` for endpoints.
- Parse existing `services/<service_name>/docs/` for contextual metadata.

### 2. Classification & Filtering
- **If `--scope public`**: 
    - Strip all files containing `ADR`, `internal`, or `infrastructure/` tags.
    - Generate sanitized API references and user guides.
- **If `--scope internal`**: 
    - Collate all technical documentation including ADRs, NFRs, and architecture diagrams.

### 3. Synthesis
- Dynamically update the `mkdocs.yml` navigation structure based on the identified scope.
- Convert legacy `.png` assets into embedded Mermaid.js diagrams to enable `git diff` capabilities.

### 4. Deployment Verification
- CI/CD pipelines must validate the build output to ensure no files from `/internal` are present in the `/public` artifact deployment.

## ADR Template (For Internal Documentation)
Every architectural decision must be logged using the following structure:
- **Context**: The technical problem or constraints.
- **Decision**: The selected solution.
- **Consequences**: Trade-offs, latency impact, or hardware requirements.

---
*Maintained by Engineering Excellence Team.*