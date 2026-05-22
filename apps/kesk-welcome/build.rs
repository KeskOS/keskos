fn main() {
    for path in [
        "src/main.rs",
        "src/backend.rs",
        "src/logger.rs",
        "README.md",
        "packaging/kesk-welcome.desktop",
        "packaging/kesk-welcome-autostart.desktop",
    ] {
        println!("cargo:rerun-if-changed={path}");
    }
}
