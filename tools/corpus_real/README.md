# Real-world Hard Surface test parts

Eight parts supplied by the add-on author for testing, stored as Wavefront OBJ with the **polygons as Blender holds
them** (quads and n-gons, not triangulated), in millimetres with the object scale applied:

| File | What it is |
|---|---|
| `Cylinder_Ver-01/02/03.obj` | cylinder parts; Ver-03 is the disc with four holes (rounded rims) |
| `Test_Object_Ver-01..05.obj` | five parts used to test chamfers, bevels and symmetry |

Run the whole folder through the battery:

    python3 tools/cad_battery.py tools/corpus_real --target 30000
    python3 tools/cad_battery.py tools/corpus_real/Cylinder_Ver-03.obj --target 120000 --sym x --save /tmp/out

Test_Object Ver-01 and Ver-03 are fully mirror-symmetric in X. Ver-02, Ver-04 and Ver-05 are only partly symmetric,
so `--sym x` is expected to fail the deviation check on Ver-02 and Ver-05 (the part itself is not symmetric).
Triangulated input behaves differently from the polygon input of a modelled part (the 4-hole disc is cleaner as
triangles), which is why the polygons are kept.

## sym/

Symmetric (mirror-X) versions of Cylinder_Ver-01, Test_Object_Ver-03/04/05 sent on 2026-11-22 (FBX converted to OBJ; the FBX units make them 0.1 wide instead of 100). Use with `--sym x`.
