"""Estimate element-set noise (sigma) for the maneuver filter, from the 200 pilot objects.
Feature values only: prints sigmas, never counts of flagged objects. Local, no Space-Track call.
Field names SEMIMAJOR_AXIS, PERIAPSIS, APOAPSIS are from memory of the gp class: the script stops if any is missing."""
import json, pathlib
import numpy as np, pandas as pd

HIST = pathlib.Path("data/raw/gp_history")
ids = pd.read_csv("data/frozen/pilot_ids.csv", parse_dates=["DECAY"])[["NORAD_CAT_ID", "DECAY"]]
need = ["NORAD_CAT_ID", "EPOCH", "SEMIMAJOR_AXIS", "PERIAPSIS", "APOAPSIS"]
parts = []
for f in sorted(HIST.glob("batch_*.json")):  # one file at a time, 5 columns only
    rows = json.loads(f.read_text())
    if not rows: continue
    df = pd.DataFrame(rows)
    miss = [c for c in need if c not in df.columns]
    if miss: print("MISSING COLUMNS", miss, "| have", list(df.columns)); raise SystemExit
    parts.append(df[need])
h = pd.concat(parts, ignore_index=True)
h["NORAD_CAT_ID"] = h.NORAD_CAT_ID.astype(int)
h["EPOCH"] = pd.to_datetime(h.EPOCH)
for c in need[2:]: h[c] = pd.to_numeric(h[c], errors="coerce")
h = h.merge(ids, on="NORAD_CAT_ID").sort_values(["NORAD_CAT_ID", "EPOCH"])
h["days_to_decay"] = (h.DECAY + pd.Timedelta(hours=12) - h.EPOCH).dt.total_seconds() / 86400
g = h.groupby("NORAD_CAT_ID")
for c in need[2:]: h["d_" + c] = g[c].diff()
h["dt"] = g.EPOCH.diff().dt.total_seconds() / 86400
d_cols = ["d_" + c for c in need[2:]]
s = h[(h.days_to_decay >= 14) & (h.dt >= 0.25) & (h.dt <= 2)].dropna(subset=d_cols)
rsd = lambda x: 1.4826 * np.median(np.abs(x - np.median(x)))
print("pairs", len(s), "| objects", s.NORAD_CAT_ID.nunique(), "| pairs: consecutive element sets 0.25 to 2 days apart, 14+ days before decay")
print("NAIVE (includes real decay drift and differences between objects; superseded):")
for c in need[2:]:
    x = s["d_" + c]
    print(" ", c, "| median diff km", round(float(np.median(x)), 4), "| robust SD km", round(float(rsd(x)), 4))
# DRIFT-REMOVED: subtract each object's own median decay rate x dt, then pool. Objects need 20+ pairs.
s = s[s.groupby("NORAD_CAT_ID").NORAD_CAT_ID.transform("size") >= 20].copy()
print("DRIFT-REMOVED (use this one): pairs", len(s), "| objects", s.NORAD_CAT_ID.nunique())
for c in need[2:]:
    rate = (s["d_" + c] / s.dt).groupby(s.NORAD_CAT_ID).transform("median")
    r = s["d_" + c] - rate * s.dt
    print(" ", c, "| robust SD km", round(float(rsd(r)), 4))
