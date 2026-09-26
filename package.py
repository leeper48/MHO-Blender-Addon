"""Build the installable MHO Actions extension zip.

Usage:  python package.py
Output: dist/mho_fbx_to_actions-<version>.zip

Checks that MHO_ADDON_VERSION in __init__.py matches `version` in
blender_manifest.toml before building, since both must be bumped together.
"""

import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ADDON_DIR = ROOT / "mho_fbx_to_actions"
DIST_DIR = ROOT / "dist"
EXCLUDE_DIRS = {"__pycache__"}
EXCLUDE_SUFFIXES = {".pyc", ".pyo"}


def read_version(path, pattern):
    match = re.search(pattern, path.read_text(encoding="utf-8"), re.MULTILINE)
    if not match:
        sys.exit(f"ERROR: could not find version in {path.relative_to(ROOT)}")
    return match.group(1)


def main():
    init_version = read_version(
        ADDON_DIR / "__init__.py", r'^MHO_ADDON_VERSION\s*=\s*"([^"]+)"'
    )
    manifest_version = read_version(
        ADDON_DIR / "blender_manifest.toml", r'^version\s*=\s*"([^"]+)"'
    )
    if init_version != manifest_version:
        sys.exit(
            f"ERROR: version mismatch - __init__.py has {init_version}, "
            f"blender_manifest.toml has {manifest_version}. Bump both together."
        )

    DIST_DIR.mkdir(exist_ok=True)
    out_path = DIST_DIR / f"mho_fbx_to_actions-{init_version}.zip"

    files = sorted(
        p
        for p in ADDON_DIR.rglob("*")
        if p.is_file()
        and not EXCLUDE_DIRS.intersection(p.relative_to(ADDON_DIR).parts)
        and p.suffix not in EXCLUDE_SUFFIXES
    )

    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in files:
            arcname = path.relative_to(ROOT).as_posix()
            zf.write(path, arcname)
            print(f"  + {arcname}")

    print(f"Built {out_path.relative_to(ROOT)} (v{init_version})")


if __name__ == "__main__":
    main()
