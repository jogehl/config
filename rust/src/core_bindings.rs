use pyo3::prelude::*;
use pyo3::types::{PyAny, PyModule};

use simple_config_builder_core::{
    example::{
        standalone_config_defaults, standalone_config_from_path, standalone_config_merge_defaults,
        standalone_config_schema, standalone_config_to_path, standalone_config_to_value,
        validate_standalone_config_map,
    },
    ConfigError, ConfigFormat,
};

use crate::io::{json_value_to_py, py_to_json_value};

fn to_py_error(error: ConfigError) -> PyErr {
    match error {
        ConfigError::Io(error) => pyo3::exceptions::PyOSError::new_err(error.to_string()),
        ConfigError::Validation(error) => pyo3::exceptions::PyValueError::new_err(error),
        error => pyo3::exceptions::PyValueError::new_err(error.to_string()),
    }
}

fn parse_format(format: &str) -> PyResult<ConfigFormat> {
    ConfigFormat::from_name(format).map_err(to_py_error)
}

#[pyfunction]
fn rust_core_schema(py: Python<'_>) -> PyResult<Py<PyAny>> {
    json_value_to_py(py, standalone_config_schema().map_err(to_py_error)?)
}

#[pyfunction]
fn rust_core_defaults(py: Python<'_>) -> PyResult<Py<PyAny>> {
    json_value_to_py(py, standalone_config_defaults().map_err(to_py_error)?)
}

#[pyfunction]
fn rust_core_validate(py: Python<'_>, data: Bound<'_, PyAny>) -> PyResult<Py<PyAny>> {
    let value = py_to_json_value(&data)?;
    let config = validate_standalone_config_map(value).map_err(to_py_error)?;
    json_value_to_py(
        py,
        standalone_config_to_value(&config).map_err(to_py_error)?,
    )
}

#[pyfunction]
#[pyo3(signature = (path, format))]
fn rust_core_load(py: Python<'_>, path: String, format: &str) -> PyResult<Py<PyAny>> {
    let config = standalone_config_from_path(path, parse_format(format)?).map_err(to_py_error)?;
    json_value_to_py(
        py,
        standalone_config_to_value(&config).map_err(to_py_error)?,
    )
}

#[pyfunction]
#[pyo3(signature = (path, data, format))]
fn rust_core_write(path: String, data: Bound<'_, PyAny>, format: &str) -> PyResult<()> {
    let value = py_to_json_value(&data)?;
    let config = validate_standalone_config_map(value).map_err(to_py_error)?;
    standalone_config_to_path(path, &config, parse_format(format)?).map_err(to_py_error)
}

#[pyfunction]
fn rust_core_apply_defaults(py: Python<'_>, overrides: Bound<'_, PyAny>) -> PyResult<Py<PyAny>> {
    let value = py_to_json_value(&overrides)?;
    let config = standalone_config_merge_defaults(value).map_err(to_py_error)?;
    json_value_to_py(
        py,
        standalone_config_to_value(&config).map_err(to_py_error)?,
    )
}

pub(crate) fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(rust_core_schema, m)?)?;
    m.add_function(wrap_pyfunction!(rust_core_defaults, m)?)?;
    m.add_function(wrap_pyfunction!(rust_core_validate, m)?)?;
    m.add_function(wrap_pyfunction!(rust_core_load, m)?)?;
    m.add_function(wrap_pyfunction!(rust_core_write, m)?)?;
    m.add_function(wrap_pyfunction!(rust_core_apply_defaults, m)?)?;
    Ok(())
}
