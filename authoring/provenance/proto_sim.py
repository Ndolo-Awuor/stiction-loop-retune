"""
Feasibility prototype (authoring only). Question: for a sticky-valve loop with
a gain-varying process, does a PI tuning window exist that (a) has no
sustained limit cycle, (b) rejects load disturbances well, and (c) excludes
the lazy strategies (existing tuning, textbook IMC rule, blanket detune)?

Vectorised over a grid of (Kp, Ti) so the whole tuning plane is simulated at once.
"""
import numpy as np

TS = 1.0  # s


def valve_map(u, c=1.6):
    """Static valve/process characteristic: valve % -> steady PV %, equal-percentage-like."""
    return 100.0 * (np.exp(c * u / 100.0) - 1.0) / (np.exp(c) - 1.0)


def valve_inv(pv, c=1.6):
    return 100.0 / c * np.log(1.0 + (pv / 100.0) * (np.exp(c) - 1.0))


def simulate(Kp, Ti, sp_profile, d_profile, plant, noise, S=3.0, J=1.0, u_min=0.0, u_max=100.0, db=0.0):
    """
    Kp, Ti: arrays (N,)   sp_profile, d_profile, noise: arrays (T,)
    plant: dict(tau1, tau2, delay, gain_scale, c)
    Returns PV history (T, N) and OP history (T, N).
    """
    N = Kp.shape[0]
    T = sp_profile.shape[0]
    c = plant["c"]
    a1 = np.exp(-TS / plant["tau1"])
    a2 = np.exp(-TS / plant["tau2"])
    D = int(plant["delay"])
    gs = plant["gain_scale"]

    sp0 = sp_profile[0]
    u0 = valve_inv(sp0 / gs, c)
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

    pv_hist = np.zeros((T, N))
    op_hist = np.zeros((T, N))
    for k in range(T):
        pv = buf[bi] if D > 0 else x2
        pvm = pv + noise[k]
        e = sp_profile[k] - pvm
        e = e - np.clip(e, -db, db)
        P = Kp * e
        u_raw = P + I
        u = np.clip(u_raw, u_min, u_max)
        I = I + Kp * TS / Ti * e + (u - u_raw)  # integrate + back-calculation anti-windup

        # stiction (two-parameter stick-slip)
        diff = u - uref
        brk = stuck & (np.abs(diff) >= S)
        direc = np.where(brk, np.sign(diff), direc)
        stuck = np.where(brk, False, stuck)
        moving = ~stuck
        reversal = moving & ((u - uprev) * direc < 0)
        stuck = np.where(reversal, True, stuck)
        uref = np.where(reversal, uprev, uref)
        moving = ~stuck
        yv = np.where(moving, u - direc * (S - J), yv)
        yv = np.clip(yv, u_min, u_max)
        uprev = u

        # process: static map (scaled) + disturbance, two lags, transport delay
        v = gs * valve_map(yv, c) + d_profile[k]
        x1 = a1 * x1 + (1 - a1) * v
        x2 = a2 * x2 + (1 - a2) * x1
        if D > 0:
            buf[bi] = x2
            bi = (bi + 1) % D
        pv_hist[k] = pv
        op_hist[k] = u
    return pv_hist, op_hist


def moving_avg(x, w):
    k = np.ones(w) / w
    return np.apply_along_axis(lambda col: np.convolve(col, k, mode="valid"), 0, x)


def scenario(name, sp_lvl, d_step, plant_over, T=1500, seed=1):
    plant = dict(tau1=45.0, tau2=12.0, delay=7, gain_scale=1.0, c=1.6)
    plant.update(plant_over)
    sp = np.full(T, float(sp_lvl))
    d = np.zeros(T)
    d[300:] = d_step
    rng = np.random.default_rng(seed)
    noise = 0.10 * rng.standard_normal(T)
    return name, sp, d, plant, noise


SCENARIOS = [
    scenario("nominal_sp45_d+4", 45, +4.0, {}),
    scenario("highgain_sp65_d-4", 65, -4.0, {}),
    scenario("robust_g+25_dl+3_sp55_d+4", 55, +4.0, dict(gain_scale=1.25, delay=10)),
]


def metrics(Kp, Ti):
    worst_p2p = np.zeros_like(Kp)
    worst_iae = np.zeros_like(Kp)
    for name, sp, d, plant, noise in SCENARIOS:
        pv, _ = simulate(Kp, Ti, sp, d, plant, noise)
        # limit cycle: p2p of 15 s moving average over the last 500 s
        ma = moving_avg(pv[-515:], 15)
        p2p = ma.max(axis=0) - ma.min(axis=0)
        iae = np.abs(sp[300:, None] - pv[300:]).sum(axis=0) * TS
        worst_p2p = np.maximum(worst_p2p, p2p)
        worst_iae = np.maximum(worst_iae, iae)
    return worst_p2p, worst_iae


if __name__ == "__main__":
    Kps = np.geomspace(0.05, 4.0, 36)
    Tis = np.geomspace(5.0, 600.0, 36)
    KK, TT = np.meshgrid(Kps, Tis, indexing="ij")
    p2p, iae = metrics(KK.ravel(), TT.ravel())
    p2p = p2p.reshape(KK.shape)
    iae = iae.reshape(KK.shape)
    np.savez("proto_grid.npz", Kps=Kps, Tis=Tis, p2p=p2p, iae=iae)

    print("worst-case p2p (%PV) quantiles:", np.round(np.quantile(p2p, [0, .25, .5, .75, 1]), 2))
    print("worst-case IAE (%.s) quantiles:", np.round(np.quantile(iae, [0, .25, .5, .75, 1]), 0))

    named = {
        "existing (Kp=1.6, Ti=20)": (1.6, 20.0),
        "textbook IMC (Kp=1.4, Ti=51)": (1.4, 51.0),
        "blanket detune (Kp=0.2, Ti=200)": (0.2, 200.0),
        "P-heavy (Kp=0.8, Ti=300)": (0.8, 300.0),
        "moderate (Kp=0.9, Ti=90)": (0.9, 90.0),
    }
    print()
    for label, (kp, ti) in named.items():
        m = metrics(np.array([kp]), np.array([ti]))
        print(f"{label:38s} p2p={m[0][0]:6.2f}  IAE={m[1][0]:8.0f}")

    for L in (1.0, 1.5, 2.0):
        for B in (2500, 3500, 5000):
            ok = (p2p <= L) & (iae <= B)
            print(f"pass region  p2p<={L}, IAE<={B}: {ok.sum():4d} of {ok.size} grid cells")
