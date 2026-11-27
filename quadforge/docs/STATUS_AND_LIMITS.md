# Status and limits — QuadForge 0.18.1

See `EXPERIMENT_LOG.md` for the short list of what was tried, kept and rejected.

## Current status (0.18.15)
- **Surface analysis and chamfer/bevel detection (preview).** Tested on real CAD parts (a cylinder plate, a perforated plate, a flange, a spool-like part) and on synthetic parts (prisms, frustums, a tilted frustum, a UV sphere, a bracket with a tilted hole, a six-hole flange, a dome, a cone on a cylinder, an off-centre boss). Unit tests live in `engine-rs/src/stages/surfaces.rs`; the Blender test is `tests/blender_surfaces_test.py`.
- **Known limits of the analysis:** surfaces of revolution are searched only about the X, Y and Z axes through the centre of the model; fillets made of very thin facets and coarse 3-facet fillets are only partly detected; with *Use Surface Analysis* about 2 % of the faces can stay triangles (isolated ones in the quad flow); the detector is in the Linux engine checked into the repository, and in Windows / macOS builds made by CI.
- **Speed on CAD parts:** a plate with a strong size variation falls back after the second attempt (about 12 s instead of 26 s at 4K quads).

## Tested
- 0.18.15: Greg's real dragon head (889K triangles) and helmet (402K), 30K, symmetry X, Detail Medium. Dragon: 0.18.14 still fell to the pairing method (109.6 poles per 1,000, 1.36 % bad quads, 99.1 % quads); with the retry fixed it uses the grid at 50 % of Detail on Curves: 34.2 poles per 1,000, 0.20 % bad quads, 99.9 % quads, no non-manifold edges. Helmet: 100 % quads, 7.1 poles per 1,000, 0.01 % bad. Both still fail the detail check (dragon 1.44 %, helmet 1.80 % lost on the curved 10 %) because the sculpts are not symmetric and symmetry X mirrors one half; switch Symmetry off for the real shape.
- 0.18.14: form_detail suite (multi-scale mask on a one-quad spike, gentler retry after a pairing fallback), integration 26/26, UI and zone-detail suites pass. On a synthetic creature (fangs, horns, eye ridges, teeth, scales; 82K triangles) at 5K, no symmetry: Detail High loses 0.92 % of the diagonal on the curved 10 % (was 1.01), Medium 1.20 (was 1.14), Off 3.69. A stronger ratio does not help at a fixed face count (ratio 5: 1.87, ratio 7: 1.35). Not measured on the real dragon (the sculpt is not in the repository): Greg to confirm.
- 0.18.13: validation round: 20K battery 8 of 8 (Balanced), Blender form_detail, UI, integration (26/26) and FORGE suites pass. 5K Precise: 5 of 8 (patch criterion), see below.
- 0.18.12: Blender form_detail (Analyze Form colours survive an Edit Mode round trip; Speed / Precision default and pass-through), pinch and surfaces suites pass; CI green on Linux, Windows, macOS x64 and Blender 4.2 / 4.5 / 5.1 (macOS arm64 runners were cancelled for capacity several times).
- 0.18.11: Analyze Form colour fix verified with an Edit Mode round trip in Blender 5.3.
- 0.18.10: unit tests (regularize, surface smooth, geometry) and the Blender surfaces, surface and bundle suites pass; Test Object Ver-04 at 6K passes the battery with and without the regularization (same counts); surface regions on Ver-04 90 -> 38 (small ones 39 -> 10); Cylinder Ver-03 and the gear (Ver-05) unchanged and correct
- 0.18.6: ui, reload, bundle, relax, ngon, hard, integration (26 of 26), surfaces, zones, guides, head pass; an operator remesh on Test Object Ver-04 at 30K calls the relaxation
- 0.18.2: all Blender and Python suites pass (hard, integration 26 of 26, surfaces, bevel, forge, form_detail, zone_detail, zones, guides, head, preview, subdiv, uv, vgzones, surface, ui, ngon, relax, row_fit; matrix quick set 23 of 23); CAD battery at 30K, no symmetry: 8 of 8 real parts and 20 of 20 synthetic parts
- 0.18.1: all Blender and Python suites pass (hard, integration, surfaces, bevel, forge, form_detail, zone_detail, zones, guides, head, preview, subdiv, uv, vgzones, surface, ui, ngon, row_fit; matrix quick set 23 of 23), engine tests 7 of 7, battery on the 20 synthetic parts at 30K (26 of 26 with the real parts) and on the eight polygon parts at 30K (8 of 8).
- 0.18.0 Blender suite (hard, integration, surfaces, bevel, forge, form_detail, zone_detail, zones, guides, head, preview, subdiv, uv, vgzones, surface, ui): all pass; the matrix (quick set) gives 23 of 23. The 0.18.0 change is interface only, so the remesh results are the 0.17.0 ones (the full matrix gave 66 of 67 in 0.17.0: gear-like with 30 hard edges, 97 % quads).
- FORGE engine (Linux): sphere, torus, box with 12 exact hard edges, hemisphere with border, cylinder, density (length ratio 2.99 vs 3 requested), meshes with defects, 120 random cases with no failures, 1.3 M tris → 40 K in ~7 s (peak ~390 MB).
- Python backend with the real engine through a simulated mesh.
- Windows and macOS binaries are built natively by CI and pass the engine tests there; real-machine use is still limited.

## Battery with the patch criterion (0.18.12, Precise, no symmetry, 2 cores)

The battery now also fails a part that has a patch of more than 20 untidy faces touching each other, even when the overall share is small.

| Target | Passed | Detail |
|---|---|---|
| 20K | 8 of 8 | largest patch 15 faces (Cylinder Ver-01) |
| 5K | 5 of 8 | patches of 26 (Cylinder Ver-01), 22 (Test Object Ver-01) and 48 (Test Object Ver-04) faces; the earlier 8 of 8 at 5K did not measure patches |

## Speed / Precision (0.18.12), Cylinder Ver-01 / Ver-03 at 30K, symmetry X, 2 cores

| Mode | Ver-01 | Ver-03 | Notes |
|---|---|---|---|
| Fast | 13.5 s | 32 s | one pass; Ver-01 keeps a 106-face patch |
| Balanced | 41 s | 65 s | same meshes as Precise on these parts |
| Precise | 41 s | 92 s | every corrective rerun |

At 500K (Ver-01, symmetry X, Fast) one pass takes 330 s here, 290 s of it in the engine, so above 100K the engine, not the reruns, sets the time.

## Long-range battery on the symmetric test parts (0.18.10, 2 CPU cores, `tools/corpus_real`)

| Set | Target | Passed |
|---|---|---|
| 8 parts, no symmetry | 20K | 8 of 8 |
| 8 parts, no symmetry | 5K, 3.5K | 8 of 8 |
| 8 parts, no symmetry | 2.5K | 8 of 8 (after 0.18.9: Test Object Ver-04 6.1 % -> 2.0 %) |
| 8 parts, no symmetry | 1.5K | 4 of 8 (Cylinder Ver-03, Test Object Ver-03, Ver-04, Ver-05 above 3 %) |
| `sym/` (4 parts mirrored in X), symmetry X | 10K, 40K | 4 of 4 |
| `sym/`, symmetry X | 2.5K | 2 of 4 (Cylinder Ver-01, Test Object Ver-04: 7-10 % untidy faces) |

- Below about 5K faces, parts whose smallest chamfer or pocket is narrower than one cell end with triangles and squeezed quads around it. The panel already warns after the remesh and suggests 1.4x or 2x the quads; on Cylinder Ver-01 and Test Object Ver-04 that suggestion (about 5K) is where both pass.
- Analyze Surfaces on Test Object Ver-04 still shows a few teeth of the big cylinder along the border of the rounded end (one at the top is about three faces wide). The two-face rounding leaves anything wider; fixing it for good needs the engine to fit the rounded end as one surface.
- Test Object Ver-04, symmetry X, 3.5K: one vertex on the symmetry plane inside the small pocket ends 0.98 % of the diagonal off the source (limit 0.5 %). One vertex of 3318, produced by the engine (it stays with relax and joining switched off). Fixed after 0.18.7 by `pull_stray_vertices` (0.25 % now).
- Symmetry X on a part that is not mirrored (Cylinder Ver-01 and Test Object Ver-02/05 as first sent) moves the mesh off the surface by design; the panel warns when fewer than 90 % of the sampled points match.

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

## New Hard Surface test objects (five low-poly CAD parts, 0.18.0, no symmetry)
Five parts supplied by the author (424 to 6,035 source faces, 22 to 178 mm, closed and manifold), run through `tools/cad_battery.py`. Flaws are triangles plus squeezed quads; deviation is the largest distance to the source as a share of the diagonal. The parts themselves are not in the repository.

| Part | 10K | 20K | 30K | 120K |
|---|---|---|---|---|
| Ver-01 (large, free-form) | FAIL 4.75 % flaws | pass 1.32 % | pass 0.76 % | pass 0.50 % |
| Ver-02 (tall cylinder) | pass 0.33 % | pass 0.16 % | pass 0.07 % | pass 0.03 % |
| Ver-03 (slim part) | pass 0.39 % | pass 0.04 % | pass 0.00 % | pass 0.01 % |
| Ver-04 (6K source faces) | pass 1.60 % | pass 0.46 % | pass 0.26 % | pass 0.26 % |
| Ver-05 (flat plate) | pass 0.05 % | pass 0.02 % | pass 0.00 % | pass 0.00 % |

19 of 20 pass; the only failure is Ver-01 at 10K (squeezed quads). Deviation from the source stays below 0.003 % everywhere and the face counts are within 3 % of the request. Times (Linux, several runs at once, so only indicative): Ver-01 154 s and Ver-04 246 s at 120K; the others 55 to 75 s.

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

## Next: a larger change for bevels, chamfers and hole rims (planned, not started)
Chamfers and bevels are central to Hard Surface and CAD work, and the 4-hole disc shows the current limit: the rows
along circular hole rims are not aligned (see the Cylinder Ver-03 sections above). The plan, in order:
1. A rim-loop constraint in `engine-rs`: the cross field and the grid follow circular hard-edge loops (rings around holes).
2. Two dedicated detectors, one for **chamfers** (flat strips between two planes) and one for **bevels / fillets** (curved strips),
   that measure the width and the profile **per zone**, so a chamfer or bevel that changes width along its length gets the
   right number of rows in each place instead of one global setting.
3. Calibrate on the whole corpus (`tools/corpus_real/` (OBJ polygons) plus the synthetic parts) with the `stretched` count next to the verdict.
Until then, `Rounded Bevels` off or a nearby face count can give a cleaner rim on some parts.

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


## Symmetry X battery on the new Hard Surface test objects (0.18.0)

The parts now live in `tools/corpus_real/` (OBJ polygons).

| Part | Target | Symmetry | Result |
|---|---|---|---|
| Ver-03 | 30K / 120K | X | PASS, flaws 0.04 % / 0.01 % |
| Ver-04 | 30K | X | PASS, flaws 0.48 % |
| Ver-01 | 30K / 120K | X | PASS, flaws 1.02 % / 0.68 % (194 s at 120K) |
| Ver-02, Ver-05 | 30K | X | FAIL by design: the parts are not X-symmetric (deviation 1.6 % / 9.6 %) |

Correction: the "Ver-03" in those screenshots is the **Cylinder Ver-03** (the disc with four holes), not
`Test_Object_Ver-03` (the slim part). The table above is about the slim part.

### Cylinder Ver-03 hole rims: solved in 0.18.1 (the cause was the n-gon fan)

The tables in this section were measured on triangulated input or before the fix. The cause turned out to be the
engine's fan triangulation of concave n-gons (see the 0.18.1 changelog). With the fix, polygons as Blender holds them,
120K, symmetry X: 118,367 faces, 0.13 % flaws, 108 stretched quads, deviation 0.016 %, 16 triangles. What is left is a
short jagged stretch on one hole rim and a handful of triangles on the symmetry plane.

### Cylinder Ver-03 in the author's Blender, 0.18.1 (120K, symmetry X)

116,735 faces (2.7 % under the request), 116,655 quads (99.9 %), 80 triangles, 290 poles, 2,827 hard edges kept, 23 s,
one warning: 16 untidy faces near (19.44, 54.24, 21.19). The hole rims are now rings that follow each hole, where
0.18.0 showed torn rows. Images: `docs/images/hard-surface/disc-0.18.1-*.jpg`. What is still visible:
* one hole has a small spike of triangles on its inner rim (the warning location);
* on the underside, one hole rim has a short jagged stretch and a diamond-shaped cluster;
* the top edge of the concave side band has a slight sawtooth;
* star-shaped poles on the flat top near the symmetry plane.
Analyze Surfaces on the source (`disc-analysis-bevels-*.jpg`) finds two hole rims as bevels and two as chamfers, so
this part has both kinds, which the planned per-zone chamfer / bevel detectors are meant to treat separately.

### Symmetry X against no symmetry, 120K (0.18.2, measured 2026-11-21)

| Part | Symmetry X | No symmetry |
|---|---|---|
| Test Object Ver-04 | 118,739 faces, **54 triangles**, 0.09 % flaws, 106 stretched | 119,464 faces, **0 triangles**, 0.04 % flaws, 154 stretched |
| Cylinder Ver-03 | 118,368 faces, 68 triangles, 0.13 % flaws, 84 stretched | 120,042 faces, 44 triangles, 0.12 % flaws, 93 stretched |

On Ver-04, 34 of the 54 triangles sit on the symmetry plane (x = 0); 26 have an edge on it, in mirrored pairs that cannot be merged into a convex quad (the triangle has a right or obtuse angle at the seam). Seam vertices with 3 faces on one side (valence 6 after mirroring) come from the half-mesh border, where the grid is not aligned to the cut. Work-around today: switch symmetry off for parts where clean topology matters more than an exactly mirrored mesh. Planned: align the grid to the cut in the engine (border as a feature line with whole-row parity).

Tried and not adopted (relaxation in `core/detail.py`): relaxing triangles and folded faces together with two rings around them changed no count on the corpus.

Not a bug: "Widest Band (mm) 0.00" in the Analyze Surfaces panel means Auto.

### Cylinder Ver-03 through the FBX path, 120K, symmetry X (0.18.1, reproduced 2026-11-20)

Same route as the author's Blender (FBX import, scale applied, Hard Surface). Result: 116,680 faces, 54 triangles, 99 squeezed corners, 167 stretched quads, 267 s in the cloud container.

- The spike on a hole rim **reproduces**: a single tiny triangle at about (19.1, 52.4, 21.3) inside the thin rim strip. Other clusters: (0, 79, -21.7) on the symmetry plane (6 triangles), (83, 1.7, -24.8) on the outer rim, and several 2-triangle clusters along the hole rims and the lower band.
- `_join_leftover_triangles` cannot remove them: it only joins triangle pairs, and these triangles are isolated among quads. Relaxing the face-angle limit from 20 to 70 degrees joined 0 of 54.
- Conclusion: the leftover triangles come from the integer-grid step at the rims, so the remedy belongs in the engine (rim-loop constraint in `field.rs` / `param.rs`), not in the Python finishing.

**Flaws by zone** (new tool `tools/zone_report.py`, same FBX 120K result): bevels 133 flawed of 7,827 faces (**1.70 %**), chamfers 36 of 16,911 (0.21 %), flat and other 118 of 91,942 (0.13 %); near the x=0 seam 2.26 % (574 faces) against 0.24 % elsewhere. So the rounded bevels are about eight times worse than chamfers and thirteen times worse than flat areas; the seam is not the main problem. The engine work should aim at bevels first.

**What the bevel flaws are**: of the 133 flawed faces in bevels, 29 are triangles and 104 are squeezed or stretched quads. The 167 stretched quads of the whole part have a median shortest edge of 0.16 mm against a typical edge of 0.91 mm, so they are strips squeezed to a fifth of a row. Tried and not adopted: collapsing the short edges of stretched quads locally (limit 0.15 and 0.3 of the median edge). Both limits removed 2 flawed faces out of 287 and turned the collapsed quads into triangles (54 to 104 and 164). The thin strips have to be avoided where the rows are laid out (engine), not cleaned afterwards.

### Cylinder Ver-03 hole rims, reproduced (0.18.0, 120K, Hard Surface, symmetry X)

The ragged rows along the hole rims reproduce outside Blender. Two things were hiding them:

* `tools/cad_battery.py` set the angle on a field that does not exist (`sharp_angle_degrees`), so every battery run
  used 35 degrees instead of the profile's 30. Fixed (`sharp_angle_deg`).
* The verdict only counts triangles and squeezed corners. The rim problem is made of **stretched quads** (longest edge
  more than 5 times the shortest) piled up along a chamfer or step narrower than one quad, and those pass the
  corner test. The battery now prints a `stretched` count (information only for now, not part of the verdict).

Measured on the 4-hole disc at 120K, symmetry X: STL input 120,184 quads + 124 triangles, 449 stretched; the part as
Blender holds it (FBX, quad mesh) 115,192 quads, 0 triangles, 1,024 stretched. Both show the same jagged rim in a top
view, so this is an engine layout problem on thin rim steps, not a Blender-side setting. Next: resample the rim loops
of holes evenly and keep the rows along them.

### Rounded Bevels on the 4-hole disc (experiment, 30K, symmetry X, 30 degrees)

Same part, the quad mesh Blender holds (FBX import, applied scale): Rounded Bevels on = 29,359 faces, 166 triangles,
220 squeezed, 184 stretched; Rounded Bevels off = 29,707 faces, 14 triangles, 50 squeezed, 46 stretched, and a clean
top view. The rows that follow the rounded rim (rim fillet about 3 mm wide) are what tears there. It is **not** a
general fix: on the STL-input corpus at 30K (14 of 26 parts finished before the run was interrupted) switching it off
helped the bracket (stretched 111 to 46) and the disc (541 to 350), but changed the face count by more than 6 % on
Test_Object_Ver-04 and the enclosure. Not tested at 120K yet. `tools/cad_battery.py --no-soft-bevels` runs the
comparison.

### Rounded-bevel refinement on the 4-hole disc: what the sweep says

Quad mesh as Blender holds it (FBX), symmetry X, 30 degrees. `soft_bevel_detail` is the edge-length multiplier on the facets of a rounded bevel (default 0.5).

| Setting | 30K tris / squeezed / stretched | 120K tris / squeezed / stretched |
|---|---|---|
| 0.5 (default) | 166 / 220 / 184 | 0 / 1,066 / 1,024 |
| 0.35 | 316 / 306 / 235 | not run |
| 0.7 | 44 / 171 / 141 | not run |
| 0.85 | 10 / 73 / 68 | not run |
| 1.0 (no refinement) | 18 / 103 / 95 | 0 / 656 / 680 |

So halving the faces on the rim fillet makes it worse; a lighter refinement is better at 30K and no refinement
removes about a third of the stretched quads at 120K. It does **not** remove the problem: at 120K the top view
still shows dense, slanted rows on the rims at fixed angles around each hole. The remaining cause is the layout, not the
sizing: the grid is locked to the symmetry plane and the outer rim, and the engine cannot also run rows around the circular
hole rim without leaving a defect there. The fix has to constrain the cross field (and the grid) along circular rim
loops, in `engine-rs`; the default has not been changed yet because the sweep above is one part.

## 0.18.4: majority filter on the surface classification

Where: `core/surfaces.py::smooth_face_surface`, called from `core/pipeline.py` (`_mark_hard_edges_and_zones`), setting `smooth_surface_borders`. Hypothesis: the stair-stepped classification along chamfer and bevel borders makes jagged feature lines.

Measured at 30K quads, no symmetry (`tools/cad_battery.py`, `tools/zone_report.py`, sharp-chain deviation):

| Part | Filter | Flaws | Stretched | Chain vertices off the line by more than 0.15 mm |
|---|---|---|---|---|
| Cylinder_Ver-03 | off | 1.15 % | 203 | 69 |
| Cylinder_Ver-03 | 2 passes | 0.21 % | 31 | 29 |
| Cylinder_Ver-03 | 1 pass | 0.33 % | 63 | 27 |
| Test_Object_Ver-04 | off | 0.09 % | 37 | 6 |
| Test_Object_Ver-04 | 2 passes | 0.11 % | 77 | 38 |
| Test_Object_Ver-04 | 1 pass | no result in 400 s (not investigated) | | |

Reading: a clear gain on the disc, a small loss on Test_Object_Ver-04 (the chamfer zone went from 10 to 42 flawed faces in the zone report). Not proven on the rest of the corpus (each run takes about 3 minutes in the cloud). Next: run the 8 real and 20 synthetic parts with and without the filter and decide the default from the whole table.

A variant that protects the open ends of one-face strips (flip a face with one own neighbour only if that neighbour is weakly attached too) gave exactly the "filter off" numbers on both parts: the gain comes from the faces next to strip ends and notches, so the plain rule stays. Unit tests: `quadforge/tests/test_surface_smooth.py`.

## 0.18.5: marked-line distance in the engine

Where: `engine-rs/src/pipeline.rs::long_feature_chains` (`FORGE_THINFEAT`, cells). Raw engine output of the disc has 0 triangles but thin rows (0.07 mm against a 1.86 mm cell) along hole rims; the triangles appear when Python collapses them.

| `FORGE_THINFEAT` | stretched quads, 8 real parts (30K) | disc (Cylinder_Ver-03) stretched | flaws, mean of 8 |
|---|---|---|---|
| 0.75 (before) | 674 | 31 | 0.30 % |
| 1.5 | 927 | 62 | 0.41 % |
| 3 (now) | 357 | 89 | 0.20 % |

Per part: Cylinder_Ver-01 362 / 289 / 63, Test_Object_Ver-01 171 / 482 / 109. Non-monotonic, so the choice is a compromise; a real fix keeps one line of the pair but pins the other to the same row (ring constraint). Next.


## Measured for 0.18.9
- The engine result does not depend on the thread count: the 8 parts at 5K give byte-identical meshes with 1, 2 and 10 threads. A difference between a 10-core computer and the cloud's 2 cores is not a thread effect.
- Reruns (`run_steps`): up to three extra engine runs when the count is off or the layout is untidy; each is kept only when better. On symmetric parts at 10K that is 3 to 4 runs (Cylinder Ver-01: 29 s for 6 s of engine time), which is where the slowness of Cylinder Ver-03 with symmetry comes from. Tried and rejected: extra runs asking for 0.94x, 1.06x of the request (no gain, +20 s).
- Seam triangles on Test Object Ver-04 with symmetry X at 10K: 24 of 10 223 faces (0.2 %), 22 of them in mirrored pairs on the plane; lowering the shape gate of `_merge_seam_triangle_pairs` from 0.2 to 0.08 removes only 2, so it stays.
- Pinched corners (a vertex with only two edges, which the engine leaves where a chamfer is thinner than a cell) are now dissolved after the engine: 20 of them on Cylinder Ver-01 at 5K before, none now (`_dissolve_seam_corners`, plan None).
- **Pillows** (two faces on the same four vertices whose edges belong to nothing else, sometimes hanging from the mesh by one corner) were the vertices with two edges: Cylinder Ver-01 had five of them. `_remove_pillows` deletes them after the engine.
- **Soft-bevel detection can leave a flat corner at a valence-3 vertex on the crease** (82 of the 155 untidy faces of Cylinder Ver-01 at 5K: the rows along a shallow-facet bevel sit one row off the neighbouring face). The rerun `rigid` (soft bevels off) is tried last when the layout is untidy and kept only when better. On the 8 parts: 5K 8 of 8 (was 7), 3.5K 8 of 8, 2.5K 7 of 8, 20K 8 of 8; `sym/` 10K 4 of 4. Soft bevels off for everything is not better: at 20K Test Object Ver-04 lands 10 % over the requested count.
