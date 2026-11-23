"""Surface-fit helpers: relax badly shaped quads and project them back on the source.

``relax_bad_quads`` smooths only the vertices of quads with a small corner
angle (min corner sine below ``BAD_QUAD_SINE``), keeps boundary and sharp-edge
vertices fixed, projects every move onto the source surface BVH tree (Blender
C++), and reverts moves that worsen or fold quads. ``quad_corner_sines`` is the
measure it uses.
"""
from __future__ import annotations

import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

from . import geometry as geo
from . import mesh_io as mio

ZONE_ATTRIBUTE = "quadforge_zone"     # per-face integer: which isolated zone a face belongs to


BAD_QUAD_SINE = 0.55        # a quad whose sharpest corner has a smaller sine (about 33 degrees off square) is relaxed
RELAX_BAD_STRENGTH = 0.6
RELAX_BAD_MAX_MOVE_EDGES = 1.0   # a vertex moves at most one local edge length per pass
STRETCH_LIMIT = 4.0         # a quad whose longest edge is more than this many times its shortest is relaxed too (the add-on counts 5 as a flaw)
STRETCH_RINGS = 2           # rows of vertices around a stretched quad that move with it, so the pinch is spread out


def quad_corner_sines(arrays) -> tuple[np.ndarray, np.ndarray]:
    """``(quad polygon indices, smallest corner sine of each quad)``; 1 is a square, 0 is flat or folded."""
    quads = np.flatnonzero(arrays.poly_sizes == 4)
    if quads.size == 0:
        return quads, np.zeros(0)
    loops = arrays.poly_offsets[quads][:, None] + np.arange(4)[None, :]
    points = arrays.co[arrays.loop_verts[loops]].astype(np.float64)        # (Q, 4, 3)
    worst = np.ones(quads.size)
    for k in range(4):
        a = points[:, (k - 1) % 4] - points[:, k]
        b = points[:, (k + 1) % 4] - points[:, k]
        denominator = np.linalg.norm(a, axis=1) * np.linalg.norm(b, axis=1)
        sine = np.linalg.norm(np.cross(a, b), axis=1) / np.maximum(denominator, 1e-30)
        worst = np.minimum(worst, sine)
    return quads, worst


def quad_stretch(arrays) -> np.ndarray:
    """Longest edge over shortest edge of every quad (same order as ``quad_corner_sines``)."""
    quads = np.flatnonzero(arrays.poly_sizes == 4)
    if quads.size == 0:
        return np.zeros(0)
    loops = arrays.poly_offsets[quads][:, None] + np.arange(4)[None, :]
    points = arrays.co[arrays.loop_verts[loops]].astype(np.float64)
    lengths = np.stack([np.linalg.norm(points[:, (k + 1) % 4] - points[:, k], axis=1) for k in range(4)], axis=1)
    return lengths.max(axis=1) / np.maximum(lengths.min(axis=1), 1e-30)


STRAY_FRACTION = 0.003            # a vertex farther than this share of the model diagonal from the source is a stray


def pull_stray_vertices(mesh, surface_tree, plane_axes=(), plane_offsets=None, plane_tolerance: float = 0.0) -> int:
    """Put the few vertices that ended up clearly off the source surface back on it. Returns how many moved.

    Only vertices farther than ``STRAY_FRACTION`` of the model diagonal move (everything else is left as the engine
    made it, so chamfers keep their shape). A vertex on a symmetry plane keeps its plane coordinate, so the mirror
    and weld still match.
    """
    arrays = mio.read_mesh_arrays(mesh)
    if arrays.n_verts == 0:
        return 0
    before = arrays.co.astype(np.float64)
    diagonal = float(np.linalg.norm(before.max(axis=0) - before.min(axis=0)))
    limit = STRAY_FRACTION * diagonal
    plane_offsets = plane_offsets or {}
    moved = 0
    after = before.copy()
    for index in range(arrays.n_verts):
        hit = surface_tree.find_nearest(Vector(before[index]))
        if hit[0] is None:
            continue
        target = np.asarray(hit[0], dtype=np.float64)
        if float(np.linalg.norm(target - before[index])) <= limit:
            continue
        for axis in plane_axes:
            if abs(before[index][axis] - plane_offsets.get(axis, 0.0)) <= plane_tolerance:
                target[axis] = before[index][axis]
        after[index] = target
        moved += 1
    if moved:
        mesh.vertices.foreach_set("co", after.astype(np.float32).reshape(-1))
        mesh.update()
    return moved


def relax_bad_quads(mesh, surface_tree, sharp_angle_degrees, passes: int) -> int:
    """Even out only the badly shaped quads and put the moved vertices back on the original surface.

    The engine already improves the quads it makes; what is left are quads squeezed between a pole and a
    hard edge or where the size changes quickly. Vertices on hard edges and on open borders (the symmetry cut
    included) never move, a vertex moves at most one local edge per pass, and a move that folds a quad or
    flips its normal is undone. Returns how many bad quads were left.
    """
    left = 0
    for _ in range(max(0, passes)):
        arrays = mio.read_mesh_arrays(mesh)
        quads, sines = quad_corner_sines(arrays)
        stretch = quad_stretch(arrays)
        is_bad = (sines < BAD_QUAD_SINE) | (stretch > STRETCH_LIMIT)
        bad = quads[is_bad]
        left = int(bad.size)
        if bad.size == 0:
            break
        fixed = geo.boundary_vertex_mask(arrays)
        if sharp_angle_degrees is not None:
            fixed |= geo.edge_vertex_mask(arrays, geo.detect_sharp_edges(arrays, sharp_angle_degrees))
        in_bad = np.zeros(arrays.n_verts, dtype=bool)
        loops = arrays.poly_offsets[bad][:, None] + np.arange(4)[None, :]
        in_bad[arrays.loop_verts[loops].reshape(-1)] = True
        stretched = quads[stretch > STRETCH_LIMIT]
        if stretched.size and STRETCH_RINGS > 0:
            # a pinched row cannot open if only its own vertices move: let the rows around it share the change
            in_stretch = np.zeros(arrays.n_verts, dtype=bool)
            in_stretch[arrays.loop_verts[(arrays.poly_offsets[stretched][:, None] + np.arange(4)[None, :]).reshape(-1)]] = True
            for _ in range(STRETCH_RINGS):
                grown = in_stretch.copy()
                grown[arrays.edges[in_stretch[arrays.edges[:, 0]], 1]] = True
                grown[arrays.edges[in_stretch[arrays.edges[:, 1]], 0]] = True
                in_stretch = grown
            in_bad |= in_stretch
        free = in_bad & ~fixed
        if not free.any():
            break
        before = arrays.co.astype(np.float64)
        relaxed = geo.relax_positions(before, arrays.edges, ~free, RELAX_BAD_STRENGTH, iterations=1)
        limit = RELAX_BAD_MAX_MOVE_EDGES * geo.vertex_mean_edge_length(arrays)
        after = before.copy()
        for index in np.flatnonzero(free):
            hit = surface_tree.find_nearest(Vector(relaxed[index]))
            target = np.asarray(hit[0] if hit[0] is not None else relaxed[index], dtype=np.float64)
            step = target - before[index]
            length = float(np.linalg.norm(step))
            if length > limit[index] > 0.0:
                step *= limit[index] / length
            after[index] = before[index] + step

        # undo the moves that make a neighbouring quad worse than it was or fold it
        trial = geo.MeshArrays(co=after, edges=arrays.edges, poly_offsets=arrays.poly_offsets,
                               loop_verts=arrays.loop_verts, loop_edges=arrays.loop_edges)
        _, new_sines = quad_corner_sines(trial)
        new_stretch = quad_stretch(trial)
        worse = quads[(new_sines < sines - 0.05) | (new_sines < 0.15)
                      | ((new_stretch > STRETCH_LIMIT) & (new_stretch > stretch + 0.5))]
        if worse.size:
            loops = arrays.poly_offsets[worse][:, None] + np.arange(4)[None, :]
            revert = np.unique(arrays.loop_verts[loops].reshape(-1))
            after[revert] = before[revert]
        if np.allclose(after, before):
            break
        mio.write_vertex_coordinates(mesh, after)
    return left


def copy_face_data(reference_mesh, target_mesh) -> None:
    """Copy material index and zone label from the nearest face of ``reference_mesh``.

    The engine rebuilds the mesh from scratch and drops per-face data; this
    restores it so materials survive and the next level still knows its zones.
    """
    reference = mio.read_mesh_arrays(reference_mesh)
    materials = mio.read_material_indices(reference_mesh)
    zone_attribute = reference_mesh.attributes.get(ZONE_ATTRIBUTE)
    zones = mio.read_attribute(reference_mesh, ZONE_ATTRIBUTE, reference.n_polys) if zone_attribute else None

    flat_loops = reference.loop_verts.tolist()
    offsets = reference.poly_offsets.tolist()
    polygons = [flat_loops[offsets[i]:offsets[i + 1]] for i in range(reference.n_polys)]
    tree = BVHTree.FromPolygons(reference.co.tolist(), polygons)

    target = mio.read_mesh_arrays(target_mesh)
    centers = geo.polygon_centroids(target)
    new_materials = np.zeros(target.n_polys, dtype=np.int32)
    new_zones = np.zeros(target.n_polys, dtype=np.int32)
    for face_index, center in enumerate(centers):
        hit = tree.find_nearest(Vector(center))
        if hit[2] is None:
            continue
        new_materials[face_index] = materials[hit[2]]
        if zones is not None:
            new_zones[face_index] = zones[hit[2]]
    mio.write_material_indices(target_mesh, new_materials)
    if zones is not None:
        mio.write_int_face_attribute(target_mesh, ZONE_ATTRIBUTE, new_zones)
        return new_zones
    return None
