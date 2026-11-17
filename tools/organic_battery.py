#!/usr/bin/env python3
"""Organic battery: runs the Soft Surface / Organic remesh on sculpts (STL or .fmesh) and measures every result.

Needs Blender's Python module (``pip install bpy``). Examples::

    python3 tools/organic_battery.py parts/ --target 10000
    python3 tools/organic_battery.py head.stl dragon.fmesh --target 5000 --curvature OFF --csv organic.csv

It uses the settings of the Soft Surface / Organic button (``presets.SURFACE_PROFILES["ORGANIC"]``) and lets you override
Detail on Curves with ``--curvature``. For every part it prints the numbers that matter for a sculpt:

* quads: share of quads and distance of the face count to the request;
* quad shape: share of quads with a scaled Jacobian below 0.3 (``bad``) and the 1st percentile;
* poles: vertices that are not 4-way, per 1000 faces;
* surface error as a share of the bounding-box diagonal: ``fwd`` (result vertices to the source, p99) and ``back``
  (source points to the result, p99: what the new surface lost) and ``feat`` (``back`` on the 10 % most curved source
  vertices, where eyes, lips, horns and teeth are);
* time.

Verdict: the thresholds in ``CRITERIA`` were set from the 0.17.0 measurements (female head, Hada and hand pass; the
helmet and the dragon at 10K are limited by resolution: fine feathers, rivets, scales and teeth need more quads, so they
fail on purpose; run them at 40K or more). The last line is the share of parts that passed. Use ``--csv`` to compare two
runs.
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
    "min_quad_share": 0.99,
    "count_tolerance": 0.06,
    "max_bad_share": 0.01,       # quads with scaled Jacobian < 0.3
    "bad_jacobian": 0.3,
    "max_fwd_p99": 0.003,        # of the diagonal
    "max_feat_p99": 0.010,       # 1 % of the diagonal on the most curved 10 % (0.17.0: head 0.74, Hada 0.91, hand 0.58)
    "max_poles_per_1k": 60.0,
}

from cad_battery import load_part, make_object  # noqa: E402


def poles_per_1k(mesh):
    """Interior vertices that are not 4-way, per 1000 faces."""
    edges = np.empty(len(mesh.edges) * 2, dtype=np.int64)
    mesh.edges.foreach_get("vertices", edges)
    valence = np.bincount(edges, minlength=len(mesh.vertices))
    border = np.zeros(len(mesh.vertices), dtype=bool)
    count = np.zeros(len(mesh.edges), dtype=np.int64)
    loop_edges = np.empty(len(mesh.loops), dtype=np.int64)
    mesh.loops.foreach_get("edge_index", loop_edges)
    count = np.bincount(loop_edges, minlength=len(mesh.edges))
    open_edges = np.flatnonzero(count == 1)
    pairs = edges.reshape(-1, 2)
    border[pairs[open_edges].ravel()] = True
    interior = ~border & (valence > 0)
    return 1000.0 * float(np.count_nonzero(interior & (valence != 4))) / max(1, len(mesh.polygons))


def jacobian_stats(mesh, limit):
    """(share of quads with scaled Jacobian below ``limit``, 1st percentile) of the quads of a mesh."""
    from quadforge.core import mesh_io as mio
    import quality_metrics as qm
    arrays = mio.read_mesh_arrays(mesh)
    sizes = np.diff(arrays.poly_offsets)
    jacobian, quads = qm.scaled_jacobian(arrays.co, sizes, arrays.loop_verts)
    if len(jacobian) == 0:
        return 1.0, 0.0
    return float(np.mean(jacobian < limit)), float(np.percentile(jacobian, 1))


def source_curvature(co, sizes, idx):
    """Normal-variation curvature proxy per vertex (0 flat .. 1 sharply bent) from the source triangles."""
    offsets = np.concatenate([[0], np.cumsum(sizes)])
    first = idx[offsets[:-1]]
    second = idx[offsets[:-1] + 1]
    third = idx[offsets[:-1] + 2]
    normal = np.cross(co[second] - co[first], co[third] - co[first]).astype(np.float64)
    normal /= np.linalg.norm(normal, axis=1, keepdims=True) + 1e-30
    summed = np.zeros((len(co), 3))
    counts = np.zeros(len(co))
    for corner in (first, second, third):
        np.add.at(summed, corner, normal)
        np.add.at(counts, corner, 1.0)
    return 1.0 - np.linalg.norm(summed, axis=1) / np.maximum(counts, 1.0)


def surface_errors(source_co, source_sizes, source_idx, result_mesh, diagonal, samples=60000):
    """p99 of (result vertices to source), (source points to result), and the same on the 10 % most curved source vertices."""
    from mathutils.bvhtree import BVHTree
    from stlio import read_stl  # noqa: F401  (keeps the import path honest)
    source_co = np.asarray(source_co, dtype=np.float64)
    offsets = np.concatenate([[0], np.cumsum(source_sizes)])
    polygons = [tuple(int(v) for v in source_idx[offsets[i]:offsets[i + 1]]) for i in range(len(source_sizes))]
    source_tree = BVHTree.FromPolygons([tuple(c) for c in source_co], polygons)
    forward = []
    for vertex in result_mesh.vertices:
        hit = source_tree.find_nearest(vertex.co)
        forward.append(hit[3] if hit[0] is not None else 0.0)
    result_tree = BVHTree.FromPolygons([tuple(v.co) for v in result_mesh.vertices],
                                       [tuple(p.vertices) for p in result_mesh.polygons])
    rng = np.random.default_rng(0)
    pick = rng.choice(len(source_co), min(samples, len(source_co)), replace=False)
    back = np.array([(result_tree.find_nearest(tuple(source_co[i]))[3] or 0.0) for i in pick])
    curvature = source_curvature(source_co, source_sizes, source_idx)[pick]
    curved = back[curvature >= np.percentile(curvature, 90)]
    diag = max(diagonal, 1e-12)
    return (float(np.percentile(forward, 99)) / diag, float(np.percentile(back, 99)) / diag,
            float(np.percentile(curved, 99)) / diag)


def run_part(bpy, pipeline, presets, path, args):
    co, sizes, idx = load_part(path)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    obj = make_object(bpy, co, sizes, idx, "part")
    settings = pipeline.RemeshSettings()
    settings.output = "QUADS"
    settings.target_quads = args.target
    settings.hide_original = False
    for name, value in presets.SURFACE_PROFILES["ORGANIC"].values.items():
        if name == "sharp_angle_degrees":
            settings.sharp_angle_degrees = float(value)
        elif hasattr(settings, name):
            setattr(settings, name, value)
    if args.curvature:
        settings.curvature_detail = args.curvature
    settings.sym_x = args.sym == "x"
    started = time.time()
    result = pipeline.run(bpy.context, obj, settings)
    seconds = time.time() - started
    mesh = result.levels[0].object.data
    faces = len(mesh.polygons)
    totals = np.empty(faces, dtype=np.int64)
    mesh.polygons.foreach_get("loop_total", totals)
    diagonal = float(np.linalg.norm(np.ptp(np.asarray(co, dtype=np.float64), axis=0)))
    bad_share, jacobian_p1 = jacobian_stats(mesh, CRITERIA["bad_jacobian"])
    forward, back, feature = (0.0, 0.0, 0.0) if args.no_distance else surface_errors(co, sizes, idx, mesh, diagonal)
    row = {
        "part": os.path.basename(path), "faces": faces,
        "quad_share": float(np.mean(totals == 4)), "count_error": abs(faces - args.target) / args.target,
        "bad_share": bad_share, "jacobian_p1": jacobian_p1, "poles_per_1k": poles_per_1k(mesh),
        "fwd_p99": forward, "back_p99": back, "feat_p99": feature, "seconds": seconds,
    }
    reasons = []
    if row["quad_share"] < CRITERIA["min_quad_share"]:
        reasons.append("quads")
    if row["count_error"] > CRITERIA["count_tolerance"]:
        reasons.append("count")
    if row["bad_share"] > CRITERIA["max_bad_share"]:
        reasons.append("bad quads")
    if not args.no_distance and row["fwd_p99"] > CRITERIA["max_fwd_p99"]:
        reasons.append("deviation")
    if not args.no_distance and row["feat_p99"] > CRITERIA["max_feat_p99"]:
        reasons.append("features lost")
    if row["poles_per_1k"] > CRITERIA["max_poles_per_1k"]:
        reasons.append("poles")
    row["verdict"] = "PASS" if not reasons else "FAIL: " + ", ".join(reasons)
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("parts", nargs="+", help="STL / .fmesh files or folders")
    parser.add_argument("--target", type=int, default=10000)
    parser.add_argument("--curvature", choices=["OFF", "LOW", "MEDIUM", "HIGH"], help="override Detail on Curves")
    parser.add_argument("--sym", choices=["none", "x"], default="none")
    parser.add_argument("--no-distance", action="store_true", help="skip the surface error (faster on big parts)")
    parser.add_argument("--csv", help="write the table to this file")
    args = parser.parse_args()

    import bpy
    from quadforge.core import pipeline
    from quadforge import presets

    files = []
    for entry in args.parts:
        files += sorted(glob.glob(os.path.join(entry, "*.stl")) + glob.glob(os.path.join(entry, "*.fmesh"))) \
            if os.path.isdir(entry) else [entry]
    rows = []
    for path in files:
        try:
            row = run_part(bpy, pipeline, presets, path, args)
        except Exception as error:   # keep going: one bad part must not hide the others
            row = {"part": os.path.basename(path), "verdict": f"ERROR {error!r}"}
            print(f"{row['part']:<22} {row['verdict']}", flush=True)
            rows.append(row)
            continue
        rows.append(row)
        print(f"{row['part']:<18} {row['faces']:>7} faces  quads {100 * row['quad_share']:5.1f}%  count {100 * row['count_error']:4.1f}%  "
              f"bad {100 * row['bad_share']:4.2f}%  poles/1k {row['poles_per_1k']:5.1f}  "
              f"fwd {100 * row['fwd_p99']:.3f}%  back {100 * row['back_p99']:.3f}%  feat {100 * row['feat_p99']:.3f}%  "
              f"{row['seconds']:6.1f}s  {row['verdict']}", flush=True)
    passed = sum(1 for row in rows if row["verdict"] == "PASS")
    print(f"{passed} of {len(rows)} parts passed ({100 * passed // max(1, len(rows))} %)")
    if args.csv:
        keys = ["part", "faces", "quad_share", "count_error", "bad_share", "jacobian_p1", "poles_per_1k",
                "fwd_p99", "back_p99", "feat_p99", "seconds", "verdict"]
        with open(args.csv, "w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=keys, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)


if __name__ == "__main__":
    main()
