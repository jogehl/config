# config

[![PyPI - Version](https://img.shields.io/pypi/v/config.svg)](https://pypi.org/project/simple_config_builder)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/config.svg)](https://pypi.org/project/simple_config_builder)

-----

## Table of Contents

- [Installation](#installation)
- [License](#license)

## Installation

```console
pip install simple_config_builder
```

## Architecture

The package now has two layers:

- `simple_config_builder_core`: pure Rust validation, schema generation, and JSON/YAML/TOML IO with no PyO3 dependency
- `simple_config_builder`: Python bindings and the existing dynamic `Configclass` API on top of the Rust implementation

This keeps Rust as the source of truth for standalone config validation and file handling, while preserving a Python-facing API.

## Rust-Only Example

```rust
use garde::Validate;
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};
use simple_config_builder_core::{
	schema_for_type, load_from_str, validate, write_to_string, ConfigFormat,
};

#[derive(Debug, Clone, Serialize, Deserialize, JsonSchema, Validate, PartialEq, Eq)]
struct DatabaseConfig {
	#[garde(length(min = 1))]
	host: String,
	#[garde(range(min = 1, max = 65535))]
	port: u16,
}

#[derive(Debug, Clone, Serialize, Deserialize, JsonSchema, Validate, PartialEq, Eq)]
struct ServerConfig {
	#[garde(length(min = 1))]
	name: String,
	#[garde(dive)]
	database: DatabaseConfig,
	#[garde(skip)]
	enabled: bool,
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
	let config = ServerConfig {
		name: "demo".to_string(),
		database: DatabaseConfig {
			host: "localhost".to_string(),
			port: 5432,
		},
		enabled: true,
	};

	validate(&config)?;
	let yaml = write_to_string(&config, ConfigFormat::Yaml)?;
	let decoded: ServerConfig = load_from_str(&yaml, ConfigFormat::Yaml)?;
	let schema = schema_for_type::<ServerConfig>()?;

	assert_eq!(decoded, config);
	assert_eq!(schema["properties"]["database"]["$ref"], "#/$defs/DatabaseConfig");
	Ok(())
}
```

## License

`simple_config_builder` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.
