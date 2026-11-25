# maarg UI

This directory is reserved for the optional maarg web interface.

The UI will be developed independently of the maarg core package.

## Design principles

- Keep UI dependencies separate from core dependencies.
- Do not modify core tracking behavior to support the UI.
- Use existing maarg storage and query APIs wherever possible.
- Keep the interface local-first initially.
