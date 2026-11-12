# Changelog

All notable changes to maarg are documented here.

## [0.4.1] — 2026-11-13

### Fixed

- Handle dictionary outputs with non-string keys safely, preventing key changes during SQLite JSON serialization.

### Added

- Regression tests for non-string dictionary keys.
- SQLite round-trip test to verify structured dictionary outputs retain their values.

### Changed

- Centered the logo and main headings in the Code of Conduct and Security Policy documents.

## [0.4.0] — 2026-11-11

### Added

- Structured dictionary output capture in `run.metrics`, preserving
  JSON-compatible nested dictionaries and lists.
- Support for preserving numeric values, booleans, strings, and `None`
  within structured dictionary outputs.

### Changed

- `top_n()` and `best_run()` continue to rank scalar numeric metrics.
- Boolean values are excluded from numeric metric ranking.
- Updated output capture documentation and regression tests.

## [0.3.1] — 2026-10-04

### Changed

- Updated project metadata and release documentation for the 0.3.1 release.
- Migrated the project license from MIT to Apache License 2.0.
- Updated project documentation, branding, and planning materials.
- Refined package metadata and PyPI-facing project information.

## [0.3.0] — 2026-10-03

### Added

- Failure-safe tracking with `strict` mode for successful runs.
- `MaargTrackingError` and `MaargTrackingWarning` for tracking failures.
- Artifact filename sanitization to prevent path-traversal-style filenames.
- SQLite indexes on `function`, `experiment`, and `timestamp`.
- Extensible serializer registry for custom artifact/result types.

### Changed

- Failure tracking now preserves the original user exception even if
  persistence fails.
- Matplotlib figure capture now uses the serializer registry.

## [0.2.0.post1]

Previous release.
