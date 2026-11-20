"""Publication-lag and element-conversion check on the 200 pilot objects (local, no network).
Answers two questions the TLE zip bundles raise:
 1. How long after EPOCH is a set published (CREATION_DATE - EPOCH)? Needed if the bundles carry no creation time.
 2. Does semi-major axis / perigee / apogee recomputed from MEAN_MOTION and ECCENTRICITY match the gp fields we already used?
Field names MEAN_MOTION, ECCENTRICITY are from memory: the script stops and prints the columns if any is missing."""
import json, pathlib
import numpy as np, pandas as pd

HIST = pathlib.Path("data/raw/gp_history")
cand = pd.read_csv("data/frozen/candidates.csv", parse_dates=["DECAY"])[["NORAD_CAT_ID", "OBJECT_TYPE", "DECAY"]]
need = ["NORAD_CAT_ID", "EPOCH", "CREATION_DATE", "MEAN_MOTION", "ECCENTRICITY", "SEMIMAJOR_AXIS", "PERIAPSIS", "APOAPSIS"]
MU, RE = 398600.4418, 6378.135
parts = []
for f in sorted(HIST.glob("batch_*.json")):
    rows = json.loads(f.read_text())
    if not rows: continue
    df = pd.DataFrame(rows)
    miss = [c for c in need if c not in df.columns]
    if miss: print("MISSING COLUMNS", miss, "| have", list(df.columns)); raise SystemExit
    df = df[need].copy(); df["NORAD_CAT_ID"] = df.NORAD_CAT_ID.astype(int)
    for k in ("EPOCH", "CREATION_DATE"): df[k] = pd.to_datetime(df[k])
    for k in need[3:]: df[k] = pd.to_numeric(df[k], errors="coerce")
    df["lag_h"] = (df.CREATION_DATE - df.EPOCH).dt.total_seconds() / 3600
    n = df.MEAN_MOTION * 2 * np.pi / 86400
    a = (MU / n ** 2) ** (1 / 3)
    df["da_sma"] = a - df.SEMIMAJOR_AXIS
    df["da_peri"] = a * (1 - df.ECCENTRICITY) - RE - df.PERIAPSIS
    df["da_apo"] = a * (1 + df.ECCENTRICITY) - RE - df.APOAPSIS
    df = df.merge(cand, on="NORAD_CAT_ID")
    df["dtd"] = (df.DECAY + pd.Timedelta(hours=12) - df.EPOCH).dt.total_seconds() / 86400
    parts.append(df[["OBJECT_TYPE", "dtd", "lag_h", "da_sma", "da_peri", "da_apo"]])
h = pd.concat(parts, ignore_index=True)
q = [.5, .9, .99, .999]
print("element sets", len(h))
print("PUBLICATION LAG, hours (CREATION_DATE - EPOCH):")
print("  all: quantiles 50/90/99/99.9%", h.lag_h.quantile(q).round(2).tolist(), "| max", round(float(h.lag_h.max()), 1),
      "| share < 0:", round(float((h.lag_h < 0).mean()), 4), "| share > 24 h:", round(float((h.lag_h > 24).mean()), 4), "| share > 72 h:", round(float((h.lag_h > 72).mean()), 4))
print("  by class, 99th percentile:", h.groupby("OBJECT_TYPE").lag_h.quantile(.99).round(1).to_dict())
b = pd.cut(h.dtd, [-1e9, 3, 14, 1e9], labels=["last 3 d", "3-14 d", ">14 d"])
print("  by days to decay, 99th percentile:", h.groupby(b, observed=True).lag_h.quantile(.99).round(1).to_dict())
print("RECOMPUTED minus GP FIELD, km (median / 99th percentile of absolute difference):")
for k in ("da_sma", "da_peri", "da_apo"):
    print(" ", k, round(float(h[k].median()), 4), "/", round(float(h[k].abs().quantile(.99)), 4))
