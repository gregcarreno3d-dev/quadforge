"""Row fit: how fine the faces of a thin strip (a chamfer or a bevel) must be for a whole number of quad rows to fit in it.

The remesh grid places an integer number of quad rows across every strip between two hard edges. A strip 1.45 quad
lengths wide cannot hold 1.45 rows: the grid squeezes one row or stretches two, and the rows zigzag along the strip.
The fix is to size the faces of the strip so that its width is a whole number of them:

    rows = max(1, round(width / quad_length))        the whole number of rows the strip should get
    scale = (width / quad_length) / rows              size multiplier that makes `rows` rows exactly fill it

A multiplier above 1 (a strip 1.4 wide would need coarser faces to hold one row) is not applied: the strip keeps the
normal size and gets one row. Below 1 the strip is refined, down to ``floor`` (the engine's grid cannot follow finer
sizes than that). This is the one place that decides it, for chamfers (flat strips between two planes) and for
bevels / fillets (curved strips) alike; ``pipeline._refine_thin_bands`` calls it per strip, so a chamfer or bevel
whose width changes along the part gets a different multiplier in each zone.

Tested in ``quadforge/tests/row_fit_test.py`` (no Blender needed).
"""
import numpy as np

# Strips at least this many quad lengths wide are left at the normal size: the grid already snaps them to the nearest
# whole number of rows, and refining them tore the hole rims of the 4-hole test disc. Only strips narrower than this are
# refined so that rows fit them.
REFINE_BELOW = 1.0


def rows_for_width(width_in_quads):
    """Whole number of quad rows a strip of this width (in quad lengths) should hold (at least 1)."""
    return np.maximum(1.0, np.floor(np.asarray(width_in_quads, dtype=np.float64) + 0.5))


def row_fit_scale(width_in_quads, floor: float = 0.0):
    """Size multiplier (<= 1) that makes a whole number of rows fill a strip of this width (in quad lengths)."""
    ratio = np.asarray(width_in_quads, dtype=np.float64)
    scale = np.where(ratio < REFINE_BELOW, ratio / rows_for_width(ratio), 1.0)
    return np.clip(scale, floor, 1.0)
