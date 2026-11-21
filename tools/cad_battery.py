#!/usr/bin/env python3
"""CAD battery: runs the Hard Surface remesh on a folder of STL (or .fmesh) parts and judges every result.

Needs Blender's Python module (``pip install bpy``, or run it with Blender's Python). Examples::

    python3 tools/cad_battery.py parts/ --target 20000
    python3 tools/cad_battery.py parts/*.stl --target 10000 --sym x --attempts 3 --csv battery.csv

For every part it prints one line and a verdict. A part PASSES when all of these hold:

* the result is closed and manifold if the source was (no open or non-manifold edges),
* at least 98 % of the faces are quads,
* at most 3 % of the faces are triangles or quads with a corner whose sine is below 0.3 (squeezed),
* no result vertex lies further than 0.5 % of the part's diagonal from the source surface (creases and chamfers kept),
* the face count is within 6 % of the request.

The thresholds are the ones in ``CRITERIA``; change them in one place. The summary at the end gives the share of
parts that passed: that is the number to watch while the remesh is being improved.
"""
import argparse
import csv
import glob
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)

CRITERIA = {
    "min_quad_share": 0.98,
    "max_flaw_share": 0.03,       # triangles + squeezed quads
    "squeezed_sine": 0.3,
    "max_deviation_diag": 0.005,  # of the bounding-box diagonal
    "count_tolerance": 0.06,
}


def load_part(path):
    """(coordinates, face sizes, loop vertex indices) of an STL or .fmesh file."""
    if path.lower().endswith(".obj"):
        # polygons as they are (quads and n-gons), the way Blender holds a modelled part
        verts, sizes, idx = [], [], []
        with open(path) as handle:
            for line in handle:
                parts = line.split()
                if not parts:
                    continue
                if parts[0] == "v":
                    verts.append([float(x) for x in parts[1:4]])
                elif parts[0] == "f":
                    face = [int(token.split("/")[0]) - 1 for token in parts[1:]]
                    sizes.append(len(face))
                    idx.extend(face)
        return np.array(verts, dtype=np.float32), np.array(sizes, dtype=np.int32), np.array(idx, dtype=np.int32)
    if path.lower().endswith(".stl"):
        from stlio import read_stl
        co, tris = read_stl(path)
        return co.astype(np.float32), np.full(len(tris), 3, dtype=np.int32), tris.astype(np.int32).ravel()
    from quadforge.core import forge_io
    co, sizes, idx = forge_io.read_fmesh(path)[:3]
    return co, sizes, idx


def make_object(bpy, co, sizes, idx, name):
    mesh = bpy.data.meshes.new(name)
    mesh.vertices.add(len(co))
    mesh.vertices.foreach_set("co", np.asarray(co, dtype=np.float32).ravel())
    mesh.loops.add(len(idx))
    mesh.loops.foreach_set("vertex_index", np.asarray(idx, dtype=np.int32))
    mesh.polygons.add(len(sizes))
    mesh.polygons.foreach_set("loop_start", np.cumsum(np.r_[0, sizes[:-1]]).astype(np.int32))
    mesh.polygons.foreach_set("loop_total", np.asarray(sizes, dtype=np.int32))
    mesh.update(calc_edges=True)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    return obj


def layout_flaws(positions, faces):
    """(triangles, squeezed quads) of a polygon list."""
    triangles = sum(1 for f in faces if len(f) == 3)
    quads = [f for f in faces if len(f) == 4]
    if not quads:
        return triangles, 0
    corners = positions[np.array(quads)]
    worst = np.ones(len(quads))
    for k in range(4):
        a = corners[:, k - 1] - corners[:, k]
        b = corners[:, (k + 1) % 4] - corners[:, k]
        sine = np.linalg.norm(np.cross(a, b), axis=1) / (np.linalg.norm(a, axis=1) * np.linalg.norm(b, axis=1) + 1e-30)
        worst = np.minimum(worst, sine)
    return triangles, int(np.count_nonzero(worst < CRITERIA["squeezed_sine"]))


def stretched_quads(positions, faces, ratio=5.0):
    """Quads whose longest edge is more than ``ratio`` times the shortest: the thin, dense rows that pile up along narrow
    chamfers and hole rims. They are not counted as flaws (their corners can still be right angles), so they are
    reported next to the verdict, not part of it."""
    quads = [f for f in faces if len(f) == 4]
    if not quads:
        return 0
    corners = positions[np.array(quads)]
    edges = np.stack([np.linalg.norm(corners[:, (k + 1) % 4] - corners[:, k], axis=1) for k in range(4)], axis=1)
    return int(np.count_nonzero(edges.max(axis=1) > ratio * np.maximum(edges.min(axis=1), 1e-12)))


def max_deviation(source_mesh, result_mesh):
    """Largest distance from a result vertex to the source surface."""
    import bmesh
    from mathutils.bvhtree import BVHTree
    # triangulate the way Blender does (ear clipping): a fan over a large concave n-gon would cover the wrong area
    bm = bmesh.new()
    bm.from_mesh(source_mesh)
    big = [face for face in bm.faces if len(face.verts) > 3]   # a triangle needs no cutting (and an STL has only triangles)
    if big:
        bmesh.ops.triangulate(bm, faces=big)
    tree = BVHTree.FromBMesh(bm)
    bm.free()
    worst = 0.0
    for vertex in result_mesh.vertices:
        hit = tree.find_nearest(vertex.co)
        if hit[0] is not None:
            worst = max(worst, hit[3])
    return worst


def run_part(bpy, pipeline, path, args):
    co, sizes, idx = load_part(path)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    obj = make_object(bpy, co, sizes, idx, "part")
    source_closed = True
    try:
        import bmesh
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        source_closed = all(e.is_manifold for e in bm.edges)
        bm.free()
    except Exception:
        pass
    settings = pipeline.RemeshSettings()
    settings.output = "QUADS"
    settings.target_quads = args.target
    settings.hide_original = False
    settings.use_sharp_angle = True
    settings.sharp_angle_deg = 30.0
    settings.smart_features = True
    settings.keep_right_angles = True
    settings.curvature_detail = "OFF"
    settings.use_surface_analysis = True
    settings.shading = "FLAT"
    settings.quality_attempts = args.attempts
    settings.sym_x = args.sym == "x"
    if args.no_soft_bevels:
        settings.soft_bevels = False
    if args.no_smooth:
        settings.smooth_surface_borders = False
    started = time.time()
    result = pipeline.run(bpy.context, obj, settings)
    seconds = time.time() - started
    level = result.levels[0]
    stats = level.stats
    mesh = level.object.data
    positions = np.array([v.co[:] for v in mesh.vertices], dtype=np.float64)
    faces = [list(p.vertices) for p in mesh.polygons]
    triangles, squeezed = layout_flaws(positions, faces)
    if getattr(args, "save", None):
        os.makedirs(args.save, exist_ok=True)
        with open(os.path.join(args.save, os.path.splitext(os.path.basename(path))[0] + "_result.obj"), "w") as fh:
            fh.writelines("v %.6f %.6f %.6f\n" % tuple(p) for p in positions)
            fh.writelines("f " + " ".join(str(i + 1) for i in f) + "\n" for f in faces)
    diagonal = float(np.linalg.norm(np.ptp(np.asarray(co, dtype=np.float64), axis=0)))
    deviation = max_deviation(obj.data, mesh) / max(diagonal, 1e-12)
    n = max(1, len(faces))
    row = {
        "part": os.path.basename(path), "faces": len(faces), "quad_share": round(1.0 - triangles / n, 4),
        "flaw_share": round((triangles + squeezed) / n, 4), "triangles": triangles, "squeezed": squeezed, "stretched": stretched_quads(positions, faces),
        "deviation_diag": round(deviation, 5), "count_error": round(abs(len(faces) - args.target) / args.target, 4),
        "open_edges": stats.get("border_edges", 0) + stats.get("non_manifold_edges", 0),
        "source_closed": source_closed, "seconds": round(seconds, 1),
    }
    problems = []
    if source_closed and row["open_edges"]:
        problems.append("open or non-manifold edges")
    if row["quad_share"] < CRITERIA["min_quad_share"]:
        problems.append("too many triangles")
    if row["flaw_share"] > CRITERIA["max_flaw_share"]:
        problems.append("squeezed quads")
    if row["deviation_diag"] > CRITERIA["max_deviation_diag"]:
        problems.append("moved off the source surface")
    if row["count_error"] > CRITERIA["count_tolerance"]:
        problems.append("face count off the request")
    row["verdict"] = "PASS" if not problems else "FAIL: " + ", ".join(problems)
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("inputs", nargs="+", help="STL / OBJ / .fmesh files or folders")
    parser.add_argument("--target", type=int, default=20000, help="requested face count (default 20000)")
    parser.add_argument("--sym", choices=["none", "x"], default="none", help="symmetry on X (default none)")
    parser.add_argument("--attempts", type=int, default=1, help="Quality Attempts (default 1)")
    parser.add_argument("--csv", help="write the table to this CSV file")
    parser.add_argument("--no-soft-bevels", action="store_true", help="switch Rounded Bevels off (experiment)")
    parser.add_argument("--no-smooth", action="store_true", help="switch the surface-border majority filter off (experiment)")
    parser.add_argument("--save", help="folder: write every result as a Wavefront OBJ there for inspection")
    args = parser.parse_args()

    paths = []
    for item in args.inputs:
        if os.path.isdir(item):
            for pattern in ("*.stl", "*.STL", "*.obj", "*.fmesh"):
                paths += sorted(glob.glob(os.path.join(item, pattern)))
        else:
            paths.append(item)
    if not paths:
        sys.exit("No STL or .fmesh files found.")

    import bpy
    from quadforge.core import pipeline
    rows = []
    for path in paths:
        try:
            row = run_part(bpy, pipeline, path, args)
        except Exception as error:      # one bad part must not stop the battery
            row = {"part": os.path.basename(path), "verdict": f"ERROR: {error}"}
        rows.append(row)
        print(f"{row['part']:<28} {row.get('faces', '-'):>7} faces  flaws {100 * row.get('flaw_share', 0):5.2f}%  "
              f"stretched {row.get('stretched', 0):>5}  "
              f"dev {100 * row.get('deviation_diag', 0):5.3f}%  {row.get('seconds', '-'):>6}s  {row['verdict']}", flush=True)
    passed = sum(1 for r in rows if r["verdict"] == "PASS")
    print(f"\n{passed} of {len(rows)} parts passed ({100 * passed / len(rows):.0f} %)")
    if args.csv:
        columns = sorted({k for r in rows for k in r})
        with open(args.csv, "w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns)
            writer.writeheader()
            writer.writerows(rows)
        print("table written to", args.csv)


if __name__ == "__main__":
    main()
