import sys, numpy as np
import proto_sim as ps

def make(name, sp_lvl, d_step, over, seed, T):
    plant = dict(tau1=45.0, tau2=12.0, delay=7, gain_scale=1.0, c=1.6); plant.update(over)
    sp = np.full(T, float(sp_lvl)); d = np.zeros(T); d[300:] = d_step
    noise = 0.10*np.random.default_rng(seed).standard_normal(T)
    return name, sp, d, plant, noise

def run(Kp, Ti, S, J, T=3000, seeds=(1,2)):
    scen = [("nom45",45,+4,{}),("hi65",65,-4,{}),("rob55",55,+4,dict(gain_scale=1.25,delay=10))]
    p2p_w = np.zeros_like(Kp); iae_w = np.zeros_like(Kp)
    for nm,lvl,ds,ov in scen:
        iae_s = np.zeros_like(Kp)
        for sd in seeds:
            _, sp, d, plant, noise = make(nm,lvl,ds,ov,sd,T)
            pv,_ = ps.simulate(Kp,Ti,sp,d,plant,noise,S=S,J=J)
            ma = ps.moving_avg(pv[-1515:],15)
            p2p_w = np.maximum(p2p_w, ma.max(0)-ma.min(0))
            iae_s += np.abs(sp[300:1800,None]-pv[300:1800]).sum(0)*ps.TS/len(seeds)
        iae_w = np.maximum(iae_w, iae_s)
    return p2p_w, iae_w

if __name__ == "__main__":
    S = float(sys.argv[1]); J = S/3
    Kps = np.geomspace(0.1, 4.0, 24); Tis = np.geomspace(8.0, 600.0, 24)
    KK,TT = np.meshgrid(Kps,Tis,indexing="ij")
    p2p,iae = run(KK.ravel(),TT.ravel(),S,J); p2p=p2p.reshape(KK.shape); iae=iae.reshape(KK.shape)
    np.savez(f"proto2_S{S}.npz",Kps=Kps,Tis=Tis,p2p=p2p,iae=iae)
    named = {"existing(1.6,20)":(1.6,20.),"textbookIMC(1.4,51)":(1.4,51.),"blanket(0.2,200)":(0.2,200.),"moderate(0.9,90)":(0.9,90.)}
    print(f"=== S={S} J={J:.2f} ===")
    for k,(kp,ti) in named.items():
        m = run(np.array([kp]),np.array([ti]),S,J); print(f"  {k:22s} p2p={m[0][0]:5.2f} IAE={m[1][0]:6.0f}")
    for L in (1.0,1.5):
        for B in (2000,2500,3000):
            ok=(p2p<=L)&(iae<=B); print(f"  p2p<={L}, IAE<={B}: {ok.sum():3d}/{ok.size}")
