"""Tidy the surface classification so each real face of the part is one region with clean borders.

The engine labels every triangle on its own, so a smooth dome or a fillet can come out as a mosaic (cylinder, sphere and
freeform patches side by side) with stair-stepped borders. This module runs on the labels only (no engine, no Blender):

1. ``merge_fragments``: a small curved region (or a small flat one that only curved regions surround, chamfer and bevel strips aside) joins the neighbour it shares the longest smooth border with.
2. ``majority_filter``: single faces on the wrong side of a border change side.
3. ``rebuild_borders``: the border list is rebuilt for the new labels (old kind kept where the pair existed;
   a new pair is tangent when its dihedral angle is small, sharp otherwise).

Planes are never absorbed by curved regions and curved regions never absorbed by planes across a crease: only borders
whose mean dihedral angle is below ``SMOOTH_DEG`` count as smooth. Entry point: :func:`regularize`.
"""
from __future__ import annotations

import numpy as np

SMOOTH_DEG = 20.0      # mean dihedral across a border below this = smooth (tangent) transition
TANGENT_DEG = 12.0     # new border pairs below this are reported as tangent, otherwise sharp
SMALL_FACES = 12       # curved regions up to this many faces (or SMALL_FRACTION of the part) are fragments
SMALL_FRACTION = 0.004
PLANE = "plane"
MERGE_FLAT = True       # small flat fragments enclosed by curved regions join them
BAND_KINDS = ("chamfer", "bevel")   # defined by the band detector (exact width): never grown or eroded here


class Topology:
    """Face adjacency and per-edge dihedral angles of a polygon soup given as ``sizes`` / ``idx`` arrays."""

    def __init__(self, co: np.ndarray, sizes: np.ndarray, idx: np.ndarray):
        offsets = np.concatenate([[0], np.cumsum(sizes)])
        n = len(sizes)
        normals = np.zeros((n, 3))
        self.size = np.zeros(n)           # longest edge of every face
        for f in range(n):
            p = co[idx[offsets[f]:offsets[f + 1]]].astype(np.float64)
            q = np.roll(p, -1, axis=0)
            nrm = np.array([((p[:, 1] - q[:, 1]) * (p[:, 2] + q[:, 2])).sum(),
                            ((p[:, 2] - q[:, 2]) * (p[:, 0] + q[:, 0])).sum(),
                            ((p[:, 0] - q[:, 0]) * (p[:, 1] + q[:, 1])).sum()])
            length = np.linalg.norm(nrm)
            normals[f] = nrm / length if length > 0 else 0.0
            self.size[f] = np.linalg.norm(q - p, axis=1).max()
        edge_faces: dict[tuple[int, int], list[int]] = {}
        for f in range(n):
            v = idx[offsets[f]:offsets[f + 1]]
            for k in range(len(v)):
                a, b = int(v[k]), int(v[(k + 1) % len(v)])
                edge_faces.setdefault((a, b) if a < b else (b, a), []).append(f)
        pairs = [(l[0], l[1]) for l in edge_faces.values() if len(l) == 2]
        self.n = n
        self.pairs = np.array(pairs, dtype=np.int64).reshape(-1, 2)
        dots = np.einsum("ij,ij->i", normals[self.pairs[:, 0]], normals[self.pairs[:, 1]]) if len(pairs) else np.zeros(0)
        self.angle = np.degrees(np.arccos(np.clip(dots, -1.0, 1.0)))
        self.neighbours: list[list[int]] = [[] for _ in range(n)]
        for a, b in pairs:
            self.neighbours[a].append(b)
            self.neighbours[b].append(a)


def _components(topo: Topology, labels: np.ndarray) -> np.ndarray:
    comp = -np.ones(topo.n, dtype=np.int64)
    count = 0
    for s in range(topo.n):
        if comp[s] >= 0:
            continue
        comp[s] = count
        stack = [s]
        while stack:
            f = stack.pop()
            for g in topo.neighbours[f]:
                if comp[g] < 0 and labels[g] == labels[f]:
                    comp[g] = count
                    stack.append(g)
        count += 1
    return comp


BAND_REACH = 3.0     # a face may join a chamfer / bevel only when its longest edge is at most this many band widths


def band_widths(report: dict) -> dict[int, float]:
    """Width of the chamfer / bevel band behind every band-kind surface id (from the analysis report)."""
    bands = (report.get("bands") or {}).get("bands", [])
    out = {}
    for s in report["surfaces"]:
        if s["kind"] in BAND_KINDS and 0 <= s.get("band", -1) < len(bands):
            out[s["id"]] = float(bands[s["band"]]["width"])
    return out


def can_join_band(topo: Topology, face: int, label: int, widths: dict | None) -> bool:
    """A small fragment may be absorbed by a band strip; a big triangle (a wedge of a fan next to a ring) may not."""
    if widths is None or label not in widths:
        return True
    return topo.size[face] <= BAND_REACH * widths[label]


def merge_fragments(topo: Topology, labels: np.ndarray, kinds: list[str],
                    widths: dict | None = None) -> tuple[np.ndarray, int]:
    """Small curved connected regions join the neighbour they share most smooth border with. Returns (labels, merged)."""
    labels = labels.copy()
    limit = max(SMALL_FACES, int(SMALL_FRACTION * topo.n))
    merged = 0
    for _ in range(4):   # a merge can expose another fragment
        comp = _components(topo, labels)
        sizes = np.bincount(comp)
        shared: dict[int, dict[int, float]] = {}
        touching: dict[int, set] = {}
        for (a, b), ang in zip(topo.pairs, topo.angle):
            ca, cb = comp[a], comp[b]
            if ca == cb or labels[a] < 0 or labels[b] < 0:
                continue
            if kinds[int(labels[b])] not in BAND_KINDS:
                touching.setdefault(ca, set()).add(int(labels[b]))
            if kinds[int(labels[a])] not in BAND_KINDS:
                touching.setdefault(cb, set()).add(int(labels[a]))
            if ang < SMOOTH_DEG:
                shared.setdefault(ca, {}).setdefault(cb, 0.0)
                shared[ca][cb] += 1.0
                shared.setdefault(cb, {}).setdefault(ca, 0.0)
                shared[cb][ca] += 1.0
        first_face = {}
        for f in range(topo.n):
            first_face.setdefault(int(comp[f]), f)
        step = 0
        for c in np.argsort(sizes):
            if sizes[c] > limit:
                break
            f0 = first_face[int(c)]
            lab = int(labels[f0])
            if lab < 0 or int(c) not in shared:
                continue
            if kinds[lab] == PLANE and not MERGE_FLAT:
                continue
            if kinds[lab] == PLANE and not (touching.get(int(c)) and all(kinds[t] != PLANE for t in touching[int(c)])):
                continue     # a flat fragment merges only when curved regions alone surround it
            best = max(shared[int(c)], key=shared[int(c)].get)
            target = int(labels[first_face[best]])
            if target < 0 or target == lab or sizes[best] < sizes[c] or (kinds[target] in BAND_KINDS and not all(can_join_band(topo, int(g), target, widths) for g in np.flatnonzero(comp == c))) \
                    or (kinds[lab] == PLANE and kinds[target] == PLANE):
                continue
            labels[comp == c] = target
            step += 1
        merged += step
        if not step:
            break
    return labels, merged


def majority_filter(topo: Topology, labels: np.ndarray, kinds: list[str], rounds: int = 2,
                    widths: dict | None = None) -> np.ndarray:
    """A face with fewer than two same-label neighbours moves to a label held by two or more of its neighbours.

    Plane faces never move (a flat face is a few large triangles, so it always has few neighbours), chamfer and bevel
    faces neither move nor receive faces (their width comes from the band detector; a thin wedge fan next to a bevel
    ring used to turn into stripes of it), and a face never crosses a crease: the edges it shares with the new label must be smooth (below ``SMOOTH_DEG`` on average).
    """
    out = labels.copy()
    edge_angle: dict[tuple[int, int], float] = {}
    for (a, b), ang in zip(topo.pairs.tolist(), topo.angle.tolist()):
        edge_angle[(a, b)] = edge_angle[(b, a)] = ang
    for _ in range(rounds):
        new = out.copy()
        changed = 0
        for f in range(topo.n):
            mine = int(out[f])
            if mine < 0 or kinds[mine] == PLANE:
                continue
            ids = [int(out[g]) for g in topo.neighbours[f]]
            same = ids.count(mine)
            if same >= 2:
                continue
            others: dict[int, int] = {}
            for i in ids:
                if i >= 0 and i != mine and (kinds[i] not in BAND_KINDS or can_join_band(topo, f, i, widths)):
                    others[i] = others.get(i, 0) + 1
            if others:
                best = max(others, key=others.get)
                angles = [edge_angle[(f, g)] for g in topo.neighbours[f] if int(out[g]) == best]
                if others[best] >= 2 and others[best] > same and np.mean(angles) < SMOOTH_DEG:
                    new[f] = best
                    changed += 1
        out = new
        if not changed:
            break
    return out


def rebuild_borders(topo: Topology, labels: np.ndarray, old_borders: list) -> list:
    """Border list for ``labels``: one entry per touching surface pair, keeping the old kind where the pair existed."""
    old = {(b["a"], b["b"]): b for b in old_borders}
    acc: dict[tuple[int, int], list[float]] = {}
    for (fa, fb), ang in zip(topo.pairs, topo.angle):
        a, b = int(labels[fa]), int(labels[fb])
        if a == b or a < 0 or b < 0:
            continue
        key = (a, b) if a < b else (b, a)
        acc.setdefault(key, []).append(float(ang))
    result = []
    for key, angles in sorted(acc.items()):
        mean = float(np.mean(angles))
        if key in old:
            entry = dict(old[key])
            entry["edges"] = len(angles)
        else:
            entry = {"a": key[0], "b": key[1], "length": 0.0, "edges": len(angles), "angle": mean,
                     "kind": "tangent" if mean < TANGENT_DEG else "sharp"}
        result.append(entry)
    return result


def regularize(co: np.ndarray, sizes: np.ndarray, idx: np.ndarray, labels: np.ndarray, report: dict) -> tuple[np.ndarray, dict]:
    """Return ``(labels, report)`` with fragments merged, borders straightened and the report kept consistent."""
    topo = Topology(co, sizes, idx)
    kinds = [s["kind"] for s in report["surfaces"]]
    widths = band_widths(report)
    new, merged = merge_fragments(topo, labels, kinds, widths)
    new = majority_filter(topo, new, kinds, widths=widths)
    report = dict(report)
    counts = np.bincount(new[new >= 0], minlength=len(kinds))
    surfaces = []
    for s, n in zip(report["surfaces"], counts):
        s = dict(s)
        s["triangles"] = int(n)
        surfaces.append(s)
    report["surfaces"] = surfaces
    report["borders"] = rebuild_borders(topo, new, report["borders"])
    report["face_surface"] = new.tolist()
    report["regularized"] = {"merged_regions": merged, "changed_faces": int((new != labels).sum())}
    return new, report
