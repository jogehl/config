//! Type-safe configuration loading, validation, and serialization.
//!
//! # Quick Start
//!
//! ```
//! use garde::Validate;
//! use schemars::JsonSchema;
//! use serde::{Deserialize, Serialize};
//! use simple_config_builder_core::{
//!     load_from_str, schema_for_type, validate, write_to_string, ConfigFormat,
//! };
//!
//! #[derive(Debug, Clone, PartialEq, Serialize, Deserialize, JsonSchema, Validate)]
//! struct Config {
//!     #[garde(length(min = 1))]
//!     name: String,
//!     #[garde(range(min = 1, max = 65535))]
//!     port: u16,
//! }
//!
//! let config = Config { name: "demo".into(), port: 8080 };
//! validate(&config).unwrap();
//!
//! let json = write_to_string(&config, ConfigFormat::Json).unwrap();
//! let decoded: Config = load_from_str(&json, ConfigFormat::Json).unwrap();
//! assert_eq!(decoded, config);
//!
//! let schema = schema_for_type::<Config>().unwrap();
//! assert!(schema["properties"]["name"].is_object());
//! ```

use garde::Validate;
use schemars::{schema_for, JsonSchema};
use serde::de::DeserializeOwned;
use serde::{Deserialize, Serialize};
use serde_json::{Map, Value};
use std::env;
use std::fmt::{Display, Formatter};
use std::fs;
use std::path::Path;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ConfigFormat {
    Json,
    #[cfg(feature = "yaml")]
    Yaml,
    #[cfg(feature = "toml")]
    Toml,
}

impl ConfigFormat {
    /// Parses a format name string into a [`ConfigFormat`] variant.
    ///
    /// Accepts `"json"`, `"yaml"` / `"yml"` (requires `yaml` feature), and
    /// `"toml"` (requires `toml` feature), case-insensitively.
    ///
    /// # Examples
    ///
    /// ```
    /// use simple_config_builder_core::ConfigFormat;
    ///
    /// assert_eq!(ConfigFormat::from_name("JSON").unwrap(), ConfigFormat::Json);
    /// assert_eq!(ConfigFormat::from_name("json").unwrap(), ConfigFormat::Json);
    /// assert!(ConfigFormat::from_name("xml").is_err());
    /// ```
    pub fn from_name(name: &str) -> Result<Self, ConfigError> {
        match name.to_ascii_lowercase().as_str() {
            "json" => Ok(Self::Json),
            #[cfg(feature = "yaml")]
            "yaml" | "yml" => Ok(Self::Yaml),
            #[cfg(feature = "toml")]
            "toml" => Ok(Self::Toml),
            _ => Err(ConfigError::UnsupportedFormat(name.to_string())),
        }
    }
}

#[derive(Debug)]
pub enum ConfigError {
    Io(std::io::Error),
    Json(serde_json::Error),
    #[cfg(feature = "yaml")]
    Yaml(serde_yml::Error),
    #[cfg(feature = "toml")]
    TomlDeserialize(toml::de::Error),
    #[cfg(feature = "toml")]
    TomlSerialize(toml::ser::Error),
    Validation(String),
    UnsupportedFormat(String),
}

impl Display for ConfigError {
    fn fmt(&self, f: &mut Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Io(error) => write!(f, "{error}"),
            Self::Json(error) => write!(f, "{error}"),
            #[cfg(feature = "yaml")]
            Self::Yaml(error) => write!(f, "{error}"),
            #[cfg(feature = "toml")]
            Self::TomlDeserialize(error) => write!(f, "{error}"),
            #[cfg(feature = "toml")]
            Self::TomlSerialize(error) => write!(f, "{error}"),
            Self::Validation(error) => write!(f, "{error}"),
            Self::UnsupportedFormat(name) => {
                write!(f, "Unsupported config format: {name}")
            }
        }
    }
}

impl std::error::Error for ConfigError {}

impl From<std::io::Error> for ConfigError {
    fn from(value: std::io::Error) -> Self {
        Self::Io(value)
    }
}

impl From<serde_json::Error> for ConfigError {
    fn from(value: serde_json::Error) -> Self {
        Self::Json(value)
    }
}

#[cfg(feature = "yaml")]
impl From<serde_yml::Error> for ConfigError {
    fn from(value: serde_yml::Error) -> Self {
        Self::Yaml(value)
    }
}

#[cfg(feature = "toml")]
impl From<toml::de::Error> for ConfigError {
    fn from(value: toml::de::Error) -> Self {
        Self::TomlDeserialize(value)
    }
}

#[cfg(feature = "toml")]
impl From<toml::ser::Error> for ConfigError {
    fn from(value: toml::ser::Error) -> Self {
        Self::TomlSerialize(value)
    }
}

/// Demonstration module — shows how to apply the library's pattern to your own structs.
///
/// Copy the derive macros (`Serialize`, `Deserialize`, `JsonSchema`, `Validate`),
/// add `#[garde(...)]` constraints on fields, implement `Default`, then use the
/// top-level functions ([`validate`], [`load_from_str`], [`write_to_string`], …).
///
/// # Examples
///
/// ```
/// use simple_config_builder_core::example::{
///     standalone_config_defaults, standalone_config_schema, StandaloneConfig,
/// };
/// use simple_config_builder_core::{validate, write_to_string, ConfigFormat};
///
/// let config = StandaloneConfig::default();
/// validate(&config).unwrap();
///
/// let defaults = standalone_config_defaults().unwrap();
/// assert_eq!(defaults["port"], 8080);
///
/// let schema = standalone_config_schema().unwrap();
/// assert!(schema["properties"]["name"].is_object());
///
/// let yaml = write_to_string(&config, ConfigFormat::Yaml).unwrap();
/// assert!(yaml.contains("name:"));
/// ```
pub mod example {
    use super::*;

    #[derive(Debug, Clone, Serialize, Deserialize, JsonSchema, Validate, PartialEq, Eq)]
    pub struct StandaloneConfig {
        #[garde(length(min = 1))]
        pub name: String,
        #[garde(length(min = 1))]
        pub host: String,
        #[garde(range(min = 1, max = 65535))]
        pub port: u16,
        #[garde(skip)]
        pub enabled: bool,
        #[garde(length(min = 1))]
        pub profile: String,
    }

    impl Default for StandaloneConfig {
        fn default() -> Self {
            Self {
                name: "simple-config".to_string(),
                host: "127.0.0.1".to_string(),
                port: 8080,
                enabled: true,
                profile: "default".to_string(),
            }
        }
    }

    pub fn validate_standalone_config_map(value: Value) -> Result<StandaloneConfig, ConfigError> {
        let config: StandaloneConfig = serde_json::from_value(value)?;
        super::validate(&config)?;
        Ok(config)
    }

    pub fn standalone_config_schema() -> Result<Value, ConfigError> {
        super::schema_for_type::<StandaloneConfig>()
    }

    pub fn standalone_config_defaults() -> Result<Value, ConfigError> {
        serde_json::to_value(StandaloneConfig::default()).map_err(ConfigError::from)
    }

    pub fn standalone_config_to_value(config: &StandaloneConfig) -> Result<Value, ConfigError> {
        serde_json::to_value(config).map_err(ConfigError::from)
    }

    pub fn standalone_config_from_path(
        path: impl AsRef<Path>,
        format: ConfigFormat,
    ) -> Result<StandaloneConfig, ConfigError> {
        super::load_from_path(path, format)
    }

    pub fn standalone_config_to_path(
        path: impl AsRef<Path>,
        value: &StandaloneConfig,
        format: ConfigFormat,
    ) -> Result<(), ConfigError> {
        super::write_to_path(path, value, format)
    }

    pub fn standalone_config_merge_defaults(
        overrides: Value,
    ) -> Result<StandaloneConfig, ConfigError> {
        let mut base = match standalone_config_defaults()? {
            Value::Object(map) => map,
            _ => Map::new(),
        };
        let overrides = match overrides {
            Value::Object(map) => map,
            _ => {
                return Err(ConfigError::Validation(
                    "StandaloneConfig overrides must be a JSON object".to_string(),
                ))
            }
        };
        for (key, value) in overrides {
            base.insert(key, value);
        }
        validate_standalone_config_map(Value::Object(base))
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DynamicFieldSchema {
    pub name: String,
    pub annotation: Option<String>,
    pub required: bool,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum DynamicFieldKind {
    ExplicitField,
    PlainDefault,
    Required,
}

#[derive(Debug, Clone, PartialEq)]
pub struct DynamicFieldDefinition {
    pub name: String,
    pub annotation: Option<String>,
    pub kind: DynamicFieldKind,
    pub required: bool,
    pub has_default: bool,
    pub has_default_factory: bool,
    pub gt: Option<f64>,
    pub lt: Option<f64>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum DynamicValueKind {
    String,
    Integer,
    Float,
    Boolean,
    List,
    Dict,
    Callable,
    Object,
}

#[derive(Debug, Clone, PartialEq)]
pub struct DynamicFieldValidation {
    pub name: String,
    pub annotation: Option<String>,
    pub kind: DynamicValueKind,
    pub numeric_value: Option<f64>,
    pub gt: Option<f64>,
    pub lt: Option<f64>,
    pub literal_matches: Option<bool>,
    pub type_matches: Option<bool>,
}

fn schema_type_from_annotation(annotation: Option<&str>) -> &'static str {
    match annotation {
        Some("str") => "string",
        Some("int") => "integer",
        Some("float") => "number",
        Some("bool") => "boolean",
        Some("list") => "array",
        Some("dict") => "object",
        _ => "object",
    }
}

/// Returns `true` if the annotation string names a callable type.
///
/// Matches the literal `"Callable"` or any string ending in `".Callable"`
/// (e.g. `"typing.Callable"`).
///
/// # Examples
///
/// ```
/// use simple_config_builder_core::annotation_requires_callable;
///
/// assert!(annotation_requires_callable(Some("Callable")));
/// assert!(annotation_requires_callable(Some("typing.Callable")));
/// assert!(!annotation_requires_callable(Some("str")));
/// assert!(!annotation_requires_callable(None));
/// ```
pub fn annotation_requires_callable(annotation: Option<&str>) -> bool {
    matches!(annotation, Some("Callable"))
        || annotation.is_some_and(|annotation| annotation.ends_with(".Callable"))
}

/// Builds a minimal JSON Schema object for a dynamically-described config class.
///
/// This is used by the Python layer to generate schemas for `Configclass` subclasses
/// whose fields are declared at runtime rather than as Rust types.
///
/// # Examples
///
/// ```
/// use simple_config_builder_core::{build_dynamic_object_schema, DynamicFieldSchema};
///
/// let schema = build_dynamic_object_schema(
///     "MyConfig",
///     &[
///         DynamicFieldSchema { name: "host".into(), annotation: Some("str".into()), required: true },
///         DynamicFieldSchema { name: "debug".into(), annotation: Some("bool".into()), required: false },
///     ],
/// );
///
/// assert_eq!(schema["title"], "MyConfig");
/// assert_eq!(schema["properties"]["host"]["type"], "string");
/// assert_eq!(schema["required"], serde_json::json!(["host"]));
/// ```
pub fn build_dynamic_object_schema(title: &str, fields: &[DynamicFieldSchema]) -> Value {
    let properties = fields
        .iter()
        .map(|field| {
            (
                field.name.clone(),
                serde_json::json!({
                    "type": schema_type_from_annotation(field.annotation.as_deref())
                }),
            )
        })
        .collect::<Map<String, Value>>();
    let required = fields
        .iter()
        .filter(|field| field.required)
        .map(|field| Value::String(field.name.clone()))
        .collect::<Vec<_>>();

    serde_json::json!({
        "title": title,
        "type": "object",
        "properties": properties,
        "required": required,
    })
}

/// Normalizes raw field metadata into a [`DynamicFieldDefinition`].
///
/// Determines the [`DynamicFieldKind`] from the combination of flags and
/// computes whether the field is required.
///
/// # Examples
///
/// ```
/// use simple_config_builder_core::{normalize_dynamic_field_definition, DynamicFieldKind};
///
/// // Explicit Field() call with a default
/// let field = normalize_dynamic_field_definition(
///     "port", Some("int".into()), true, true, false, Some(0.0), None,
/// );
/// assert_eq!(field.kind, DynamicFieldKind::ExplicitField);
/// assert!(!field.required);
/// assert_eq!(field.gt, Some(0.0));
///
/// // Plain class-level default (no Field call)
/// let plain = normalize_dynamic_field_definition(
///     "host", Some("str".into()), false, true, false, None, None,
/// );
/// assert_eq!(plain.kind, DynamicFieldKind::PlainDefault);
///
/// // No default — required
/// let required = normalize_dynamic_field_definition(
///     "name", Some("str".into()), false, false, false, None, None,
/// );
/// assert_eq!(required.kind, DynamicFieldKind::Required);
/// assert!(required.required);
/// ```
pub fn normalize_dynamic_field_definition(
    name: impl Into<String>,
    annotation: Option<String>,
    has_explicit_field: bool,
    has_default: bool,
    has_default_factory: bool,
    gt: Option<f64>,
    lt: Option<f64>,
) -> DynamicFieldDefinition {
    let kind = if has_explicit_field {
        DynamicFieldKind::ExplicitField
    } else if has_default {
        DynamicFieldKind::PlainDefault
    } else {
        DynamicFieldKind::Required
    };

    DynamicFieldDefinition {
        name: name.into(),
        annotation,
        kind,
        required: !has_default && !has_default_factory,
        has_default,
        has_default_factory,
        gt,
        lt,
    }
}

/// Validates a single dynamic field value against its annotated constraints.
///
/// Checks numeric `gt`/`lt` bounds, literal membership, callable requirement,
/// and type match. Returns the first violation found.
///
/// # Examples
///
/// ```
/// use simple_config_builder_core::{validate_dynamic_field, DynamicFieldValidation, DynamicValueKind};
///
/// let valid = DynamicFieldValidation {
///     name: "port".into(),
///     annotation: Some("int".into()),
///     kind: DynamicValueKind::Integer,
///     numeric_value: Some(8080.0),
///     gt: Some(0.0),
///     lt: Some(65536.0),
///     literal_matches: None,
///     type_matches: Some(true),
/// };
/// assert!(validate_dynamic_field(&valid).is_ok());
///
/// // Value out of range
/// let invalid = DynamicFieldValidation { numeric_value: Some(0.0), ..valid };
/// assert!(validate_dynamic_field(&invalid).is_err());
/// ```
pub fn validate_dynamic_field(validation: &DynamicFieldValidation) -> Result<(), ConfigError> {
    let name = &validation.name;

    if let Some(gt) = validation.gt {
        let Some(number) = validation.numeric_value else {
            return Err(ConfigError::Validation(format!("{name} must be numeric")));
        };
        if number <= gt {
            return Err(ConfigError::Validation(format!(
                "{name} must be greater than {gt}"
            )));
        }
    }

    if let Some(lt) = validation.lt {
        let Some(number) = validation.numeric_value else {
            return Err(ConfigError::Validation(format!("{name} must be numeric")));
        };
        if number >= lt {
            return Err(ConfigError::Validation(format!(
                "{name} must be less than {lt}"
            )));
        }
    }

    if validation.literal_matches == Some(false) {
        return Err(ConfigError::Validation(format!(
            "{name} is not one of the allowed literal values"
        )));
    }

    if annotation_requires_callable(validation.annotation.as_deref())
        && validation.kind != DynamicValueKind::Callable
    {
        return Err(ConfigError::Validation(format!("{name} must be callable")));
    }

    if validation.type_matches == Some(false) {
        let expected = validation.annotation.as_deref().unwrap_or("object");
        return Err(ConfigError::Validation(format!(
            "{name} must be of type {expected}"
        )));
    }

    Ok(())
}

/// Runs `garde` validation on any type that derives [`Validate`].
///
/// # Examples
///
/// ```
/// # use serde::{Deserialize, Serialize};
/// # use schemars::JsonSchema;
/// use garde::Validate;
/// use simple_config_builder_core::validate;
///
/// #[derive(Serialize, Deserialize, JsonSchema, Validate)]
/// struct Config {
///     #[garde(length(min = 1))]
///     name: String,
/// }
///
/// assert!(validate(&Config { name: "ok".into() }).is_ok());
/// assert!(validate(&Config { name: String::new() }).is_err());
/// ```
pub fn validate<T>(value: &T) -> Result<(), ConfigError>
where
    T: Validate,
    T::Context: Default,
{
    value
        .validate()
        .map_err(|error| ConfigError::Validation(error.to_string()))
}

/// Deserializes and validates `content` in the given [`ConfigFormat`].
///
/// Deserialization and validation run together — an invalid document is
/// rejected even if it parses successfully.
///
/// # Examples
///
/// ```
/// # use serde::{Deserialize, Serialize};
/// # use schemars::JsonSchema;
/// use garde::Validate;
/// use simple_config_builder_core::{load_from_str, ConfigFormat};
///
/// #[derive(Debug, PartialEq, Serialize, Deserialize, JsonSchema, Validate)]
/// struct Config {
///     #[garde(length(min = 1))]
///     name: String,
///     #[garde(range(min = 1, max = 65535))]
///     port: u16,
/// }
///
/// let json = r#"{"name":"demo","port":8080}"#;
/// let cfg: Config = load_from_str(json, ConfigFormat::Json).unwrap();
/// assert_eq!(cfg.name, "demo");
/// assert_eq!(cfg.port, 8080);
///
/// // Invalid data is rejected after deserialization
/// let bad = r#"{"name":"","port":8080}"#;
/// assert!(load_from_str::<Config>(bad, ConfigFormat::Json).is_err());
/// ```
pub fn load_from_str<T>(content: &str, format: ConfigFormat) -> Result<T, ConfigError>
where
    T: DeserializeOwned + Validate,
    T::Context: Default,
{
    let value = match format {
        ConfigFormat::Json => serde_json::from_str(content)?,
        #[cfg(feature = "yaml")]
        ConfigFormat::Yaml => serde_yml::from_str(content)?,
        #[cfg(feature = "toml")]
        ConfigFormat::Toml => toml::from_str(content)?,
    };
    validate(&value)?;
    Ok(value)
}

/// Reads a file at `path`, then deserializes and validates it.
///
/// # Examples
///
/// ```no_run
/// # use serde::{Deserialize, Serialize};
/// # use schemars::JsonSchema;
/// use garde::Validate;
/// use simple_config_builder_core::{load_from_path, write_to_path, ConfigFormat};
///
/// #[derive(Debug, PartialEq, Serialize, Deserialize, JsonSchema, Validate)]
/// struct Config { #[garde(skip)] name: String }
///
/// let path = "/tmp/cfg_example.json";
/// write_to_path(path, &Config { name: "demo".into() }, ConfigFormat::Json).unwrap();
/// let loaded: Config = load_from_path(path, ConfigFormat::Json).unwrap();
/// assert_eq!(loaded.name, "demo");
/// ```
pub fn load_from_path<T>(path: impl AsRef<Path>, format: ConfigFormat) -> Result<T, ConfigError>
where
    T: DeserializeOwned + Validate,
    T::Context: Default,
{
    let content = fs::read_to_string(path)?;
    load_from_str(&content, format)
}

/// Coerces a raw env-var string to the JSON type of the existing field value.
fn coerce_env_string(raw: String, target: &Value) -> Value {
    match target {
        Value::Number(_) => {
            if let Ok(n) = raw.parse::<i64>() {
                return Value::Number(n.into());
            }
            if let Ok(f) = raw.parse::<f64>() {
                if let Some(num) = serde_json::Number::from_f64(f) {
                    return Value::Number(num);
                }
            }
            Value::String(raw)
        }
        Value::Bool(_) => match raw.to_ascii_lowercase().as_str() {
            "true" | "1" | "yes" => Value::Bool(true),
            "false" | "0" | "no" => Value::Bool(false),
            _ => Value::String(raw),
        },
        _ => Value::String(raw),
    }
}

/// Loads a config file at `path`, then overrides top-level fields from
/// environment variables named `{PREFIX}_{FIELD}` (upper-cased).
///
/// Only fields that already exist in the deserialized value are overridden.
/// The merged result is validated before returning.
///
/// # Examples
///
/// ```no_run
/// # use serde::{Deserialize, Serialize};
/// # use schemars::JsonSchema;
/// use garde::Validate;
/// use simple_config_builder_core::{load_with_env_overrides, write_to_path, ConfigFormat};
///
/// #[derive(Debug, PartialEq, Serialize, Deserialize, JsonSchema, Validate)]
/// struct Config {
///     #[garde(length(min = 1))]
///     host: String,
///     #[garde(skip)]
///     debug: bool,
/// }
///
/// // APP_HOST=db.example.com overrides the "host" field.
/// // std::env::set_var("APP_HOST", "db.example.com");
/// let cfg: Config = load_with_env_overrides("/tmp/svc.json", ConfigFormat::Json, "APP").unwrap();
/// ```
pub fn load_with_env_overrides<T>(
    path: impl AsRef<Path>,
    format: ConfigFormat,
    env_prefix: &str,
) -> Result<T, ConfigError>
where
    T: DeserializeOwned + Serialize + Validate,
    T::Context: Default,
{
    let base: T = load_from_path(path, format)?;
    let mut map = match serde_json::to_value(&base).map_err(ConfigError::from)? {
        Value::Object(m) => m,
        _ => {
            return Err(ConfigError::Validation(
                "Config root must be a JSON object".to_string(),
            ))
        }
    };

    let prefix = format!("{}_", env_prefix.to_uppercase());
    for (key, raw_val) in env::vars() {
        let Some(field) = key.strip_prefix(&prefix) else {
            continue;
        };
        let field = field.to_lowercase();
        if let Some(existing) = map.get(&field) {
            let coerced = coerce_env_string(raw_val, existing);
            map.insert(field, coerced);
        }
    }

    let merged: T = serde_json::from_value(Value::Object(map))?;
    validate(&merged)?;
    Ok(merged)
}

/// Serializes `value` to a pretty-printed string in the given [`ConfigFormat`].
///
/// # Examples
///
/// ```
/// # use serde::{Deserialize, Serialize};
/// # use schemars::JsonSchema;
/// use garde::Validate;
/// use simple_config_builder_core::{write_to_string, ConfigFormat};
///
/// #[derive(Serialize, Deserialize, JsonSchema, Validate)]
/// struct Config { #[garde(skip)] name: String }
///
/// let json = write_to_string(&Config { name: "demo".into() }, ConfigFormat::Json).unwrap();
/// assert!(json.contains(r#""name": "demo""#));
/// ```
pub fn write_to_string<T>(value: &T, format: ConfigFormat) -> Result<String, ConfigError>
where
    T: Serialize,
{
    match format {
        ConfigFormat::Json => Ok(serde_json::to_string_pretty(value)?),
        #[cfg(feature = "yaml")]
        ConfigFormat::Yaml => Ok(serde_yml::to_string(value)?),
        #[cfg(feature = "toml")]
        ConfigFormat::Toml => Ok(toml::to_string_pretty(value)?),
    }
}

/// Serializes `value` and writes it to `path`, creating or overwriting the file.
///
/// # Examples
///
/// ```no_run
/// # use serde::{Deserialize, Serialize};
/// # use schemars::JsonSchema;
/// use garde::Validate;
/// use simple_config_builder_core::{write_to_path, ConfigFormat};
///
/// #[derive(Serialize, Deserialize, JsonSchema, Validate)]
/// struct Config { #[garde(skip)] name: String }
///
/// write_to_path("/tmp/out.json", &Config { name: "demo".into() }, ConfigFormat::Json).unwrap();
/// ```
pub fn write_to_path<T>(
    path: impl AsRef<Path>,
    value: &T,
    format: ConfigFormat,
) -> Result<(), ConfigError>
where
    T: Serialize,
{
    let content = write_to_string(value, format)?;
    fs::write(path, content)?;
    Ok(())
}

/// Returns the JSON Schema for type `T` as a [`serde_json::Value`].
///
/// Uses [`schemars`] under the hood. `T` must derive [`JsonSchema`].
///
/// # Examples
///
/// ```
/// # use serde::{Deserialize, Serialize};
/// use garde::Validate;
/// use schemars::JsonSchema;
/// use simple_config_builder_core::schema_for_type;
///
/// #[derive(Serialize, Deserialize, JsonSchema, Validate)]
/// struct Config { #[garde(skip)] host: String, #[garde(skip)] port: u16 }
///
/// let schema = schema_for_type::<Config>().unwrap();
/// let props = schema["properties"].as_object().unwrap();
/// assert!(props.contains_key("host"));
/// assert!(props.contains_key("port"));
/// ```
pub fn schema_for_type<T>() -> Result<Value, ConfigError>
where
    T: JsonSchema,
{
    serde_json::to_value(schema_for!(T)).map_err(ConfigError::from)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[derive(Debug, Clone, Serialize, Deserialize, JsonSchema, Validate, PartialEq, Eq)]
    struct NestedDatabaseConfig {
        #[garde(length(min = 1))]
        host: String,
        #[garde(range(min = 1, max = 65535))]
        port: u16,
    }

    #[derive(Debug, Clone, Serialize, Deserialize, JsonSchema, Validate, PartialEq, Eq)]
    struct NestedStandaloneConfig {
        #[garde(length(min = 1))]
        name: String,
        #[garde(dive)]
        database: NestedDatabaseConfig,
        #[garde(skip)]
        enabled: bool,
    }

    #[test]
    fn standalone_config_schema_has_required_properties() {
        let schema = example::standalone_config_schema().unwrap();
        let properties = schema
            .get("properties")
            .and_then(|value| value.as_object())
            .unwrap();

        assert!(properties.contains_key("name"));
        assert!(properties.contains_key("port"));
    }

    #[test]
    fn standalone_config_validation_rejects_invalid_port() {
        let err = example::validate_standalone_config_map(serde_json::json!({
            "name": "demo",
            "host": "127.0.0.1",
            "port": 0,
            "enabled": true,
            "profile": "dev"
        }))
        .unwrap_err();

        assert!(err.to_string().contains("port"));
    }

    #[test]
    fn standalone_config_round_trips_json() {
        let config = example::StandaloneConfig::default();
        let text = write_to_string(&config, ConfigFormat::Json).unwrap();
        let decoded: example::StandaloneConfig = load_from_str(&text, ConfigFormat::Json).unwrap();

        assert_eq!(decoded, config);
    }

    #[test]
    fn dynamic_object_schema_maps_builtin_types() {
        let schema = build_dynamic_object_schema(
            "Example",
            &[
                DynamicFieldSchema {
                    name: "name".to_string(),
                    annotation: Some("str".to_string()),
                    required: true,
                },
                DynamicFieldSchema {
                    name: "enabled".to_string(),
                    annotation: Some("bool".to_string()),
                    required: false,
                },
            ],
        );

        assert_eq!(schema["title"], "Example");
        assert_eq!(schema["properties"]["name"]["type"], "string");
        assert_eq!(schema["properties"]["enabled"]["type"], "boolean");
        assert_eq!(schema["required"], serde_json::json!(["name"]));
    }

    #[test]
    fn normalize_dynamic_field_definition_tracks_field_kinds() {
        let explicit = normalize_dynamic_field_definition(
            "port",
            Some("int".to_string()),
            true,
            true,
            false,
            Some(0.0),
            Some(10.0),
        );
        assert_eq!(explicit.kind, DynamicFieldKind::ExplicitField);
        assert!(!explicit.required);
        assert_eq!(explicit.gt, Some(0.0));

        let plain_default = normalize_dynamic_field_definition(
            "host",
            Some("str".to_string()),
            false,
            true,
            false,
            None,
            None,
        );
        assert_eq!(plain_default.kind, DynamicFieldKind::PlainDefault);
        assert!(!plain_default.required);

        let required = normalize_dynamic_field_definition(
            "name",
            Some("str".to_string()),
            false,
            false,
            false,
            None,
            None,
        );
        assert_eq!(required.kind, DynamicFieldKind::Required);
        assert!(required.required);
    }

    #[test]
    fn validate_dynamic_field_reports_numeric_and_type_errors() {
        let error = validate_dynamic_field(&DynamicFieldValidation {
            name: "port".to_string(),
            annotation: Some("int".to_string()),
            kind: DynamicValueKind::String,
            numeric_value: None,
            gt: Some(0.0),
            lt: None,
            literal_matches: None,
            type_matches: Some(false),
        })
        .unwrap_err();

        assert_eq!(error.to_string(), "port must be numeric");
    }

    #[test]
    fn validate_dynamic_field_reports_callable_and_literal_errors() {
        let callable_error = validate_dynamic_field(&DynamicFieldValidation {
            name: "handler".to_string(),
            annotation: Some("Callable".to_string()),
            kind: DynamicValueKind::Object,
            numeric_value: None,
            gt: None,
            lt: None,
            literal_matches: None,
            type_matches: None,
        })
        .unwrap_err();
        assert_eq!(callable_error.to_string(), "handler must be callable");

        let literal_error = validate_dynamic_field(&DynamicFieldValidation {
            name: "mode".to_string(),
            annotation: Some("typing.Literal['dev', 'prod']".to_string()),
            kind: DynamicValueKind::String,
            numeric_value: None,
            gt: None,
            lt: None,
            literal_matches: Some(false),
            type_matches: None,
        })
        .unwrap_err();
        assert_eq!(
            literal_error.to_string(),
            "mode is not one of the allowed literal values"
        );
    }

    #[test]
    fn nested_standalone_config_round_trips_yaml() {
        let config = NestedStandaloneConfig {
            name: "demo".to_string(),
            database: NestedDatabaseConfig {
                host: "localhost".to_string(),
                port: 5432,
            },
            enabled: true,
        };

        validate(&config).unwrap();
        let text = write_to_string(&config, ConfigFormat::Yaml).unwrap();
        let decoded: NestedStandaloneConfig = load_from_str(&text, ConfigFormat::Yaml).unwrap();
        let schema = schema_for_type::<NestedStandaloneConfig>().unwrap();

        assert_eq!(decoded, config);
        assert_eq!(
            schema["properties"]["database"]["$ref"],
            "#/$defs/NestedDatabaseConfig"
        );
    }
}
