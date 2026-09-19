"""
Seeded generator: draws a hidden plant and produces a historian log recorded under the
EXISTING (poorly performing) PI controller. The hidden plant parameters are ground-truth
inputs to the verifier only.

Usage: python make_instance.py <seed> <outdir>
"""
import csv
import json
import sys
import numpy as np
import plantsim as ps

HIST_T = 21600  # 6 h at 1 s


def draw_plant(seed):
    r = np.random.default_rng(1000 + seed)
    S = float(r.uniform(1.5, 6.0))
    gs = float(r.uniform(0.9, 1.8))
    plant = {
        "tau1": float(r.uniform(38, 58)),
        "tau2": float(r.uniform(9, 18)),
        "delay": int(r.integers(5, 10)),
        "c": float(r.uniform(1.3, 1.9)),
        "gain_scale": gs,
        "S": S,
        "J": float(S * r.uniform(0.25, 0.45)),
        "noise_sigma": float(r.uniform(0.3, 1.8)),
    }
    k50 = ps.local_gain(plant, 50.0)
    plant["existing"] = {"Kp": float(r.uniform(1.2, 2.0) / (k50 / 1.2)), "Ti": float(r.uniform(15, 30)), "Td": 0.0, "db": 0.0}
    return plant


def historian_profiles(seed):
    r = np.random.default_rng(5000 + seed)
    # operator setpoint schedule: plateaus of 25-45 min at varying levels
    levels = []
    t = 0
    sp = np.zeros(HIST_T)
    cur = 50.0
    while t < HIST_T:
        dur = int(r.integers(1500, 2700))
        sp[t:t + dur] = cur
        t += dur
        nxt = float(np.clip(cur + r.choice([-1, 1]) * r.uniform(8, 22), 32, 68))
        cur = round(nxt, 1)
    # unmeasured load disturbance: a few steps plus slow drift
    d = np.zeros(HIST_T)
    t = int(r.integers(600, 1500))
    lvl = 0.0
    while t < HIST_T:
        lvl += r.choice([-1, 1]) * r.uniform(1.0, 2.5)
        lvl = float(np.clip(lvl, -4, 4))
        d[t:] = lvl
        t += int(r.integers(1500, 3300))
    drift = np.cumsum(r.standard_normal(HIST_T)) * 0.004
    d = d + drift - drift.mean()
    return sp, d


def make(seed, outdir):
    plant = draw_plant(seed)
    sp, d = historian_profiles(seed)
    noise = ps.coloured_noise(np.random.default_rng(9000 + seed), HIST_T, plant["noise_sigma"])
    ctrl = {k: [v] for k, v in plant["existing"].items()}
    pv, pvm, op = ps.simulate(ctrl, sp, d, noise, plant)
    return plant, sp, pvm[:, 0], op[:, 0]


if __name__ == "__main__":
    seed = int(sys.argv[1])
    outdir = sys.argv[2]
    plant, sp, pvm, op = make(seed, outdir)
    import os
    os.makedirs(outdir, exist_ok=True)
    with open(os.path.join(outdir, "historian.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["time_s", "SP", "PV", "OP"])
        for k in range(HIST_T):
            w.writerow([k, f"{sp[k]:.2f}", f"{pvm[k]:.3f}", f"{op[k]:.3f}"])
    with open(os.path.join(outdir, "hidden_plant.json"), "w") as f:
        json.dump(plant, f, indent=2)
    print("wrote", outdir, "S=%.2f J=%.2f" % (plant["S"], plant["J"]))
