import json, glob, sys
import numpy as np
CYC, SS_FRAC, RATIO = 0.25, 0.65, 2.5
pat = sys.argv[1] if len(sys.argv) > 1 else '../evidence/reeval_*.json'
rows = [json.load(open(f)) for f in sorted(glob.glob(pat))]
names = ["solver_a","solver_b","existing","textbook_imc","blanket_detune","textbook_db1","textbook_db2","textbook_db3","textbook_db4","textbook_db6","textbook_db8","textbook_true_db"]
tally = {n: 0 for n in names}; n_ok = 0; fails = []
print("seed  S    SK  | brute(IAE,db) | solver_a: cyc  iae/br  ss/gate  (Kp,Ti,db) | solver_b: cyc iae/br ss/gate (Kp,Ti,db)")
for r in rows:
    b = r['brute']
    if b is None: print(r['seed'], 'no brute'); continue
    sk = r['plant']['S'] * r['K_local_50']; gate_ss = SS_FRAC * sk; gate_iae = RATIO * b['iae']; n_ok += 1
    a, bb = r['metrics']['solver_a'], r['metrics']['solver_b']; pa, pb = r['params']['solver_a'], r['params']['solver_b']
    print(f"{r['seed']:>3} {r['plant']['S']:4.1f} {sk:4.1f} | ({b['iae']:5.0f},{b['db']:4.2f}) | {a['cyc']:.2f} {a['iae']/b['iae']:5.2f} {a['ss']/gate_ss:5.2f} ({pa[0]:.2f},{pa[1]:.0f},{pa[3]:.2f}) | {bb['cyc']:.2f} {bb['iae']/b['iae']:5.2f} {bb['ss']/gate_ss:5.2f} ({pb[0]:.2f},{pb[1]:.0f},{pb[3]:.2f})")
    for n in names:
        if n not in r['metrics']: continue
        m = r['metrics'][n]; tally[n] += (m['cyc'] <= CYC and m['ss'] <= gate_ss and m['iae'] <= gate_iae)
print(f"\npass counts /{n_ok}  (cyc<={CYC}, ss<={SS_FRAC}xSK, IAE<={RATIO}x brute optimum):")
for n in names: print(f"  {n:18s} {tally[n]}")
