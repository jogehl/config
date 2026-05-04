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

#[proc_macro_attribute]
pub fn configclass(_attr: TokenStream, item: TokenStream) -> TokenStream {
    let args = parse_macro_input!(_attr as ConfigclassArgs);
    let input = parse_macro_input!(item as ItemStruct);
    if !derives_default(&input.attrs) {
        return syn::Error::new_spanned(
            &input.ident,
            "#[configclass] requires the Rust config struct to derive or implement Default. Add #[derive(Default)] to the struct.",
        )
        .to_compile_error()
        .into();
    }

    let ident = &input.ident;
    let generics = &input.generics;
    let (impl_generics, ty_generics, where_clause) = generics.split_for_impl();

    #[cfg(feature = "python")]
    {
        let crate_path = &args.crate_path;
        quote! {
            #[pyo3::pyclass(subclass, extends = #crate_path::Configclass)]
            #[derive(serde::Serialize, serde::Deserialize)]
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
            #[derive(serde::Serialize, serde::Deserialize)]
            #input
        }
        .into()
    }
}
