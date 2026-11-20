"""Concave n-gons are cut with ear clipping before the remesh (a fan from the first vertex flips triangles on them).
Run: python run_in_bpy.py blender_ngon_test.py (bpy module)."""
import sys
from pathlib import Path

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from quadforge.core import pipeline  # noqa: E402

fails = []


def check(name, ok, detail=""):
    print(("ok   " if ok else "FAIL ") + name, detail)
    if not ok:
        fails.append(name)


# a U-shaped (concave) polygon, counter-clockwise, 8 vertices; area = 4*3 - 2*2 = 8... (outer 4x3, notch 2x2 from the top)
outline = [(0, 0), (4, 0), (4, 3), (3, 3), (3, 1), (1, 1), (1, 3), (0, 3)]
area = 4 * 3 - 2 * 2
mesh = bpy.data.meshes.new("u")
mesh.from_pydata([(x, y, 0.0) for x, y in outline], [], [list(range(len(outline)))])
mesh.update()

# the fan from vertex 0, which is what the engine used to do: its signed area is wrong on a concave polygon
fan_area = 0.0
for i in range(1, len(outline) - 1):
    ax, ay = np.subtract(outline[i], outline[0])
    bx, by = np.subtract(outline[i + 1], outline[0])
    fan_area += abs(0.5 * (ax * by - ay * bx))
check("a fan covers the wrong area on this concave polygon", abs(fan_area - area) > 0.5, f"fan {fan_area:.2f} vs {area}")

count = pipeline._triangulate_ngons(mesh)
check("one n-gon was cut", count == 1, str(count))
check("it became 6 triangles", len(mesh.polygons) == len(outline) - 2 and all(len(p.vertices) == 3 for p in mesh.polygons))
total = sum(p.area for p in mesh.polygons)
check("the triangles cover exactly the polygon", abs(total - area) < 1e-6, f"{total:.4f}")
check("all triangles face the same way", all(p.normal.z > 0.99 for p in mesh.polygons))

# quads and triangles are left alone
quad = bpy.data.meshes.new("q")
quad.from_pydata([(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)], [], [[0, 1, 2, 3]])
quad.update()
check("a quad is untouched", pipeline._triangulate_ngons(quad) == 0 and len(quad.polygons) == 1)

print("FAILED" if fails else "all ok", fails)
sys.exit(1 if fails else 0)
