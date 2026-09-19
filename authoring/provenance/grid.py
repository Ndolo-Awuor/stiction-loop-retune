"""Save the full (Kp, Ti, db) grid of true-plant metrics for one seed, for offline gate design."""
import sys, numpy as np
import plantsim as ps, grading as g, make_instance as mi
seed = int(sys.argv[1])
plant, *_ = mi.make(seed, None)
K = ps.local_gain(plant, 50.0)
Kps = np.geomspace(0.2, 3.0, 9) * 1.2 / K
Tis = np.geomspace(15, 300, 9)
dbs = np.array([0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0, 6.0, 7.5])
A, B, C = np.meshgrid(Kps, Tis, dbs, indexing="ij")
ctrl = {"Kp": A.ravel(), "Ti": B.ravel(), "Td": np.zeros(A.size), "db": C.ravel()}
m = g.evaluate(ctrl, plant)
np.savez(f"../evidence/grid_{seed}.npz", Kp=A.ravel(), Ti=B.ravel(), db=C.ravel(), dn=g.do_nothing_iae(plant),
         sk=g.stick_band_pv(plant), sigma=plant["noise_sigma"], **m)
print("done", seed)
