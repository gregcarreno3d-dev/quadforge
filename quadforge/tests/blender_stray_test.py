"""pull_stray_vertices moves only vertices far from the source, and keeps a symmetry-plane vertex on its plane.
Run: python run_in_bpy.py blender_stray_test.py (bpy module)."""
import sys
from pathlib import Path

import bpy
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from quadforge.core import detail  # noqa: E402

fails = []


def check(name, ok, detail_text=""):
    print(("ok   " if ok else "FAIL ") + name, detail_text)
    if not ok:
        fails.append(name)


bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.mesh.primitive_uv_sphere_add(radius=1.0, segments=16, ring_count=8)
source = bpy.context.active_object
tree = BVHTree.FromObject(source, bpy.context.evaluated_depsgraph_get())

bpy.ops.mesh.primitive_uv_sphere_add(radius=1.0, segments=16, ring_count=8)
test = bpy.context.active_object
vertices = test.data.vertices
near = next(i for i, v in enumerate(vertices) if abs(v.co.x) > 0.5)
vertices[near].co *= 1.001                        # a tiny error: must stay
stray = max(range(len(vertices)), key=lambda i: vertices[i].co.z)
vertices[stray].co.z += 0.3                       # clearly off the surface
vertices[stray].co.x = 0.0
vertices[stray].co.y = 0.0
before_near = vertices[near].co.copy()
moved = detail.pull_stray_vertices(test.data, tree, plane_axes=(0,), plane_offsets={0: 0.0}, plane_tolerance=1e-4)
check("one stray vertex moved", moved == 1, str(moved))
check("small error left alone", (test.data.vertices[near].co - before_near).length < 1e-6)
check("back on the surface", abs(test.data.vertices[stray].co.length - 1.0) < 0.02, str(test.data.vertices[stray].co.length))
check("keeps its plane coordinate", abs(test.data.vertices[stray].co.x) < 1e-6)
sys.exit(1 if fails else 0)
