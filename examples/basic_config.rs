//! Basic usage of `simple_config_builder_core`.
//!
//! Run with:
//!   cargo run --example basic_config

use garde::Validate;
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};
use simple_config_builder_core::{
    load_from_str, schema_for_type, validate, write_to_string, ConfigFormat,
};

// ── Define your config structs with standard derive macros ──────────────────

#[derive(Debug, Clone, Serialize, Deserialize, JsonSchema, Validate, PartialEq)]
struct DatabaseConfig {
    /// Hostname or IP address of the database server.
    #[garde(length(min = 1))]
    host: String,
    /// Port number (1–65535).
    #[garde(range(min = 1, max = 65535))]
    port: u16,
    /// Maximum number of connections in the pool.
    #[garde(range(min = 1, max = 256))]
    max_connections: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize, JsonSchema, Validate, PartialEq)]
struct AppConfig {
    /// Human-readable name for this deployment.
    #[garde(length(min = 1))]
    name: String,
    /// Environment tag, e.g. "dev", "staging", "prod".
    #[garde(length(min = 1))]
    environment: String,
    /// Nested database configuration.
    #[garde(dive)]
    database: DatabaseConfig,
    /// Feature flag — skipped by garde validation.
    #[garde(skip)]
    debug: bool,
}

impl Default for AppConfig {
    fn default() -> Self {
        Self {
            name: "my-app".to_string(),
            environment: "dev".to_string(),
            database: DatabaseConfig {
                host: "localhost".to_string(),
                port: 5432,
                max_connections: 10,
            },
            debug: false,
        }
    }
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    // ── 1. Validate a value ──────────────────────────────────────────────────
    let config = AppConfig::default();
    validate(&config)?;
    println!("✓ Default config is valid");

    // ── 2. Serialize to YAML / JSON / TOML ──────────────────────────────────
    let yaml = write_to_string(&config, ConfigFormat::Yaml)?;
    println!("\n── YAML ────────────────────────────────\n{yaml}");

    let json = write_to_string(&config, ConfigFormat::Json)?;
    println!("── JSON ────────────────────────────────\n{json}\n");

    let toml_str = write_to_string(&config, ConfigFormat::Toml)?;
    println!("── TOML ────────────────────────────────\n{toml_str}");

    // ── 3. Deserialize and validate back ────────────────────────────────────
    let decoded: AppConfig = load_from_str(&yaml, ConfigFormat::Yaml)?;
    assert_eq!(decoded, config);
    println!("✓ YAML round-trip succeeded");

    // ── 4. Generate JSON Schema ──────────────────────────────────────────────
    let schema = schema_for_type::<AppConfig>()?;
    println!(
        "── JSON Schema (top-level properties) ──\n{}",
        serde_json::to_string_pretty(schema.get("properties").unwrap())?
    );

    // ── 5. Demonstrate validation error ─────────────────────────────────────
    let bad_config = AppConfig {
        name: String::new(), // violates length(min = 1)
        ..AppConfig::default()
    };
    match validate(&bad_config) {
        Err(e) => println!("\n✓ Caught expected validation error: {e}"),
        Ok(_) => panic!("Should have failed validation"),
    }

    Ok(())
}
