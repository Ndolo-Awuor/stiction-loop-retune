"""
Reference solver A (route: identification -> simulation-based design).

Works only from historian.csv (time_s, SP, PV, OP) and the documented controller law:
  1. static map  : mean OP vs mean PV on long constant-SP plateaus -> quadratic fit -> local gain
  2. dynamics +  : fit two lags, delay, stiction (S, J) by simulation error. OP is the measured
     stiction     input, so this is an output-error fit that avoids closed-loop bias. Windows start at
                  setpoint changes; the load-disturbance level at each window start is inferred from
                  the initial steady state.
  3. design      : search (Kp, Ti, db) on the fitted model, robustly over stick-band uncertainty and
                  gain/delay variants; keep no sustained oscillation, minimise disturbance IAE.
Writes controller.json {Kp, Ti, Td, db}.
"""
import csv
import json
import sys
import numpy as np

TS = 1.0
WIN = 1500


def load(path):
    t, sp, pv, op = [], [], [], []
    with open(path) as f:
        r = csv.DictReader(f)
        for row in r:
            t.append(float(row["time_s"]))
            sp.append(float(row["SP"]))
            pv.append(float(row["PV"]))
            op.append(float(row["OP"]))
    return np.array(t), np.array(sp), np.array(pv), np.array(op)


def plateaus(sp, min_len=1200):
    idx = np.where(np.diff(sp) != 0)[0] + 1
    bounds = np.concatenate([[0], idx, [len(sp)]])
    return [(a, b) for a, b in zip(bounds[:-1], bounds[1:]) if b - a >= min_len]


def static_map(sp, pv, op):
    """Quadratic through plateau means, extended linearly outside the observed OP range so it
    stays monotone (a raw quadratic can turn over and wreck any design done on it)."""
    pts = []
    for a, b in plateaus(sp):
        s = slice(b - 800, b)
        pts.append((op[s].mean(), pv[s].mean()))
    pts = np.array(pts)
    lo, hi = pts[:, 0].min() - 2.0, pts[:, 0].max() + 2.0
    q = np.polyfit(pts[:, 0], pts[:, 1], 2)
    us = np.linspace(lo, hi, 200)
    if np.polyval(np.polyder(q), us).min() < 0.05:
        lin = np.polyfit(pts[:, 0], pts[:, 1], 1)
        q = np.array([0.0, lin[0], lin[1]])
    return np.concatenate([q, [lo, hi]])


def fmap(coef, u):
    a, b, c, lo, hi = coef
    uc = np.clip(u, lo, hi)
    core = a * uc ** 2 + b * uc + c
    slo = max(2 * a * lo + b, 0.05)
    shi = max(2 * a * hi + b, 0.05)
    return core + np.where(u < lo, slo * (u - lo), 0.0) + np.where(u > hi, shi * (u - hi), 0.0)


# ---------------------------------------------------------------- open-loop fit
def sim_open(params, op_w, pv0, yv0, coef):
    """
    params: (5, P)  rows tau1, tau2, delay, S, Jfrac ;  op_w: (T, W) ; pv0, yv0: (W,)
    returns pv model (T, P, W)
    """
    tau1, tau2, dly, S, jf = params
    P = tau1.shape[0]
    T, W = op_w.shape
    a1 = np.exp(-TS / tau1)[:, None]
    a2 = np.exp(-TS / tau2)[:, None]
    D = np.round(dly).astype(int)[:, None]
    S = S[:, None]
    J = (jf * params[3])[:, None]
    d0 = pv0 - fmap(coef, yv0)  # (W,)
    x1 = np.tile(pv0, (P, 1))
    x2 = x1.copy()
    yv = np.tile(yv0, (P, 1))
    uref = yv.copy()
    stuck = np.ones((P, W), dtype=bool)
    direc = np.zeros((P, W))
    uprev = yv.copy()
    hist = np.zeros((T, P, W))
    out = np.zeros((T, P, W))
    pidx = np.arange(P)[:, None]
    widx = np.arange(W)[None, :]
    for k in range(T):
        idx = np.maximum(k - D, 0)
        out[k] = np.where(k - D >= 0, hist[idx, pidx, widx], pv0[None, :])
        u = np.broadcast_to(op_w[k][None, :], (P, W))
        diff = u - uref
        brk = stuck & (np.abs(diff) >= S)
        direc = np.where(brk, np.sign(diff), direc)
        stuck = np.where(brk, False, stuck)
        rev = (~stuck) & ((u - uprev) * direc < 0)
        stuck = np.where(rev, True, stuck)
        uref = np.where(rev, uprev, uref)
        yv = np.where(~stuck, np.clip(u - direc * (S - J), 0.0, 100.0), yv)
        uprev = u
        v = fmap(coef, yv) + d0[None, :]
        x1 = a1 * x1 + (1 - a1) * v
        x2 = a2 * x2 + (1 - a2) * x1
        hist[k] = x2
    return out



def differential_evolution(cost, bounds, popsize=14, maxiter=45, seed=0):
    """Minimal vectorised DE (rand/1/bin). cost(x) takes x of shape (D, P) and returns (P,)."""
    rng = np.random.default_rng(seed)
    lo = np.array([b[0] for b in bounds], float)
    hi = np.array([b[1] for b in bounds], float)
    D = len(bounds)
    P = popsize * D
    pop = lo + (hi - lo) * rng.random((P, D))
    fit = cost(pop.T)
    for _ in range(maxiter):
        idx = np.array([rng.choice(P, 3, replace=False) for _ in range(P)])
        F = rng.uniform(0.5, 1.0, (P, 1))
        mutant = np.clip(pop[idx[:, 0]] + F * (pop[idx[:, 1]] - pop[idx[:, 2]]), lo, hi)
        cross = rng.random((P, D)) < 0.8
        cross[np.arange(P), rng.integers(0, D, P)] = True
        trial = np.where(cross, mutant, pop)
        tf = cost(trial.T)
        better = tf < fit
        pop[better] = trial[better]
        fit[better] = tf[better]
    i = int(np.argmin(fit))
    return pop[i], float(fit[i])

def fit_dynamics(sp, pv, op, coef, seed=0, hp=600):
    """Output-error fit over the whole record on HIGH-PASSED residuals: slow unmeasured load
    disturbances are removed, stick-slip and lag dynamics remain."""
    op_w = op[:, None]
    pv0 = np.array([pv[:30].mean()])
    yv0 = np.array([op[0]])

    def cost(x):
        params = np.asarray(x)
        if params.ndim == 1:
            params = params[:, None]
        pm = sim_open(params, op_w, pv0, yv0, coef)[:, :, 0]
        r = pv[:, None] - pm
        c = np.cumsum(r, axis=0)
        r_hp = r[hp:] - (c[hp:] - c[:-hp]) / hp
        return np.mean(r_hp ** 2, axis=0)

    bounds = [(15, 100), (3, 30), (2, 16), (0.3, 6.0), (0.0, 0.8)]
    x, fun = differential_evolution(cost, bounds, popsize=10, maxiter=30, seed=seed)
    tau1, tau2, dly, S, jf = x
    return {"tau1": float(tau1), "tau2": float(tau2), "delay": int(round(dly)),
            "S": float(S), "J": float(jf * S), "fit_mse": fun}


# ---------------------------------------------------------------- closed-loop design on fitted model
def sim_closed(ctrl, sp, d, noise, model, coef):
    Kp = np.asarray(ctrl["Kp"], float)
    Ti = np.asarray(ctrl["Ti"], float)
    db = np.asarray(ctrl["db"], float)
    N = Kp.shape[0]
    T = sp.shape[0]
    a1 = np.exp(-TS / model["tau1"])
    a2 = np.exp(-TS / model["tau2"])
    D = int(model["delay"])
    S, J = model["S"], model["J"]
    gs = model.get("gain_mult", 1.0)
    sp0 = float(sp[0])
    # invert the fitted static map at sp0 (monotone on 0..100)
    us = np.linspace(0, 100, 2001)
    u0 = float(np.interp(sp0, gs * fmap(coef, us), us))
    x1 = np.full(N, sp0)
    x2 = np.full(N, sp0)
    buf = np.full((max(D, 1), N), sp0)
    bi = 0
    I = np.full(N, u0)
    yv = np.full(N, u0)
    uref = np.full(N, u0)
    stuck = np.ones(N, dtype=bool)
    direc = np.zeros(N)
    uprev = np.full(N, u0)
    pvs = np.zeros((T, N))
    for k in range(T):
        pv = buf[bi]
        e = sp[k] - (pv + noise[k])
        e = e - np.clip(e, -db, db)
        u_raw = Kp * e + I
        u = np.clip(u_raw, 0.0, 100.0)
        I = I + Kp * TS / Ti * e + (u - u_raw)
        diff = u - uref
        brk = stuck & (np.abs(diff) >= S)
        direc = np.where(brk, np.sign(diff), direc)
        stuck = np.where(brk, False, stuck)
        rev = (~stuck) & ((u - uprev) * direc < 0)
        stuck = np.where(rev, True, stuck)
        uref = np.where(rev, uprev, uref)
        yv = np.where(~stuck, np.clip(u - direc * (S - J), 0.0, 100.0), yv)
        uprev = u
        v = gs * fmap(coef, yv) + d[k]
        x1 = a1 * x1 + (1 - a1) * v
        x2 = a2 * x2 + (1 - a2) * x1
        buf[bi] = x2
        bi = (bi + 1) % D if D > 0 else 0
        pvs[k] = pv
    return pvs


def design(model, coef, noise_sigma, pv_levels=(40.0, 50.0, 62.0)):
    """Judge every candidate on the fitted model the way the verifier will: several noise seeds and
    plant variants, fraction of runs with a sustained oscillation, seed-averaged IAE and offset."""
    us_ = np.linspace(0, 100, 2001)
    u50 = float(np.interp(50.0, fmap(coef, us_), us_))
    k_mid = float((fmap(coef, u50 + 0.5) - fmap(coef, u50 - 0.5)) / 1.0)
    Kps = np.geomspace(0.25, 2.4, 10) / k_mid          # loop gain Kp*K kept in a conventional range
    Tis = np.geomspace(30, 300, 10)
    sk_hat = model["S"] * k_mid                          # stick band in PV units
    dbs = sk_hat * np.array([0.15, 0.22, 0.3, 0.4, 0.5, 0.6, 0.75, 0.9, 1.1, 1.4])
    A, B, C = np.meshgrid(Kps, Tis, dbs, indexing="ij")
    ctrl = {"Kp": A.ravel(), "Ti": B.ravel(), "db": C.ravel()}
    T = 2400
    variants = []
    for gm, dl in ((1.0, 0), (1.25, 3), (0.8, 0), (1.0, 6)):
        m = dict(model)
        m["gain_mult"] = gm
        m["delay"] = model["delay"] + dl
        variants.append(m)
    n_cfg = A.size
    cyc = np.zeros(n_cfg)
    iae = np.zeros(n_cfg)
    ss = np.zeros(n_cfg)
    runs = 0
    k15 = np.ones(15) / 15
    for vi, m in enumerate(variants):
        for lvl, ds in zip(pv_levels, (+4.0, -4.0, +4.0)):
            for sd in (0, 1):
                rng = np.random.default_rng(100 * vi + 10 * sd + int(lvl))
                sp = np.full(T, lvl)
                d = np.zeros(T)
                d[300:] = ds
                noise = noise_sigma * rng.standard_normal(T)
                pv = sim_closed(ctrl, sp, d, noise, m, coef)
                ma = np.apply_along_axis(lambda c: np.convolve(c, k15, "valid"), 0, pv[-1215:])
                cyc += ((ma.max(0) - ma.min(0)) > 1.5)
                ss += np.abs(sp[-1000:, None] - pv[-1000:]).mean(0)
                iae += np.abs(sp[300:1800, None] - pv[300:1800]).sum(0)
                runs += 1
    cyc /= runs
    ss /= runs
    iae /= runs
    ok = (cyc <= 0.1) & (ss <= 0.8 * sk_hat)
    feas = ok.reshape(A.shape).astype(float)
    pad = np.pad(feas, 1, mode="edge")
    nb = sum(pad[i:i + A.shape[0], j:j + A.shape[1], k:k + A.shape[2]]
             for i in range(3) for j in range(3) for k in range(3)) / 27.0
    nb = nb.ravel()
    core = ok & (nb >= 0.7)
    if not core.any():
        core = ok
    if not core.any():
        core = cyc <= cyc.min() + 0.1
    i = int(np.argmin(np.where(core, iae, np.inf)))
    return {"Kp": float(ctrl["Kp"][i]), "Ti": float(ctrl["Ti"][i]), "Td": 0.0, "db": float(ctrl["db"][i])}, {
        "cyc": float(cyc[i]), "iae": float(iae[i]), "n_feasible": int(ok.sum()), "n_core": int(core.sum())}


def solve(hist_path):
    t, sp, pv, op = load(hist_path)
    coef = static_map(sp, pv, op)
    model = fit_dynamics(sp, pv, op, coef)
    noise_sigma = float(np.std(np.diff(pv[:600])) / np.sqrt(2)) * 0.9
    ctrl, info = design(model, coef, noise_sigma)
    return ctrl, model, info


if __name__ == "__main__":
    ctrl, model, info = solve(sys.argv[1])
    print("fitted model:", {k: round(v, 3) if isinstance(v, float) else v for k, v in model.items()})
    print("design info:", info)
    with open(sys.argv[2], "w") as f:
        json.dump(ctrl, f, indent=2)
    print("controller:", ctrl)
