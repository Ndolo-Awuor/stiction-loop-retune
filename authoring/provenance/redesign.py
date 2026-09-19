"""Fast path: reuse stored fitted models, rerun only solver A's design step, re-grade. python redesign.py <seed>"""
import json, sys, numpy as np
import grading as g, solver_a as sa

def main(seed):
    r = json.load(open(f"../evidence/reeval_{seed}.json"))
    pl = dict(r['plant']); model = r['model']
    t, sp, pv, op = sa.load(f"../scratch/inst{seed}/historian.csv")
    coef = sa.static_map(sp, pv, op)
    ns = float(np.std(np.diff(pv[:600])) / np.sqrt(2)) * 0.9
    ctrl, info = sa.design(model, coef, ns)
    m = g.evaluate({k: [v] for k, v in ctrl.items()}, pl)
    r['params']['solver_a_v2'] = [ctrl['Kp'], ctrl['Ti'], 0.0, ctrl['db']]
    r['metrics']['solver_a_v2'] = {k: float(v[0]) for k, v in m.items()}
    r['do_nothing_iae'] = g.do_nothing_iae(pl)
    json.dump(r, open(f"../evidence/reeval2_{seed}.json", "w"), indent=1)
    print("done", seed)

if __name__ == "__main__":
    main(int(sys.argv[1]))
