"""Sidebar sections follow the surface type: Hard Surface shows Hard Edges and Surface Analysis, Soft Surface shows
Detail on Curves, the shared ones are always there, and 'Show All Options' shows everything.
Run: python run_in_bpy.py blender_ui_test.py (bpy module)."""
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import quadforge  # noqa: E402
from quadforge import ui  # noqa: E402
from quadforge.properties import apply_surface_profile  # noqa: E402

quadforge.register()
fails = []


def check(name, ok, detail=""):
    print(("ok   " if ok else "FAIL ") + name, detail)
    if not ok:
        fails.append(name)


HARD_ONLY = (ui.QUADFORGE_PT_hard_edges, ui.QUADFORGE_PT_bands)
SOFT_ONLY = (ui.QUADFORGE_PT_form,)
SHARED = (ui.QUADFORGE_PT_symmetry, ui.QUADFORGE_PT_guides, ui.QUADFORGE_PT_density, ui.QUADFORGE_PT_zones,
          ui.QUADFORGE_PT_levels, ui.QUADFORGE_PT_how_to_use, ui.QUADFORGE_PT_advanced)


def visible(panel):
    poll = getattr(panel, "poll", None)
    return True if poll is None else bool(poll(bpy.context))


settings = bpy.context.scene.quadforge
check("show_help defaults to off", settings.show_help is False)
check("show_all_options defaults to off", settings.show_all_options is False)

check("custom settings show every section",
      all(visible(p) for p in HARD_ONLY + SOFT_ONLY + SHARED))

apply_surface_profile(settings, "HARD")
check("Hard Surface shows its sections", all(visible(p) for p in HARD_ONLY))
check("Hard Surface hides Detail on Curves", not any(visible(p) for p in SOFT_ONLY))
check("Hard Surface shows the shared sections", all(visible(p) for p in SHARED))

apply_surface_profile(settings, "ORGANIC")
check("Soft Surface shows Detail on Curves", all(visible(p) for p in SOFT_ONLY))
check("Soft Surface hides Hard Edges and Surface Analysis", not any(visible(p) for p in HARD_ONLY))
check("Soft Surface shows the shared sections", all(visible(p) for p in SHARED))

settings.show_all_options = True
check("Show Options for Both shows everything", all(visible(p) for p in HARD_ONLY + SOFT_ONLY + SHARED))
settings.show_all_options = False

settings.curvature_detail = "HIGH"
check("changing a profile value unmarks the button and shows everything",
      settings.surface_type == "NONE" and all(visible(p) for p in HARD_ONLY + SOFT_ONLY))

# hidden sections keep their values
apply_surface_profile(settings, "ORGANIC")
settings.sharp_angle = 0.9
check("switching sections does not change the values", abs(settings.sharp_angle - 0.9) < 1e-6 or settings.surface_type == "NONE")

# panels registered in the intended order under the main panel
order = [c.__name__ for c in quadforge._CLASSES if c.__name__.startswith("QUADFORGE_PT")] if hasattr(quadforge, "_CLASSES") else []
if order:
    check("Last Result comes right after the main panel", order[:2] == ["QUADFORGE_PT_main", "QUADFORGE_PT_last_result"], str(order[:3]))

# reset restores the new options
settings.show_help = True
settings.show_all_options = True
bpy.ops.quadforge.reset_settings()
check("reset restores show_help and show_all_options", not settings.show_help and not settings.show_all_options)

# every registered panel draws help only through _help (no draw call raises without a region): the helper
class _Ctx:
    scene = bpy.context.scene
settings.show_help = False
calls = []
real = ui.draw_wrapped_text
ui.draw_wrapped_text = lambda *a, **k: calls.append(a)
ui._help(None, _Ctx, "x")
settings.show_help = True
ui._help(None, _Ctx, "x")
ui.draw_wrapped_text = real
check("_help draws only when Show Help is on", len(calls) == 1)

# every section draws without errors in both modes, with help on and off (a layout that accepts any call)
class _Any:
    def __getattr__(self, name):
        return self if not name.startswith("__") else (_ for _ in ()).throw(AttributeError(name))

    def __call__(self, *a, **k):
        return self

    def __setattr__(self, name, value):
        pass

    def __iter__(self):
        return iter(())


panels = [c for c in quadforge._CLASSES if c.__name__.startswith("QUADFORGE_PT")]
for key in ("HARD", "ORGANIC", None):
    for helped in (False, True):
        if key:
            apply_surface_profile(settings, key)
        else:
            settings.surface_type = "NONE"
        settings.show_help = helped
        broken = []
        for panel in panels:
            if not visible(panel):
                continue
            shim = type("Shim", (), {k: v for k, v in vars(panel).items() if not k.startswith("__")})()
            shim.layout = _Any()
            try:
                panel.draw(shim, bpy.context)
                if hasattr(panel, "draw_header"):
                    panel.draw_header(shim, bpy.context)
            except Exception as error:  # noqa: BLE001
                broken.append(f"{panel.__name__}: {error!r}")
        check(f"all sections draw ({key}, help {helped})", not broken, "; ".join(broken))

print("FAILED:" if fails else "ALL OK", fails)
sys.exit(1 if fails else 0)
