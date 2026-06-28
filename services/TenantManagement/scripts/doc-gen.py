#!/usr/bin/env python3
"""
doc-gen.py — Generate MkDocs documentation for a BackendServiceKit service.

Parses FastAPI router files via AST (no service imports required), filters
endpoints by scope, and writes structured Markdown under docs/<scope>/.
Regenerates api-reference.md and mkdocs.yml on every run; hand-authored pages
(index.md, getting-started.md, state-machine.md) are preserved.

Usage (from service root):
    python3 scripts/doc-gen.py TenantManagement --scope public
    python3 scripts/doc-gen.py TenantManagement --scope internal
"""

from __future__ import annotations

import argparse
import ast
import sys
from dataclasses import dataclass, field
from pathlib import Path
from textwrap import dedent

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

HTTP_METHODS = {"get", "post", "patch", "put", "delete"}


@dataclass
class Endpoint:
    method: str
    path: str
    summary: str
    description: str
    tags: list[str] = field(default_factory=list)
    status_code: int | str = 200


# ---------------------------------------------------------------------------
# AST helpers
# ---------------------------------------------------------------------------


def _const(node: ast.expr) -> str | int | float | None:
    if isinstance(node, ast.Constant):
        return node.value
    return None


def _str_list(node: ast.expr) -> list[str]:
    if isinstance(node, ast.List):
        return [e.value for e in node.elts if isinstance(e, ast.Constant) and isinstance(e.value, str)]
    return []


def _parse_file(path: Path) -> list[Endpoint]:
    try:
        tree = ast.parse(path.read_text())
    except SyntaxError:
        return []

    # Find router-level prefix and tags from: router = APIRouter(prefix=..., tags=[...])
    router_prefix = ""
    router_tags: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        val = node.value
        if not isinstance(val, ast.Call):
            continue
        fn = val.func
        fn_name = fn.id if isinstance(fn, ast.Name) else (fn.attr if isinstance(fn, ast.Attribute) else "")
        if fn_name != "APIRouter":
            continue
        for kw in val.keywords:
            if kw.arg == "prefix":
                v = _const(kw.value)
                if v is not None:
                    router_prefix = str(v)
            elif kw.arg == "tags":
                router_tags = _str_list(kw.value)

    endpoints: list[Endpoint] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for dec in node.decorator_list:
            if not isinstance(dec, ast.Call):
                continue
            fn = dec.func
            if not isinstance(fn, ast.Attribute) or fn.attr not in HTTP_METHODS:
                continue

            # Path — first positional arg
            ep_path = ""
            if dec.args:
                v = _const(dec.args[0])
                if v is not None:
                    ep_path = str(v)

            kw_map: dict[str, object] = {}
            for kw in dec.keywords:
                if kw.arg is None:
                    continue
                if kw.arg == "tags":
                    kw_map["tags"] = _str_list(kw.value)
                elif kw.arg == "status_code":
                    v = _const(kw.value)
                    if v is not None:
                        kw_map["status_code"] = v
                    elif isinstance(kw.value, ast.Attribute):
                        # e.g. status.HTTP_201_CREATED
                        kw_map["status_code"] = kw.value.attr
                else:
                    v = _const(kw.value)
                    if v is not None:
                        kw_map[kw.arg] = v

            tags: list[str] = list(kw_map.get("tags", router_tags))  # type: ignore[arg-type]
            desc = dedent(str(kw_map.get("description", ""))).strip()
            fallback_summary = node.name.replace("_", " ").title()

            endpoints.append(
                Endpoint(
                    method=fn.attr.upper(),
                    path=router_prefix + ep_path,
                    summary=str(kw_map.get("summary", fallback_summary)),
                    description=desc,
                    tags=tags,
                    status_code=kw_map.get("status_code", 200),
                )
            )

    return endpoints


def collect_endpoints(api_dir: Path) -> list[Endpoint]:
    all_endpoints: list[Endpoint] = []
    for py_file in sorted(api_dir.rglob("*.py")):
        if py_file.name.startswith("_"):
            continue
        all_endpoints.extend(_parse_file(py_file))
    return all_endpoints


# ---------------------------------------------------------------------------
# Scope filtering
# ---------------------------------------------------------------------------

_INTERNAL_TAGS = {"internal", "admin", "infrastructure", "debug"}
_INTERNAL_SEGMENTS = {"/internal/", "/admin/", "/debug/"}


def _is_public(ep: Endpoint) -> bool:
    if {t.lower() for t in ep.tags} & _INTERNAL_TAGS:
        return False
    return not any(seg in ep.path for seg in _INTERNAL_SEGMENTS)


def filter_endpoints(endpoints: list[Endpoint], scope: str) -> list[Endpoint]:
    if scope == "public":
        return [ep for ep in endpoints if _is_public(ep)]
    return endpoints


# ---------------------------------------------------------------------------
# Status code → label
# ---------------------------------------------------------------------------

_STATUS_LABELS: dict[int | str, str] = {
    200: "200 OK",
    201: "201 Created",
    204: "204 No Content",
    "HTTP_200_OK": "200 OK",
    "HTTP_201_CREATED": "201 Created",
    "HTTP_204_NO_CONTENT": "204 No Content",
}


def _status_label(code: int | str) -> str:
    return _STATUS_LABELS.get(code, str(code))


# ---------------------------------------------------------------------------
# Markdown generation
# ---------------------------------------------------------------------------

_COMMON_RESPONSES = """\
## Common Response Codes

| Code | Meaning |
|---|---|
| `200 OK` | Successful read or update |
| `201 Created` | Resource successfully created |
| `204 No Content` | Successful deletion (no body) |
| `401 Unauthorized` | Missing or invalid bearer token |
| `403 Forbidden` | Authenticated but insufficient permissions |
| `404 Not Found` | Resource does not exist |
| `409 Conflict` | Business rule violation (duplicate, invalid state) |
| `422 Unprocessable Entity` | Request body validation failed |
| `423 Locked` | Operation not permitted on an archived resource |
"""


def generate_api_reference(endpoints: list[Endpoint]) -> str:
    sections = [
        "# API Reference",
        "",
        "**Base URL:** `http://<host>:8000/api/v1`",
        "",
        "All endpoints require `Authorization: Bearer <token>`. "
        "All request and response bodies are `application/json`.",
        "",
        "---",
        "",
        _COMMON_RESPONSES,
        "---",
        "",
    ]

    # Group by first tag
    by_tag: dict[str, list[Endpoint]] = {}
    for ep in endpoints:
        tag = ep.tags[0] if ep.tags else "General"
        by_tag.setdefault(tag, []).append(ep)

    for tag, eps in by_tag.items():
        sections += [f"## {tag}", ""]
        for ep in eps:
            sections += [
                f"### `{ep.method}` `{ep.path}` — {ep.summary}",
                "",
            ]
            if ep.description:
                sections += [ep.description, ""]
            sections += [
                f"**Success:** `{_status_label(ep.status_code)}`",
                "",
                "---",
                "",
            ]

    return "\n".join(sections)


# ---------------------------------------------------------------------------
# mkdocs.yml generation
# ---------------------------------------------------------------------------

_MKDOCS_TEMPLATE = """\
site_name: {service} Service
site_description: {desc} for the {service} Service
docs_dir: docs/{scope}
site_dir: site

theme:
  name: material
  palette:
    - scheme: default
      primary: indigo
      accent: indigo
  features:
    - navigation.tabs
    - navigation.sections
    - navigation.top
    - content.code.copy

markdown_extensions:
  - admonition
  - pymdownx.superfences:
      custom_fences:
        - name: mermaid
          class: mermaid
          format: !!python/name:pymdownx.superfences.fence_code_format
  - pymdownx.tabbed:
      alternate_style: true
  - tables
  - toc:
      permalink: true

nav:
{nav}
"""

_NAV_LABELS = {
    "index.md": "Overview",
    "getting-started.md": "Getting Started",
    "state-machine.md": "Tenant Lifecycle",
    "api-reference.md": "API Reference",
    "FunctionalRequirements.md": "Functional Requirements",
    "NonFunctionalRequirements.md": "Non-Functional Requirements",
    "BusinessLogic.md": "Business Logic",
    "TenentStates.md": "Tenant States",
    "TenentLifecycle.md": "Tenant Lifecycle",
    "ImplemetationSteps.md": "Implementation Steps",
}

_PLANNING_DOCS = [
    "FunctionalRequirements.md",
    "NonFunctionalRequirements.md",
    "BusinessLogic.md",
    "TenentStates.md",
    "TenentLifecycle.md",
    "ImplemetationSteps.md",
]


def generate_mkdocs(
    service: str,
    scope: str,
    top_files: list[str],
    planning_files: list[str] | None = None,
) -> str:
    desc = "Public API and user guide" if scope == "public" else "Internal technical reference"

    nav_lines = ""
    for f in top_files:
        label = _NAV_LABELS.get(Path(f).name, Path(f).stem.replace("-", " ").replace("_", " ").title())
        nav_lines += f"  - {label}: {f}\n"

    if planning_files:
        nav_lines += "  - Planning:\n"
        for f in planning_files:
            label = _NAV_LABELS.get(Path(f).name, Path(f).stem.replace("-", " ").replace("_", " ").title())
            nav_lines += f"    - {label}: {f}\n"

    return _MKDOCS_TEMPLATE.format(service=service, desc=desc, scope=scope, nav=nav_lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

_HAND_AUTHORED = ["index.md", "getting-started.md", "state-machine.md"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("service", help="Service directory name (e.g. TenantManagement)")
    parser.add_argument("--scope", choices=["public", "internal"], required=True)
    args = parser.parse_args()

    # Resolve service directory: always the parent of the scripts/ folder.
    # The service name arg is used for display only, not path resolution.
    service_dir = Path(__file__).resolve().parent.parent
    if not service_dir.is_dir():
        print(f"ERROR: service directory not found: {service_dir}", file=sys.stderr)
        sys.exit(1)

    api_dir = service_dir / "app" / "api"
    if not api_dir.is_dir():
        print(f"ERROR: app/api not found in {service_dir}", file=sys.stderr)
        sys.exit(1)

    out_dir = service_dir / "docs" / args.scope
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"doc-gen  service={args.service}  scope={args.scope}")
    print(f"  scanning {api_dir.relative_to(service_dir)}")

    # 1. Collect and filter endpoints
    all_eps = collect_endpoints(api_dir)
    eps = filter_endpoints(all_eps, args.scope)
    print(f"  endpoints: {len(all_eps)} found, {len(eps)} kept for scope={args.scope!r}")

    # 2. api-reference.md (always regenerated)
    (out_dir / "api-reference.md").write_text(generate_api_reference(eps))
    print(f"  wrote  docs/{args.scope}/api-reference.md")

    # 3. For internal scope, verify planning docs are present in docs/internal/planning/
    if args.scope == "internal":
        planning_dir = out_dir / "planning"
        planning_dir.mkdir(exist_ok=True)
        present = [f for f in _PLANNING_DOCS if (planning_dir / f).exists()]
        missing = [f for f in _PLANNING_DOCS if not (planning_dir / f).exists()]
        if missing:
            print(f"  WARNING: missing planning docs: {', '.join(missing)}", file=sys.stderr)
        if present:
            print(f"  planning docs: {len(present)} found in docs/internal/planning/")

    # 4. mkdocs.yml
    top_files: list[str] = []
    for name in _HAND_AUTHORED:
        if (out_dir / name).exists():
            top_files.append(name)
    top_files.append("api-reference.md")

    planning_files: list[str] | None = None
    if args.scope == "internal":
        planning_files = [
            f"planning/{fname}"
            for fname in _PLANNING_DOCS
            if (out_dir / "planning" / fname).exists()
        ]

    (service_dir / "mkdocs.yml").write_text(
        generate_mkdocs(args.service, args.scope, top_files, planning_files)
    )
    total = len(top_files) + (len(planning_files) if planning_files else 0)
    print(f"  wrote  mkdocs.yml  (nav: {len(top_files)} top-level + {len(planning_files) if planning_files else 0} under Planning)")

    print()
    print("Done. To serve:")
    print(f"  pip install mkdocs-material && mkdocs serve")


if __name__ == "__main__":
    main()
