"""Installing a new version over an old one must not leave old sub-modules in memory, and the panel must be able to
tell when it happens. Run: python run_in_bpy.py blender_reload_test.py (bpy module)."""
import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import quadforge  # noqa: E402
from quadforge.core import pipeline, version  # noqa: E402

fails = []


def check(name, ok):
    print(("ok   " if ok else "FAIL ") + name)
    if not ok:
        fails.append(name)


pipeline._stale_marker = True
importlib.reload(quadforge)                       # what happens when Blender imports the package again
fresh = sys.modules.get("quadforge.core.pipeline")
check("sub-modules of the old copy are dropped", fresh is None or not hasattr(fresh, "_stale_marker"))
from quadforge.core import pipeline as again  # noqa: E402,F811
check("pipeline is imported fresh", not hasattr(again, "_stale_marker"))
from quadforge import ui  # noqa: E402
check("code version matches the panel version", version.CODE_VERSION == ui.ADDON_VERSION and version.CODE_VERSION != "?")
print("FAILED:" if fails else "all ok", fails)
sys.exit(1 if fails else 0)
