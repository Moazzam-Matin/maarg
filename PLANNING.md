# maarg — Project Planning

## Vision
A decorator that auto-captures a function's inputs and outputs via introspection
(signature + return value) and logs them — no `log_param()`, no `log_metric()`,
no boilerplate. Every existing experiment tracker (MLflow, W&B, Neptune, Comet,
Aim, Sacred) still requires you to write explicit logging calls. maarg's core
differentiator is that it doesn't.

## Who it's for
1. Individual researchers/data scientists running many small experiments
   (primary wedge use case)
2. Anyone re-running a parameterized function and comparing results —
   hyperparameter sweeps, algorithm benchmarking, backtests, simulations
   (broader addressable market, not ML-exclusive)
3. Small teams wanting lightweight tracking without standing up server
   infrastructure (not a v1 design target, but shouldn't be architecturally
   blocked later)

## v1 Scope
- `@track` decorator, zero-config by default
- Automatic input filtering: log small/simple values, skip large/complex objects
  (detection based on actual type/size, not name-guessing)
- Automatic output handling: numbers, dicts of numbers, figures/images,
  graceful fallback for unknown types
- Serializer registry: extensible support for new output types without
  touching core code
- Storage backend interface: local-first default (SQLite), pluggable for
  future backends
- Python query API + CLI to browse/filter/compare past runs

## v1 Non-goals
- No web dashboard (separate package, later)
- No distributed/multi-machine tracking server
- No experiment orchestration (integrate with Airflow/Optuna/Ray, don't
  compete with them)
- No auth/permissions/governance features
- No model registry / artifact versioning beyond file-path tracking

## Architecture — the three seams that matter
1. **Storage backend interface** — where runs live (SQLite now, anything later)
2. **Serializer registry** — how output types are recognized and captured
3. **Capture hooks/callbacks** — react to a completed run (webhook, Slack, etc.)

## Naming
- Package/import name: `maarg` (Hindi: मार्ग, "path/route" — a direct semantic
  translation of "track")
- Checked clear: PyPI, GitHub
- Still to verify: maarg.dev / maarg.io / readthedocs domain (manual registrar check)

## License
MIT

## Open decisions
- [ ] Domain availability check (maarg.dev / maarg.io / readthedocs)
- [ ] Repo visibility: private during initial scaffolding, public once
      README + working decorator + clean history are in place

## Roadmap (rough phases)
- **Phase 0:** Repo scaffolding, PLANNING.md, license, CI skeleton
- **Phase 1:** Core `@track` decorator + input filtering + local SQLite storage
- **Phase 2:** Output serializer registry (metrics, dicts, figures)
- **Phase 3:** Query API + CLI
- **Phase 4:** Docs site, examples (scikit-learn, PyTorch), go public
- **Phase 5 (post-v1):** Dashboard as separate package, more storage backends