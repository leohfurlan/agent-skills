#!/usr/bin/env python3
"""Plan, create, and validate a layered Atos SDD harness."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROFILE_ORDER = ("minimal", "standard", "high-risk")
TOKEN_PREFIX = "{{"
TOKEN_SUFFIX = "}}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Plan, create, or validate a merge-safe Atos SDD harness."
    )
    parser.add_argument("--project-root", required=True, type=Path)
    parser.add_argument("--project-name")
    parser.add_argument("--profile", choices=PROFILE_ORDER, default="standard")
    parser.add_argument("--fast-command", action="append", default=[])
    parser.add_argument("--full-command", action="append", default=[])
    parser.add_argument("--architecture-command", action="append", default=[])
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--apply", action="store_true")
    action.add_argument("--validate", action="store_true")
    return parser.parse_args()


def load_catalog() -> dict[str, dict[str, str]]:
    path = Path(__file__).resolve().parent.parent / "assets" / "harness_templates.json"
    with path.open(encoding="utf-8") as stream:
        catalog: dict[str, dict[str, str]] = json.load(stream)
    return catalog


def selected_templates(
    catalog: dict[str, dict[str, str]], profile: str
) -> dict[str, str]:
    result: dict[str, str] = {}
    limit = PROFILE_ORDER.index(profile)
    for layer in PROFILE_ORDER[: limit + 1]:
        overlap = result.keys() & catalog[layer].keys()
        if overlap:
            names = ", ".join(sorted(overlap))
            raise ValueError(f"Template duplicado entre perfis: {names}")
        result.update(catalog[layer])
    return result


def tokens(args: argparse.Namespace, root: Path) -> dict[str, str]:
    project_name = args.project_name or root.name
    has_product_specs = PROFILE_ORDER.index(args.profile) >= 1
    return {
        "PROJECT_NAME": project_name,
        "PROFILE": args.profile,
        "PRODUCT_REQUIREMENTS": (
            "docs/product/PRD.md" if has_product_specs else "null"
        ),
        "SPECIFICATIONS": "docs/specs" if has_product_specs else "null",
        "FAST_COMMANDS_JSON": json.dumps(
            args.fast_command, ensure_ascii=False, indent=4
        ),
        "FULL_COMMANDS_JSON": json.dumps(
            args.full_command, ensure_ascii=False, indent=4
        ),
        "ARCHITECTURE_COMMANDS_JSON": json.dumps(
            args.architecture_command, ensure_ascii=False, indent=4
        ),
    }


def render(content: str, values: dict[str, str]) -> str:
    rendered = content
    for key, value in values.items():
        rendered = rendered.replace(f"{TOKEN_PREFIX}{key}{TOKEN_SUFFIX}", value)
    if TOKEN_PREFIX in rendered or TOKEN_SUFFIX in rendered:
        raise ValueError("Template contém marcador não resolvido")
    return rendered


def contained_target(root: Path, relative: str) -> Path:
    target = root / Path(relative)
    resolved = target.resolve(strict=False)
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"Destino sai da raiz por symlink: {relative}") from exc
    return target


def build_plan(
    root: Path, templates: dict[str, str], values: dict[str, str]
) -> list[dict[str, Any]]:
    plan: list[dict[str, Any]] = []
    for relative, template in sorted(templates.items()):
        target = contained_target(root, relative)
        content = render(template, values)
        if target.is_symlink():
            status = "conflict"
        elif not target.exists():
            status = "create"
        elif target.is_file() and target.read_text(
            encoding="utf-8", errors="replace"
        ) == content:
            status = "preserve-compatible"
        else:
            status = "integration-required"
        plan.append(
            {
                "path": relative,
                "status": status,
                "target": target,
                "content": content,
            }
        )
    return plan


def print_plan(plan: list[dict[str, Any]], *, mode: str) -> None:
    print(f"MODE={mode}")
    counts: dict[str, int] = {}
    for item in plan:
        status = item["status"]
        counts[status] = counts.get(status, 0) + 1
        print(f"{status.upper():20} {item['path']}")
    summary = " ".join(f"{key}={counts[key]}" for key in sorted(counts))
    print(f"SUMMARY {summary} total={len(plan)}")


def apply_plan(root: Path, plan: list[dict[str, Any]]) -> None:
    conflicts = [item["path"] for item in plan if item["status"] == "conflict"]
    if conflicts:
        raise ValueError("Conflitos de symlink: " + ", ".join(conflicts))
    for item in plan:
        if item["status"] != "create":
            continue
        target: Path = item["target"]
        target.parent.mkdir(parents=True, exist_ok=True)
        contained_target(root, item["path"])
        try:
            with target.open("x", encoding="utf-8", newline="\n") as stream:
                stream.write(item["content"])
        except FileExistsError as exc:
            raise RuntimeError(
                f"Arquivo surgiu após o plano; revisar antes de repetir: {item['path']}"
            ) from exc


def validate(root: Path, expected: dict[str, str], values: dict[str, str]) -> int:
    problems: list[str] = []
    parsed_json: dict[str, Any] = {}
    for relative in sorted(expected):
        try:
            path = contained_target(root, relative)
        except ValueError as exc:
            problems.append(str(exc))
            continue
        if path.is_symlink():
            problems.append(f"symlink não permitido em caminho controlado: {relative}")
            continue
        if not path.is_file():
            problems.append(f"ausente: {relative}")
            continue
        content = path.read_text(encoding="utf-8", errors="replace")
        if not content:
            problems.append(f"vazio: {relative}")
        if TOKEN_PREFIX in content or TOKEN_SUFFIX in content:
            problems.append(f"marcador não resolvido: {relative}")
        if relative.endswith(".json"):
            try:
                parsed_json[relative] = json.loads(content)
            except json.JSONDecodeError as exc:
                problems.append(f"JSON inválido: {relative}: {exc}")

    gates = parsed_json.get(".harness/gates.json")
    if not isinstance(gates, dict):
        problems.append(".harness/gates.json deve conter um objeto")
    else:
        if gates.get("profile") != values["PROFILE"]:
            problems.append("perfil de .harness/gates.json diverge do perfil validado")
        working_directory = gates.get("working_directory")
        if not isinstance(working_directory, str) or not working_directory.strip():
            problems.append("working_directory de gates.json deve ser texto não vazio")
        else:
            try:
                working_path = (root / working_directory).resolve()
                working_path.relative_to(root)
            except ValueError:
                problems.append("working_directory de gates.json sai da raiz")
        groups = gates.get("groups")
        if not isinstance(groups, dict):
            problems.append("groups de gates.json deve ser um objeto")
        else:
            for group in ("fast", "full", "architecture"):
                commands = groups.get(group)
                invalid = not isinstance(commands, list) or any(
                    not isinstance(command, str) or not command.strip()
                    for command in commands or []
                )
                if invalid:
                    problems.append(f"grupo {group} de gates.json deve ser array de strings")

    project_path = root / ".harness" / "project.yaml"
    if project_path.is_file():
        project_content = project_path.read_text(encoding="utf-8")
        expected_profile = f'  profile: "{values["PROFILE"]}"'
        if expected_profile not in project_content:
            problems.append("perfil de .harness/project.yaml diverge do perfil validado")
        expected_sources = (
            f'  product_requirements: {values["PRODUCT_REQUIREMENTS"]}',
            f'  specifications: {values["SPECIFICATIONS"]}',
        )
        if any(source not in project_content for source in expected_sources):
            problems.append("fontes de .harness/project.yaml divergem do perfil validado")

    for adapter in ("AGENTS.md", "CLAUDE.md"):
        path = root / adapter
        if path.is_file() and "DEVELOPMENT.md" not in path.read_text(
            encoding="utf-8", errors="replace"
        ):
            problems.append(f"{adapter} não aponta para DEVELOPMENT.md")

    if problems:
        print("INVALID")
        for problem in problems:
            print(f"- {problem}")
        return 1
    print(f"VALID profile={values['PROFILE']} files={len(expected)}")
    return 0


def main() -> int:
    args = parse_args()
    root = args.project_root.resolve()
    if not root.is_dir():
        print(f"Raiz inexistente: {root}", file=sys.stderr)
        return 2

    catalog = load_catalog()
    templates = selected_templates(catalog, args.profile)
    values = tokens(args, root)

    if args.validate:
        return validate(root, templates, values)

    plan = build_plan(root, templates, values)
    print_plan(plan, mode="apply" if args.apply else "plan")
    if args.apply:
        apply_plan(root, plan)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
