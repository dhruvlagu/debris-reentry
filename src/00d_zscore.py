import sys
import numpy as np, pandas as pd
IDS=[40363,44325,21622,44467,40068,39395]
if len(sys.argv)>1: IDS=[int(x) for x in sys.argv[1:]]
THR_P=1.06
pq=pd.read_parquet("data/frozen/modelA_train.parquet")
t=pd.read_csv("data/frozen/tle_merged_dupfilt.csv",usecols=["NORAD_CAT_ID","EPOCH","PERIAPSIS","APOAPSIS"])
t["EPOCH"]=pd.to_datetime(t["EPOCH"])
for o in IDS:
    r=pq[(pq.norad_id==o)&(pq.horizon_d==30)]
    if r.empty: continue
    dec=pd.Timestamp(r.iloc[0].decay_time)
    g=t[(t.NORAD_CAT_ID==o)&(t.EPOCH>=dec-pd.Timedelta(days=90))&(t.EPOCH<=dec-pd.Timedelta(days=3))].sort_values("EPOCH").reset_index(drop=True)
    dt=g.EPOCH.diff().dt.total_seconds()/86400
    fall=-g.PERIAPSIS.diff(); rate=fall/dt
    hit=(dt>=0.25)&(dt<=2)&(fall>THR_P)&(g.APOAPSIS.diff().abs()<0.2*fall)
    print(f"\n{o}: {int(hit.sum())} hits")
    for i in g.index[hit]:
        nb=pd.concat([rate.iloc[max(1,i-10):i],rate.iloc[i+1:i+11]]).dropna()
        med=nb.median(); sd=1.4826*(nb-med).abs().median()+1e-6
        print(f"  {(dec-g.EPOCH[i]).total_seconds()/86400:5.1f} d before decay  dt={dt[i]:.2f} d  perigee fall {fall[i]:.2f} km  rate {rate[i]:.2f} km/d  local median {med:.2f}  z={(rate[i]-med)/sd:.1f}")
