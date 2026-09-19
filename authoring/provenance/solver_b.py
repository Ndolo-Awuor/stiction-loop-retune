"""
Independent solver B (route: simulation-free field heuristic, no model fit, no simulation).

  1. stick band in PV units from the limit-cycle amplitude on constant-SP plateaus:
        S*K  ~=  PV_peak_to_peak(15 s average) / 1.46        (empirical amplitude ratio)
  2. sensor noise sigma from second differences of PV (var(d2) ~ 2.5 sigma^2 for mildly coloured noise)
  3. dead-band  db = max(0.4 * S*K,  3 * sigma)               (above the noise band and near the stick band)
  4. tuning     detune the existing loop: Kp = 0.5 * Kp_old, Ti = 2.5 * Ti_old
                (the field response to a cycling loop: cut the gain, lengthen the reset time)
Variant "B1" of the offline variant study (authoring/evidence/bvar_*.json).
"""
import json, sys
import numpy as np


def load(path):
    a = np.genfromtxt(path, delimiter=",", skip_header=1)
    return a[:, 1], a[:, 2], a[:, 3]


def plateaus(sp, min_len=1200):
    idx = np.where(np.diff(sp) != 0)[0] + 1
    b = np.concatenate([[0], idx, [len(sp)]])
    return [(x, y) for x, y in zip(b[:-1], b[1:]) if y - x >= min_len]


def solve(path, kp_old, ti_old):
    sp, pv, op = load(path)
    p2ps = []
    for a, b in plateaus(sp):
        seg = pv[b - 900:b]
        ma = np.convolve(seg, np.ones(15) / 15, "valid")
        p2ps.append(np.ptp(ma))
    sk = float(np.median(p2ps)) / 1.46
    d2 = pv[2:] - 2.0 * pv[1:-1] + pv[:-2]
    sigma = float(np.sqrt(np.var(d2) / 2.5))
    return {"Kp": 0.5 * kp_old, "Ti": 2.5 * ti_old, "Td": 0.0, "db": max(0.4 * sk, 3.0 * sigma)}

if __name__ == "__main__":
    c = solve(sys.argv[1], float(sys.argv[2]), float(sys.argv[3]))
    json.dump(c, open(sys.argv[4], "w"), indent=2)
    print(c)
