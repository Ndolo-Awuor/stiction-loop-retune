"""
Held-out grading scenarios and metrics, shared by the verifier and the calibration harness.

Every scenario is simulated on the HIDDEN true plant (or a perturbed variant of it) with noise
seeds the agent never saw. Metrics per (scenario, seed):
  p2p : peak-to-peak of a 15 s moving average of the true PV over the last 1500 s of a 3000 s run
        (sustained oscillation / limit cycle at constant setpoint)
  iae : integral of |SP - PV| over t = 300..1800 s (load-disturbance rejection; disturbance at t = 300)
  ss  : mean |SP - PV| over the last 1000 s (steady-state offset)
"""
import numpy as np
import plantsim as ps

T = 3000
SEEDS = (11, 12, 13, 14, 15)
CYC_THRESH = 1.5  # %PV peak-to-peak of the 15 s average counted as a sustained oscillation

# name, SP, load-disturbance step, plant perturbation
SCENARIOS = [
    ("lo_sp40_d+4", 40.0, +4.0, {}),
    ("mid_sp50_d-4", 50.0, -4.0, {}),
    ("hi_sp62_d+4", 62.0, +4.0, {}),
    ("rob_gain+25_delay+3", 55.0, +4.0, {"gain_mult": 1.25, "delay_add": 3}),
    ("rob_gain-20", 45.0, -4.0, {"gain_mult": 0.80}),
]


def perturbed(plant, pert):
    p = dict(plant)
    p["gain_scale"] = plant["gain_scale"] * pert.get("gain_mult", 1.0)
    p["delay"] = plant["delay"] + pert.get("delay_add", 0)
    return p


def scenario_inputs(sp_level, d_step, sigma, seed):
    sp = np.full(T, sp_level)
    d = np.zeros(T)
    d[300:] = d_step
    noise = ps.coloured_noise(np.random.default_rng(seed), T, sigma)
    return sp, d, noise


def evaluate(ctrl, plant, seeds=SEEDS):
    """ctrl: dict of arrays (N,). Returns arrays (N,):
       cyc : fraction of (scenario, seed) runs with a sustained oscillation (p2p > CYC_THRESH)
       p2p : worst peak-to-peak over runs (diagnostic)
       iae : worst-over-scenarios of the seed-averaged disturbance IAE
       ss  : worst-over-scenarios of the seed-averaged steady-state offset
       trav: worst-over-scenarios of the seed-averaged controller-output travel (sum |dOP|, t >= 300 s)"""
    Kp = np.atleast_1d(np.asarray(ctrl["Kp"], float))
    N = Kp.shape[0]
    cyc = np.zeros(N)
    worst_p2p = np.zeros(N)
    worst_iae = np.zeros(N)
    worst_ss = np.zeros(N)
    worst_tr = np.zeros(N)
    runs = len(SCENARIOS) * len(seeds)
    for _, lvl, ds, pert in SCENARIOS:
        pl = perturbed(plant, pert)
        iae_acc = np.zeros(N)
        ss_acc = np.zeros(N)
        tr_acc = np.zeros(N)
        for sd in seeds:
            sp, d, noise = scenario_inputs(lvl, ds, plant["noise_sigma"], sd)
            pv, _, op = ps.simulate(ctrl, sp, d, noise, pl)
            ma = ps.moving_avg(pv[-1515:], 15)
            p2p = ma.max(0) - ma.min(0)
            cyc += (p2p > CYC_THRESH) / runs
            worst_p2p = np.maximum(worst_p2p, p2p)
            ss_acc += np.abs(sp[-1000:, None] - pv[-1000:]).mean(0) / len(seeds)
            iae_acc += np.abs(sp[300:1800, None] - pv[300:1800]).sum(0) * ps.TS / len(seeds)
            tr_acc += np.abs(np.diff(op[300:], axis=0)).sum(0) / len(seeds)
        worst_iae = np.maximum(worst_iae, iae_acc)
        worst_ss = np.maximum(worst_ss, ss_acc)
        worst_tr = np.maximum(worst_tr, tr_acc)
    return {"cyc": cyc, "p2p": worst_p2p, "iae": worst_iae, "ss": worst_ss, "trav": worst_tr}


def passes(m, gates):
    return (m["cyc"] <= gates["cyc"]) & (m["iae"] <= gates["iae"]) & (m["ss"] <= gates["ss"]) & (m["trav"] <= gates["trav"])


def stick_band_pv(plant):
    """Stick band expressed in PV units at mid-range: S x local process gain at PV = 50."""
    return plant["S"] * ps.local_gain(plant, 50.0)


GATE_CYC = 0.25         # max fraction of held-out runs allowed to show a sustained oscillation
GATE_SS_FRAC = 0.9      # steady-state offset allowed, as a fraction of the stick band in PV units
GATE_IAE_FRAC = 0.75    # disturbance IAE allowed, as a fraction of the uncontrolled ("do nothing") IAE
GATE_TRAV_MULT = 3.0    # controller-output travel allowed, as a multiple of the least travel any good tuning needs


def do_nothing_iae(plant):
    """IAE of a controller that effectively never moves the valve: the physical no-control baseline."""
    m = evaluate({"Kp": [1e-4], "Ti": [2000.0], "Td": [0.0], "db": [0.0]}, plant)
    return float(m["iae"][0])


def yardstick(plant):
    """Independent yardstick on the TRUE plant: the least controller-output travel among tunings that
    are clearly good (no oscillation, small offset, strong disturbance rejection). Sets the travel gate only."""
    sk = stick_band_pv(plant)
    dn = do_nothing_iae(plant)
    K = ps.local_gain(plant, 50.0)
    Kps = np.geomspace(0.2, 3.0, 9) * 1.2 / K
    Tis = np.geomspace(15, 300, 9)
    dbs = np.array([0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0, 6.0, 7.5])
    A, B, C = np.meshgrid(Kps, Tis, dbs, indexing="ij")
    ctrl = {"Kp": A.ravel(), "Ti": B.ravel(), "Td": np.zeros(A.size), "db": C.ravel()}
    m = evaluate(ctrl, plant)
    ok = (m["cyc"] <= 0.2) & (m["ss"] <= GATE_SS_FRAC * sk) & (m["iae"] <= 0.6 * dn)
    if not ok.any():
        return None
    i = int(np.argmin(np.where(ok, m["trav"], np.inf)))
    return {"Kp": float(ctrl["Kp"][i]), "Ti": float(ctrl["Ti"][i]), "db": float(ctrl["db"][i]),
            "trav": float(m["trav"][i]), "iae": float(m["iae"][i]), "n_ok": int(ok.sum()), "dn": dn}


def make_gates(plant, yard):
    return {"cyc": GATE_CYC, "ss": GATE_SS_FRAC * stick_band_pv(plant), "iae": GATE_IAE_FRAC * yard["dn"],
            "trav": GATE_TRAV_MULT * yard["trav"]}
