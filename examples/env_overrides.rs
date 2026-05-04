//! Demonstrates loading a config file and overriding fields via environment
//! variables using `load_with_env_overrides`.
//!
//! Run with:
//!   APP_HOST=db.example.com APP_PORT=3306 cargo run --example env_overrides

use garde::Validate;
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};
use simple_config_builder_core::{load_with_env_overrides, write_to_path, ConfigFormat};

#[derive(Debug, Clone, Serialize, Deserialize, JsonSchema, Validate, PartialEq)]
struct ServiceConfig {
    #[garde(length(min = 1))]
    host: String,
    #[garde(range(min = 1, max = 65535))]
    port: u16,
    #[garde(length(min = 1))]
    profile: String,
    #[garde(skip)]
    debug: bool,
}

impl Default for ServiceConfig {
    fn default() -> Self {
        Self {
            host: "localhost".to_string(),
            port: 8080,
            profile: "default".to_string(),
            debug: false,
        }
    }
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Write a baseline config file to a temporary path.
    let tmp = std::env::temp_dir().join("service_config.yaml");
    let base = ServiceConfig::default();
    write_to_path(&tmp, &base, ConfigFormat::Yaml)?;
    println!("Wrote baseline config to {}", tmp.display());
    println!("  host={}  port={}  profile={}", base.host, base.port, base.profile);

    // Load with env-var overrides.
    // Fields are matched by {PREFIX}_{FIELD} (upper-cased).
    // e.g.  APP_HOST=db.example.com  APP_PORT=3306
    let config: ServiceConfig =
        load_with_env_overrides(&tmp, ConfigFormat::Yaml, "APP")?;

    println!("\nAfter APP_* env-var overrides:");
    println!("  host={}  port={}  profile={}", config.host, config.port, config.profile);

    if config.host != base.host {
        println!("  → host overridden by APP_HOST");
    }
    if config.port != base.port {
        println!("  → port overridden by APP_PORT");
    }
    if config.profile != base.profile {
        println!("  → profile overridden by APP_PROFILE");
    }

    Ok(())
}
