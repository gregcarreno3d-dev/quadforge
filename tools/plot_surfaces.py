"""Draw the Analyze Surfaces classification of a mesh, coloured as in the viewport (By Type), from a fixed view.

    python3 tools/plot_surfaces.py SOURCE.obj OUT.jpg [--view az,el] [--no-regularize]

Painter's algorithm with flat shading, no Blender needed. Used to check the segmentation (stair-stepped borders, stray
patches) and for the gallery. Prints the number of regions, small regions (10 faces or fewer) and surfaces by kind.
"""
import argparse
import pathlib
import sys
from collections import Counter

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.collections import PolyCollection  # noqa: E402

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from quadforge.core import surfaces as S  # noqa: E402


def load(path):
    verts, faces = [], []
    for line in open(path):
        t = line.split()
        if t and t[0] == "v":
            verts.append([float(x) for x in t[1:4]])
        elif t and t[0] == "f":
            faces.append([int(x.split("/")[0]) - 1 for x in t[1:]])
    return np.array(verts, np.float32), faces


def region_stats(faces, labels):
    edge_faces = {}
    for fi, f in enumerate(faces):
        for k in range(len(f)):
            a, b = f[k], f[(k + 1) % len(f)]
            edge_faces.setdefault((min(a, b), max(a, b)), []).append(fi)
    nb = [[] for _ in faces]
    for l in edge_faces.values():
        if len(l) == 2:
            nb[l[0]].append(l[1])
            nb[l[1]].append(l[0])
    seen = np.zeros(len(faces), bool)
    sizes = []
    for s in range(len(faces)):
        if seen[s]:
            continue
        stack, n = [s], 0
        seen[s] = True
        while stack:
            f = stack.pop()
            n += 1
            for g in nb[f]:
                if not seen[g] and labels[g] == labels[f]:
                    seen[g] = True
                    stack.append(g)
        sizes.append(n)
    return sizes


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source")
    ap.add_argument("out")
    ap.add_argument("--view", default="35,30", help="azimuth,elevation in degrees")
    ap.add_argument("--no-regularize", action="store_true")
    args = ap.parse_args()
    verts, faces = load(args.source)
    sizes = np.array([len(f) for f in faces], np.int32)
    idx = np.array([i for f in faces for i in f], np.int32)
    labels, report = S.analyze_arrays(verts, sizes, idx, regularize=not args.no_regularize)
    kinds = {s["id"]: s["kind"] for s in report["surfaces"]}
    region_sizes = region_stats(faces, labels)
    print(f"{len(faces)} faces, {len(region_sizes)} regions, {sum(1 for n in region_sizes if n <= 10)} small (<=10 faces)")
    print("faces by kind:", dict(Counter(kinds[int(l)] for l in labels)))
    az, el = (float(x) for x in args.view.split(","))
    az, el = np.radians(az), np.radians(el)
    view = np.array([np.cos(el) * np.cos(az), np.cos(el) * np.sin(az), np.sin(el)])
    right = np.cross([0, 0, 1], view)
    right /= np.linalg.norm(right)
    up = np.cross(view, right)
    polys, depth, colors = [], [], []
    for fi, f in enumerate(faces):
        p = verts[f].astype(float)
        n = np.cross(p[1] - p[0], p[2] - p[0])
        ln = np.linalg.norm(n)
        if ln == 0 or n @ view < 0:
            continue
        shade = 0.45 + 0.55 * abs(float(n @ view)) / ln
        base = np.array(S.KIND_CODES and S.KIND_COLORS[S.KIND_CODES.get(kinds[int(labels[fi])], 6)][:3])
        colors.append(np.clip(base ** (1 / 2.2) * shade, 0, 1))
        polys.append(np.c_[p @ right, p @ up])
        depth.append(float(p.mean(0) @ view))
    order = np.argsort(depth)
    fig, ax = plt.subplots(figsize=(12, 9), dpi=100)
    ax.add_collection(PolyCollection([polys[i] for i in order], facecolors=[colors[i] for i in order],
                                     edgecolors="none", linewidths=0))
    ax.autoscale()
    ax.set_aspect("equal")
    ax.axis("off")
    plt.tight_layout()
    plt.savefig(args.out, format="jpg", pil_kwargs={"quality": 88})


if __name__ == "__main__":
    main()
