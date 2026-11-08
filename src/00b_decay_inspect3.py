import pandas as pd
d = pd.read_json("data/raw/decay_msgs.json", dtype=False)
d["NORAD_CAT_ID"] = pd.to_numeric(d.NORAD_CAT_ID, errors="coerce")
d["DECAY_EPOCH"] = pd.to_datetime(d.DECAY_EPOCH, errors="coerce")
d["MSG_EPOCH"] = pd.to_datetime(d.MSG_EPOCH, errors="coerce")
c = pd.read_csv("data/frozen/candidates.csv")
ids = set(c.NORAD_CAT_ID)
x = d[d.NORAD_CAT_ID.isin(ids)]
sat = x[x.SOURCE == "satcat"].groupby("NORAD_CAT_ID").DECAY_EPOCH.max()
dm = x[x.SOURCE == "decay_msg"].groupby("NORAD_CAT_ID").DECAY_EPOCH.max()
b = pd.concat([sat, dm], axis=1, keys=["sat", "dm"]).dropna()
gap = (b.dm - b.sat).dt.total_seconds().abs() / 86400
print("both:", len(b), "| gap > 1 day:", int((gap > 1).sum()), "| gap > 30 days:", int((gap > 30).sum()))
print(gap[gap > 1].describe().round(1).to_dict())
print(b.assign(gap_days=gap)[gap > 1].sort_values("gap_days", ascending=False).head(5))
p = x[x.SOURCE == "60day_msg"].merge(sat.rename("true").reset_index(), on="NORAD_CAT_ID")
p["lead"] = (p.true + pd.Timedelta(hours=12) - p.MSG_EPOCH).dt.total_seconds() / 86400
print("60day msgs per candidate object", p.groupby("NORAD_CAT_ID").size().describe().round(1).to_dict())
print("lead-time quantiles (days)", p.lead.quantile([0, .05, .25, .5, .75, .95, 1]).round(1).to_dict())
for H in (30, 14, 7, 3, 1):
    n = p[(p.lead >= H * 0.8) & (p.lead <= H * 1.2)].NORAD_CAT_ID.nunique()
    print("objects with a 60day msg within +/-20% of", H, "days before decay:", n)
