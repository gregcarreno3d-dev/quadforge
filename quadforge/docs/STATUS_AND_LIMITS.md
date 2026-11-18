# Status and limits — QuadForge 0.17.0

See `EXPERIMENT_LOG.md` for the short list of what was tried, kept and rejected.

## Current status (0.17.0)
- **Surface analysis and chamfer/bevel detection (preview).** Tested on real CAD parts (a cylinder plate, a perforated plate, a flange, a spool-like part) and on synthetic parts (prisms, frustums, a tilted frustum, a UV sphere, a bracket with a tilted hole, a six-hole flange, a dome, a cone on a cylinder, an off-centre boss). Unit tests live in `engine-rs/src/stages/surfaces.rs`; the Blender test is `tests/blender_surfaces_test.py`.
- **Known limits of the analysis:** surfaces of revolution are searched only about the X, Y and Z axes through the centre of the model; fillets made of very thin facets and coarse 3-facet fillets are only partly detected; with *Use Surface Analysis* about 2 % of the faces can stay triangles (isolated ones in the quad flow); the detector is in the Linux engine checked into the repository, and in Windows / macOS builds made by CI.
- **Speed on CAD parts:** a plate with a strong size variation falls back after the second attempt (about 12 s instead of 26 s at 4K quads).

## Tested
- 0.17.0 Blender suite (hard, integration, surfaces, bevel, forge, zone_detail, zones, guides, head, preview, subdiv, uv, vgzones, surface): all pass; the matrix gives 66 of 67 (gear-like with 30 hard edges: 97 % quads, same as 0.16.7).
- FORGE engine (Linux): sphere, torus, box with 12 exact hard edges, hemisphere with border, cylinder, density (length ratio 2.99 vs 3 requested), meshes with defects, 120 random cases with no failures, 1.3 M tris → 40 K in ~7 s (peak ~390 MB).
- Python backend with the real engine through a simulated mesh.
- Windows and macOS binaries are built natively by CI and pass the engine tests there; real-machine use is still limited.

## Tested inside Blender (5.2.2, `bpy` module, headless)
- 28 original scenarios + 10 FORGE scenarios (`tests/blender_integration_test.py`, `tests/blender_forge_test.py`): pipeline, symmetry, levels, zones, density vertex group, quads/triangles output, operator, cancel (engine process stops, no leftovers), and installation of the real extension zip.
- Models by the author: hand (119K tris), bull ant with peg (119K), hard-surface plate (8K, 4 through holes): all produce valid, closed, consistently oriented meshes.

## Measured: FORGE vs QuadriFlow (2 CPU cores)
Target 4000 quads (historical comparison with Blender's QuadriFlow, which is no longer part of the add-on):
| Model | Engine (method) | Poles / 1000 quads | Regular vertices | Time |
|---|---|---|---|---|
| Bull ant | FORGE 0.7 (integer grid) | 40 | 96 % | 2.3 s |
| Bull ant | FORGE 0.5.1 (pairing) | 103 | 89 % | 1.6 s |
| Bull ant | QuadriFlow | 54 | 95 % | 4.9 s |
| Hard-surface plate (no marked edges) | FORGE 0.7 (integer grid) | 15 | 98 % | 1.0 s |
| Hard-surface plate (12 % marked edges) | FORGE 0.7 (pairing path) | 58–80 | 92 % | 0.4 s |
| Hard-surface plate | QuadriFlow | 20 | 98 % | 5.2 s |
| Hand | FORGE 0.7 (integer grid) | 11–14 | 98.6 % | 1.7 s |
| Hand | FORGE 0.5.1 (pairing) | 94 | 90 % | 1.4 s |
| Hand | QuadriFlow | 17 | 98 % | 4.9 s |

At higher counts FORGE 0.7: hand 20 000 quads 2.7 poles/1000 (13 s), 80 000 quads 2.8 (35 s); ant 20 000 quads 12, 80 000 quads 6.7 (67 s). QuadriFlow on your machine: about 1 pole per 1000 at 80–120 K quads, 30–100 s.
FORGE is faster at every size and now has fewer poles at 4000 quads; QuadriFlow still has roughly 2–3x fewer at 80 K quads and aligns better to hard edges.

## Benchmark against Blender's QuadriFlow (0.10.31, 20 000 faces, 2 CPU cores, no symmetry)

Scaled Jacobian (1 = perfect square, mean / worst 1 %), share of irregular vertices, and time. QuadriFlow = `bpy.ops.object.quadriflow_remesh`; FORGE default = Detail on Curves Off; FORGE face = Medium.

| Model | Method | Faces | Jacobian mean | Jacobian worst 1% | Irregular % | Seconds |
|---|---|---|---|---|---|---|
| head | QuadriFlow | 20236 | 0.988 | 0.841 | 0.31 | 16 |
| head | FORGE default | 19558 | 0.985 | 0.771 | 0.32 | 28 |
| head | FORGE face | 19966 | 0.980 | 0.797 | 0.60 | 32 |
| fairy | QuadriFlow | 17079 | 0.966 | 0.565 | 0.46 | 12 |
| fairy | FORGE default | 19877 | 0.983 | 0.714 | 0.73 | 20 |
| fairy | FORGE face | 20006 | 0.983 | 0.785 | 0.72 | 24 |
| skull | QuadriFlow | 20119 | 0.980 | 0.763 | 0.51 | 25 |
| skull | FORGE default | 19751 | 0.987 | 0.886 | 0.41 | 8 |
| hand | QuadriFlow | 18803 | 0.971 | 0.739 | 0.50 | 29 |
| hand | FORGE default | 20500 | 0.993 | 0.918 | 0.24 | 11 |
| ant | QuadriFlow | 19451 | 0.951 | 0.483 | 1.40 | 28 |
| ant | FORGE default | 19936 | 0.975 | 0.758 | 1.08 | 13 |

Reading: FORGE has better squares on 4 of 5 models, hits the face target (QuadriFlow missed it by 15 % on the fairy) and is faster on 3 of 5. QuadriFlow is a little better on the plain head (shape quality) and has fewer irregular vertices on the fairy. Detail on Curves raises the share of irregular vertices on purpose (more detail and rows that follow the creases).

## Triangle output against Blender's Decimate (Collapse), same triangle count

Smallest triangle angle (mean / worst 1 %), share of triangles under 20 degrees, worst distance from the source surface to the result (% of model size). Measured on the 297k-triangle sculpts, 2 CPU cores.

| Model | Tris | Method | Min angle mean | Worst 1% | Under 20 deg | Worst distance | Time |
|---|---|---|---|---|---|---|---|
| head | 20000 | FORGE | 53.0 | 41.1 | 0 % | 0.69 % | 2.6 s |
| head | 20000 | Decimate | 34.4 | 10.8 | 12.1 % | 1.57 % | 1.9 s |
| head | 5000 | FORGE | 53.0 | 41.0 | 0 % | 1.57 % | 2.4 s |
| head | 5000 | Decimate | 33.9 | 8.2 | 14.4 % | 3.03 % | 2.4 s |
| hand | 5000 | FORGE | 52.9 | 40.7 | 0 % | 1.27 % | 0.9 s |
| helmet | 30000 | FORGE | 52.8 | 40.5 | 0 % | 0.95 % | 4.7 s |
| helmet | 30000 | Decimate | 27.0 | 2.4 | 36.6 % | 2.23 % | 2.8 s |
| hand | 5000 | Decimate | 28.7 | 8.0 | 28.3 % | 3.91 % | 0.7 s |

Reading: FORGE triangles are close to equilateral and follow the surface about twice as closely. Decimate keeps the original vertices and FORGE does not: FORGE rebuilds the mesh. Since 0.10.31 the UV maps of the original are copied onto the result (Copy UV Maps), accurate except on faces that cross an old seam. Not adopted: curvature / thickness adaptive density in triangle mode (8x slower and the worst distance got worse).

## Tried and not adopted (0.10.31 work)

- Chord-rotation pole optimiser on the final quads (`FORGE_POLEMOVES`): fairy 145 -> 140 poles, about 3 %. The poles come from the field singularities, not from local moves.
- Distance rings around creases (`FORGE_RING`, `FORGE_RINGR`): eyes and nostrils wrap a little better, but with symmetry X the fairy went from 149 to 298 poles and the seam opened in a lighter setting. Off by default; kept as an experiment switch.

## Which quad method runs (automatic)
- **Integer-grid parametrization (0.7)**: closed surface, no density group, fewer than 1 % of the edges marked hard. Quads come from the iso-lines of a seamless (u, v) map; every face is then split into quads and relaxed on the surface. Fallback: the 0.6 position-field lattice (`--no-param`).
- **Triangle pairing (0.5.x)**: only as a fallback, when the integer-grid method fails or cannot follow a strong density gradient. Marked hard edges (0.8), painted density (0.9) and open borders (0.10) go through the integer-grid method. Pairing keeps hard edges and borders exactly.
Open borders: the engine closes every border loop with a cap, treats the loop as a hard-edge line, runs the integer-grid method and removes the quads on the cap. Loops shorter than about 6 quad edges are left closed (the hole disappears). The border may get a few triangles where very short edges were welded.

## Not tested
- Windows and macOS on real machines. Blender 4.2.0, 4.5.15 LTS, 5.1.2 and 5.2 were tested on Linux through the `bpy` module (integration, zones, guides, UV, surface, hard-edge suites and the 67-case matrix all pass); the Blender GUI itself was only used on 5.2 and 5.3 (0.16.9 and 0.17.0 tests).
- Test note: the `bpy` module can crash or hang at interpreter shutdown on 4.2 and 4.5 (a Blender issue, not the add-on's), so tests run through `quadforge/tests/run_in_bpy.py`, which exits with `os._exit`.

## Limitations
- Cells thinner than the quad size (very thin legs, antennae) can come out ragged or open.
- Hard-surface models with density groups on a smooth shape with very few singularities may fall back to the older pairing path (~60–80 poles/1000 quads). Caps of non-convex or very deep holes can intersect the model; then the engine falls back to pairing.
- **Finger tips, 120 000+ quads (improved in 0.10.13)**: where the parametrization stretches the grid (3–5× at thin tips) the isotropic mesh had fewer vertices than lattice points, so some cells were lost and filled with irregular patches. 0.10.13 subdivides stretched triangles virtually before extracting cells (hand at 118K: poles 280 → ~60, holes 13 → 5). A few holes can remain in the thinnest tips; they are filled and the result stays valid. Debug switch: `FORGE_NOSUBDIV=1`.
- Large counts take tens of seconds (a plain conjugate-gradient solver). Remeshing can be cancelled with Esc.
- No guide curves and no directly painted density (vertex group only). Detail by Zone gives about 1.7 times more faces for a factor of 2, not 4: the engine changes density gradually to keep clean quads.
- Subdivision Match is made for smooth shapes: near sharp creases points can move up to a third of an edge; triangles and n-gons are skipped.
- Flow guides on closed loops (around an eye) raise the share of quad rows that follow the loop only modestly on a synthetic head (62–70 %); real heads are still needed to tune this.
- Robustness suite (`t07_robustness.py`): 114/115 cases pass (0.10.31). Known miss: very small targets on hard-surface parts with many small features (a gear asked for 600 faces gives 372).
- Symmetry with FORGE quads on closed models: the whole model is remeshed with the planes as guide lines, then cut and mirrored (0.10.13; ant: poles 570 → 324, no open seam edges). The other cases still cut first.
- With symmetry the result is mirrored: if the model is not symmetric the shape changes (a warning is shown).

## Where the Hard Surface remesh still has defects (measured on 0.16.4)

Measured on the Ver-03 test part (a disc with four holes, a revolution wall and chamfers / bevels, about 8.7K triangles in, Hard Surface, 20K quads, with and without symmetry X). A bad quad is one whose worst corner has a scaled Jacobian (sine of the corner) below 0.3.

| Run | Faces | Triangles | Bad quads (below 0.3) |
|---|---|---|---|
| Symmetry X | 18,478 | 100 | about 140 (0.8 %) |
| No symmetry | 20,726 | 0 | about 515 (2.5 %) |

- The defects are small and local: they sit on the rings (hole rims, outer edge) at the places where the quad rows turn to follow the ring, and, with symmetry on, where a ring crosses the mirror line. The big surfaces are clean.
- The count is the same at 8K and 20K quads, so it is a structural effect of the field (several close hard-edge lines: ring edge, both sides of a chamfer), not of the density.
- About 24 of the 100 triangles lie on the mirror line (skinny pairs, corners of about 20 and 175 degrees that are not joined into a quad on purpose); the rest are isolated singularities.
- Tried and **not** enough (changes were reverted): joining triangle pairs again after the mirror, letting the vertices on the mirror plane slide along it, and letting the vertices of a crease line slide along it during the bad-quad relaxation. They moved the count of bad quads from 140 to about 134, so the cure has to change the topology (the engine: the way the cross field aligns to close parallel hard lines), not the vertex positions.
- At 80,000 quads with symmetry X the rims show the same effect over a larger area (84 s on this part).

## Soft Surface / Organic: measured with 0.17.0 (`tools/organic_battery.py`, 10K quads, symmetry X)
| Model | Quads | Poles / 1000 | Scaled Jacobian < 0.3 | Detail lost on the most curved 10 % (p99) | Time |
|---|---|---|---|---|---|
| Female head | 99.9 % | 7.0 | 0.08 % | 0.74 % | 17 s |
| Hada | 100 % | 16.0 | 0.03 % | 0.91 % | 19 s |
| Helmet | 100 % | 14.2 | 0.04 % | 2.2 % | 44 s |
| Dragon head (890K source) | 99.9 % | 74.5 | 1.1 % | 2.3 % | 74 s |
Hand at 5K without symmetry: 100 % quads, 11 poles per 1000, 0.58 %, 5 s. The helmet and the dragon are limited by resolution at 10K (feathers, rivets, scales, teeth need more quads). Results depend slightly on the machine (floating-point rounding is amplified by the layout).

## Soft Surface / Organic: first user tests of 0.16.9 (Blender 5.3, symmetry X)
Counts come from the panel's Last Result. (The 0.16.9 screenshots were replaced by the 0.17.0 ones below.)

| Model | Request | Faces | Quads | Poles | Time |
|---|---|---|---|---|---|
| Female head | 20K | 20,064 | 100 % | 52 | 9.5 s |
| Female head (source already 116,662 quads) | 120K | 116,662 | 100 % | 124 | 17.5 s |
| Helmet | 20K | 19,370 | 100 % | 193 | 13.2 s |
| Helmet | 120K | 120,252 | 12 triangles | 635 | 30.3 s |
| Dragon head (889K source triangles) | 120K | 123,639 | 16 triangles | 969 | 45 s |
| Dragon head | 20K | 19,505 | 99.7 % (58 triangles, 2 n-gons) | 843 | 23.8 s |

- The dragon at 20K with symmetry X reported "The result contains non-manifold edges". It could not be reproduced on the development machine (19,104 faces, 34 triangles, no non-manifold edges, same for 1, 2 and 4 threads). 0.16.9 adds a final repair of edges shared by three or more faces as a safety net; it is untested against the original case.
- Scaling the model by a power of two (0.5x, 2x) gives exactly the same mesh (19,104 faces); scaling by 0.01x or 5x gives a different one (19,441 and 19,383 faces; 0.01x also took 103 s, about twice as long). So the tolerances are relative to the model, as intended, and the difference is floating-point rounding that the layout decisions amplify. Two machines can therefore give slightly different meshes for the same sculpt.
- Triangles concentrate on the symmetry plane and at open necks.

## First user tests of 0.17.0 (Blender 5.3, 120K requested unless noted)
Screenshots in `docs/images/soft-surface` and `docs/images/hard-surface` (cropped to the viewport and the add-on panel). Counts come from the panel's Last Result.

| Model | Mode | Faces (vs request) | Triangles | Poles | Time |
|---|---|---|---|---|---|
| Female head, symmetry X, Detail on Curves Medium | Soft | 118,490 (-1.3 %) | 8 | 501 | 29.1 s |
| Bull ant, symmetry X, Medium | Soft | 115,548 (-3.7 %) | 0 | 136 | 18.1 s |
| Helmet, symmetry X, Medium | Soft | 114,639 (-4.5 %) | 10 (+2 n-gons) | 906 | 90.2 s |
| Dragon head (889K source), symmetry X, request 80K | Soft | 74,881 (-6.4 %) | not recorded | not recorded | not recorded |
| Plate with ring and slot | Hard | 116,772 (-2.7 %) | 30 | 202 | 23.3 s |
| Cylinder Ver-01 | Hard | 117,389 (-2.2 %) | not recorded | not recorded | not recorded |
| Cylinder Ver-02, symmetry X | Hard | 120,504 (+0.4 %) | not recorded | not recorded | not recorded |
| Cylinder Ver-03, symmetry X | Hard | 118,712 (-1.1 %) | not recorded | not recorded | not recorded |

What the screenshots show:
- **Analyze Form works as intended.** Orange (finer faces) lands on eyelids, ear rims, nostrils and lips of the head, on the joints and feet of the ant, on the rivets and edges of the helmet and on the teeth, horns and spines of the dragon; flat areas stay blue.
- **Clean results:** head, ant, Cylinder Ver-02 and the flat areas of the plate are regular and almost all quads.
- **Ver-03 still has torn patches around the four holes** (zigzag rows of thin quads on the rims; the rest of the part is clean). This was already open in 0.16.9 and 0.17.0 did not fix it. It is the next Hard Surface item.
- **Ver-01 (free-form top)** shows three spiral-shaped pole groups on the top face, and in the side view a dark band of stretched quads on the sloping surface (it may be partly the grazing view angle; to be checked on the mesh).
- **Plate:** small irregular patches near the chamfers around the holes; the local warning reported a group of 11 untidy faces near (21.07, 16.26, 0.14).
- **Counts:** the helmet (-4.5 %) and the dragon (-6.4 %) fall short of the request; the dragon is just outside the 6 % tolerance of the organic battery. The helmet took 90 s at 120K (30 s in 0.16.9 at the same request); the likely cause is Detail on Curves (Medium), not yet measured.
- The dragon's non-manifold warning at 20K was not retested in this round.

## Known issues
- **Intermittent seam gap with symmetry.** Once, on GitHub's continuous-integration runner, the matrix scenario "block-holes,
  symmetry X + hard edges" ended with 3 open edges on the centre seam (the add-on warned about it). It could not be
  reproduced in about 100 local runs of that scenario (different thread counts, coordinate jitter, 24 repeated runs of that scenario),
  so the cause is most likely a platform-dependent numeric difference. Small gaps (one or two dropped quads at the
  seam) are repaired by the add-on; a gap of 14 or more edges is not (it needs a hole larger than the 12-side fill limit).
  The matrix test therefore reports but does not block the build. If you see "The centre seam has N open edges",
  try a slightly different target count or a larger Weld Distance, and please open an issue with the model.
- **Face Sets can differ from materials on one boundary face.** Once, on the Blender 4.2 runner, the zones test check
  "Face Sets copied and agree with materials" failed on the first run and passed on the rerun; it never failed in
  about 15 local runs (sizes 480 to 740, 1 to 8 threads, Blender 4.2 and 5.2, both engines). Materials and Face Sets are
  copied by two separate nearest-face lookups (`detail.copy_face_data` and `zonedata.copy_sculpt_data`), so a face
  whose centre lies exactly between two zones can be given one zone by each. It is cosmetic (one face of a zone border).

## Suggested roadmap
0.5.x: fixes after the author's tests. 0.6: lattice extraction. 0.7: integer-grid parametrization. 0.8: alignment to hard edges. Next: borders, a faster solver, thin-part handling. Then the Rust port (parallel version) and publishing.

## CAD battery results (0.17.0)

Same corpus and settings as 0.16.8: **20 of 20 at 20K quads, 18 of 20 at 30K (flange 7.6 %, heat sink 3.7 %), 15 of 20 at 10K** (countersunk, enclosure, flange, gear, heat sink); real parts at 30K (Plate and Cylinder Ver-01, Ver-02, Ver-03): 4 of 4. The heat sink at 30K was 3.7 % flaws already in the version just before 0.17.0, so it is the near-threshold case of a part with thin fins, not a result of the 0.17.0 changes. What 0.17.0 fixed here is orientation: the flange at 25K came out with 53 flipped edges (engine output had none) because sewing the slit of a removed folded strip reversed faces; the cleanup now restores a consistent winding.

## CAD battery results (0.16.8)

`tools/cad_battery.py` on the 20 synthetic parts of `tools/cad_corpus.py` (Hard Surface, no symmetry): **20 of 20 at 20K quads (100 %), 19 of 20 at 30K (95 %), 15 of 20 at 10K (75 %)**; real parts Plate, Cylinder Ver-01 and Ver-02 at 30K: 3 of 3. Face counts are within 6 % of the request in every passing case. The failure at 30K is the flange (7.6 % flaws, 168 s); it is not monotonic in the count (14K pass, 20K pass, 25K 4.7 %, 30K 7.6 %, 42K 0.8 %), so a nearby count is the remedy and is what the warning suggests. Below, the 0.16.7 section keeps the earlier numbers.

## CAD battery results (0.16.7)

`tools/cad_battery.py` on the 20 synthetic parts of `tools/cad_corpus.py` (Hard Surface, no symmetry): **18 of 20 pass at 20K quads, 15 of 20 at 10K**. The remaining failures are squeezed quads and a few triangles on rings (flange, bracket at 20K; flange, gear, enclosure, countersunk at 10K) and the heat sink's fins at 10K. Pass rates on these synthetic parts are a floor for the work still to do, not a promise for real parts: the target is 9 of 10 on real STL files.

Experiments that did not help (0.16.6 work): collapsing every edge shorter than 10 % of the median (flange 8.1 % to 6.7 % flaws, but the corpus fell from 15 to 13 passes because the collapsed quads became triangles); letting vertices on feature lines slide along their line in the engine's quad-quality pass (flange 1766 to 1739 flaws before finishing, 1403 to 1486 after). The squeezed quads on rings come from the vertex-count mismatch between the radial grid and the band rows, so they need a change in how the grid is laid out near rings, not a local fix afterwards.

Where the triangles of the Plate sit (30K quads, 160 triangles out of 29 108 faces): around the rims of the two round holes and the central bore (ring defect), and in a straight line along the long groove on the left side of the plate, where the quad rows on the two sides of the groove do not line up. The groove line is the cheaper of the two to fix: it is a straight feature, so the rows on both sides can be given the same spacing.

Ring-grid experiments in the engine (none kept): giving every closed marked loop a cell size that fits a whole number of quads, and giving the loops of one bevel (rim line, crease, rim line) the same quad count (flange at 20K: 8.1 % to 7.7 % flaws and four times slower; the other ring parts did not change); changing how close two marked lines may be before one is dropped (`FORGE_THINFEAT` 0.4 and 0: no gain, three times slower or worse). A circumference that is not a whole number of cells costs only about one percent of a cell per quad on a hole of any size, so it is not the cause. What remains is the strip between two rim lines about as narrow as one cell (a 0.7 mm bevel with two segments at 0.45 mm cells), where the grid has no room for a row: the cell size would have to follow the strip width, which is a different feature (a size field from the band width) and not a tweak.

Band-width size field (Unreleased): the add-on already had one (`_refine_thin_bands`), held at a floor of 0.6 of the normal size. Floor 0.35 as the default: 17 of 20 at 20K (fixes flange and bracket, breaks bolt, countersunk and ratchet); floor 0.45 was worse than both on the flange, so the effect is not monotonic. Kept as a second chance only when a result has more than 3 % flaws: 20 of 20 at 20K, 15 of 20 at 10K (flange, enclosure, countersunk, gear and heatsink still fail there, mostly because the grid has no room at that cell size). Heat sink at 10K (11.6 % flaws): 9 fins 1.2 mm thick with a 0.35 mm two-segment bevel on cells of about 0.9 mm leave a flat top of 0.5 mm, about half a cell; the engine gave 1195 flaws and the finer-strip rerun 1053 before cleanup, not enough to be kept. A part whose features are narrower than a cell needs more quads, not a better layout.

Where the remaining flaws sit (flange 20K, heat sink 10K, measured on the finished mesh): they are not scattered. Flange: 1577 squeezed quads in 80 connected groups (largest 342, 96, 90 faces), 8 singletons; the shortest edge of a flawed quad is a median 0.06 of an average cell (about 0.04 mm), so these are strips squeezed almost flat, not slightly narrow quads. Heat sink: 1183 flaws in 81 groups, 256 triangles. Only 7 % (flange) / 17 % (heat sink) of the vertices around them are poles. Removing the squeezed strip as a quad loop does not work as a local cleanup: an edge ring is global, short inside the squeezed strip and normal length across the rest of the part, so only 2 rings of the flange (4 edges each) were short along their whole length, and both tore the surface open when collapsed. Collapsing only the short stretch of a ring leaves a triangle at each end. A local fix would have to move poles (singularities) as quad tools do, which is a change in the engine's field and extraction, not in the finishing step.
