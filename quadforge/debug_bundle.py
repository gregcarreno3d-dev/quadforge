"""Debug bundle: one zip with everything needed to reproduce a run on another computer.

Contents: every selected mesh object (and the matching source / result of the active one) as OBJ in world space, the
current settings as JSON, the last result report, the add-on and Blender versions, the platform, the engine binary and
its size/hash. Written by the "Save Debug Bundle" button (Advanced panel); read by a developer with
`python3 tools/replay_bundle.py BUNDLE.zip`.

Only the writer lives here; it needs Blender (`bpy`) at call time, not at import time.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import os
import platform
import sys
import time
import zipfile

RESULT_SUFFIX = "_quads"


def partner_names(name: str) -> list[str]:
    """The result of 'Part' is 'Part_quads' and the other way round (both are exported when present)."""
    if name.endswith(RESULT_SUFFIX):
        return [name[: -len(RESULT_SUFFIX)]]
    return [name + RESULT_SUFFIX]


def object_to_obj_text(obj, depsgraph=None) -> str:
    """OBJ text of the evaluated mesh of `obj`, vertices in world space (no Blender operator needed)."""
    import bpy  # noqa: F401  (only to make the Blender requirement explicit)

    evaluated = obj.evaluated_get(depsgraph) if depsgraph is not None else obj
    mesh = evaluated.to_mesh()
    try:
        matrix = obj.matrix_world
        lines = [f"# {obj.name}"]
        for vertex in mesh.vertices:
            x, y, z = matrix @ vertex.co
            lines.append(f"v {x:.6f} {y:.6f} {z:.6f}")
        for poly in mesh.polygons:
            lines.append("f " + " ".join(str(i + 1) for i in poly.vertices))
        return "\n".join(lines) + "\n"
    finally:
        evaluated.to_mesh_clear()


def engine_info(engine_path: str | None) -> dict:
    if not engine_path or not os.path.isfile(engine_path):
        return {"path": engine_path, "found": False}
    digest = hashlib.sha256(open(engine_path, "rb").read()).hexdigest()
    return {"path": engine_path, "found": True, "bytes": os.path.getsize(engine_path), "sha256": digest}


def build_info(context, settings, addon_version: str, engine_path: str | None) -> dict:
    import bpy

    plain = dataclasses.asdict(settings.to_settings()) if hasattr(settings, "to_settings") else {}
    return {
        "created": time.strftime("%Y-%m-%d %H:%M:%S"),
        "addon_version": addon_version,
        "blender": bpy.app.version_string,
        "platform": platform.platform(),
        "python": sys.version.split()[0],
        "cpu_count": os.cpu_count(),
        "engine": engine_info(engine_path),
        "settings": plain,
        "last_result": {
            key: getattr(settings, key)
            for key in ("last_faces", "last_quads", "last_tris", "last_ngons", "last_poles", "last_hard_edges",
                        "last_seconds", "last_peak_memory_gb", "last_levels_text", "last_warnings")
            if hasattr(settings, key)
        },
        "unit_scale": context.scene.unit_settings.scale_length,
        "unit_system": context.scene.unit_settings.system,
    }


def write_bundle(context, path: str, addon_version: str, engine_path: str | None) -> list[str]:
    """Write the zip at `path`; returns the names of the objects exported."""
    settings = context.scene.quadforge
    depsgraph = context.evaluated_depsgraph_get()
    wanted: dict[str, object] = {}
    for obj in context.selected_objects or []:
        if obj.type == "MESH":
            wanted[obj.name] = obj
    active = context.active_object
    if active is not None and active.type == "MESH":
        wanted[active.name] = active
        for other in partner_names(active.name):
            if other in context.scene.objects and context.scene.objects[other].type == "MESH":
                wanted[other] = context.scene.objects[other]
    info = build_info(context, settings, addon_version, engine_path)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as bundle:
        bundle.writestr("info.json", json.dumps(info, indent=2, default=str))
        for name, obj in wanted.items():
            safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in name)
            bundle.writestr(f"meshes/{safe}.obj", object_to_obj_text(obj, depsgraph))
    return list(wanted)
