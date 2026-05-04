mod core_bindings;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList, PyModule, PyString, PyTuple, PyType};
use pyo3::types::PyTypeMethods;
use serde::{Deserialize, Serialize};
use simple_config_builder_core::{
    annotation_requires_callable, build_dynamic_object_schema,
    normalize_dynamic_field_definition, validate_dynamic_field,
    ConfigError, DynamicFieldDefinition, DynamicFieldKind,
    DynamicFieldSchema, DynamicFieldValidation, DynamicValueKind,
};
use std::cell::RefCell;
use std::collections::HashMap;

mod io;

pub use simple_config_builder_macros::configclass;

thread_local! {
    static CLASS_REGISTRY: RefCell<HashMap<String, Py<PyAny>>> =
        RefCell::new(HashMap::new());
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct CallableReference {
    r#type: String,
    module: String,
    name: String,
    file_path: String,
}

#[pyclass(subclass, dict, module = "simple_config_builder._native")]
#[derive(Default)]
pub struct Configclass;

#[pymethods]
impl Configclass {
    #[new]
    pub fn new() -> Self {
        Self
    }
}

#[pyclass(module = "simple_config_builder._native")]
pub struct FieldInfo {
    #[pyo3(get, set)]
    annotation: Option<Py<PyAny>>,
    #[pyo3(get)]
    default: Option<Py<PyAny>>,
    #[pyo3(get)]
    default_factory: Option<Py<PyAny>>,
    #[pyo3(get)]
    gt: Option<f64>,
    #[pyo3(get)]
    lt: Option<f64>,
}

impl FieldInfo {
    fn clone_for_class(&self, py: Python<'_>, annotation: Py<PyAny>) -> Self {
        Self {
            annotation: Some(annotation),
            default: self.default.as_ref().map(|value| value.clone_ref(py)),
            default_factory: self
                .default_factory
                .as_ref()
                .map(|value| value.clone_ref(py)),
            gt: self.gt,
            lt: self.lt,
        }
    }
}

impl FieldInfo {
    fn from_definition(
        annotation: Py<PyAny>,
        definition: &DynamicFieldDefinition,
        default: Option<Py<PyAny>>,
        default_factory: Option<Py<PyAny>>,
    ) -> Self {
        Self {
            annotation: Some(annotation),
            default,
            default_factory,
            gt: definition.gt,
            lt: definition.lt,
        }
    }
}

#[pymethods]
impl FieldInfo {
    fn is_required(&self) -> bool {
        self.default.is_none() && self.default_factory.is_none()
    }
}

#[pyfunction(name = "Field")]
#[pyo3(signature = (*_args, **kwargs))]
fn field(
    _args: Bound<'_, PyTuple>,
    kwargs: Option<Bound<'_, PyDict>>,
) -> PyResult<FieldInfo> {
    let Some(kwargs) = kwargs else {
        return Ok(FieldInfo {
            annotation: None,
            default: None,
            default_factory: None,
            gt: None,
            lt: None,
        });
    };

    Ok(FieldInfo {
        annotation: None,
        default: kwargs
            .get_item("default")?
            .map(|value| value.unbind()),
        default_factory: kwargs
            .get_item("default_factory")?
            .map(|value| value.unbind()),
        gt: kwargs
            .get_item("gt")?
            .map(|value| value.extract())
            .transpose()?,
        lt: kwargs
            .get_item("lt")?
            .map(|value| value.extract())
            .transpose()?,
    })
}

fn callable_reference_from_py(value: &Bound<'_, PyAny>) -> PyResult<CallableReference> {
    if !value.is_callable() {
        return Err(pyo3::exceptions::PyTypeError::new_err(
            "Expected a callable object.",
        ));
    }

    let module: String = value.getattr("__module__")?.extract()?;
    let name: String = value.getattr("__name__")?.extract()?;
    let file_path = match PyModule::import(value.py(), &module) {
        Ok(_) => String::new(),
        Err(_) => value
            .getattr("__code__")?
            .getattr("co_filename")?
            .extract()?,
    };

    Ok(CallableReference {
        r#type: "callable".to_string(),
        module,
        name,
        file_path,
    })
}

fn callable_reference_to_dict<'py>(
    py: Python<'py>,
    reference: CallableReference,
) -> PyResult<Bound<'py, PyDict>> {
    let dict = PyDict::new(py);
    dict.set_item("type", reference.r#type)?;
    dict.set_item("module", reference.module)?;
    dict.set_item("name", reference.name)?;
    dict.set_item("file_path", reference.file_path)?;
    Ok(dict)
}

#[pyfunction]
fn callable_to_reference<'py>(
    py: Python<'py>,
    value: Bound<'py, PyAny>,
) -> PyResult<Bound<'py, PyDict>> {
    callable_reference_to_dict(py, callable_reference_from_py(&value)?)
}

#[pyfunction]
fn callable_from_reference<'py>(
    py: Python<'py>,
    value: Bound<'py, PyDict>,
) -> PyResult<Bound<'py, PyAny>> {
    let module_name: String = value
        .get_item("module")?
        .ok_or_else(|| pyo3::exceptions::PyKeyError::new_err("module"))?
        .extract()?;
    let name: String = value
        .get_item("name")?
        .ok_or_else(|| pyo3::exceptions::PyKeyError::new_err("name"))?
        .extract()?;
    let file_path: String = value
        .get_item("file_path")?
        .map(|file_path| file_path.extract())
        .transpose()?
        .unwrap_or_default();

    let module = if file_path.is_empty() {
        PyModule::import(py, &module_name)?.into_any()
    } else {
        let importlib_util = PyModule::import(py, "importlib.util")?;
        let spec = importlib_util.call_method1(
            "spec_from_file_location",
            (&name, &file_path),
        )?;
        if spec.is_none() {
            return Err(pyo3::exceptions::PyImportError::new_err(format!(
                "Could not find spec for module {name} at {file_path}"
            )));
        }
        let module = importlib_util.call_method1("module_from_spec", (&spec,))?;
        let loader = spec.getattr("loader")?;
        if loader.is_none() {
            return Err(pyo3::exceptions::PyImportError::new_err(format!(
                "Could not load module {name} at {file_path}"
            )));
        }
        loader.call_method1("exec_module", (&module,))?;
        module
    };

    module.getattr(name)
}

fn class_fields<'py>(cls: &Bound<'py, PyAny>) -> PyResult<Bound<'py, PyDict>> {
    Ok(cls.getattr("__config_fields__")?.cast_into::<PyDict>()?)
}

fn type_name(value: &Bound<'_, PyAny>) -> PyResult<String> {
    if let Ok(name) = value.getattr("__name__") {
        return name.extract();
    }
    Ok(value.repr()?.extract()?)
}

fn class_string(class_to_register: &Bound<'_, PyAny>) -> PyResult<String> {
    Ok(format!(
        "{}.{}",
        class_to_register
            .getattr("__module__")?
            .extract::<String>()?,
        class_to_register
            .getattr("__name__")?
            .extract::<String>()?
    ))
}

pub fn get_class_str_from_bound(class_to_register: &Bound<'_, PyAny>) -> PyResult<String> {
    class_string(class_to_register)
}

pub fn register_bound_config_class(class_to_register: Bound<'_, PyAny>) -> PyResult<()> {
    let class_str = class_string(&class_to_register)?;
    CLASS_REGISTRY.with(|registry| {
        registry
            .borrow_mut()
            .insert(class_str, class_to_register.unbind());
    });
    Ok(())
}

fn is_literal_annotation<'py>(
    annotation: &Bound<'py, PyAny>,
) -> PyResult<Option<Bound<'py, PyTuple>>> {
    let typing = PyModule::import(annotation.py(), "typing")?;
    let origin = typing.call_method1("get_origin", (annotation,))?;
    if origin.is_none() {
        return Ok(None);
    }
    let repr: String = origin.repr()?.extract()?;
    if repr.contains("typing.Literal") {
        return Ok(Some(typing.call_method1("get_args", (annotation,))?.cast_into()?));
    }
    Ok(None)
}

fn dynamic_value_kind(value: &Bound<'_, PyAny>) -> DynamicValueKind {
    if value.is_callable() {
        return DynamicValueKind::Callable;
    }
    if value.extract::<bool>().is_ok() {
        return DynamicValueKind::Boolean;
    }
    if value.extract::<i64>().is_ok() || value.extract::<u64>().is_ok() {
        return DynamicValueKind::Integer;
    }
    if value.extract::<f64>().is_ok() {
        return DynamicValueKind::Float;
    }
    if value.extract::<String>().is_ok() {
        return DynamicValueKind::String;
    }
    if value.cast::<PyList>().is_ok() {
        return DynamicValueKind::List;
    }
    if value.cast::<PyDict>().is_ok() {
        return DynamicValueKind::Dict;
    }
    DynamicValueKind::Object
}

fn dynamic_validation_error(error: ConfigError) -> PyErr {
    match error {
        ConfigError::Validation(message) => {
            pyo3::exceptions::PyValueError::new_err(message)
        }
        other => pyo3::exceptions::PyValueError::new_err(other.to_string()),
    }
}

fn validate_value(name: &str, field: &Bound<'_, FieldInfo>, value: &Bound<'_, PyAny>) -> PyResult<()> {
    let py = value.py();
    let field_ref = field.borrow();

    let Some(annotation) = &field_ref.annotation else {
        return validate_dynamic_field(&DynamicFieldValidation {
            name: name.to_string(),
            annotation: None,
            kind: dynamic_value_kind(value),
            numeric_value: value.extract::<f64>().ok(),
            gt: field_ref.gt,
            lt: field_ref.lt,
            literal_matches: None,
            type_matches: None,
        })
        .map_err(dynamic_validation_error);
    };
    let annotation = annotation.bind(py);
    let annotation_name = type_name(annotation)?;
    let literal_matches = if let Some(args) = is_literal_annotation(annotation)? {
        let mut matched = false;
        for item in args.iter_borrowed() {
            if value.eq(&item)? {
                matched = true;
                break;
            }
        }
        Some(matched)
    } else {
        None
    };
    let type_matches = if literal_matches.is_none()
        && !annotation_requires_callable(Some(&annotation_name))
        && annotation.is_instance_of::<pyo3::types::PyType>()
    {
        Some(value.is_instance(annotation)?)
    } else {
        None
    };

    validate_dynamic_field(&DynamicFieldValidation {
        name: name.to_string(),
        annotation: Some(annotation_name),
        kind: dynamic_value_kind(value),
        numeric_value: value.extract::<f64>().ok(),
        gt: field_ref.gt,
        lt: field_ref.lt,
        literal_matches,
        type_matches,
    })
    .map_err(dynamic_validation_error)
}

fn serialize_value<'py>(py: Python<'py>, value: &Bound<'py, PyAny>) -> PyResult<Py<PyAny>> {
    if value.is_callable() {
        return Ok(callable_reference_to_dict(py, callable_reference_from_py(value)?)?
            .into_any()
            .unbind());
    }

    if let Ok(list) = value.cast::<PyList>() {
        let out = PyList::empty(py);
        for item in list.iter() {
            out.append(serialize_value(py, &item)?)?;
        }
        return Ok(out.into_any().unbind());
    }

    if let Ok(dict) = value.cast::<PyDict>() {
        let out = PyDict::new(py);
        for (key, item) in dict.iter() {
            out.set_item(key, serialize_value(py, &item)?)?;
        }
        return Ok(out.into_any().unbind());
    }

    if value.hasattr("model_dump")? {
        return Ok(value.call_method0("model_dump")?.unbind());
    }

    Ok(value.clone().unbind())
}

fn deserialize_value<'py>(py: Python<'py>, value: &Bound<'py, PyAny>) -> PyResult<Py<PyAny>> {
    if let Ok(dict) = value.cast::<PyDict>() {
        if let Some(kind) = dict.get_item("type")? {
            if kind.extract::<String>().ok().as_deref() == Some("callable") {
                return Ok(callable_from_reference(py, dict.clone())?.unbind());
            }
        }
        let out = PyDict::new(py);
        for (key, item) in dict.iter() {
            out.set_item(key, deserialize_value(py, &item)?)?;
        }
        return Ok(out.into_any().unbind());
    }

    if let Ok(list) = value.cast::<PyList>() {
        let out = PyList::empty(py);
        for item in list.iter() {
            out.append(deserialize_value(py, &item)?)?;
        }
        return Ok(out.into_any().unbind());
    }

    Ok(value.clone().unbind())
}

#[pyfunction]
fn configure_config_class(py: Python<'_>, cls: Bound<'_, PyAny>) -> PyResult<()> {
    let annotations = match cls.getattr("__annotations__") {
        Ok(value) => value.cast_into::<PyDict>()?,
        Err(_) => PyDict::new(py),
    };
    let config_fields = PyDict::new(py);

    for (key, annotation) in annotations.iter() {
        let name: String = key.extract()?;
        let raw_field = cls.getattr(&name).ok();
        let explicit_field = raw_field
            .as_ref()
            .and_then(|value| value.clone().cast_into::<FieldInfo>().ok());
        let definition = if let Some(field) = explicit_field.as_ref() {
            let field_ref = field.borrow();
            normalize_dynamic_field_definition(
                name.clone(),
                None,
                true,
                field_ref.default.is_some(),
                field_ref.default_factory.is_some(),
                field_ref.gt,
                field_ref.lt,
            )
        } else {
            normalize_dynamic_field_definition(
                name.clone(),
                None,
                false,
                raw_field.is_some(),
                false,
                None,
                None,
            )
        };
        let field_info = match definition.kind {
            DynamicFieldKind::ExplicitField => {
                let field = explicit_field.expect("explicit field metadata missing");
                let field_ref = field.borrow();
                Py::new(py, field_ref.clone_for_class(py, annotation.unbind()))?
            }
            DynamicFieldKind::PlainDefault => {
                let raw_default = raw_field.expect("plain default missing").unbind();
                Py::new(
                    py,
                    FieldInfo::from_definition(
                        annotation.unbind(),
                        &definition,
                        Some(raw_default),
                        None,
                    ),
                )?
            }
            DynamicFieldKind::Required => Py::new(
                py,
                FieldInfo::from_definition(
                    annotation.unbind(),
                    &definition,
                    None,
                    None,
                ),
            )?,
        };
        config_fields.set_item(name, field_info)?;
    }

    let private_attrs = PyDict::new(py);
    private_attrs.set_item("_config_class_type", py.None())?;
    cls.setattr("__config_fields__", &config_fields)?;
    cls.setattr("__private_attributes__", &private_attrs)?;
    Ok(())
}

#[pyfunction]
fn registry_get_class_str_from_class(class_to_register: Bound<'_, PyAny>) -> PyResult<String> {
    class_string(&class_to_register)
}

#[pyfunction]
fn registry_register_class(py: Python<'_>, class_to_register: Bound<'_, PyAny>) -> PyResult<()> {
    let _ = py;
    register_bound_config_class(class_to_register)
}

#[pyfunction]
fn registry_list_classes() -> Vec<String> {
    CLASS_REGISTRY.with(|registry| registry.borrow().keys().cloned().collect())
}

#[pyfunction]
fn registry_is_registered(class_to_register: Bound<'_, PyAny>) -> PyResult<bool> {
    let class_str = class_string(&class_to_register)?;
    Ok(CLASS_REGISTRY.with(|registry| registry.borrow().contains_key(&class_str)))
}

#[pyfunction]
pub(crate) fn get_registered_class(py: Python<'_>, class_name: &str) -> PyResult<Py<PyAny>> {
    CLASS_REGISTRY.with(|registry| {
        registry
            .borrow()
            .get(class_name)
            .map(|class_to_register| class_to_register.clone_ref(py))
            .ok_or_else(|| {
                pyo3::exceptions::PyValueError::new_err(format!(
                    "{class_name} is not registered."
                ))
            })
    })
}

#[pyfunction]
fn registry_get(py: Python<'_>, class_name: String) -> PyResult<Py<PyAny>> {
    get_registered_class(py, &class_name)
}

#[pyfunction]
fn registry_get_class_attributes(
    py: Python<'_>,
    class_name: String,
) -> PyResult<Bound<'_, PyDict>> {
    let config_class = registry_get(py, class_name)?;
    let fields = config_class
        .bind(py)
        .getattr("__config_fields__")?
        .cast_into::<PyDict>()?;
    let out = PyDict::new(py);
    for (key, field_obj) in fields.iter() {
        let annotation = field_obj.getattr("annotation")?;
        out.set_item(key, annotation)?;
    }
    Ok(out)
}

#[pyfunction]
#[pyo3(signature = (base_class, include_base=false, recursive=false))]
fn registry_list_subclasses(
    py: Python<'_>,
    base_class: Bound<'_, PyAny>,
    include_base: bool,
    recursive: bool,
) -> PyResult<Vec<String>> {
    let base_type = if base_class.is_instance_of::<PyString>() {
        let class_name: String = base_class.extract()?;
        registry_get(py, class_name)?
    } else {
        base_class.unbind()
    };
    let base_bound = base_type.bind(py);
    let mut matches = Vec::new();

    CLASS_REGISTRY.with(|registry| -> PyResult<()> {
        for (class_name, registered_class) in registry.borrow().iter() {
            let registered_bound = registered_class.bind(py);
            if registered_bound.eq(base_bound)? {
                if include_base {
                    matches.push(class_name.clone());
                }
                continue;
            }
            let Ok(registered_type) = registered_bound.cast::<PyType>() else {
                continue;
            };
            if !registered_type.is_subclass(base_bound)? {
                continue;
            }
            if recursive || registered_bound.getattr("__base__")?.eq(base_bound)? {
                matches.push(class_name.clone());
            }
        }
        Ok(())
    })?;

    Ok(matches)
}

#[pyfunction]
fn init_config_instance(py: Python<'_>, instance: Bound<'_, PyAny>, data: Bound<'_, PyDict>) -> PyResult<()> {
    let cls = instance.get_type().into_any();
    let fields = class_fields(&cls)?;
    let instance_dict = instance.getattr("__dict__")?.cast_into::<PyDict>()?;
    let config_type = format!(
        "{}.{}",
        cls.getattr("__module__")?.extract::<String>()?,
        cls.getattr("__name__")?.extract::<String>()?
    );

    for (key, field_obj) in fields.iter() {
        let name: String = key.extract()?;
        let field = field_obj.cast_into::<FieldInfo>()?;
        let value = if let Some(value) = data.get_item(&name)? {
            deserialize_value(py, &value)?
        } else {
            let field_ref = field.borrow();
            if let Some(factory) = &field_ref.default_factory {
                factory.call0(py)?
            } else if let Some(default) = &field_ref.default {
                default.clone_ref(py)
            } else {
                return Err(pyo3::exceptions::PyValueError::new_err(format!(
                    "Missing required field {name}"
                )));
            }
        };
        validate_value(&name, &field, value.bind(py))?;
        instance_dict.set_item(name, value)?;
    }

    for (key, _) in data.iter() {
        let name: String = key.extract()?;
        if name == "_config_class_type" {
            continue;
        }
        if !fields.contains(&name)? {
            return Err(pyo3::exceptions::PyValueError::new_err(format!(
                "Unexpected field {name}"
            )));
        }
    }

    instance_dict.set_item("_config_class_type", config_type)?;
    Ok(())
}

#[pyfunction]
fn set_config_attr(py: Python<'_>, instance: Bound<'_, PyAny>, name: &str, value: Bound<'_, PyAny>) -> PyResult<bool> {
    let cls = instance.get_type().into_any();
    let fields = class_fields(&cls)?;
    let Some(field_obj) = fields.get_item(name)? else {
        return Ok(false);
    };
    let field = field_obj.cast_into::<FieldInfo>()?;
    validate_value(name, &field, &value)?;
    instance.getattr("__dict__")?.cast_into::<PyDict>()?.set_item(name, value)?;
    let _ = py;
    Ok(true)
}

#[pyfunction]
fn model_dump<'py>(
    py: Python<'py>,
    instance: Bound<'py, PyAny>,
) -> PyResult<Bound<'py, PyDict>> {
    let cls = instance.get_type().into_any();
    let fields = class_fields(&cls)?;
    let instance_dict = instance.getattr("__dict__")?.cast_into::<PyDict>()?;
    let out = PyDict::new(py);
    out.set_item(
        "_config_class_type",
        instance_dict.get_item("_config_class_type")?,
    )?;
    for key in fields.keys().iter() {
        let name: String = key.extract()?;
        if let Some(value) = instance_dict.get_item(&name)? {
            out.set_item(name, serialize_value(py, &value)?)?;
        }
    }
    Ok(out)
}

#[pyfunction]
fn model_dump_json(instance: Bound<'_, PyAny>) -> PyResult<String> {
    let json = PyModule::import(instance.py(), "json")?;
    json.call_method1("dumps", (model_dump(instance.py(), instance)?,))?
        .extract()
}

#[pyfunction]
fn model_validate<'py>(
    cls: Bound<'py, PyAny>,
    data: Bound<'py, PyDict>,
) -> PyResult<Bound<'py, PyAny>> {
    cls.call((), Some(&data))
}

#[pyfunction]
fn model_validate_json<'py>(
    py: Python<'py>,
    data: Bound<'py, PyAny>,
) -> PyResult<Bound<'py, PyAny>> {
    let json = PyModule::import(py, "json")?;
    Ok(if data.is_instance_of::<PyString>() {
        json.call_method1("loads", (data,))?
    } else {
        let text: String = data.str()?.extract()?;
        json.call_method1("loads", (text,))?
    })
}

#[pyfunction]
fn model_json_schema<'py>(
    py: Python<'py>,
    cls: Bound<'py, PyAny>,
) -> PyResult<Bound<'py, PyDict>> {
    let fields = class_fields(&cls)?;
    let title: String = cls.getattr("__name__")?.extract()?;
    let mut field_schemas = Vec::new();

    for (key, field_obj) in fields.iter() {
        let name: String = key.extract()?;
        let field = field_obj.cast_into::<FieldInfo>()?;
        let field_ref = field.borrow();
        let annotation = field_ref
            .annotation
            .as_ref()
            .map(|annotation| type_name(annotation.bind(py)))
            .transpose()?;

        field_schemas.push(DynamicFieldSchema {
            name,
            annotation,
            required: field_ref.is_required(),
        });
    }

    let schema = build_dynamic_object_schema(&title, &field_schemas);
    Ok(io::json_value_to_py(py, schema)?
        .bind(py)
        .clone()
        .cast_into::<PyDict>()?)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::configclass;

    #[configclass(crate_path = crate)]
    #[derive(Default)]
    struct MacroConfig {
        port: u16,
    }

    #[test]
    fn class_string_uses_python_module_and_name() {
        Python::attach(|py| {
            let builtins = PyModule::import(py, "builtins").unwrap();
            let int_type = builtins.getattr("int").unwrap();

            assert_eq!(class_string(&int_type).unwrap(), "builtins.int");
        });
    }

    #[test]
    fn native_registry_registers_and_lists_python_classes() {
        Python::attach(|py| {
            let builtins = PyModule::import(py, "builtins").unwrap();
            let str_type = builtins.getattr("str").unwrap();
            let class_name = class_string(&str_type).unwrap();

            register_bound_config_class(str_type).unwrap();

            assert!(CLASS_REGISTRY.with(|registry| {
                registry.borrow().contains_key(&class_name)
            }));
        });
    }

    #[test]
    fn configclass_macro_builds_default_rust_config() {
        let config = MacroConfig::default();

        assert_eq!(config.port, 0);
    }
}

#[pymodule]
fn _native(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<Configclass>()?;
    m.add_class::<FieldInfo>()?;
    m.add_function(wrap_pyfunction!(field, m)?)?;
    m.add_function(wrap_pyfunction!(callable_to_reference, m)?)?;
    m.add_function(wrap_pyfunction!(callable_from_reference, m)?)?;
    m.add_function(wrap_pyfunction!(configure_config_class, m)?)?;
    m.add_function(wrap_pyfunction!(init_config_instance, m)?)?;
    m.add_function(wrap_pyfunction!(set_config_attr, m)?)?;
    m.add_function(wrap_pyfunction!(model_dump, m)?)?;
    m.add_function(wrap_pyfunction!(model_dump_json, m)?)?;
    m.add_function(wrap_pyfunction!(model_validate, m)?)?;
    m.add_function(wrap_pyfunction!(model_validate_json, m)?)?;
    m.add_function(wrap_pyfunction!(model_json_schema, m)?)?;
    m.add_function(wrap_pyfunction!(registry_get_class_str_from_class, m)?)?;
    m.add_function(wrap_pyfunction!(registry_register_class, m)?)?;
    m.add_function(wrap_pyfunction!(registry_list_classes, m)?)?;
    m.add_function(wrap_pyfunction!(registry_is_registered, m)?)?;
    m.add_function(wrap_pyfunction!(registry_get, m)?)?;
    m.add_function(wrap_pyfunction!(registry_get_class_attributes, m)?)?;
    m.add_function(wrap_pyfunction!(registry_list_subclasses, m)?)?;
    core_bindings::register(m)?;
    io::register(m)?;
    Ok(())
}
