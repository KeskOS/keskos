from __future__ import annotations

from pathlib import Path
import sys


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: keskos_systemsettings_ui.py <systemsettings-source-root>")

    source_root = Path(sys.argv[1]).resolve()
    qml_root = source_root / "app" / "qml"
    overlay_root = Path(__file__).resolve().with_name("keskos_systemsettings_qml")

    required_files = (
        "CategoriesPage.qml",
        "CategoryItem.qml",
        "HamburgerMenuButton.qml",
        "SubCategoryPage.qml",
    )

    if not qml_root.is_dir():
        raise SystemExit(f"systemsettings QML directory not found: {qml_root}")
    if not overlay_root.is_dir():
        raise SystemExit(f"KeskOS override directory not found: {overlay_root}")

    for name in required_files:
        source_file = overlay_root / name
        target_file = qml_root / name
        if not source_file.is_file():
            raise SystemExit(f"missing override file: {source_file}")
        target_file.write_text(source_file.read_text(encoding="utf-8"), encoding="utf-8", newline="\n")

    print(f"Applied KeskOS System Settings QML overrides to {qml_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
