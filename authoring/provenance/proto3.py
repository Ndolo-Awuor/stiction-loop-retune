import numpy as np, proto_sim as ps
from proto2 import make

def run(Kp, Ti, db, S, J, T=3000, seeds=(1,2)):
    scen = [("nom45",45,+4,{}),("hi65",65,-4,{}),("rob55",55,+4,dict(gain_scale=1.25,delay=10))]
    p2p_w = np.zeros_like(Kp); iae_w = np.zeros_like(Kp); ss_w = np.zeros_like(Kp)
    for nm,lvl,ds,ov in scen:
        iae_s = np.zeros_like(Kp)
        for sd in seeds:
            _, sp, d, plant, noise = make(nm,lvl,ds,ov,sd,T)
            pv,_ = ps.simulate(Kp,Ti,sp,d,plant,noise,S=S,J=J,db=db)
            ma = ps.moving_avg(pv[-1515:],15)
            p2p_w = np.maximum(p2p_w, ma.max(0)-ma.min(0))
            ss_w = np.maximum(ss_w, np.abs(sp[-1000:,None]-pv[-1000:]).mean(0))
            iae_s += np.abs(sp[300:1800,None]-pv[300:1800]).sum(0)*ps.TS/len(seeds)
        iae_w = np.maximum(iae_w, iae_s)
    return p2p_w, iae_w, ss_w

if __name__ == "__main__":
    S=2.0; J=S/3
    Kps=np.geomspace(0.2,3.0,10); Tis=np.geomspace(15,400,10); dbs=np.array([0,0.5,1.0,1.5,2.0,3.0,4.0])
    A,B,C = np.meshgrid(Kps,Tis,dbs,indexing="ij")
    p2p,iae,ss = run(A.ravel(),B.ravel(),C.ravel(),S,J)
    p2p=p2p.reshape(A.shape); iae=iae.reshape(A.shape); ss=ss.reshape(A.shape)
    np.savez("proto3.npz",Kps=Kps,Tis=Tis,dbs=dbs,p2p=p2p,iae=iae,ss=ss)
    for L,Bd,E in [(1.5,2000,3.0),(1.5,2500,3.0),(1.5,3000,3.0)]:
        ok=(p2p<=L)&(iae<=Bd)&(ss<=E)
        print(f"gate p2p<={L}, IAE<={Bd}, ssErr<={E}: pass cells by db:", {float(d):int(ok[:,:,i].sum()) for i,d in enumerate(dbs)}, "of", A.shape[0]*A.shape[1], "per db")
    named={"existing(1.6,20,db0)":(1.6,20.,0.),"textbookIMC(1.4,51,db0)":(1.4,51.,0.),"blanket(0.2,200,db0)":(0.2,200.,0.),
           "textbook+db1":(1.4,51.,1.0),"textbook+db2":(1.4,51.,2.0),"textbook+db3":(1.4,51.,3.0),"moderate+db2":(0.9,90.,2.0)}
    for k,(kp,ti,db) in named.items():
        m=run(np.array([kp]),np.array([ti]),np.array([db]),S,J)
        print(f"  {k:26s} p2p={m[0][0]:5.2f} IAE={m[1][0]:6.0f} ssErr={m[2][0]:5.2f}")
