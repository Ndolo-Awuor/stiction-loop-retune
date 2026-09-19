"""
Canonical closed-loop simulator for the sticky-valve loop (synthetic plant).

One implementation is shared by the historian generator, the verifier and the
solvers, so the data the agent sees and the way its answer is graded cannot drift apart.

Plant (continuous-time intent, discretised exactly at Ts = 1 s):
  valve position y_v  ->  static characteristic  PV_ss = gain_scale * 100*(exp(c*y_v/100)-1)/(exp(c)-1)
                      ->  + unmeasured load disturbance d (enters ahead of the lags)
                      ->  two first-order lags (tau1, tau2)  ->  transport delay  ->  PV
Valve: two-parameter stick-slip stiction (stick band S, slip jump J), in % of OP.
Sensor: PV + coloured measurement noise.

Controller law (ISA-style, Ts = 1 s, reverse acting, output limits 0-100 %):
  e      = SP - PV_meas
  e_db   = e - clip(e, -db, +db)                  # error dead-band
  P      = Kp * e_db
  I     += Kp*Ts/Ti * e_db  + (u_clamped - u_raw) # back-calculation anti-windup, Tt = Ts
  PV_f   = first-order filter of PV_meas, time constant Td/N with N = 8 (only if Td > 0)
  D      = -Kp * Td * (PV_f[k] - PV_f[k-1]) / Ts  # derivative on measurement
  u      = clip(P + I + D, 0, 100)
"""
import numpy as np

TS = 1.0
N_FILT = 8.0


def valve_map(u, c):
    return 100.0 * (np.exp(c * u / 100.0) - 1.0) / (np.exp(c) - 1.0)


def valve_inv(pv, c):
    return 100.0 / c * np.log(1.0 + (pv / 100.0) * (np.exp(c) - 1.0))


def local_gain(plant, pv_level, h=0.5):
    """Local steady-state gain dPV/dOP at a given PV level (used only by authoring/calibration)."""
    u = valve_inv(pv_level / plant["gain_scale"], plant["c"])
    return float((valve_map(u + h, plant["c"]) - valve_map(u - h, plant["c"])) / (2 * h) * plant["gain_scale"])


def coloured_noise(rng, T, sigma, rho=0.5):
    w = rng.standard_normal(T)
    x = np.zeros(T)
    for k in range(1, T):
        x[k] = rho * x[k - 1] + np.sqrt(1 - rho ** 2) * w[k]
    return sigma * x


def simulate(ctrl, sp, d, noise, plant, return_valve=False):
    """
    ctrl : dict of arrays (N,) with keys Kp, Ti, Td, db   (N controllers simulated in parallel)
    sp, d, noise : arrays (T,)
    plant : dict with tau1, tau2, delay, c, gain_scale, S, J
    Returns pv (T,N) [true PV], pvm (T,N) [measured], op (T,N)  (+ valve position if requested)
    """
    Kp = np.atleast_1d(np.asarray(ctrl["Kp"], float))
    Ti = np.atleast_1d(np.asarray(ctrl["Ti"], float))
    Td = np.atleast_1d(np.asarray(ctrl["Td"], float))
    db = np.atleast_1d(np.asarray(ctrl["db"], float))
    N = Kp.shape[0]
    T = sp.shape[0]
    c = plant["c"]
    S = plant["S"]
    J = plant["J"]
    gs = plant["gain_scale"]
    a1 = np.exp(-TS / plant["tau1"])
    a2 = np.exp(-TS / plant["tau2"])
    D = int(plant["delay"])

    sp0 = float(sp[0])
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
    pvf = np.full(N, sp0)
    use_d = Td > 0
    tf = np.where(use_d, Td / N_FILT, 1.0)
    af = np.where(use_d, TS / (tf + TS), 0.0)

    pv_h = np.zeros((T, N))
    pvm_h = np.zeros((T, N))
    op_h = np.zeros((T, N))
    yv_h = np.zeros((T, N)) if return_valve else None
    for k in range(T):
        pv = buf[bi] if D > 0 else x2
        pvm = pv + noise[k]
        e = sp[k] - pvm
        e = e - np.clip(e, -db, db)
        pvf_new = pvf + af * (pvm - pvf)
        Dterm = np.where(use_d, -Kp * Td * (pvf_new - pvf) / TS, 0.0)
        pvf = pvf_new
        u_raw = Kp * e + I + Dterm
        u = np.clip(u_raw, 0.0, 100.0)
        I = I + Kp * TS / Ti * e + (u - u_raw)

        diff = u - uref
        brk = stuck & (np.abs(diff) >= S)
        direc = np.where(brk, np.sign(diff), direc)
        stuck = np.where(brk, False, stuck)
        reversal = (~stuck) & ((u - uprev) * direc < 0)
        stuck = np.where(reversal, True, stuck)
        uref = np.where(reversal, uprev, uref)
        yv = np.where(~stuck, np.clip(u - direc * (S - J), 0.0, 100.0), yv)
        uprev = u

        v = gs * valve_map(yv, c) + d[k]
        x1 = a1 * x1 + (1 - a1) * v
        x2 = a2 * x2 + (1 - a2) * x1
        if D > 0:
            buf[bi] = x2
            bi = (bi + 1) % D
        pv_h[k] = pv
        pvm_h[k] = pvm
        op_h[k] = u
        if return_valve:
            yv_h[k] = yv
    if return_valve:
        return pv_h, pvm_h, op_h, yv_h
    return pv_h, pvm_h, op_h


def moving_avg(x, w):
    k = np.ones(w) / w
    return np.apply_along_axis(lambda col: np.convolve(col, k, mode="valid"), 0, x)
