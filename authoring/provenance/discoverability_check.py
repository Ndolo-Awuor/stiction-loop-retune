"""Is the sticking valve detectable from the historian alone? For OP moves of different sizes on
constant-setpoint stretches, measure how much PV follows (after the dead time). Uses no plant knowledge.
Usage: python discoverability_check.py ../../environment/data/historian.csv"""
import sys, numpy as np
a = np.genfromtxt(sys.argv[1], delimiter=",", skip_header=1)
t, sp, pv, op = a[:, 0], a[:, 1], a[:, 2], a[:, 3]
W, L = 20, 25
k = np.arange(W, len(op) - L - W)
dOP = op[k] - op[k - W]
dPV = pv[k + L + W] - pv[k + L]
ok = np.array([np.ptp(sp[i - W:i + L + W]) == 0 for i in k])
dOP, dPV = dOP[ok], dPV[ok]
bins = [0, 0.5, 1, 1.5, 2, 2.5, 3, 4, 6, 12, 100]
print("|dOP| bin   n   mean dPV/dOP (same sign)")
for lo, hi in zip(bins[:-1], bins[1:]):
    m = (np.abs(dOP) >= lo) & (np.abs(dOP) < hi)
    if m.sum() >= 30:
        print(f"{lo:4.1f}-{hi:5.1f} {m.sum():5d}   {np.mean(dPV[m] * np.sign(dOP[m])) / np.mean(np.abs(dOP[m])):.2f}")
