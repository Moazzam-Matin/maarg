# Changelog

All notable changes to maarg are documented here.

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
