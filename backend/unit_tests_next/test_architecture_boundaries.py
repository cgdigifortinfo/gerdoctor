"""Executable dependency rules for the backend architecture."""
from __future__ import annotations

import ast
from pathlib import Path


BACKEND = Path(__file__).resolve().parents[1]


def imported_roots(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".", 1)[0])
    return roots


def imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def python_files(package: str) -> tuple[Path, ...]:
    return tuple(path for path in (BACKEND / package).rglob("*.py") if path.name != "__init__.py")


def assert_forbidden(package: str, forbidden: set[str]) -> None:
    violations = {
        str(path.relative_to(BACKEND)): sorted(imported_roots(path) & forbidden)
        for path in python_files(package)
        if imported_roots(path) & forbidden
    }
    assert violations == {}


def test_domain_is_framework_and_adapter_independent() -> None:
    domain_files = tuple((BACKEND / "slices").glob("*/domain.py")) + tuple(
        (BACKEND / "slices").glob("*/models.py")
    ) + tuple((BACKEND / "slices").glob("*/mappers.py"))
    violations = {
        str(path.relative_to(BACKEND)): sorted(module for module in imported_modules(path) if (
            module.split(".", 1)[0] in {"bson", "fastapi", "infrastructure", "motor", "pymongo", "stripe"}
            or module.endswith((".repository", ".service", ".ports", ".web", ".web_errors", ".web_serializers"))
        ))
        for path in domain_files
    }
    assert {path: modules for path, modules in violations.items() if modules} == {}


def test_shared_contains_only_dependency_free_types() -> None:
    assert_forbidden("shared", {
        "bson", "database", "domain", "fastapi", "infrastructure", "motor",
        "pymongo", "repositories", "services", "stripe", "web",
    })


def test_infrastructure_does_not_depend_on_application_or_web_layers() -> None:
    assert_forbidden("infrastructure", {"database", "domain", "fastapi", "repositories", "services", "web"})


def test_web_does_not_access_database_or_repository_adapters() -> None:
    web_files = tuple(path for path in (BACKEND / "slices").glob("*/web*.py"))
    violations = {
        str(path.relative_to(BACKEND)): sorted(module for module in imported_modules(path) if (
            module == "database" or module.endswith(".repository")
        ))
        for path in web_files
    }
    assert {path: modules for path, modules in violations.items() if modules} == {}
