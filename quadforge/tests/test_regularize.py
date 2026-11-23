"""Unit tests for core/regularize.py (no Blender, no engine): fragments merge, planes and creases are respected."""
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from quadforge.core import regularize as R  # noqa: E402


def strip(n, bend_at=None):
    """A row of n quads (2n triangles) along x, flat or folded 90 degrees at column ``bend_at``."""
    co, tris = [], []
    for i in range(n + 1):
        x, z = float(i), 0.0
        if bend_at is not None and i > bend_at:
            x, z = float(bend_at), float(i - bend_at)
        co += [[x, 0, z], [x, 1, z]]
    for i in range(n):
        a, b, c, d = 2 * i, 2 * i + 1, 2 * i + 2, 2 * i + 3
        tris += [[a, c, b], [b, c, d]]
    idx = np.array(tris, np.int32).ravel()
    return np.array(co, np.float32), np.full(len(tris), 3, np.int32), idx


def test_small_curved_fragment_joins_neighbour():
    co, sizes, idx = strip(20)
    labels = np.zeros(len(sizes), np.int32)
    labels[18:21] = 1      # a stray fragment inside surface 0
    kinds = ["cylinder", "sphere"]
    topo = R.Topology(co, sizes, idx)
    out, merged = R.merge_fragments(topo, labels, kinds)
    assert merged >= 1 and set(out.tolist()) == {0}


def test_plane_never_absorbed_and_crease_kept():
    co, sizes, idx = strip(20, bend_at=10)
    labels = np.array([0] * 20 + [1] * 20, np.int32)
    kinds = ["plane", "cylinder"]
    topo = R.Topology(co, sizes, idx)
    out, merged = R.merge_fragments(topo, labels, kinds)
    out = R.majority_filter(topo, out, kinds)
    assert merged == 0 and (out == labels).all()


def test_band_strips_never_grow_and_enclosed_flat_fragment_joins():
    co, sizes, idx = strip(30)
    labels = np.zeros(len(sizes), np.int32)
    labels[:20] = 0                    # a long curved region
    labels[20:30] = 2                  # a plane wedge fan, enclosed by curved regions only ...
    labels[30:] = 1                    # ... and a bevel strip beyond
    kinds = ["cylinder", "bevel", "plane"]
    topo = R.Topology(co, sizes, idx)
    out, _ = R.merge_fragments(topo, labels, kinds)
    out = R.majority_filter(topo, out, kinds)
    assert (out[30:] == 1).all()                         # the bevel strip did not grow or shrink
    labels2 = labels.copy()
    labels2[24:26] = 2
    labels2[20:24] = 0
    labels2[26:30] = 0
    out2, merged = R.merge_fragments(topo, labels2, kinds)
    assert merged >= 1 and (out2[24:26] == 0).all()      # a 2-face flat sliver inside the curved region joined it


def grid(w, h):
    """w x h quads (2 triangles each) on a flat sheet."""
    co = np.array([[float(x), float(y), 0.0] for y in range(h + 1) for x in range(w + 1)], np.float32)
    tris = []
    for y in range(h):
        for x in range(w):
            a, b, c, d = y * (w + 1) + x, y * (w + 1) + x + 1, (y + 1) * (w + 1) + x, (y + 1) * (w + 1) + x + 1
            tris += [[a, b, c], [b, d, c]]
    return co, np.full(len(tris), 3, np.int32), np.array(tris, np.int32).ravel()


def test_two_face_tooth_on_a_border_is_rounded_off_but_planes_stay():
    co, sizes, idx = grid(12, 8)
    topo = R.Topology(co, sizes, idx)
    centroids = np.array([co[idx[3 * f:3 * f + 3]].mean(0) for f in range(len(sizes))])
    labels = np.where(centroids[:, 0] < 6.0, 0, 1).astype(np.int32)
    tooth = (centroids[:, 0] > 5.0) & (centroids[:, 0] < 7.2) & (centroids[:, 1] > 3.0) & (centroids[:, 1] < 4.2)
    labels[tooth] = 0                     # a tooth of region 0 reaching two cells into region 1
    kinds = ["cylinder", "freeform"]
    out = R.smooth_boundaries(topo, labels, kinds)
    assert (out != labels).sum() > 0 and (out[tooth] == 1).sum() > 0
    flat = R.smooth_boundaries(topo, labels, ["plane", "freeform"])
    assert (flat == labels).all()         # a plane never moves


def test_poor_primitive_fit_is_reported_as_freeform():
    co, sizes, idx = strip(4)
    report = {"surfaces": [{"id": 0, "kind": "cone", "triangles": 8, "err": 0.0034},
                           {"id": 1, "kind": "cylinder", "triangles": 0, "err": 0.0005}],
              "borders": [], "bands": {"bands": []}}
    labels = np.zeros(8, np.int32)
    _, out = R.regularize(co, sizes, idx, labels, report)
    assert out["surfaces"][0]["kind"] == "freeform" and out["surfaces"][1]["kind"] == "cylinder"
