"""Label checks on ALL candidates (no gp_history needed, no network).
Writes results/0b_label_flags.csv (mismatch, single_source, rcs_size). Prints label-source stats, the TIP date check
(reporting only, changes no rule) and the label-noise gate per horizon (PREREG Section 4: worst-case half-width 12 h)."""
import pandas as pd, numpy as np

d = pd.read_json("data/raw/decay_msgs.json", dtype=False)
d["NORAD_CAT_ID"] = pd.to_numeric(d.NORAD_CAT_ID, errors="coerce")
def dt(x):  # mixed date-only and date-time strings: do not let one format coerce the other to NaT
    try: return pd.to_datetime(x, format="mixed", errors="coerce")
    except (ValueError, TypeError): return pd.to_datetime(x, errors="coerce")
d["DECAY_EPOCH"] = dt(d.DECAY_EPOCH); d["MSG_EPOCH"] = dt(d.MSG_EPOCH)
print("unparsed DECAY_EPOCH:", int(d.DECAY_EPOCH.isna().sum()), "| unparsed MSG_EPOCH:", int(d.MSG_EPOCH.isna().sum()))
c = pd.read_csv("data/frozen/candidates.csv")
x = d[d.NORAD_CAT_ID.isin(set(c.NORAD_CAT_ID))]
sat = x[x.SOURCE == "satcat"].groupby("NORAD_CAT_ID").DECAY_EPOCH.max()
dm = x[x.SOURCE == "decay_msg"].groupby("NORAD_CAT_ID").DECAY_EPOCH.max()
gap = (dm - sat.reindex(dm.index)).dt.total_seconds().abs() / 86400
lab = pd.DataFrame({"NORAD_CAT_ID": c.NORAD_CAT_ID})
lab["single_source"] = ~lab.NORAD_CAT_ID.isin(dm.index)
lab["mismatch"] = lab.NORAD_CAT_ID.map(gap).fillna(0) >= 1
size = x.dropna(subset=["RCS_SIZE"]).groupby("NORAD_CAT_ID").RCS_SIZE.agg(lambda s: s.mode().iloc[0])
lab["rcs_size"] = lab.NORAD_CAT_ID.map(size).fillna("UNKNOWN")
lab.to_csv("results/0b_label_flags.csv", index=False)

print("candidates", len(c), "| with decay_msg", int((~lab.single_source).sum()), "| single-source (SATCAT only)", int(lab.single_source.sum()))
print("date mismatch >= 1 day (excluded):", int(lab.mismatch.sum()), "| of those >= 2 days:", int((gap >= 2).sum()))

tip = x[x.SOURCE == "TIP_msg"].copy()
tip["lead"] = (tip.DECAY_EPOCH - tip.MSG_EPOCH).dt.total_seconds() / 86400
tip = tip[(tip.lead >= 0) & (tip.lead <= 10)]          # content-only plausibility filter
last = tip.sort_values("MSG_EPOCH").groupby("NORAD_CAT_ID").tail(1).set_index("NORAD_CAT_ID")
s0 = sat.reindex(last.index)
diff_h = (last.DECAY_EPOCH - (s0 + pd.Timedelta(hours=12))).dt.total_seconds() / 3600
print("TIP check (reporting only): objects", len(last),
      "| SATCAT date equals UTC date of last TIP decay:", round(float((last.DECAY_EPOCH.dt.normalize() == s0).mean()), 3),
      "| within +/-12 h of noon:", round(float((diff_h.abs() <= 12).mean()), 3))
print("TIP last decay minus SATCAT noon, hours, quantiles 5/25/50/75/95:", diff_h.quantile([.05, .25, .5, .75, .95]).round(1).tolist())

print("Label-noise gate (resolution 20% of horizon, tolerance half of it, date-only label half-width 12 h):")
for H in (30, 14, 7, 3, 1):
    tol = 0.5 * 0.2 * H * 24
    print(f"  {H:>2} d: tolerance {tol:5.1f} h vs 12.0 h ->", "PASS" if 12 <= tol else "FAIL (drop horizon)")
