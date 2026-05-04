use std::env;
use std::path::Path;
use std::process::Command;

fn python_executable() -> Option<String> {
    env::var("PYO3_PYTHON")
        .ok()
        .or_else(|| env::var("PYTHON_SYS_EXECUTABLE").ok())
        .or_else(|| {
            env::var("VIRTUAL_ENV")
                .ok()
                .map(|venv| format!("{venv}/bin/python"))
        })
        .or_else(|| env::var("PYTHON").ok())
}

fn main() {
    println!("cargo:rerun-if-env-changed=PYO3_PYTHON");
    println!("cargo:rerun-if-env-changed=PYTHON_SYS_EXECUTABLE");
    println!("cargo:rerun-if-env-changed=VIRTUAL_ENV");
    println!("cargo:rerun-if-env-changed=PYTHON");

    let Some(python) = python_executable() else {
        return;
    };

    let output = Command::new(&python)
        .args([
            "-c",
            "import sysconfig; print(sysconfig.get_config_var('LIBDIR') or '')",
        ])
        .output();

    let Ok(output) = output else {
        return;
    };
    if !output.status.success() {
        return;
    }

    let libdir = String::from_utf8_lossy(&output.stdout).trim().to_string();
    if libdir.is_empty() || !Path::new(&libdir).exists() {
        return;
    }

    println!("cargo:rustc-link-arg=-Wl,-rpath,{libdir}");
}
