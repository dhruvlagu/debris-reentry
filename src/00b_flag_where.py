import json, pathlib
import pandas as pd
K, RATIO, SIG_P, EXCL = 5, 0.2, 0.2125, 3.0
HIST = pathlib.Path("data/raw/gp_history")
fl = pd.read_csv("results/0b_maneuver_flags.csv")
want = set(fl[fl.flag_B_burn].NORAD_CAT_ID)
cand = pd.read_csv("data/frozen/candidates.csv", parse_dates=["DECAY"])[["NORAD_CAT_ID", "OBJECT_TYPE", "DECAY"]]
need = ["NORAD_CAT_ID", "EPOCH", "PERIAPSIS", "APOAPSIS"]
out = []
for f in sorted(HIST.glob("batch_*.json")):
    rows = json.loads(f.read_text())
    if not rows: continue
    df = pd.DataFrame(rows)[need].copy(); df["NORAD_CAT_ID"] = df.NORAD_CAT_ID.astype(int)
    df = df[df.NORAD_CAT_ID.isin(want)]
    if df.empty: continue
    df["EPOCH"] = pd.to_datetime(df.EPOCH)
    for c in need[2:]: df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.merge(cand, on="NORAD_CAT_ID").sort_values(["NORAD_CAT_ID", "EPOCH"])
    df["dtd"] = (df.DECAY + pd.Timedelta(hours=12) - df.EPOCH).dt.total_seconds() / 86400
    for oid, g in df.groupby("NORAD_CAT_ID"):
        g = g[g.dtd >= EXCL].dropna(subset=need[2:]).copy()
        g["dt"] = g.EPOCH.diff().dt.total_seconds() / 86400
        g["dp"], g["da"] = g.PERIAPSIS.diff(), g.APOAPSIS.diff()
        hit = g[(g.dt >= 0.25) & (g.dt <= 2) & (g.dp < -K * SIG_P) & (g.da.abs() < RATIO * g.dp.abs())]
        out.append({"id": oid, "type": g.OBJECT_TYPE.iloc[0], "pairs_flagged": len(hit), "pairs_total": len(g),
                    "dtd_first": round(hit.dtd.max(), 1), "dtd_last": round(hit.dtd.min(), 1),
                    "median_dp_km": round(hit.dp.median(), 2), "median_da_km": round(hit.da.median(), 2),
                    "apo_minus_peri_km": round((g.APOAPSIS - g.PERIAPSIS).median(), 1)})
print(pd.DataFrame(out).sort_values("dtd_last").to_string(index=False))
