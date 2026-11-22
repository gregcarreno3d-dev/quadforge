"""The debug bundle writes info.json and the OBJ of the active object and of its '_quads' partner.
Run: python run_in_bpy.py blender_bundle_test.py (bpy module)."""
import json
import sys
import tempfile
import zipfile
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import quadforge  # noqa: E402
from quadforge import debug_bundle  # noqa: E402

fails = []


def check(name, ok, detail=""):
    print(("ok   " if ok else "FAIL ") + name, detail)
    if not ok:
        fails.append(name)


check("partner names", debug_bundle.partner_names("Part") == ["Part_quads"] and debug_bundle.partner_names("Part_quads") == ["Part"])
bpy.ops.wm.read_factory_settings(use_empty=True)
quadforge.register()
try:
    bpy.ops.mesh.primitive_cube_add(size=2.0, location=(1.0, 2.0, 3.0))
    source = bpy.context.active_object
    source.name = "Part"
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    bpy.context.active_object.name = "Part_quads"
    bpy.context.view_layer.objects.active = source
    path = str(Path(tempfile.mkdtemp()) / "bundle.zip")
    names = debug_bundle.write_bundle(bpy.context, path, "9.9.9", None)
    check("both objects exported", sorted(names) == ["Part", "Part_quads"], str(names))
    with zipfile.ZipFile(path) as z:
        info = json.loads(z.read("info.json"))
        check("info has version and settings", info["addon_version"] == "9.9.9" and "target_quads" in info["settings"])
        text = z.read("meshes/Part.obj").decode()
        check("world space vertices", "v 2.000000 3.000000 4.000000" in text, text.splitlines()[1])
        check("faces written", sum(1 for l in text.splitlines() if l.startswith("f ")) == 6)
finally:
    quadforge.unregister()
sys.exit(1 if fails else 0)
