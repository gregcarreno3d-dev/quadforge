"""Version of the code that is actually loaded.

Read from blender_manifest.toml when this module is first imported. The panel compares it with the version it reads
itself: Blender keeps the sub-modules of an add-on in memory when a new version is installed over the old one without
a restart, so a panel can show the new version while the old remesh code still runs. A difference means "restart Blender".
"""
import os
import re


def read_manifest_version(manifest_path: str) -> str:
    try:
        with open(manifest_path, encoding="utf-8") as handle:
            match = re.search(r'^version\s*=\s*"([^"]+)"', handle.read(), re.M)
        return match.group(1) if match else "?"
    except OSError:
        return "?"


CODE_VERSION = read_manifest_version(
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "blender_manifest.toml"))
