# TypeScript UI starter

This folder contains a lightweight TypeScript API client for the GUI backend.

## Quick start

1. Start backend:

```bash
simple_config_builder start --host 0.0.0.0 --port 8000
```

2. Use `ConfigBuilderApiClient` in your UI app to:
- list classes
- fetch JSON schema / normalized schema
- validate drafts
- save configs
- poll file metadata (`mtime_ns`, `sha256`) to detect external changes

## Notes

The backend is stateless by default (no UI session token handling required).
