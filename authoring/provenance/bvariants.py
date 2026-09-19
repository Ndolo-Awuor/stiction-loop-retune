import json, sys, numpy as np
import grading as g, solver_b as sb
seed = int(sys.argv[1])
r = json.load(open(f"../evidence/cal_{seed}.json")); pl = dict(r['plant'])
kp_old, ti_old = r['params']['existing'][0], r['params']['existing'][1]
sp, pv, op = sb.load(f"../scratch/inst{seed}/historian.csv")
p2ps = [np.ptp(np.convolve(pv[b-900:b], np.ones(15)/15, "valid")) for a, b in sb.plateaus(sp)]
sk = float(np.median(p2ps)) / 1.46
d2 = pv[2:] - 2*pv[1:-1] + pv[:-2]; sig = float(np.sqrt(np.var(d2)/2.5))
V = {"B0": (0.6*kp_old, 2.0*ti_old, max(0.5*sk, 2.5*sig)),
     "B1": (0.5*kp_old, 2.5*ti_old, max(0.4*sk, 3.0*sig)),
     "B2": (0.5*kp_old, 2.5*ti_old, max(0.4*sk, 3.5*sig)),
     "B3": (0.4*kp_old, 2.5*ti_old, max(0.4*sk, 3.0*sig)),
     "B4": (0.5*kp_old, 3.0*ti_old, 3.0*sig + 0.25*sk)}
names = list(V); arr = np.array([V[n] for n in names])
m = g.evaluate({"Kp": arr[:,0], "Ti": arr[:,1], "Td": np.zeros(len(names)), "db": arr[:,2]}, pl)
json.dump({"seed": seed, "params": {n: list(map(float, V[n])) for n in names},
           "metrics": {n: {k: float(m[k][i]) for k in m} for i, n in enumerate(names)}}, open(f"../evidence/bvar_{seed}.json", "w"))
print("done", seed)
