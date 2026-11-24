#!/usr/bin/env python3
"""qGlacier (qTimeDelay.f90) as written, with Lemon Creek's five glaciers' areas, against one reservoir: the per-glacier storages with one k
sum to it to rounding, whatever the split; with a k per glacier (as glacStor_k by length would be) they do not."""
import numpy as np
rng = np.random.default_rng(1)
melt = np.maximum(rng.normal(2e-8, 2e-8, 24 * 365), 0)
dt = 3600.0
area = np.array([7.64279007e3, 4.20353454e4, 7.77271750e6, 6.26708785e5, 1.41391616e5])
def q_glacier(melt, frac, k):
    fut = np.zeros(len(k)); out = np.zeros(len(melt))
    for i, m in enumerate(melt):
        f = frac(i) if callable(frac) else frac
        q = fut + m * f - m * f * np.exp(-dt / k)
        fut = q * np.exp(-dt / k); out[i] = q.sum()
    return out
one = q_glacier(melt, np.ones(1), np.full(1, 54e3))
five = q_glacier(melt, area / area.sum(), np.full(5, 54e3))
moving = q_glacier(melt, lambda i: np.roll(area, i // 2000) / area.sum(), np.full(5, 54e3))
own = q_glacier(melt, area / area.sum(), 54e3 * np.array([.18, .28, 1, .36, .09]))
for n, x in (("five glaciers, one k", five), ("five, areas changing in time, one k", moving), ("five, k by length", own)):
    print(f"{n}: largest difference from one reservoir {np.abs(x - one).max() / one.mean():.1e} of the mean")
