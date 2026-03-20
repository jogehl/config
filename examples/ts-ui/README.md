# TypeScript React UI (full app)

This is a complete React + TypeScript UI for the `simple_config_builder` backend.

## What users can do

- enter a config file path
- load config data and inspect metadata
- choose a registered `Configclass`
- edit values via schema-driven form inputs
- edit the full config tree as raw JSON
- validate against selected class
- save in inferred file format (`json`/`yaml`/`toml`)
- see warning if file changed externally (multi-user/process-safe signal)

## Run

1. Start backend:

```bash
simple_config_builder start --host 0.0.0.0 --port 8000
```

2. Start UI:

```bash
cd examples/ts-ui
npm install
npm run dev
```

The app runs on `http://localhost:5173` by default and talks to backend at `http://localhost:8000/api/v1`.
