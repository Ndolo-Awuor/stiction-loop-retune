"""One instance per process:  python calibrate.py <seed>  ->  ../evidence/cal_<seed>.json
Generates the instance, runs reference solver A (fit + design) and independent solver B, grades every
candidate on the hidden true plant with the held-out scenarios, and computes the travel yardstick."""
import json, os, sys, numpy as np
import plantsim as ps, grading as g, make_instance as mi, solver_a as sa, solver_b as sb

def main(seed):
    plant, sp, pvm, op = mi.make(seed, None)
    scratch = f"../scratch/inst{seed}"; os.makedirs(scratch, exist_ok=True)
    hist = f"{scratch}/historian.csv"
    with open(hist, "w") as f:
        f.write("time_s,SP,PV,OP\n")
        for k in range(len(sp)):
            f.write(f"{k},{sp[k]:.2f},{pvm[k]:.3f},{op[k]:.3f}\n")
    ctrl, model, info = sa.solve(hist)
    ex = plant['existing']
    cb = sb.solve(hist, ex['Kp'], ex['Ti'])
    K = ps.local_gain(plant, 50.0)
    tau = plant['tau1'] + plant['tau2'] / 2; th = plant['delay'] + plant['tau2'] / 2
    imc = (tau / (K * 2 * th), tau)
    sig = plant['noise_sigma']
    cand = {
        "solver_a": (ctrl['Kp'], ctrl['Ti'], 0.0, ctrl['db']),
        "solver_b": (cb['Kp'], cb['Ti'], 0.0, cb['db']),
        "existing": (ex['Kp'], ex['Ti'], 0.0, 0.0),
        "textbook_imc": (imc[0], imc[1], 0.0, 0.0),
        "blanket_detune": (0.2, 200.0, 0.0, 0.0),
        "textbook_dbnoise": (imc[0], imc[1], 0.0, 3.0 * sig),
        "textbook_db_true_stick": (imc[0], imc[1], 0.0, 0.45 * plant['S'] * K),
    }
    for d in (1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0):
        cand[f"textbook_db{d:g}"] = (imc[0], imc[1], 0.0, d)
    names = list(cand); arr = np.array([cand[n] for n in names])
    m = g.evaluate({"Kp": arr[:, 0], "Ti": arr[:, 1], "Td": arr[:, 2], "db": arr[:, 3]}, plant)
    yard = g.yardstick(plant)
    out = {"seed": seed, "plant": {k: v for k, v in plant.items() if k != 'existing'}, "K50": K, "model": model,
           "design_info": info, "params": {n: list(map(float, cand[n])) for n in names},
           "metrics": {n: {k: float(m[k][i]) for k in m} for i, n in enumerate(names)}, "yard": yard}
    json.dump(out, open(f"../evidence/cal_{seed}.json", "w"), indent=1)
    print("done", seed)

if __name__ == "__main__":
    main(int(sys.argv[1]))
