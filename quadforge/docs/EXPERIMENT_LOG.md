# Experiment log (Hard Surface remesh)

What was tried, what it measured and whether it is in the add-on. Kept so that nothing is tried twice by accident and so a
result can be checked against the same corpus (`tools/cad_corpus.py` + `tools/cad_battery.py`). Details and numbers are in
`STATUS_AND_LIMITS.md` and `CHANGELOG.md`. Rule: an experiment that does not raise the share of corpus parts that pass, or
that breaks another part, stays out of the code and is listed here.

## In the add-on (measured gain)

| Change | Result |
| --- | --- |
| Ordered lists instead of sets in the finishing steps (0.16.7) | Same part, same mesh every run |
| Folded-strip cleanup threshold 1e-4 of the average face area + slit sewing (0.16.6/0.16.7) | No open edges left in the corpus; heat sink and shaft pass at 20K |
| `validate()` before removing doubles (0.16.6) | No hang on STL faces that collapse when welded |
| Strip collapse undone if it adds open edges (0.16.6) | No torn bevel corners |
| Count correction on the finished mesh (Unreleased) | Plate at 30K: 6 % short to inside 5 % |
| Second chance with finer thin strips (floor 0.35) when flaws > 3 % (Unreleased) | 20K: 18/20 to 20/20; 10K and real parts unchanged |
| Warning with a suggested quad count when flaws > 3 % (Unreleased) | 1.4x quads fixed flange, gear, enclosure, countersunk at 14K; heat sink needs 2x (20K) |

## Tried and not kept

| Experiment | Result | Why it stays out |
| --- | --- | --- |
| Aggressive sliver collapse (edge limit well above 1 % of the median) | 13/20 | Collapsing single edges of a quad makes triangles; worse than before |
| Finer thin-strip floor 0.35 as the default | 17/20 | Fixes flange, bracket; breaks bolt, countersunk, ratchet. Floor 0.45 was worse than both on the flange (not monotonic) |
| Sliding feature vertices in `improve_quads` | no gain | |
| Joining triangle pairs after the engine | no gain | |
| Loop-snap size fields (per loop and grouped), ring-grid in the Rust engine | flange 8.1 % to 7.7 %, 4x slower | Circumference not a whole number of cells costs ~1 % of a cell; not the cause |
| `FORGE_THINFEAT` 0.4 and 0 | no gain, 3x slower | |
| Quad-loop removal of squeezed strips as a post step | 2 usable rings on the flange, both tore the surface | An edge ring is global (short in the strip, normal elsewhere); a partial collapse leaves a triangle at each end |
- **Snap radius to marked lines 0.3 -> 0.1 / 0.2 / 0.45 / 0.6 / 1.0 rho (engine, `finish.rs`)**, Cylinder Ver-01 at 5K: up to 0.45 no change; 0.6 on the 8 parts at 5K: 1 of 8 pass (Test Object Ver-01 18 % untidy). Keep 0.3. (Cylinder Ver-01 alone passes at 1.0 by luck.)
- **Reruns with 0.94x and 1.06x of the request; relax passes 2 / 6 / 12; strip collapse 5 / 50 %; quad quality off (engine)** on Cylinder Ver-01 at 5K: no change or worse, +20 s. Not kept.
- **What the untidy faces of Cylinder Ver-01 at 5K are** (154 quads under 11.5 degrees): 82 have a flat (about 180 degrees) corner at a valence-3 vertex, 34 flat corner at valence 4, 40 needles or short edges. They sit on the fillet that joins the top face to the wall, not in thin chamfers: a coarse lattice where the border jogs one row. Cause found afterwards: the detection of shallow-facet bevels (`soft_bevels`). Off, the flat valence-3 corners drop from 82 to 5 and Cylinder Ver-01 passes at 5K. Soft bevels off for every run is not better (20K Test Object Ver-04 lands 10 % over the count, 7 of 8), so 0.18.9 tries it as the last rerun and keeps it only when better.

## Open

* Remaining failures at 10K: flange, enclosure, countersunk, gear, heat sink. Features about as narrow as one cell; more quads fix them.
* Flaws are connected groups of nearly flat quads (flange 20K: 80 groups, shortest edge ~0.06 cell), not scattered quads. A real fix moves
  poles in the engine's field / extraction (what QuadWild and QuadriFlow do); not started.
* Plate: slot-through-cylinder patch, corner notch; Ver-01 transition patch; Ver-03 zigzag at hole rims; "3 flipped edges" warning not reproduced locally.
* Triangle counts differ between machines and thread counts (`FORGE_THREADS` reproduces a given count).

## Soft Surface / Organic (measured with `tools/organic_battery.py`, 10K unless said)

| Experiment | Result | Status |
| --- | --- | --- |
| Engine `--curv-adapt` (old Detail on Curves) on the female head | dropped by the safeguard (2x the poles): identical to Off | replaced |
| Bend map from averaged normals as `quadforge_density`, ratio 2.5, patch 2 quad lengths | head back 0.69 to 0.18 %, Hada 5K 1.54 to 0.67 %, dragon feat 8.0 to 2.0 %, poles equal or fewer (dragon 55 to 73 per 1000) | in the add-on (Detail on Curves) |
| Same with symmetry at ratio 2.5 | seam corners and a few triangles at the mouth groove of the synthetic head (folded strips) | ratio halved with symmetry |
| Ratio 2.0 / 3.0, patch 1 / 2 / 3, power 2 | not monotonic (Hada back 0.56 / 0.27 / 0.31 %); patch 2 gave fewer poles and fewer bad quads than patch 1; power 2 worse | patch 2, power 1 |
| Joining leftover triangles in the final mesh (face angle 45, shape 75) | no change: the leftovers are single triangles inside quads | not kept |
| Hand at 5K | feat 0.25 to 0.80 %: fingers are curved everywhere, so the map spends faces on them | known weakness |

Baseline (engine curvature, 10K, no symmetry): head back 0.69 %, Hada 0.42 %, hand 0.08 %, helmet 2.3 %, dragon 3.7 % (feat 8.0 %).

## Found on the dragon head with the 0.16.9 tests (sym X, 20K)
- Greg's run: 19,505 faces, 58 triangles, 2 n-gons, non-manifold warning. Here (same settings, 1/2/4 threads): 19,104 faces, 34 triangles, 6 n-gons, no non-manifold. Same result for every thread count, so the difference is the source or the scale.
- **Scale check:** 0.5x and 2x give exactly the same mesh as 1x (19,104 faces); 0.01x (19,441 faces, 103 s) and 5x (19,383) do not. The tolerances are relative to the model, so the cause is rounding amplified by the layout, not an absolute weld distance (the first guess here, which was wrong). It explains why Greg's machine gave 19,505 faces.
- Kept: `_merge_seam_triangle_pairs` (two mirror triangles sharing a seam edge become one convex quad): dragon 20K sym X 34 to 16 triangles. The rest are mirror pairs that only touch the plane at a vertex.
- Triangles cluster on the symmetry plane (x about 0) and at the neck end (z about -60); without symmetry only 8 triangles.
- Kept: `_split_non_manifold` as a final safety net.

## 0.17.0 tuning of Detail on Curves (organic battery, 10K quads, symmetry X; hand 5K without)
Single runs, so differences under about 0.1 % are noise (the layout is chaotic at that level).
| Setting | Hand 5K feat | Hada 10K poles / feat | Head 10K feat | Dragon 10K | Kept |
|---|---|---|---|---|---|
| patch 2.0 quads (0.16.9) | 0.63 | 27 / 1.73 | 0.90 | bad 0.54 %, feat 2.46, 150 s | replaced |
| patch 3.0, steps capped at 200 | 0.58 | 16 / 0.91 | 0.74 | bad 1.46 %, feat 2.86 | cap raised |
| patch 3.0, steps up to 450 | 0.58 | 16 / 0.91 | 0.74 | bad 1.12 %, feat 2.31, 73 s | **kept** |
| patch 2.5 | - | 21 / 1.14 | 1.14 | same as 3.0 capped | no |
| patch 4.0 | - | 18 / 1.28 | 1.02 | - | no |
| percentile 30 / 90 or 70 / 99 (hand) | 0.69 to 0.90 | - | - | - | no |
| Detail Off (reference) | 0.70 | 11.6 / 2.11 | - | - | - |
- The "hand at 5K is worse than Off" seen with 0.16.9 does not hold with the current metric: Medium 0.58 against Off 0.70.
- The 200-step cap made the dragon (890K source) use a smaller patch than asked; at 450 it is as asked, and faster overall because the engine gets a smoother density.
- Weakness left: dragon at 10K has 1.1 % of quads with a scaled Jacobian under 0.3 (0.5 % with the old patch). It is a stress case (a complex head in 10K quads).
- Seen on the way: sewing the slit of a removed folded strip reversed faces on some CAD parts (flange at 25K: 53 flipped edges). Kept: `_restore_winding` after the cleanup.

## Ideas not started (Soft Surface / Organic)

Soft version of the Hard Surface detection: continuous measures that weight the size and direction fields instead of hard edges.

* **Local feature size** (thin parts such as fingers, ear rims, eyelids) feeding the size field, the organic counterpart of `_refine_thin_bands`.
* **Curvature anisotropy map** (|k1 - k2|): strong direction alignment on ridges (lip edge, eyelids, nostrils, ear helix), weak alignment and pole placement preferred where the surface is isotropic (cheeks, forehead).
* **Automatic flow guides** from closed high-curvature loops (eye and mouth rings), as the bevel rings are found today.
* **Measure first:** head at 5K / 10K / 20K, uniform vs curvature-weighted, deviation from the source and poles near eyes and mouth. Weights only, never constraints: a finer or stronger constraint made the integer grid fail on Hard Surface parts (floor 0.35 was not monotonic).
