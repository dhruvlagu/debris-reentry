import sys
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
IDS=[40363,44325,21622,44467,40068,39395]
if len(sys.argv)>1: IDS=[int(x) for x in sys.argv[1:]]
THR_P=1.06
pq=pd.read_parquet("data/frozen/modelA_train.parquet")
t=pd.read_csv("data/frozen/tle_merged_dupfilt.csv",usecols=["NORAD_CAT_ID","EPOCH","PERIAPSIS","APOAPSIS"])
t["EPOCH"]=pd.to_datetime(t["EPOCH"])
fig,axs=plt.subplots(2,3,figsize=(16,8))
for ax,o in zip(axs.ravel(),IDS):
    r=pq[(pq.norad_id==o)&(pq.horizon_d==30)]
    if r.empty: continue
    dec=pd.Timestamp(r.iloc[0].decay_time)
    g=t[(t.NORAD_CAT_ID==o)&(t.EPOCH>=dec-pd.Timedelta(days=90))&(t.EPOCH<=dec-pd.Timedelta(days=3))].sort_values("EPOCH").reset_index(drop=True)
    dt=g.EPOCH.diff().dt.total_seconds()/86400; x=(g.EPOCH-dec).dt.total_seconds()/86400
    dP=g.PERIAPSIS.diff(); dA=g.APOAPSIS.diff()
    ax.plot(x,dP,".",ms=3,label="perigee change per record (km)"); ax.plot(x,dA,".",ms=3,label="apogee change per record (km)")
    fall=-dP; hit=(dt>=0.25)&(dt<=2)&(fall>THR_P)&(dA.abs()<0.2*fall)
    rec=0
    for i in g.index[hit]:
        nxt=g.PERIAPSIS.iloc[i+1:i+4]
        if len(nxt) and nxt.max()-g.PERIAPSIS.iloc[i]>=0.5*fall[i]: rec+=1
        ax.axvline(x[i],color="r",lw=0.5)
    lo,hi=np.nanpercentile(pd.concat([dP,dA]),[1,99]); ax.set_ylim(min(lo,-8),max(hi,3))
    print(f"{o}: hits {int(hit.sum())}, recovered within 3 records {rec} (noise-like), persistent {int(hit.sum())-rec}")
    ax.set_title(str(o),fontsize=9); ax.legend(fontsize=6)
fig.savefig("results/0d/checks/flagged6_rates.png",dpi=110,bbox_inches="tight")
