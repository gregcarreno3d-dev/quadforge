"""Detail on Curves (form detail): the edge-length multiplier follows the bending of the form.
Run: python run_in_bpy.py blender_form_detail_test.py (bpy module)."""
import sys
from pathlib import Path

import numpy as np
import bpy
import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import quadforge  # noqa: E402
from quadforge.core import form_detail, pipeline  # noqa: E402

quadforge.register()
fails = []


def check(name, ok, detail=""):
    print(("ok   " if ok else "FAIL ") + name, detail)
    if not ok:
        fails.append(name)


def bumpy_plane():
    """A flat plate with a narrow ridge along x = 0: flat everywhere except at the ridge."""
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=120, y_segments=120, size=1.0)
    for vertex in bm.verts:
        vertex.co.z = 0.08 * np.exp(-(vertex.co.x / 0.03) ** 2)
    mesh = bpy.data.meshes.new("ridge")
    bm.to_mesh(mesh)
    bm.free()
    return mesh


mesh = bumpy_plane()
multiplier = form_detail.form_multiplier(mesh, 2000, 2.5)
x = np.array([v.co.x for v in mesh.vertices])
near = multiplier[np.abs(x) < 0.04]
far = multiplier[np.abs(x) > 0.5]
check("multiplier has one value per vertex", len(multiplier) == len(mesh.vertices))
check("never below 1 / ratio", float(multiplier.min()) >= 1.0 / 2.5 - 1e-9, f"min {multiplier.min():.3f}")
check("never above 1", float(multiplier.max()) <= 1.0 + 1e-9)
check("flat area stays at 1", float(far.mean()) > 0.99, f"{far.mean():.3f}")
check("ridge gets finer faces", float(near.mean()) < 0.8, f"{near.mean():.3f}")
check("ratio 1 changes nothing", bool(np.all(form_detail.form_multiplier(mesh, 2000, 1.0) == 1.0)))

# the same multiplier is used by the pipeline: a ridge gets more faces than a flat area of the same size
sphere = bpy.data.meshes.new("s")
bm = bmesh.new()
bmesh.ops.create_icosphere(bm, subdivisions=5, radius=1.0)
for vertex in bm.verts:
    vertex.co.z *= 1.0 + 0.25 * np.exp(-((vertex.co.x ** 2 + vertex.co.y ** 2) / 0.02))
bm.to_mesh(sphere)
bm.free()
obj = bpy.data.objects.new("bump", sphere)
bpy.context.scene.collection.objects.link(obj)
settings = pipeline.RemeshSettings()
settings.output = "QUADS"
settings.target_quads = 3000
settings.hide_original = False
settings.curvature_detail = "MEDIUM"
result = pipeline.run(bpy.context, obj, settings)
out = result.levels[0].object.data
check("pipeline result is quads", result.levels[0].stats["quads"] == result.levels[0].stats["faces"],
      f"{result.levels[0].stats['faces']} faces")
check("pipeline result is closed", result.levels[0].stats["non_manifold_edges"] == 0 and result.levels[0].stats["border_edges"] == 0)
check("face count near the request", abs(result.levels[0].stats["faces"] - 3000) / 3000 < 0.1)

# Analyze Form (preview): colours the mesh, changes nothing else
bpy.ops.object.select_all(action="DESELECT")
obj.select_set(True)
bpy.context.view_layer.objects.active = obj
bpy.context.scene.quadforge.curvature_detail = "MEDIUM"
bpy.context.scene.quadforge.target_quads = 3000
faces_before = len(sphere.polygons)
check("Analyze Form runs", bpy.ops.quadforge.analyze_form() == {"FINISHED"})
form_colors = sphere.color_attributes.get("QuadForge Form Colours")
check("Analyze Form writes a colour per vertex", form_colors is not None and len(form_colors.data) == len(sphere.vertices))
red = np.array([c.color[0] for c in form_colors.data])
check("bumped area is red, flat area is blue", red.max() > 0.8 and red.min() < 0.2, f"{red.min():.2f}..{red.max():.2f}")
sphere_obj = bpy.context.active_object
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.object.mode_set(mode="OBJECT")
qsettings = bpy.context.scene.quadforge
check("Speed / Precision defaults to Balanced", qsettings.remesh_quality == "BALANCED" and qsettings.to_settings().quality == "BALANCED")
qsettings.remesh_quality = "FAST"
check("Speed / Precision reaches the pipeline settings", qsettings.to_settings().quality == "FAST")
qsettings.remesh_quality = "BALANCED"
check("Analyze Form colours survive an Edit Mode round trip", sphere.color_attributes.get("QuadForge Form Colours") is not None)
check("Analyze Form writes an editable vertex group", sphere_obj.vertex_groups.get("QuadForge Form") is not None)
check("Analyze Form does not change the mesh", len(sphere.polygons) == faces_before)
bpy.context.scene.quadforge.curvature_detail = "OFF"
check("Analyze Form with Detail Off is refused", bpy.ops.quadforge.analyze_form() == {"CANCELLED"})

# multi-scale mask: a spike about one quad wide (a fang, a tooth) gets the finest faces even though a wide patch averages it out
spike_bm = bmesh.new()
bmesh.ops.create_grid(spike_bm, x_segments=150, y_segments=150, size=1.0)
for vertex in spike_bm.verts:
    vertex.co.z = 0.10 * np.exp(-((vertex.co.x ** 2 + vertex.co.y ** 2) / 0.0006))
spike = bpy.data.meshes.new("spike")
spike_bm.to_mesh(spike)
spike_bm.free()
spike_multiplier = form_detail.form_multiplier(spike, 1500, 3.5)
spike_x = np.array([v.co.x for v in spike.vertices])
spike_y = np.array([v.co.y for v in spike.vertices])
tip = spike_multiplier[(spike_x ** 2 + spike_y ** 2) < 0.03 ** 2]
check("a one-quad spike gets the finest faces", float(tip.min()) < 1.0 / 3.0, f"{tip.min():.3f}")
check("flat area around the spike stays at 1", float(spike_multiplier[(spike_x ** 2 + spike_y ** 2) > 0.5 ** 2].mean()) > 0.99)

# the grid method cannot always follow the density: the pipeline retries with part of it instead of the pairing method
from quadforge.core.backends import forge as forge_backend  # noqa: E402
real_backend = pipeline.get_backend
calls = []


class PairOnce:
    def __init__(self, backend):
        self.backend = backend

    def remesh_steps(self, context, work_object, request):
        yield from self.backend.remesh_steps(context, work_object, request)
        calls.append(1)
        if len(calls) == 1:
            request.engine_info["method"] = "pair"
            request.engine_info["fallback"] = "the size variation is too strong for a regular grid on this shape"
        else:
            request.engine_info["method"] = "grid"

    def __getattr__(self, name):
        return getattr(self.backend, name)


pipeline.get_backend = lambda: PairOnce(real_backend())
retry_settings = pipeline.RemeshSettings()
retry_settings.output = "QUADS"
retry_settings.target_quads = 1500
from quadforge import presets  # noqa: E402
for name, value in presets.SURFACE_PROFILES["ORGANIC"].values.items():
    if hasattr(retry_settings, name):
        setattr(retry_settings, name, value)
retry_settings.curvature_detail = "HIGH"
retry_settings.target_quads = 1500
retry_settings.hide_original = False
try:
    retry_result = pipeline.run(bpy.context, obj, retry_settings)
finally:
    pipeline.get_backend = real_backend
check("pairing fallback on size variation triggers a gentler retry", len(calls) == 2, f"{len(calls)} engine runs")
check("the retry is reported", any("softened" in w for w in retry_result.warnings))

# the cleanup restores a flipped face next to its neighbour (a slit sewn together can leave one)
bm = bmesh.new()
bmesh.ops.create_grid(bm, x_segments=3, y_segments=3, size=1.0)
bm.faces.ensure_lookup_table()
bmesh.ops.reverse_faces(bm, faces=[bm.faces[4]])
check("test setup has flipped edges", pipeline._flipped_edges(bm) > 0)
pipeline._restore_winding(bm)
check("winding restored", pipeline._flipped_edges(bm) == 0)
bm.free()

print("\nALL PASSED" if not fails else f"\n{len(fails)} FAILED: {fails}")
sys.exit(1 if fails else 0)
