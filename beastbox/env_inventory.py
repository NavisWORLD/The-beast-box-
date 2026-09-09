from __future__ import annotations

import argparse
import ast
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence


class EnvironmentInventoryError(ValueError):
    """Raised when environment-variable usage cannot be audited safely."""


@dataclass(frozen=True)
class SourceEnvironmentInventory:
    variables: set[str]
    dynamic_reads: list[str]


def _literal_name(node: ast.AST | None, *, filename: str, lineno: int) -> str:
    if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value:
        return node.value
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
    """Return literal environment-variable reads from Python source.

    Supported forms are os.getenv("NAME"), getenv("NAME"),
    os.environ.get("NAME"), environ.get("NAME"), and subscription reads such as
    os.environ["NAME"]. Dynamic names fail closed because they cannot be compared
    reliably against the committed environment contract.
    """

    try:
        tree = ast.parse(source, filename=filename)
    except SyntaxError as exc:
        raise EnvironmentInventoryError(f"{filename}: cannot parse Python source: {exc}") from exc

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
                variables.add(
                    _literal_name(
                        node.args[0],
                        filename=filename,
                        lineno=getattr(node, "lineno", 0),
                    )
                )

        if isinstance(node, ast.Subscript) and _is_os_environ(node.value):
            variables.add(
                _literal_name(
                    node.slice,
                    filename=filename,
                    lineno=getattr(node, "lineno", 0),
                )
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


def inventory_paths(paths: Iterable[Path]) -> set[str]:
    variables: set[str] = set()
    for root in paths:
        candidates = [root] if root.is_file() else sorted(root.rglob("*.py"))
        for path in candidates:
            if path.suffix != ".py" or "__pycache__" in path.parts:
                continue
            result = scan_python_source(path.read_text(encoding="utf-8"), filename=str(path))
            variables.update(result.variables)
    return variables


def check_env_example(*, example: Path, roots: Sequence[Path]) -> dict[str, object]:
    declared = parse_env_example(example.read_text(encoding="utf-8"))
    used = inventory_paths(roots)
    missing = sorted(used - declared)
    unused = sorted(declared - used)
    return {
        "example": str(example),
        "roots": [str(path) for path in roots],
        "used": sorted(used),
        "declared": sorted(declared),
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
