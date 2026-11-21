# Testing guide for QuadForge 0.18.3

Thank you for testing. The engine passes its automated tests on Linux, Windows and macOS in continuous integration, and the
add-on was run on Blender 4.2, 4.5, 5.1 and 5.2 on Linux. What has **not** had real use is Windows and macOS on real
machines and your own models. That is what this guide is for. Plan about 30 minutes.

## Install

1. Download the zip for your system from the release (`windows-x64`, `macos-arm64` for Apple Silicon, `macos-x64` for
   Intel, `linux-x64`).
2. Blender: `Edit > Preferences > Get Extensions > ▾ > Install from Disk…`, pick the zip, enable it.
3. 3D Viewport, press **N**, tab **QuadForge**. The sections below the Remesh button change with the surface button (Hard Surface or Soft Surface / Organic); press **Show Help** to read the explanations. If a section you expect is missing, check *Advanced > Show All Options* and tell me which one.

If the engine does not start, the panel shows a message that says why; please copy it into your report.

## What to try

Use your own models where you can: a character or creature sculpt, a hard-surface part, and one messy mesh.

1. **Basic run.** Select a mesh, *Soft Surface (Organic)*, target 5,000 quads, *Remesh*. Does it finish, and does the flow look sensible?
2. **Quick Preview.** Press *Quick Preview* on a heavy sculpt (100K faces or more). It should take a few seconds and give a small copy. Then press *Remesh*: the preview should disappear.
3. **Hard Surface.** *Hard Surface*, a part with sharp edges. Are the edges kept?
4. **Symmetry.** Turn on X symmetry on a symmetric model. Is there an open seam in the middle? (Edit Mode, select non-manifold.)
5. **Detail by Zone.** Give two parts different materials, turn on *Isolate Zones > Materials*, press *Refresh Zones*, set one zone to 2. Does that zone get more faces, and is the border clean?
6. **Density.** Paint a vertex group on a face, choose it under *Density*. Do the painted areas get smaller faces?
7. **Subdivision Match** (Advanced, quads only). Remesh with it on, then add a Subdivision Surface modifier (level 2). Compare with the original: does the smooth result sit on the sculpt?
8. **Esc.** Start a large remesh (100K quads) and press Esc. Does it stop cleanly?
9. **Your worst model.** Open surfaces, loose parts, very thin parts, very dense (1M faces). Anything that fails or looks wrong is the most valuable report.

## How to report

Open an issue at the repository, or write to the person who sent you the zip, with:

- your operating system and Blender version (Help > About Blender);
- the QuadForge version (0.14.0) and the settings you used (a screenshot of the panel is enough);
- what you expected and what happened; the **Last Result** box and any yellow warning text, copied exactly;
- if you can share it, the model (or a cut-down version) that fails.

You do not need to find a problem to be useful: "tested on Windows 11, Blender 4.5, items 1 to 8 worked" is a good report too.

## Releasing

Releases are automatic. Update `version` in `quadforge/blender_manifest.toml` and add a matching `## <version>` section to `quadforge/CHANGELOG.md`, push, then push a tag `v<version>` (or run the *Release* workflow by hand with that tag). The workflow builds the engine on Linux, Windows, macOS arm64 and macOS x64, runs the 29 engine hard cases on each, packages the five zips, checks that the tag matches the manifest and publishes the GitHub release with the changelog section as its notes.


## CAD battery (for developers)

`python3 tools/cad_battery.py FOLDER_OR_FILES --target 20000 [--sym x] [--attempts 3] [--csv table.csv]` remeshes every STL / `.fmesh` with the Hard Surface settings and prints one verdict per part. A part passes when the result is closed (if the source was), has at least 98 % quads, at most 3 % triangles or squeezed quads, no vertex further than 0.5 % of the diagonal from the source, and a face count within 6 % of the request. The last line is the share of parts that passed. It needs Blender's Python module (`pip install bpy`). The thresholds are in `CRITERIA` at the top of the script. `python3 tools/cad_corpus.py OUT_FOLDER` writes 20 synthetic CAD parts to run it on (needs `bpy`).

`python3 tools/organic_battery.py FOLDER_OR_FILES --target 10000 [--curvature OFF] [--sym x] [--csv table.csv]` does the same for sculpts with the Soft Surface / Organic settings and prints, per part, the share of quads, the distance of the face count to the request, the quads with a scaled Jacobian below 0.3, poles per 1000 faces, and the surface error as a share of the bounding-box diagonal: `fwd` (result to source), `back` (source to result, the detail lost) and `feat` (`back` on the 10 % most curved source vertices). The thresholds in `CRITERIA` are provisional: compare two runs with `--csv` rather than trusting the verdict.
