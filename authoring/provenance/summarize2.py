import json, glob, sys
CYC, SS_FRAC, IAE_FRAC = 0.25, 0.9, 0.75
pat = sys.argv[1] if len(sys.argv) > 1 else '../evidence/reeval2_*.json'
rows = [json.load(open(f)) for f in sorted(glob.glob(pat))]
names = ["solver_a_v2","solver_a","solver_b","existing","textbook_imc","blanket_detune","textbook_db1","textbook_db2","textbook_db3","textbook_db4","textbook_db6","textbook_db8","textbook_true_db"]
tally = {n: 0 for n in names}
print("seed  SK   dn_IAE | solver_a_v2: cyc  iae/dn ss/gate (Kp,Ti,db) | solver_b: cyc iae/dn ss/gate")
for r in rows:
    sk = r['plant']['S'] * r['K_local_50']; gss = SS_FRAC * sk; gi = IAE_FRAC * r['do_nothing_iae']
    a = r['metrics']['solver_a_v2']; b = r['metrics']['solver_b']; pa = r['params']['solver_a_v2']
    print(f"{r['seed']:>3} {sk:4.1f} {r['do_nothing_iae']:6.0f} | {a['cyc']:.2f} {a['iae']/r['do_nothing_iae']:5.2f} {a['ss']/gss:5.2f} ({pa[0]:.2f},{pa[1]:.0f},{pa[3]:.2f}) | {b['cyc']:.2f} {b['iae']/r['do_nothing_iae']:5.2f} {b['ss']/gss:5.2f}")
    for n in names:
        m = r['metrics'].get(n)
        if m: tally[n] += (m['cyc'] <= CYC and m['ss'] <= gss and m['iae'] <= gi)
print(f"\npass counts /{len(rows)} (cyc<={CYC}, ss<={SS_FRAC}xSK, IAE<={IAE_FRAC}x do-nothing IAE):")
for n in names: print(f"  {n:18s} {tally[n]}")
