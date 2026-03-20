# config

[![PyPI - Version](https://img.shields.io/pypi/v/config.svg)](https://pypi.org/project/simple_config_builder)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/config.svg)](https://pypi.org/project/simple_config_builder)

-----

## Installation

```console
pip install simple_config_builder
```

> Python requirement: **>3.12**

## GUI backend + TypeScript UI support

The package includes a FastAPI backend with endpoints for schema-driven UIs:

- `GET /api/v1/formats`
- `GET /api/v1/get-config-classes`
- `GET /api/v1/get-config-class/{class_name}`
- `POST /api/v1/load-config`
- `POST /api/v1/validate-config`
- `POST /api/v1/save-config`
- `POST /api/v1/config-metadata` (for multi-user change detection)

Run the backend:

```console
simple_config_builder start --host localhost --port 8000
```

The API is stateless by default (no session token required).

A TypeScript starter API client is available at `examples/ts-ui/src/apiClient.ts`.

## License

`simple_config_builder` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.
