from __future__ import annotations

import argparse
import ast
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

DYNAMIC_SECRET_REFERENCE_CONTRACT = "secret-reference-v1"
DYNAMIC_CONTRACT_NAME = "__beastbox_dynamic_env_contract__"


class EnvironmentInventoryError(ValueError):
    """Raised when environment-variable usage cannot be audited safely."""


@dataclass(frozen=True)
class SourceEnvironmentInventory:
    variables: set[str]
    dynamic_reads: list[str]


def _dynamic_contract(tree: ast.Module, *, filename: str) -> str | None:
    contract: str | None = None
    for node in tree.body:
        value: ast.AST | None = None
        target_names: list[str] = []
        if isinstance(node, ast.Assign):
            value = node.value
            target_names = [target.id for target in node.targets if isinstance(target, ast.Name)]
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            value = node.value
            target_names = [node.target.id]
        if DYNAMIC_CONTRACT_NAME not in target_names:
            continue
        if contract is not None:
            raise EnvironmentInventoryError(f"{filename}: duplicate dynamic environment contract declaration")
        if not isinstance(value, ast.Constant) or value.value != DYNAMIC_SECRET_REFERENCE_CONTRACT:
            raise EnvironmentInventoryError(
                f"{filename}: unsupported dynamic environment contract; expected {DYNAMIC_SECRET_REFERENCE_CONTRACT!r}"
            )
        contract = DYNAMIC_SECRET_REFERENCE_CONTRACT
    return contract


def _read_name(
    node: ast.AST | None,
    *,
    filename: str,
    lineno: int,
    contract: str | None,
    variables: set[str],
    dynamic_reads: list[str],
) -> None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value:
        variables.add(node.value)
        return
    if contract == DYNAMIC_SECRET_REFERENCE_CONTRACT:
        dynamic_reads.append(f"{filename}:{lineno}:{contract}")
        return
    raise EnvironmentInventoryError(
        f"{filename}:{lineno}: dynamic environment variable read; use a literal name so configuration remains auditable"
    )


def _is_os_environ(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Attribute)
        and node.attr == "environ"
        and isinstance(node.value, ast.Name)
        and node.value.id == "os"
    ) or (isinstance(node, ast.Name) and node.id == "environ")


def scan_python_source(source: str, *, filename: str = "<source>") -> SourceEnvironmentInventory:
    """Return auditable environment-variable reads from Python source.

    Literal reads are normal configuration and must be represented in the
    committed env example. Dynamic reads fail closed unless the module declares
    the narrow ``secret-reference-v1`` contract. That contract exists for
    provider profiles that intentionally carry an environment-variable *name*
    rather than a credential value; such reads are reported separately and are
    never silently treated as ordinary configuration.
    """

    try:
        tree = ast.parse(source, filename=filename)
    except SyntaxError as exc:
        raise EnvironmentInventoryError(f"{filename}: cannot parse Python source: {exc}") from exc

    contract = _dynamic_contract(tree, filename=filename)
    variables: set[str] = set()
    dynamic_reads: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            is_getenv = (
                isinstance(func, ast.Attribute)
                and func.attr == "getenv"
                and isinstance(func.value, ast.Name)
                and func.value.id == "os"
            ) or (isinstance(func, ast.Name) and func.id == "getenv")
            is_environ_get = (
                isinstance(func, ast.Attribute)
                and func.attr == "get"
                and _is_os_environ(func.value)
            )
            if is_getenv or is_environ_get:
                if not node.args:
                    raise EnvironmentInventoryError(
                        f"{filename}:{getattr(node, 'lineno', 0)}: environment read is missing a variable name"
                    )
                _read_name(
                    node.args[0],
                    filename=filename,
                    lineno=getattr(node, "lineno", 0),
                    contract=contract,
                    variables=variables,
                    dynamic_reads=dynamic_reads,
                )

        if isinstance(node, ast.Subscript) and _is_os_environ(node.value):
            _read_name(
                node.slice,
                filename=filename,
                lineno=getattr(node, "lineno", 0),
                contract=contract,
                variables=variables,
                dynamic_reads=dynamic_reads,
            )

    return SourceEnvironmentInventory(variables=variables, dynamic_reads=dynamic_reads)


def parse_env_example(content: str) -> set[str]:
    """Parse assignment keys from an env example and reject duplicate entries."""

    keys: set[str] = set()
    for lineno, raw_line in enumerate(content.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        if "=" not in line:
            raise EnvironmentInventoryError(f".env.example:{lineno}: expected KEY=value assignment")
        key, _value = line.split("=", 1)
        key = key.strip()
        if not key or not key.replace("_", "A").isalnum() or not key[0].isalpha():
            raise EnvironmentInventoryError(f".env.example:{lineno}: invalid environment variable name {key!r}")
        if key in keys:
            raise EnvironmentInventoryError(f".env.example:{lineno}: duplicate environment variable {key}")
        keys.add(key)
    return keys


def _scan_paths(paths: Iterable[Path]) -> SourceEnvironmentInventory:
    variables: set[str] = set()
    dynamic_reads: list[str] = []
    for root in paths:
        candidates = [root] if root.is_file() else sorted(root.rglob("*.py"))
        for path in candidates:
            if path.suffix != ".py" or "__pycache__" in path.parts:
                continue
            result = scan_python_source(path.read_text(encoding="utf-8"), filename=str(path))
            variables.update(result.variables)
            dynamic_reads.extend(result.dynamic_reads)
    return SourceEnvironmentInventory(variables=variables, dynamic_reads=sorted(dynamic_reads))


def inventory_paths(paths: Iterable[Path]) -> set[str]:
    """Compatibility helper returning only fixed-name configuration variables."""

    return _scan_paths(paths).variables


def check_env_example(*, example: Path, roots: Sequence[Path]) -> dict[str, object]:
    declared = parse_env_example(example.read_text(encoding="utf-8"))
    inventory = _scan_paths(roots)
    used = inventory.variables
    missing = sorted(used - declared)
    unused = sorted(declared - used)
    return {
        "example": str(example),
        "roots": [str(path) for path in roots],
        "used": sorted(used),
        "declared": sorted(declared),
        "dynamic_secret_references": inventory.dynamic_reads,
        "missing": missing,
        "unused": unused,
        "ok": not missing,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audit Beast Box environment-variable contracts")
    parser.add_argument("--check", type=Path, required=True, metavar="ENV_EXAMPLE")
    parser.add_argument("roots", nargs="+", type=Path)
    parser.add_argument("--json", action="store_true", dest="as_json")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        result = check_env_example(example=args.check, roots=args.roots)
    except (EnvironmentInventoryError, OSError) as exc:
        print(f"environment inventory error: {exc}")
        return 2

    if args.as_json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"Environment variables used: {len(result['used'])}")
        print(f"Environment variables documented: {len(result['declared'])}")
        dynamic = result["dynamic_secret_references"]
        if dynamic:
            print("Audited dynamic secret references:")
            for reference in dynamic:
                print(f"  - {reference}")
        if result["missing"]:
            print("Undocumented environment variables:")
            for name in result["missing"]:
                print(f"  - {name}")
        if result["unused"]:
            print("Documented but currently unused in audited roots:")
            for name in result["unused"]:
                print(f"  - {name}")

    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
