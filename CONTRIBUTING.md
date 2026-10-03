<p align="center">
  <img src="https://raw.githubusercontent.com/Moazzam-Matin/maarg/main/docs/assets/maarg_icon.svg" alt="maarg icon" width="100">
</p>

<h1 align="center">Contributing to maarg</h1>

Thank you for your interest in contributing to `maarg`.

`maarg` is a lightweight Python library for experiment tracking with zero boilerplate. The project focuses on making experiment tracking simple, local-first, and easy to integrate into existing Python workflows.

Contributions are welcome in the form of bug fixes, improvements, documentation, tests, new storage backends, capture support, and other changes that align with the project's goals.

## Before You Start

Before working on a change:

* Check the existing documentation and issue tracker.
* For larger changes, open an issue or discussion first to describe the proposed approach.
* Keep changes focused on a single problem or improvement.
* Add or update tests for behavioral changes.
* Keep the public API and documentation consistent with the implementation.

## Development Setup

`maarg` uses a `src`-based Python package layout and supports Python 3.9 and newer.

### 1. Clone the repository

```bash
git clone https://github.com/Moazzam-Matin/maarg.git
cd maarg
```

### 2. Create a virtual environment

On Windows:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

On macOS/Linux:

```bash
python -m venv .venv
source .venv/bin/activate
```

### 3. Install the development dependencies

```bash
pip install -e ".[dev]"
```

This installs `maarg` in editable mode together with the tools used for development and testing.

## Running Tests

Run the complete test suite with:

```bash
pytest
```

Before submitting a pull request, make sure the test suite passes.

When changing existing behavior or adding new functionality, add or update tests to cover the change.

## Code Quality

`maarg` uses Ruff for linting and formatting and MyPy for type checking.

Run Ruff with:

```bash
ruff check .
```

Run the formatter check with:

```bash
ruff format --check .
```

Run MyPy with:

```bash
mypy src/maarg
```

Fix any relevant issues before submitting a pull request.

## Making Changes

When working on a change:

1. Create a focused branch for your work.
2. Make the smallest reasonable change that solves the problem.
3. Add or update tests.
4. Update documentation when public behavior changes.
5. Run the test and code-quality checks locally.
6. Review your changes before opening a pull request.

Avoid unrelated refactoring or changes that make a focused contribution harder to review.

## Project Structure

The main package is located in `src/maarg/`.

```text
src/
└── maarg/
    ├── __init__.py
    ├── _capture.py
    ├── _convenience.py
    ├── _exceptions.py
    ├── _models.py
    ├── _query.py
    ├── _tracking.py
    └── storage/
        ├── __init__.py
        ├── _base.py
        └── _sqlite.py
```

Tests are located in `tests/` and cover tracking, capture, models, querying, convenience APIs, and storage.

## Public API and Compatibility

Changes to the public API should be made carefully.

When modifying public behavior:

* Consider backward compatibility.
* Update relevant tests.
* Update the README and other documentation where necessary.
* Keep public APIs simple and consistent with the project's lightweight design.

Avoid exposing internal implementation details unless there is a clear reason to make them part of the public API.

## Storage Backends

`maarg` separates tracking from persistence through the `StorageBackend` interface.

Contributions that add new storage backends are welcome when they:

* Follow the existing storage abstraction.
* Preserve the expected behavior of tracked runs.
* Include appropriate tests.
* Do not introduce unnecessary dependencies into the core package.

The default `SQLiteStorage` implementation should remain lightweight and local-first.

## Capture and Serialization

`maarg` intentionally captures only supported values and avoids indiscriminate serialization of arbitrary Python objects.

When adding support for new captured values or artifacts:

* Consider safety and serialization behavior.
* Respect existing capture limits.
* Avoid unexpectedly storing large or complex objects.
* Add tests for supported, unsupported, and edge-case values.
* Document user-visible behavior.

For artifact support, prefer the existing serializer-based design rather than adding special cases to the tracking layer.

## Error Handling

Tracking should not unnecessarily interfere with the user's experiment.

When modifying error handling:

* Preserve the original exception raised by the user's function.
* Keep failed-run recording behavior consistent.
* Respect the existing `strict` mode semantics.
* Add tests for both successful and failed executions.

Changes that affect `MaargTrackingError` or `MaargTrackingWarning` should be made carefully because they are part of the library's public behavior.

## Documentation

Documentation is an important part of `maarg`.

When a change affects user-facing behavior, update the relevant documentation.

This may include:

* `README.md`
* API examples
* `CONTRIBUTING.md`
* `CHANGELOG.md` when preparing a release

Examples should be runnable and consistent with the current implementation.

## Pull Requests

When opening a pull request:

* Clearly describe what changed.
* Explain why the change was needed.
* Mention relevant issues if applicable.
* Include tests for behavioral changes.
* Keep the pull request focused.
* Confirm that the test suite passes.
* Confirm that documentation is updated when necessary.

A good pull request should be understandable and reviewable without requiring extensive additional context.

## Commit Messages

Use clear, concise commit messages that describe the change.

Examples:

```text
feat: add custom storage backend support
fix: preserve original exception during tracking
docs: improve query API documentation
test: add failure tracking coverage
refactor: simplify input capture
```

Keep commits focused on a logical change whenever practical.

## Reporting Bugs

When reporting a bug, include enough information to reproduce it.

Where possible, provide:

* Python version
* `maarg` version
* Operating system
* Minimal reproduction example
* Expected behavior
* Actual behavior
* Relevant error message or traceback

A small reproducible example makes debugging significantly easier.

## Feature Requests

Feature ideas are welcome.

Before implementing a larger feature, consider opening an issue to discuss:

* The problem being solved
* The proposed behavior
* How it fits the scope of `maarg`
* Potential API changes
* Any additional dependencies or infrastructure required

The project aims to remain lightweight, so new functionality should be evaluated against that goal.

## Development Principles

Contributions should generally follow these principles:

* **Simple** — Prefer straightforward implementations.
* **Lightweight** — Avoid unnecessary dependencies and infrastructure.
* **Local-first** — Preserve the simplicity of the default local workflow.
* **Explicit** — Keep public behavior understandable.
* **Tested** — Behavioral changes should have appropriate test coverage.
* **Backward-conscious** — Avoid unnecessary breaking changes.
* **User-focused** — Prioritize useful functionality over complexity.

## License

By contributing to `maarg`, you agree that your contributions will be licensed under the project's [Apache License 2.0](LICENSE).

---

Thank you for helping improve `maarg`.
