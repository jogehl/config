use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList, PyModule, PyTuple};
use serde::Serialize;
use serde_json::ser::{PrettyFormatter, Serializer};
use serde_json::{Map, Number, Value};
use std::fs;
use std::path::Path;

use crate::get_registered_class;

pub(crate) fn py_to_json_value(value: &Bound<'_, PyAny>) -> PyResult<Value> {
    if value.hasattr("model_dump")? {
        return py_to_json_value(&value.call_method0("model_dump")?);
    }
    if value.is_none() {
        return Ok(Value::Null);
    }
    if let Ok(value) = value.extract::<bool>() {
        return Ok(Value::Bool(value));
    }
    if let Ok(value) = value.extract::<i64>() {
        return Ok(Value::Number(Number::from(value)));
    }
    if let Ok(value) = value.extract::<u64>() {
        return Ok(Value::Number(Number::from(value)));
    }
    if let Ok(value) = value.extract::<f64>() {
        let Some(number) = Number::from_f64(value) else {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "Cannot serialize non-finite float values.",
            ));
        };
        return Ok(Value::Number(number));
    }
    if let Ok(value) = value.extract::<String>() {
        return Ok(Value::String(value));
    }
    if let Ok(list) = value.cast::<PyList>() {
        return list
            .iter()
            .map(|item| py_to_json_value(&item))
            .collect::<PyResult<Vec<_>>>()
            .map(Value::Array);
    }
    if let Ok(tuple) = value.cast::<PyTuple>() {
        return tuple
            .iter()
            .map(|item| py_to_json_value(&item))
            .collect::<PyResult<Vec<_>>>()
            .map(Value::Array);
    }
    if let Ok(dict) = value.cast::<PyDict>() {
        let mut out = Map::new();
        for (key, value) in dict.iter() {
            out.insert(key.extract()?, py_to_json_value(&value)?);
        }
        return Ok(Value::Object(out));
    }

    Err(pyo3::exceptions::PyTypeError::new_err(format!(
        "Object of type {} is not config-serializable.",
        value.get_type().name()?
    )))
}

pub(crate) fn json_value_to_py(py: Python<'_>, value: Value) -> PyResult<Py<PyAny>> {
    match value {
        Value::Null => Ok(py.None()),
        Value::Bool(value) => Ok(value.into_pyobject(py)?.to_owned().into_any().unbind()),
        Value::Number(value) => {
            if let Some(value) = value.as_i64() {
                Ok(value.into_pyobject(py)?.into_any().unbind())
            } else if let Some(value) = value.as_u64() {
                Ok(value.into_pyobject(py)?.into_any().unbind())
            } else if let Some(value) = value.as_f64() {
                Ok(value.into_pyobject(py)?.into_any().unbind())
            } else {
                Err(pyo3::exceptions::PyValueError::new_err(
                    "Cannot parse JSON number.",
                ))
            }
        }
        Value::String(value) => Ok(value.into_pyobject(py)?.into_any().unbind()),
        Value::Array(values) => {
            let out = PyList::empty(py);
            for value in values {
                out.append(json_value_to_py(py, value)?)?;
            }
            Ok(out.into_any().unbind())
        }
        Value::Object(values) => {
            let out = PyDict::new(py);
            for (key, value) in values {
                out.set_item(key, json_value_to_py(py, value)?)?;
            }
            Ok(out.into_any().unbind())
        }
    }
}

fn config_type_name(config_type: &Bound<'_, PyAny>) -> PyResult<String> {
    if let Ok(value) = config_type.getattr("value") {
        return value.extract();
    }
    Ok(config_type.str()?.extract::<String>()?.to_lowercase())
}

#[pyfunction]
pub(crate) fn io_to_dict(py: Python<'_>, obj: Bound<'_, PyAny>) -> PyResult<Py<PyAny>> {
    json_value_to_py(py, py_to_json_value(&obj)?)
}

#[pyfunction]
pub(crate) fn io_parse_json(py: Python<'_>, config_file: String) -> PyResult<Py<PyAny>> {
    if !Path::new(&config_file).exists() {
        return Ok(PyDict::new(py).into_any().unbind());
    }
    let content = fs::read_to_string(config_file)?;
    let value = serde_json::from_str(&content)
        .map_err(|error| pyo3::exceptions::PyValueError::new_err(error.to_string()))?;
    json_value_to_py(py, value)
}

#[pyfunction]
pub(crate) fn io_parse_yaml(py: Python<'_>, config_file: String) -> PyResult<Py<PyAny>> {
    if !Path::new(&config_file).exists() {
        return Ok(PyDict::new(py).into_any().unbind());
    }
    let content = fs::read_to_string(config_file)?;
    let value = serde_yml::from_str(&content).map_err(|error: serde_yml::Error| {
        pyo3::exceptions::PyValueError::new_err(error.to_string())
    })?;
    json_value_to_py(py, value)
}

#[pyfunction]
pub(crate) fn io_parse_toml(py: Python<'_>, config_file: String) -> PyResult<Py<PyAny>> {
    if !Path::new(&config_file).exists() {
        return Ok(PyDict::new(py).into_any().unbind());
    }
    let content = fs::read_to_string(config_file)?;
    let value: toml::Value = toml::from_str(&content).map_err(|error: toml::de::Error| {
        pyo3::exceptions::PyValueError::new_err(error.to_string())
    })?;
    let value = serde_json::to_value(value)
        .map_err(|error| pyo3::exceptions::PyValueError::new_err(error.to_string()))?;
    json_value_to_py(py, value)
}

#[pyfunction]
pub(crate) fn io_construct_config(
    py: Python<'_>,
    config_data: Bound<'_, PyAny>,
) -> PyResult<Py<PyAny>> {
    if let Ok(list) = config_data.cast::<PyList>() {
        let out = PyList::empty(py);
        for item in list.iter() {
            out.append(io_construct_config(py, item)?)?;
        }
        return Ok(out.into_any().unbind());
    }

    let Ok(dict) = config_data.cast::<PyDict>() else {
        return Ok(config_data.unbind());
    };

    let out = PyDict::new(py);
    for (key, value) in dict.iter() {
        if key.extract::<String>().ok().as_deref() == Some("_config_class_type") {
            continue;
        }
        out.set_item(key, io_construct_config(py, value)?)?;
    }

    let Some(config_class_type) = dict.get_item("_config_class_type")? else {
        return Ok(out.into_any().unbind());
    };
    let config_class_type: String = config_class_type.extract().map_err(|_| {
        pyo3::exceptions::PyValueError::new_err(
            "The _config_class_type must be a string representing the class type.",
        )
    })?;
    let Some((config_class_module, _)) = config_class_type.rsplit_once('.') else {
        return Err(pyo3::exceptions::PyValueError::new_err(format!(
            "Please make sure the class '{config_class_type}' contains a module path."
        )));
    };

    PyModule::import(py, config_class_module).map_err(|_| {
        pyo3::exceptions::PyImportError::new_err(format!(
            "Could not import the module '{config_class_module}'. Please make sure the module is installed and available in the Python path."
        ))
    })?;
    let config_class = get_registered_class(py, &config_class_type).map_err(|_| {
        pyo3::exceptions::PyValueError::new_err(format!(
            "Please make sure the class '{config_class_type}' is in the module '{config_class_module}'."
        ))
    })?;
    let expected_fields = config_class
        .bind(py)
        .getattr("__config_fields__")?
        .cast_into::<PyDict>()?;
    for key in out.keys().iter() {
        let key_name: String = key.extract()?;
        if !expected_fields.contains(&key_name)? {
            return Err(pyo3::exceptions::PyValueError::new_err(format!(
                "Mismatched key in config data: {key_name}."
            )));
        }
    }

    Ok(config_class
        .bind(py)
        .call_method1("model_validate", (out,))?
        .unbind())
}

#[pyfunction]
pub(crate) fn io_parse_config(
    py: Python<'_>,
    config_file: String,
    config_type: Bound<'_, PyAny>,
) -> PyResult<Py<PyAny>> {
    let parsed = match config_type_name(&config_type)?.as_str() {
        "json" => io_parse_json(py, config_file)?,
        "yaml" => io_parse_yaml(py, config_file)?,
        "toml" => io_parse_toml(py, config_file)?,
        _ => {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "The configuration type is not supported.",
            ))
        }
    };
    io_construct_config(py, parsed.bind(py).clone())
}

#[pyfunction]
pub(crate) fn io_write_json(config_file: String, config_data: Bound<'_, PyAny>) -> PyResult<()> {
    let value = py_to_json_value(&config_data)?;
    let mut content = Vec::new();
    let formatter = PrettyFormatter::with_indent(b"    ");
    let mut serializer = Serializer::with_formatter(&mut content, formatter);
    value
        .serialize(&mut serializer)
        .map_err(|error| pyo3::exceptions::PyValueError::new_err(error.to_string()))?;
    let content = String::from_utf8(content)
        .map_err(|error| pyo3::exceptions::PyValueError::new_err(error.to_string()))?;
    fs::write(config_file, content)?;
    Ok(())
}

#[pyfunction]
pub(crate) fn io_write_yaml(config_file: String, config_data: Bound<'_, PyAny>) -> PyResult<()> {
    let value = py_to_json_value(&config_data)?;
    let content = serde_yml::to_string(&value).map_err(|error: serde_yml::Error| {
        pyo3::exceptions::PyValueError::new_err(error.to_string())
    })?;
    fs::write(config_file, content)?;
    Ok(())
}

#[pyfunction]
pub(crate) fn io_write_toml(config_file: String, config_data: Bound<'_, PyAny>) -> PyResult<()> {
    let value = py_to_json_value(&config_data)?;
    let content = toml::to_string(&value).map_err(|error: toml::ser::Error| {
        pyo3::exceptions::PyValueError::new_err(error.to_string())
    })?;
    fs::write(config_file, content)?;
    Ok(())
}

#[pyfunction]
pub(crate) fn io_write_config(
    config_file: String,
    data: Bound<'_, PyAny>,
    config_type: Bound<'_, PyAny>,
) -> PyResult<()> {
    let config_data = io_to_dict(data.py(), data)?;
    match config_type_name(&config_type)?.as_str() {
        "json" => io_write_json(config_file, config_data.bind(config_type.py()).clone()),
        "yaml" => io_write_yaml(config_file, config_data.bind(config_type.py()).clone()),
        "toml" => io_write_toml(config_file, config_data.bind(config_type.py()).clone()),
        _ => Err(pyo3::exceptions::PyValueError::new_err(
            "The configuration type is not supported.",
        )),
    }
}

pub(crate) fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(io_to_dict, m)?)?;
    m.add_function(wrap_pyfunction!(io_parse_config, m)?)?;
    m.add_function(wrap_pyfunction!(io_construct_config, m)?)?;
    m.add_function(wrap_pyfunction!(io_parse_json, m)?)?;
    m.add_function(wrap_pyfunction!(io_parse_yaml, m)?)?;
    m.add_function(wrap_pyfunction!(io_parse_toml, m)?)?;
    m.add_function(wrap_pyfunction!(io_write_config, m)?)?;
    m.add_function(wrap_pyfunction!(io_write_json, m)?)?;
    m.add_function(wrap_pyfunction!(io_write_yaml, m)?)?;
    m.add_function(wrap_pyfunction!(io_write_toml, m)?)?;
    Ok(())
}
