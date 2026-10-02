# maarg — Project Planning

## Vision

A decorator that auto-captures a function's inputs and outputs via introspection
(signature + return value) and logs them — no `log_param()`, no `log_metric()`,
no boilerplate. Every existing experiment tracker (MLflow, W&B, Neptune, Comet,
Aim, Sacred) still requires you to write explicit logging calls, or at best
offers framework-specific autologging hooks. maarg's core differentiator is
that it introspects the function itself, so it works on any Python function,
not just ones using a supported training framework.

## Who it's for

1. Individual researchers/data scientists running many small experiments
   (primary wedge use case)
2. Anyone re-running a parameterized function and comparing results —
   hyperparameter sweeps, algorithm benchmarking, backtests, simulations
   (broader addressable market, not ML-exclusive)
3. Small teams wanting lightweight tracking without standing up server
   infrastructure (not a v1 design target, but shouldn't be architecturally
   blocked later)

## v1 Scope — SHIPPED (0.2.0, patched to 0.2.0.post1)

- `@track` decorator, zero-config by default, bare and parenthesized usage
- Automatic input filtering: log small/simple values, skip large/complex objects
  (detection based on actual type/size, not name-guessing)
- Automatic output handling: numbers, dicts of numbers, matplotlib figures,
  graceful fallback for unknown types
- Failure tracking: a raised exception is recorded (status, error type/message)
  and re-raised unchanged
- Storage backend interface: local-first default (SQLite), pluggable for
  future backends
- Python query API: `get_runs`, `top_n`, `best_run`, `filter_runs`, `compare` —
  storage-aware convenience wrappers plus a pure, storage-independent core
- Package is public on PyPI and GitHub; validated via a TestPyPI dry run and
  real-world dogfooding on a second project (recommendation-engine), which
  surfaced and fixed real bugs before and after launch

### Deliberately not in v1

(Moved out during planning, not an oversight.)

- CLI — reasoned that maarg's users are already in Python where the query API
  is directly usable; revisit only if real demand appears

## v1 Non-goals

- No web dashboard (separate package, later)
- No distributed/multi-machine tracking server
- No experiment orchestration (integrate with Airflow/Optuna/Ray, don't
  compete with them)
- No auth/permissions/governance features
- No model registry / artifact versioning beyond file-path tracking

## Architecture — the three seams that matter

1. **Storage backend interface** — where runs live (SQLite now, anything
   later) — **done**
2. **Serializer registry** — how output types are recognized and captured —
   **done** (0.3.0)
3. **Capture hooks/callbacks** — react to a completed run (webhook, Slack,
   etc.) — **not yet built**, no committed timeline

## Naming

- Package/import name: `maarg` (Hindi: मार्ग, "path/route" — a direct semantic
  translation of "track")
- Live on PyPI (`pip install maarg`) and GitHub (public repo)
- Still to verify: maarg.dev / maarg.io / readthedocs domain (manual registrar
  check) — low priority, not blocking anything

## License

MIT

## Open decisions

- [ ] Domain availability check (maarg.dev / maarg.io / readthedocs)
- [ ] Whether/how to support step-wise, imperative logging (per-epoch metrics
      inside a loop) without compromising the zero-instrumentation identity —
      needs its own dedicated design conversation before any implementation,
      not a routine roadmap item
- [ ] Free-form run tags (`tags=[...]`) — real gap identified via dogfooding,
      not yet designed (would need a first-class `Run.tags` field, not reuse
      of `other`)

## Roadmap

- **Phase 0:** Repo scaffolding, PLANNING.md, license, CI skeleton — **done**
- **Phase 1:** Core `@track` decorator + input filtering + local SQLite
  storage — **done**
- **Phase 2:** Output classification (metrics, dicts, figures) — **done**
  (originally shipped with matplotlib as a hardcoded special case; generalized
  through the serializer registry in 0.3.0)
- **Phase 3:** Query API — **done** (CLI deliberately deferred, see above)
- **Phase 4:** README, logo, CI badges, public GitHub repo, PyPI release —
  **done**
- **0.3.0 — Robust Capture (current focus):** see below
- **0.4.0 (tentative):** CLI, if real user demand emerges
- **Later / post-v1:** Dashboard as a separate package, additional storage
  backends, free-form tags, the step-wise logging design question

## 0.3.0 — Robust Capture

Theme: the core abstraction is right; this release hardens it so it can be
trusted with real experiments, rather than adding new surface area. Triggered
by a combination of real dogfooding (recommendation-engine) and an external
technical audit of the 0.2.0 codebase.

**Objectives:**

1. **Failure-safe tracking.** — **done**
   - Add a `strict: bool = False` parameter to `@track`.
   - On the **success path**: if `save()` fails, `strict=False` emits a
     `MaargTrackingWarning` and still returns the user's result unchanged;
     `strict=True` raises a `MaargTrackingError` chained from the storage
     exception.
   - On the **failure path**: if `save()` fails, always emit a
     `MaargTrackingWarning` regardless of `strict`. The user's original
     exception must reach them unchanged in every case. This is treated as a
     non-negotiable guarantee, not something a flag can override, since it's
     the core promise failure-tracking exists to keep.

2. **Artifact name sanitization.** — **done**
   `_capture.py` currently builds `artifacts_dir / f"{name}.png"` directly from
   a user-controlled dictionary key, allowing path-traversal-style names
   (e.g. `"../../something"`) to influence the resulting file path. Fix:
   sanitize the name or generate a safe identifier, independent of the
   user-facing artifact name.

3. **SQLite indexes** on `function`, `experiment`, and `timestamp` — **done**
   Cheap, no behavior change, matters once run counts grow past a few
   thousand.

4. **Serializer registry.** — **done**
   Replace the hardcoded `_is_matplotlib_figure()` check in `_capture.py` with
   a real, extensible registration mechanism, so adding support for a new
   output type (Plotly, PIL, a custom result class) doesn't require editing
   core code. This was always planned (see Architecture above) and is now
   overdue.

**Explicitly deferred past 0.3.0** (known, not forgotten):

- Deeper JSON/edge-case serialization hardening as its own pass: NaN/Infinity,
  numpy scalar types, tuple round-tripping, Decimal, and treating dictionary
  *keys* (not just values) as a first-class validation concern
- Multi-metric sorting in `top_n`/`best_run` (sort by metric A then B)
- The CLI
- The step-wise/imperative logging design question

Last Updated: 2026-10-03
