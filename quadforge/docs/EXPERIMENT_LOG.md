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

## Open

* Remaining failures at 10K: flange, enclosure, countersunk, gear, heat sink. Features about as narrow as one cell; more quads fix them.
* Flaws are connected groups of nearly flat quads (flange 20K: 80 groups, shortest edge ~0.06 cell), not scattered quads. A real fix moves
  poles in the engine's field / extraction (what QuadWild and QuadriFlow do); not started.
* Plate: slot-through-cylinder patch, corner notch; Ver-01 transition patch; Ver-03 zigzag at hole rims; "3 flipped edges" warning not reproduced locally.
* Triangle counts differ between machines and thread counts (`FORGE_THREADS` reproduces a given count).

## Ideas not started (Soft Surface / Organic)

Soft version of the Hard Surface detection: continuous measures that weight the size and direction fields instead of hard edges.

* **Local feature size** (thin parts such as fingers, ear rims, eyelids) feeding the size field, the organic counterpart of `_refine_thin_bands`.
* **Curvature anisotropy map** (|k1 - k2|): strong direction alignment on ridges (lip edge, eyelids, nostrils, ear helix), weak alignment and pole placement preferred where the surface is isotropic (cheeks, forehead).
* **Automatic flow guides** from closed high-curvature loops (eye and mouth rings), as the bevel rings are found today.
* **Measure first:** head at 5K / 10K / 20K, uniform vs curvature-weighted, deviation from the source and poles near eyes and mouth. Weights only, never constraints: a finer or stronger constraint made the integer grid fail on Hard Surface parts (floor 0.35 was not monotonic).
