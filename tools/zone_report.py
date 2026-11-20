"""Flaws of a remesh result, split by the kind of zone they sit in.

Usage (needs the Blender `bpy` module):
    python3 tools/zone_report.py SOURCE.obj RESULT.obj [--sym-tol 0.05]

The result is the file saved by `tools/cad_battery.py --save DIR` (or any quad OBJ). Every result face takes the zone of
the nearest source face, as found by the add-on's own band detector: flat/other, chamfer or bevel (convex or concave).
Flaws counted are the add-on's: triangles, squeezed corners (sine < 0.3) and stretched quads (longest/shortest > 5).
A second table splits the same flaws by distance to a symmetry plane (x = 0), to see seam problems separately.

Why: a change to the engine's rim handling is judged by where the flaws move, not only by their total.
"""
import argparse
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)


def load_into_blender(bpy, path, name):
    from cad_battery import load_part, make_object
    co, sizes, idx = load_part(path)
    return make_object(bpy, co, sizes, idx, name)


def zone_names(bands):
    """Band id (0-based) -> label such as 'bevel convex'."""
    out = {}
    for number, band in enumerate(bands):
        kind = str(band.get("kind", "band"))
        side = str(band.get("side", band.get("convexity", "")))
        out[number] = (kind + " " + side).strip()
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source")
    ap.add_argument("result")
    ap.add_argument("--sym-tol", type=float, default=0.05, help="distance to x=0 counted as the seam (model units)")
    args = ap.parse_args()
    import bpy
    import bmesh
    from mathutils.bvhtree import BVHTree
    from quadforge.core import bands as bands_mod
    from quadforge.core import pipeline

    bpy.ops.wm.read_factory_settings(use_empty=True)
    src = load_into_blender(bpy, args.source, "source")
    res = load_into_blender(bpy, args.result, "result")
    face_band, bands, _ = bands_mod.detect(src)
    names = zone_names(bands)

    bm = bmesh.new()
    bm.from_mesh(src.data)
    bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method="BEAUTY", ngon_method="EAR_CLIP")
    owner = []   # polygon of the source that each triangle came from: triangulate keeps order only per polygon, so map by centre
    tree = BVHTree.FromBMesh(bm)
    centres = np.array([p.center[:] for p in src.data.polygons])
    # nearest source polygon centre is too coarse for big flat faces; use the triangle hit, then its polygon by area-weighted lookup
    tri_poly = {}
    for t in bm.faces:
        c = t.calc_center_median()
        tri_poly[t.index] = int(np.argmin(np.sum((centres - np.array(c[:])) ** 2, axis=1)))
    flawed = pipeline._flawed_faces(res.data)
    n = len(res.data.polygons)
    zone_of = []
    for poly in res.data.polygons:
        loc, nor, index, dist = tree.find_nearest(poly.center)
        band = face_band[tri_poly[index]] if index is not None and face_band[tri_poly[index]] >= 0 else -1
        zone_of.append(names.get(int(band), "flat / other"))
    zone_of = np.array(zone_of)
    print(f"{n} faces, {int(flawed.sum())} flawed ({100 * flawed.mean():.2f} %)")
    tri = np.array([len(poly.vertices) == 3 for poly in res.data.polygons])
    print(f"{'zone':<28}{'faces':>8}{'flawed':>8}{'share':>8}{'tris':>7}{'quads':>7}")
    groups = {}
    for z in sorted(set(zone_of)):
        mask = zone_of == z
        groups.setdefault(z.split()[0] if z != "flat / other" else z, []).append(mask)
    for kind, masks in groups.items():
        mask = np.any(masks, axis=0)
        print(f"{kind:<28}{int(mask.sum()):>8}{int((flawed & mask).sum()):>8}{100 * (flawed & mask).sum() / max(1, mask.sum()):>7.2f}%{int((tri & mask).sum()):>7}{int((flawed & ~tri & mask).sum()):>7}")
    xs = np.array([p.center[0] for p in res.data.polygons])
    near = np.abs(xs) <= args.sym_tol * 10
    print(f"{'near the x=0 seam':<28}{int(near.sum()):>8}{int((flawed & near).sum()):>8}{100 * (flawed & near).sum() / max(1, near.sum()):>7.2f}%")
    far = ~near
    print(f"{'away from the seam':<28}{int(far.sum()):>8}{int((flawed & far).sum()):>8}{100 * (flawed & far).sum() / max(1, far.sum()):>7.2f}%")


if __name__ == "__main__":
    main()
