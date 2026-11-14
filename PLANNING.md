<p align="center">
  <img src="https://raw.githubusercontent.com/Moazzam-Matin/maarg/main/docs/assets/maarg_icon.svg" alt="maarg logo" width="120">
</p>

# maarg — Project Planning

## 1. Project Vision

A decorator that automatically captures a function's inputs, outputs, execution time, and failures and records them as structured experiment runs — no `log_param()`, no `log_metric()`, no boilerplate.

maarg is designed around zero-instrumentation tracking: users write normal Python functions and add `@track`. The library handles capture, classification, persistence, and failure tracking automatically, while remaining lightweight, local-first, and independent of any specific ML framework.

### Who it's for

1. Individual researchers and data scientists running many small experiments.
2. Anyone re-running parameterized functions and comparing results — hyperparameter sweeps, algorithm benchmarking, backtests, and simulations.
3. Small teams wanting lightweight experiment tracking without standing up server infrastructure.

The broader goal is to make experiment tracking useful beyond machine learning, without compromising the simplicity of the core experience.

### Core principles

- **Zero boilerplate:** Normal Python functions should be trackable with minimal changes.
- **Local-first:** SQLite is the default storage backend. No server or external service is required.
- **Lightweight:** Avoid heavyweight dependencies and unnecessary infrastructure.
- **Framework-independent:** maarg should work with ordinary Python workloads, not just ML frameworks.
- **Failure-safe:** Tracking must never silently replace or mask the user's original exception.
- **Extensible:** Users should be able to extend supported output types without modifying maarg's core code.

---

## 2. Current Project Status

<badge color="success">v0.4.2 released</badge>

**Current version:** `0.4.2`

**License:** Apache License 2.0

**Package:** [PyPI — maarg](https://pypi.org/project/maarg/)

**Repository:** [GitHub — Moazzam-Matin/maarg](https://github.com/Moazzam-Matin/maarg)

**Tagline:** Track Experiments with Zero Boilerplate.

### Shipped capabilities

- `@track` decorator with zero-configuration defaults.
- Bare and parenthesized decorator usage.
- Automatic input filtering based on actual type and size.
- Automatic output classification and capture.
- Structured dictionary and collection output capture.
- Registered artifact-type serialization.
- Execution-time tracking.
- Failure tracking with exception information.
- Failure-safe persistence and optional strict mode.
- Artifact filename sanitization.
- SQLite storage with indexes on commonly queried fields.
- Storage backend interface.
- Query API:
  - `get_runs`
  - `filter_runs`
  - `compare`
  - `top_n`
  - `best_run`
- Optional plotting support.
- Public PyPI package and GitHub repository.
- Automated release and PyPI publishing workflow.

### Current architectural boundaries

maarg is intentionally a lightweight experiment tracking library.

It is not intended to become an experiment orchestration platform, a hosted tracking server, or a full ML lifecycle management system.

---

## 3. Release History

All published GitHub releases are listed below, in chronological order.

### v0.3.0 — Robust Capture

**Released:** October 2, 2026

- Added failure-safe tracking.
- Introduced strict mode for successful-run persistence failures.
- Added `MaargTrackingError` and `MaargTrackingWarning`.
- Added artifact filename sanitization.
- Added SQLite indexes on commonly queried fields.
- Introduced the extensible serializer registry.
- Ensured the original user exception is preserved when tracking fails.

### v0.3.1 — Packaging and Project Readiness

**Released:** October 4, 2026

- Updated package metadata and release documentation.
- Migrated the project license to Apache License 2.0.
- Updated documentation and project branding.
- Refined PyPI-facing package information.
- Improved release readiness and project presentation.

### v0.4.0 — Structured Output Capture

**Released:** November 11, 2026

- Added structured dictionary output capture.
- Preserved nested dictionaries and lists.
- Supported JSON-compatible values, including numeric values, booleans, strings, and `None`.
- Preserved the original dictionary structure instead of flattening it.
- Kept registered artifact types separate from structured metrics.
- Improved numeric metric ranking in `top_n()` and `best_run()`.
- Excluded boolean values from numeric metric ranking.
- Added regression tests and documentation updates.

### v0.4.1 — Dictionary Key Preservation

**Released:** November 12, 2026

- Fixed handling of dictionary outputs with non-string keys.
- Prevented key changes during SQLite JSON serialization.
- Added regression tests for non-string dictionary keys.
- Added SQLite round-trip coverage for structured dictionary outputs.
- Refined the presentation of community documentation.

### v0.4.2 — Project Presentation and Release Automation

**Released:** November 14, 2026

- Added a direct Changelog link to project metadata.
- Added branded Changelog and Discussions buttons to the README.
- Updated button styling to match the maarg logo gradient.
- Added GitHub Actions automation to update the Changelog button with the latest release version.
- Added manual triggering support to the PyPI publishing workflow.

---

## 4. Architecture

The architecture is built around three important extension points.

### 1. Storage backend interface — Done

Defines where experiment runs are stored.

- SQLite is the default local backend.
- The interface keeps the core tracking logic independent of the storage implementation.
- Additional backends can be considered when real demand appears.

### 2. Serializer registry — Done

Defines how output types are recognized and captured.

- Built-in output handling covers common Python values and structured collections.
- Registered serializers support artifact-oriented output types.
- The registry allows additional types to be supported without hardcoding every type into the capture implementation.

**Future consideration:** A public serializer registration API.

### 3. Capture hooks and callbacks — Not implemented

Would allow users to react when a run completes.

Possible examples include notifications, webhooks, or integrations with external tools.

There is no committed implementation timeline.

---

## 5. v0.5.0 Roadmap

### Theme: Output Reliability and Extensibility

The next development phase should build on the structured output support introduced in v0.4.0 and the key-preservation improvements in v0.4.1.

The focus is to make captured experiment results more useful and extensible without compromising the zero-boilerplate experience.

### Priority 0 — Structured Evaluation Results

**Related issue:** [#6 — Improve tracking of structured evaluation results](https://github.com/Moazzam-Matin/maarg/issues/6)

Structured dictionaries can already be captured, but nested evaluation results are not necessarily available as individually queryable scalar metrics.

For example:

```python
{
    "precision_at_k": {
        "5": 0.061,
        "10": 0.058
    },
    "recall_at_k": {
        "5": 0.025,
        "10": 0.049
    }
}
```

The goal is to investigate a lightweight and predictable way to expose selected nested numeric values as queryable metrics.

Areas to resolve:

- How users select which nested values should become metrics.
- How metric names should represent nested keys and cutoffs.
- How multiple evaluation cutoffs should be handled.
- How unsupported and non-numeric values should behave.
- How to avoid silently recording unintended values.
- How to preserve backward compatibility with existing structured output capture.

**Desired outcome:** Users should be able to query and compare important evaluation metrics without repeatedly extracting them manually.

### Priority 1 — Public Custom Serializer API

The serializer registry currently has an internal registration mechanism.

Evaluate exposing a supported public API, potentially:

```python
import maarg

maarg.register_serializer(...)
```

Potential use cases:

- Pandas DataFrames.
- Embeddings.
- Custom diagnostic objects.
- Additional plotting or visualization types.

Design requirements:

- Explicit opt-in registration.
- A simple and documented interface.
- No unnecessary default instrumentation.
- No heavy plugin architecture.
- Backward compatibility with existing serializers.

The public API and its exact design must be evaluated before committing to implementation.

### Priority 1 — Serialization Reliability

Continue hardening serialization and retrieval.

Areas to investigate:

- Nested and mixed data structures.
- Supported and unsupported values.
- SQLite persistence and retrieval.
- Round-trip consistency.
- Regression coverage for previously fixed dictionary-key behavior.

### Priority 2 — Tests and Documentation

- Expand regression coverage for structured output handling.
- Add tests for any new serializer registration API.
- Document supported output types and limitations.
- Add practical examples for structured evaluation results.
- Keep examples focused on normal Python workflows.

### v0.5.0 scope principle

The priorities above describe the intended direction, not a promise that every proposed API or feature will ship.

Implementation decisions should follow investigation and testing. Keep the release focused rather than expanding it into a collection of unrelated features.

---

## 6. Future Roadmap

These are ideas worth retaining for future evaluation. They are not committed to v0.5.0.

### Run organization

- First-class free-form run tags.
- Better filtering and grouping of runs.
- Additional comparison conveniences.

Free-form tags are a known gap identified through dogfooding. They should be designed as a first-class `Run.tags` field rather than reusing the existing `other` field.

### Query and analysis improvements

- Multi-metric sorting in `top_n()` and `best_run()`.
- More flexible comparison and filtering.
- Additional analysis conveniences based on real user needs.

### Tracking flexibility

- Step-wise or imperative logging for workflows such as per-epoch metrics inside a loop.
- Capture hooks and callbacks.
- Additional serializer integrations.

Step-wise logging requires a dedicated design discussion because it must not compromise maarg's zero-instrumentation identity.

### Ecosystem and infrastructure

- Additional storage backends.
- CLI, if real user demand emerges.
- Dashboard as a separate package.
- Integrations with orchestration tools rather than competing with them.

### Possible release direction

| Release | Direction |
|---|---|
| v0.4.2 | Project presentation and release automation — shipped |
| v0.5.0 | Structured evaluation results and extensibility |
| v0.6.0 | Potential query, comparison, and analysis improvements |

Future release themes are tentative and will be refined as the project evolves.

---

## 7. Non-goals

The following are intentionally outside the current product direction:

- A built-in web dashboard.
- A distributed or multi-machine tracking server.
- Experiment orchestration.
- Replacing tools such as Airflow, Optuna, or Ray.
- Authentication, permissions, or governance systems.
- A model registry.
- Heavyweight background tracking.
- A complex plugin framework.

The goal is to remain a focused Python experiment tracking library.

---

## 8. Project Decisions

### CLI

The CLI was deferred because maarg's users are already working in Python, where the query API is directly accessible.

Revisit only if real user demand appears.

### Step-wise logging

This requires a dedicated design discussion before implementation.

The solution must preserve the simplicity of the decorator-first experience.

### Free-form tags

A genuine gap has been identified. The design should introduce a first-class field rather than repurposing unrelated metadata.

### Domain and documentation hosting

Potential domains such as `maarg.dev` or `maarg.io` may be checked later.

This is low priority and does not block development.

---

## 9. Release Checklist

Use this checklist for every release.

### Pre-release

- [ ] Confirm release scope and completed issues.
- [ ] Confirm the target version.
- [ ] Update the version in `pyproject.toml`.
- [ ] Update the version in `src/maarg/__init__.py`, if applicable.
- [ ] Update `CHANGELOG.md`.
- [ ] Update README release references and links.
- [ ] Ensure the Changelog link uses the full GitHub URL so it works on PyPI:
      `https://github.com/Moazzam-Matin/maarg/blob/main/CHANGELOG.md`
- [ ] Review documentation and package metadata.

### Quality checks

- [ ] Run the full test suite.
- [ ] Run Ruff checks.
- [ ] Run mypy checks.
- [ ] Run `git diff --check`.
- [ ] Verify GitHub Actions CI across supported Python versions and operating systems.
- [ ] Review any failing or skipped tests.

### Build and validation

- [ ] Delete existing `build/` and `dist/` directories to prevent stale artifacts from being included.
- [ ] Build distributions:

  ```powershell
  python -m build
  ```

- [ ] Validate distributions:

  ```powershell
  python -m twine check dist/*
  ```

- [ ] Inspect the generated wheel and source distribution.
- [ ] Confirm the package version and included files are correct.

### GitHub release

- [ ] Commit and push release changes.
- [ ] Create an annotated version tag:

  ```powershell
  git tag -a vX.Y.Z -m "Release vX.Y.Z"
  ```

- [ ] Push the tag:

  ```powershell
  git push origin vX.Y.Z
  ```

- [ ] Create and publish the GitHub Release.
- [ ] Verify the release notes and tag.

### PyPI publication

- [ ] Verify the PyPI publishing workflow succeeds.
- [ ] If needed, use the manual `workflow_dispatch` trigger as a fallback.
- [ ] Confirm the new version appears on PyPI.
- [ ] Test installation using the published package.
- [ ] Verify the README and project links render correctly on PyPI.

### Post-release

- [ ] Confirm package badges display correctly.
- [ ] Confirm the automated Changelog button reflects the latest version.
- [ ] Review GitHub Issues and Discussions.
- [ ] Record the release and its key changes in this document.
- [ ] Identify any deferred work for the next release.

---

## 10. Project Identity

- **Name:** maarg
- **Meaning:** मार्ग — Hindi for path or route.
- **Tagline:** Track Experiments with Zero Boilerplate.
- **Package:** `maarg`
- **License:** Apache License 2.0
- **Primary language:** Python
- **Default storage:** SQLite
- **Repository:** https://github.com/Moazzam-Matin/maarg
- **PyPI:** https://pypi.org/project/maarg/

---

*Last Updated: November 14, 2026*  
*Current Release: v0.4.2*
