"""Detail on Curves: a per-vertex edge-length multiplier that follows how strongly the form bends.

For every vertex the surface normals are averaged over a patch about the size of the quads that are asked for. If the
normals still agree, the patch is nearly flat at that scale and the multiplier stays 1. If they disagree, the surface turns
within one quad (eyelids, lips, nostrils, ear rims, horns, teeth) and the multiplier goes down, so the engine gives that
area smaller faces and the flat areas larger ones. The measure is relative to the quad size, so noise in a sculpt that is
smaller than a quad does not count, and it is smoothed, so the density changes gradually (an abrupt change makes poles).

Numpy only (Blender's Python has no scipy). The result is written to the ``quadforge_density`` attribute the engine reads.
"""
import numpy as np

SCALES = (1.0, 2.0, 3.0)  # averaging patch widths in quad lengths: the small one catches features about one quad wide
                          # (fangs, eyelids, scales), the large one the gentle bends and a smooth gradient
MAX_STEPS = 450           # diffusion steps (a huge mesh with tiny quads is capped: the effect only gets a little wider)
LOW_PERCENTILE = 50.0     # vertices at or below this bend are left at the normal size
HIGH_PERCENTILE = 97.0    # vertices at or above this bend get the full ratio


def _diffuse(vectors: np.ndarray, first: np.ndarray, second: np.ndarray, degree: np.ndarray, steps: int) -> np.ndarray:
    """Average every vertex with its neighbours ``steps`` times."""
    count = len(vectors)
    weight = 1.0 / (degree + 1.0)
    for _ in range(steps):
        total = vectors.copy()
        for axis in range(3):
            total[:, axis] += np.bincount(first, weights=vectors[second, axis], minlength=count)
            total[:, axis] += np.bincount(second, weights=vectors[first, axis], minlength=count)
        vectors = total * weight[:, None]
    return vectors


def form_multiplier(mesh, target_faces: int, ratio: float) -> np.ndarray:
    """Edge-length multiplier per vertex (1 = normal, down to 1 / ratio on the most bent areas)."""
    count = len(mesh.vertices)
    if count == 0 or len(mesh.polygons) == 0 or ratio <= 1.0:
        return np.ones(count)
    positions = np.empty(count * 3)
    normals = np.empty(count * 3)
    mesh.vertices.foreach_get("co", positions)
    mesh.vertices.foreach_get("normal", normals)
    positions = positions.reshape(-1, 3)
    normals = normals.reshape(-1, 3)
    pairs = np.empty(len(mesh.edges) * 2, dtype=np.int64)
    mesh.edges.foreach_get("vertices", pairs)
    first, second = pairs[0::2], pairs[1::2]
    areas = np.empty(len(mesh.polygons))
    mesh.polygons.foreach_get("area", areas)
    quad_length = float(np.sqrt(max(areas.sum(), 1e-30) / max(1, target_faces)))
    edge_length = float(np.median(np.linalg.norm(positions[first] - positions[second], axis=1)))
    if edge_length <= 0.0:
        return np.ones(count)
    degree = (np.bincount(first, minlength=count) + np.bincount(second, minlength=count)).astype(np.float64)
    averaged = normals.astype(np.float64)
    done = 0
    weight = np.zeros(count)
    for scale in SCALES:
        steps = int(min(MAX_STEPS, max(1, round((scale * quad_length / edge_length) ** 2))))
        averaged = _diffuse(averaged, first, second, degree, max(0, steps - done))
        done = max(done, steps)
        bend = 1.0 - np.linalg.norm(averaged, axis=1)
        low, high = np.percentile(bend, [LOW_PERCENTILE, HIGH_PERCENTILE])
        weight = np.maximum(weight, np.clip((bend - low) / max(high - low, 1e-12), 0.0, 1.0))
    return 1.0 / (1.0 + (ratio - 1.0) * weight)
