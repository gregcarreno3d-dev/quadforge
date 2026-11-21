"""Draw the top view (X/Y) of one or more OBJ results as a wireframe, triangles filled red.

    python3 tools/plot_topology.py OUT.jpg A.obj [B.obj ...] [--zmin Z] [--titles "A,B"]

Used for the gallery images in docs/images/hard-surface (before / after comparisons). Only faces whose mean Z is
above --zmin are drawn (default: the upper half of the part).
"""
import argparse

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.collections import LineCollection  # noqa: E402


def load(path):
    verts, faces = [], []
    for line in open(path):
        t = line.split()
        if not t:
            continue
        if t[0] == "v":
            verts.append([float(x) for x in t[1:4]])
        elif t[0] == "f":
            faces.append([int(x.split("/")[0]) - 1 for x in t[1:]])
    return np.array(verts), faces


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("out")
    ap.add_argument("inputs", nargs="+")
    ap.add_argument("--zmin", type=float, default=None)
    ap.add_argument("--titles", default="")
    args = ap.parse_args()
    titles = args.titles.split(",") if args.titles else [p for p in args.inputs]
    fig, axes = plt.subplots(1, len(args.inputs), figsize=(9 * len(args.inputs), 9), dpi=100, squeeze=False)
    for ax, path, title in zip(axes[0], args.inputs, titles):
        v, faces = load(path)
        zmin = args.zmin if args.zmin is not None else float(np.median(v[:, 2]))
        sel = [f for f in faces if v[f][:, 2].mean() > zmin]
        segs = [np.vstack([v[f][:, :2], v[f][:1, :2]]) for f in sel]
        ax.add_collection(LineCollection(segs, linewidths=0.3, colors="k"))
        tris = [v[f][:, :2] for f in sel if len(f) == 3]
        for p in tris:
            ax.fill(p[:, 0], p[:, 1], color="r", alpha=0.8)
        ax.autoscale()
        ax.set_aspect("equal")
        ax.set_title(f"{title}: {len(sel)} faces, {len(tris)} triangles")
        ax.axis("off")
    plt.tight_layout(rect=(0, 0, 1, 0.95))
    plt.savefig(args.out, format="jpg", pil_kwargs={"quality": 85})


if __name__ == "__main__":
    main()
