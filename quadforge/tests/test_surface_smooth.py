"""Unit tests for core/surfaces.py::smooth_face_surface (no Blender):

    python3 quadforge/tests/test_surface_smooth.py     (from the repository root)
"""
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from quadforge.core import geometry as g  # noqa: E402
from quadforge.core import surfaces as S  # noqa: E402


def grid(n):
    """n x n quads on the XY plane; returns MeshArrays."""
    co = np.array([[x, y, 0.0] for y in range(n + 1) for x in range(n + 1)], float)
    polys = [(y * (n + 1) + x, y * (n + 1) + x + 1, (y + 1) * (n + 1) + x + 1, (y + 1) * (n + 1) + x)
             for y in range(n) for x in range(n)]
    return g.from_polygons(co, polys)


def test_lone_face_joins_its_surroundings():
    m = grid(6)
    ids = np.zeros(m.n_polys, dtype=np.int32)
    ids[:] = 0
    ids[3 * 6 + 3] = 1          # one face of another surface in the middle of surface 0
    out = S.smooth_face_surface(m, ids)
    assert np.all(out == 0)


def test_one_face_wide_strip_is_kept():
    m = grid(12)
    ids = np.zeros(m.n_polys, dtype=np.int32)
    ids[2 * 12:3 * 12] = 1        # a full row: the faces inside it have two neighbours of their own surface
    out = S.smooth_face_surface(m, ids)
    # the open ends of a strip lose up to one face per pass (documented trade-off); the middle stays
    assert np.array_equal(out[2 * 12 + 3:3 * 12 - 3], ids[2 * 12 + 3:3 * 12 - 3])


def test_straight_border_is_kept():
    m = grid(6)
    ids = np.zeros(m.n_polys, dtype=np.int32)
    ids[:, ] = np.where(np.arange(m.n_polys) % 6 >= 3, 1, 0)
    out = S.smooth_face_surface(m, ids)
    assert np.array_equal(out, ids)


if __name__ == "__main__":
    failed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS {name}")
            except Exception as exc:  # noqa: BLE001
                failed += 1
                print(f"FAIL {name}: {exc!r}")
    sys.exit(1 if failed else 0)
