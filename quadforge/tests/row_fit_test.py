"""Pure-numpy test of quadforge.core.row_fit (run: python3 quadforge/tests/row_fit_test.py)."""
import importlib.util
import os

import numpy as np

here = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("row_fit", os.path.join(here, "..", "core", "row_fit.py"))
row_fit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(row_fit)

fit, rows = row_fit.row_fit_scale, row_fit.rows_for_width

# strips that already hold a whole number of rows are left alone
for w in (1.0, 2.0, 3.0, 4.0):
    assert abs(float(fit(w)) - 1.0) < 1e-12, w
# 1.45 quads: one row at the normal size (coarsening is never asked for)
assert float(rows(1.45)) == 1.0 and float(fit(1.45)) == 1.0
# 1.6 quads would round up to 2 rows, but strips at least REFINE_BELOW (1.0) wide keep the normal size
assert float(rows(1.6)) == 2.0 and float(fit(1.6)) == 1.0
assert float(fit(2.6)) == 1.0
# just below the limit: one row as fine as the strip is wide
assert abs(float(fit(0.9)) - 0.9) < 1e-12
# narrow strips: one row, as fine as the strip is wide, but not finer than the floor
assert abs(float(fit(0.5)) - 0.5) < 1e-12
assert float(fit(0.2, floor=0.6)) == 0.6
# vectorised, never above 1, never below the floor
w = np.linspace(0.1, 6.0, 500)
s = fit(w, floor=0.35)
assert s.max() <= 1.0 and s.min() >= 0.35
print("row_fit_test OK")
