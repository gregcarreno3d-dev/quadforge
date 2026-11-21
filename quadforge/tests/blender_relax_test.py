"""Stretched quads (longest edge more than 4 times the shortest) are relaxed together with the rows around them, and the
vertices stay on the source surface; vertices on the border stay where they are.
Run: python run_in_bpy.py blender_relax_test.py (bpy module)."""
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from quadforge.core import detail, mesh_io  # noqa: E402

fails = []


def check(name, ok, detail_text=""):
    print(("ok   " if ok else "FAIL ") + name, detail_text)
    if not ok:
        fails.append(name)


N = 12
ys = [float(i) for i in range(N)]
ys[6] = 5.08                       # one row squeezed against the row before it: quads 1.0 x 0.08
verts = [(float(x), (float(j) if x in (0, N - 1) else ys[j]), 0.0) for j in range(N) for x in range(N)]   # the border stays regular
faces = [(j * N + i, j * N + i + 1, (j + 1) * N + i + 1, (j + 1) * N + i) for j in range(N - 1) for i in range(N - 1)]
mesh = bpy.data.meshes.new("grid")
mesh.from_pydata(verts, [], faces)
mesh.update()
source = BVHTree.FromPolygons([tuple(v) for v in verts], [tuple(f) for f in faces])
border_before = np.array([v.co[:] for v in mesh.vertices])

before = detail.quad_stretch(mesh_io.read_mesh_arrays(mesh))
check("grid has stretched quads before", int((before > 4.0).sum()) >= N - 3, str(int((before > 4.0).sum())))
detail.relax_bad_quads(mesh, source, None, 10)
after = detail.quad_stretch(mesh_io.read_mesh_arrays(mesh))
check("no stretched quads after", int((after > 4.0).sum()) == 0, f"worst ratio {after.max():.2f}")
co = np.array([v.co[:] for v in mesh.vertices])
check("still on the plane", float(np.abs(co[:, 2]).max()) < 1e-6)
edge = np.array([i for i, (x, y, _) in enumerate(verts) if x in (0.0, N - 1.0) or y in (0.0, N - 1.0)])
check("border did not move", float(np.abs(co[edge] - border_before[edge]).max()) < 1e-9)
print("FAILED:" if fails else "all ok", fails)
sys.exit(1 if fails else 0)
