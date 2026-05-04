use proc_macro::TokenStream;
use quote::quote;
use syn::parse::{Parse, ParseStream};
use syn::{parse_macro_input, Attribute, ItemStruct, Path, Token};

struct ConfigclassArgs {
    crate_path: Path,
}

impl Parse for ConfigclassArgs {
    fn parse(input: ParseStream<'_>) -> syn::Result<Self> {
        if input.is_empty() {
            return Ok(Self {
                crate_path: syn::parse_quote!(simple_config_builder),
            });
        }

        let key: syn::Ident = input.parse()?;
        if key != "crate_path" {
            return Err(syn::Error::new_spanned(
                key,
                "expected `crate_path = path::to::crate`",
            ));
        }
        input.parse::<Token![=]>()?;
        let crate_path = input.parse()?;
        Ok(Self { crate_path })
    }
}

fn path_ends_with(path: &Path, name: &str) -> bool {
    path.segments
        .last()
        .is_some_and(|segment| segment.ident == name)
}

fn derives_default(attrs: &[Attribute]) -> bool {
    attrs.iter().any(|attr| {
        if !path_ends_with(attr.path(), "derive") {
            return false;
        }
        let mut found = false;
        let _ = attr.parse_nested_meta(|meta| {
            if path_ends_with(&meta.path, "Default") {
                found = true;
            }
            Ok(())
        });
        found
    })
}

/// Remove derives that the macro injects itself to prevent duplicate impls.
///
/// The managed set is: `Debug`, `Clone`, `Serialize`, `Deserialize`,
/// `JsonSchema`, `Validate`.  `Default` and all other derives are kept.
fn filter_managed_derives(attrs: Vec<Attribute>) -> Vec<Attribute> {
    const MANAGED: &[&str] = &[
        "Debug",
        "Clone",
        "Serialize",
        "Deserialize",
        "JsonSchema",
        "Validate",
    ];

    let mut result = Vec::new();
    for attr in attrs {
        if !path_ends_with(attr.path(), "derive") {
            result.push(attr);
            continue;
        }

        let mut kept: Vec<Path> = Vec::new();
        let _ = attr.parse_nested_meta(|meta| {
            let is_managed = meta
                .path
                .segments
                .last()
                .map(|s| MANAGED.contains(&s.ident.to_string().as_str()))
                .unwrap_or(false);
            if !is_managed {
                kept.push(meta.path.clone());
            }
            Ok(())
        });

        if !kept.is_empty() {
            result.push(syn::parse_quote!(#[derive(#(#kept),*)]));
        }
    }
    result
}

/// Inject `#[garde(skip)]` on every field that carries no `#[garde(...)]`
/// attribute, so the struct compiles with `#[derive(garde::Validate)]`
/// without requiring the user to annotate every field manually.
fn inject_garde_skip(fields: &mut syn::Fields) {
    let skip_attr: Attribute = syn::parse_quote!(#[garde(skip)]);
    for field in fields.iter_mut() {
        let has_garde = field
            .attrs
            .iter()
            .any(|attr| path_ends_with(attr.path(), "garde"));
        if !has_garde {
            field.attrs.push(skip_attr.clone());
        }
    }
}

#[proc_macro_attribute]
pub fn configclass(_attr: TokenStream, item: TokenStream) -> TokenStream {
    let args = parse_macro_input!(_attr as ConfigclassArgs);
    let mut input = parse_macro_input!(item as ItemStruct);
    if !derives_default(&input.attrs) {
        return syn::Error::new_spanned(
            &input.ident,
            "#[configclass] requires the Rust config struct to derive or implement Default. Add #[derive(Default)] to the struct.",
        )
        .to_compile_error()
        .into();
    }

    // Strip derives that the macro injects to avoid duplicate impls.
    let old_attrs = std::mem::take(&mut input.attrs);
    input.attrs = filter_managed_derives(old_attrs);

    // Auto-skip unannotated fields so garde validation compiles without
    // requiring the user to write #[garde(skip)] on every plain field.
    inject_garde_skip(&mut input.fields);

    let ident = &input.ident;
    let generics = &input.generics;
    let (impl_generics, ty_generics, where_clause) = generics.split_for_impl();

    #[cfg(feature = "python")]
    {
        let crate_path = &args.crate_path;
        quote! {
            #[pyo3::pyclass(subclass, extends = #crate_path::Configclass, from_py_object)]
            #[derive(
                Debug, Clone,
                serde::Serialize, serde::Deserialize,
                garde::Validate, schemars::JsonSchema,
            )]
            #input

            #[pyo3::pymethods]
            impl #impl_generics #ident #ty_generics #where_clause {
                #[new]
                fn __simple_config_builder_new__() -> (Self, #crate_path::Configclass)
                where
                    Self: Default,
                {
                    (Self::default(), #crate_path::Configclass::new())
                }
            }
        }
        .into()
    }

    #[cfg(not(feature = "python"))]
    {
        let _ = args;
        quote! {
            #[derive(
                Debug, Clone,
                serde::Serialize, serde::Deserialize,
                garde::Validate, schemars::JsonSchema,
            )]
            #input
        }
        .into()
    }
}
