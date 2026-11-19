# Real-world Hard Surface test parts

Five binary STL parts (millimetres) supplied by the add-on author for testing
(exported from Blender, scale applied). Run the whole folder through the battery:

    python3 tools/cad_battery.py tools/corpus_real --target 30000
    python3 tools/cad_battery.py tools/corpus_real/Test_Object_Ver-01.stl --target 120000 --sym x

Ver-01 and Ver-03 are fully mirror-symmetric in X. Ver-02, Ver-04 and Ver-05 are
only partly symmetric, so `--sym x` is expected to fail the deviation check on
Ver-02 and Ver-05 (the part itself is not symmetric).
