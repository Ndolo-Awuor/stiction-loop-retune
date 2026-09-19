import json, glob, sys
import grading as g
pat = sys.argv[1] if len(sys.argv) > 1 else '../evidence/cal_*.json'
rows = [json.load(open(f)) for f in sorted(glob.glob(pat))]
rows = [r for r in rows if r['yard']]
names = ["solver_a","solver_b","existing","textbook_imc","blanket_detune","textbook_dbnoise","textbook_db_true_stick","textbook_db1","textbook_db1.5","textbook_db2","textbook_db2.5","textbook_db3","textbook_db4","textbook_db5"]
tally = {n: 0 for n in names}
print("seed  sigma  SK  | yard trav | solver_a: cyc iae/dn ss/gate trav/gate (Kp,Ti,db) | solver_b: cyc iae/dn ss/gate trav/gate")
for r in rows:
    pl = dict(r['plant']); pl['gain_scale'] = pl['gain_scale']
    sk = pl['S'] * r['K50']; y = r['yard']
    gates = {"cyc": g.GATE_CYC, "ss": g.GATE_SS_FRAC * sk, "iae": g.GATE_IAE_FRAC * y['dn'], "trav": g.GATE_TRAV_MULT * y['trav']}
    def cell(n):
        m = r['metrics'][n]; return f"{m['cyc']:.2f} {m['iae']/y['dn']:.2f} {m['ss']/gates['ss']:.2f} {m['trav']/gates['trav']:.2f}"
    pa = r['params']['solver_a']
    print(f"{r['seed']:>3} {pl['noise_sigma']:5.2f} {sk:4.1f} | {y['trav']:6.0f} | {cell('solver_a')} ({pa[0]:.2f},{pa[1]:.0f},{pa[3]:.2f}) | {cell('solver_b')}")
    for n in names:
        m = r['metrics'].get(n)
        if m: tally[n] += (m['cyc'] <= gates['cyc'] and m['ss'] <= gates['ss'] and m['iae'] <= gates['iae'] and m['trav'] <= gates['trav'])
print(f"\npass counts /{len(rows)}:")
for n in names: print(f"  {n:24s} {tally[n]}")
