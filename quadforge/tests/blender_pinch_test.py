"""A vertex with only two edges between two quads (a pinched corner) is dissolved into one quad; a normal vertex is not.
Run: python run_in_bpy.py blender_pinch_test.py (bpy module)."""
import sys
from pathlib import Path

import bpy
import bmesh  # noqa: E402,F401

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from quadforge.core import pipeline  # noqa: E402

fails = []


def check(name, ok, detail_text=""):
    print(("ok   " if ok else "FAIL ") + name, detail_text)
    if not ok:
        fails.append(name)


bm = bmesh.new()
v, a, b = bm.verts.new((0, 0, 0)), bm.verts.new((1, 0.3, 0)), bm.verts.new((-1, 0.3, 0))
p1, p2 = bm.verts.new((0, 1, 0)), bm.verts.new((0, -1, 0))
bm.faces.new((v, a, p1, b))
bm.faces.new((v, b, p2, a))
check("two quads share the corner", len(bm.faces) == 2 and len(v.link_edges) == 2)
count = pipeline._dissolve_seam_corners(bm, None)
check("one corner dissolved", count == 1, count)
bm.faces.ensure_lookup_table()
check("one quad left", len(bm.faces) == 1 and len(bm.faces[0].verts) == 4)
check("the corner is gone", not v.is_valid or len(v.link_faces) == 0)
bm.free()

bm = bmesh.new()
bmesh.ops.create_grid(bm, x_segments=3, y_segments=3, size=1.0)
faces_before = len(bm.faces)
count = pipeline._dissolve_seam_corners(bm, None)
check("a regular grid is left alone", count == 0 and len(bm.faces) == faces_before, count)
bm.free()
print("ALL PASSED" if not fails else f"FAILED: {fails}")
sys.exit(1 if fails else 0)
