"""Re-evaluate stored candidates with the fraction-of-runs gate. python reeval.py <seed> [evdir]"""
import json, sys, numpy as np
import grading as g, solver_b as sb

def main(seed, evdir):
    r = json.load(open(f"{evdir}/calib_{seed}.json"))
    pl = dict(r['plant'])
    kp_old, ti_old = r['params']['existing'][0], r['params']['existing'][1]
    cb = sb.solve(f"../scratch/inst{seed}/historian.csv", kp_old, ti_old)
    params = dict(r['params'])
    params['solver_b'] = [cb['Kp'], cb['Ti'], 0.0, cb['db']]
    names = list(params); arr = np.array([params[n] for n in names])
    m = g.evaluate({"Kp": arr[:,0], "Ti": arr[:,1], "Td": arr[:,2], "db": arr[:,3]}, pl)
    out = {"seed": seed, "plant": pl, "K_local_50": r['K_local_50'], "model": r['model'], "params": params,
           "metrics": {n: {k: float(m[k][i]) for k in m} for i, n in enumerate(names)},
           "brute": None, "do_nothing_iae": g.do_nothing_iae(pl)}
    out["metrics"]["solver_a_v2"] = out["metrics"]["solver_a"]
    out["params"]["solver_a_v2"] = out["params"]["solver_a"]
    json.dump(out, open(f"{evdir}/reeval2_{seed}.json", "w"), indent=1)
    print("done", seed)

if __name__ == "__main__":
    main(int(sys.argv[1]), sys.argv[2] if len(sys.argv) > 2 else "../evidence")
