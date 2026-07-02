# Python Coding Conventions

Opinionated standards for modern Python (3.10+). PEP 8 basics are assumed known this skill covers non-obvious choices.

## Tooling

- **Formatter + Linter:** `ruff` (replaces `black`, `flake8`, `isort` in a single tool)
- **Type Checker:** `mypy` with `--strict` or `pyright`
- **Test Framework:** `pytest`
- **Dependency Management:** `uv` (preferred) or `poetry`
- **Config:** Single `pyproject.toml` for all tools (no `setup.py`, `setup.cfg`, `requirements.txt` for libraries)

## Type Annotations

- Use modern syntax (3.10+): `list[str]`, `dict[str, int]`, `str | None` not `Optional[str]` or `List[str]`
- Annotate all function signatures (parameters + return type)
- Use `TypeAlias` for complex types reused across modules
- Prefer `Protocol` over `ABC` for structural typing when possible
- Use `TypedDict` for dictionary shapes with known keys

## Project Structure

```
project/
├── src/project_name/    # Source code (src layout)
│   ├── __init__.py
│   ├── models/
│   ├── services/
│   └── utils/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── conftest.py
├── pyproject.toml
└── README.md
```

- Use **src layout** for packages
- Separate `tests/unit/` and `tests/integration/`
- Shared fixtures in `conftest.py`

## Error Handling

- Use specific exception types never bare `except:`
- Create domain-specific exceptions inheriting from a base project exception
- Use `contextlib.suppress()` for intentionally ignored exceptions
- Log exceptions with `logger.exception()` (includes traceback automatically)

## Testing

- Fixtures over setup/teardown methods
- Name tests: `test_<what>_<condition>_<expected>` (e.g., `test_login_invalid_password_raises_auth_error`)
- Use `@pytest.mark.parametrize` for testing multiple inputs
- Target: unit tests for business logic, integration tests for I/O boundaries
- Use `pytest-cov` for coverage, enforce minimum threshold

## Preferred Patterns

- **Structured data:** Dataclasses or Pydantic models over plain dicts
- **File paths:** `pathlib.Path` over `os.path`
- **HTTP:** `httpx` over `requests` (async-capable)
- **Resources:** Context managers (`with`) for all resource management
- **Iteration:** Generator expressions over list comprehensions when iterating once
- **Logging:** `logging` module over `print()` for any non-trivial code
- **Config:** Environment variables via `pydantic-settings` or `python-dotenv`
- **Async:** `asyncio` + `httpx` for concurrent I/O avoid threading for I/O-bound tasks

## Anti-Patterns to Flag

- Mutable default arguments (`def f(items=[]):`)
- Wildcard imports (`from module import *`)
- Catching `Exception` without re-raising or logging
- Using `type()` for type checking instead of `isinstance()`
- String concatenation in loops (use `join()` or f-strings)
- Nested functions beyond 2 levels deep
