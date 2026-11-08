import pandas as pd
d = pd.read_json("data/raw/decay_msgs.json", dtype=False)
d["NORAD_CAT_ID"] = pd.to_numeric(d.NORAD_CAT_ID, errors="coerce")
d["DECAY_EPOCH"] = pd.to_datetime(d.DECAY_EPOCH, errors="coerce")
d["MSG_EPOCH"] = pd.to_datetime(d.MSG_EPOCH, errors="coerce")
d["has_time"] = (d.DECAY_EPOCH.dt.hour + d.DECAY_EPOCH.dt.minute + d.DECAY_EPOCH.dt.second) > 0
print(d.groupby("SOURCE").agg(n=("has_time", "size"), share_time=("has_time", "mean"), objects=("NORAD_CAT_ID", "nunique")).round(3))
c = pd.read_csv("data/frozen/candidates.csv")
x = d[d.NORAD_CAT_ID.isin(set(c.NORAD_CAT_ID))]
print("candidates with each source:", {s: int(x[x.SOURCE == s].NORAD_CAT_ID.nunique()) for s in sorted(x.SOURCE.unique())})
t = x[x.SOURCE == "TIP_msg"].groupby("NORAD_CAT_ID").agg(first_msg=("MSG_EPOCH", "min"), last_dec=("DECAY_EPOCH", "max"), n=("MSG_EPOCH", "size"))
print("TIP msgs per object", t.n.describe().round(1).to_dict())
print("days from first TIP msg to last predicted decay", ((t.last_dec - t.first_msg).dt.total_seconds() / 86400).describe().round(1).to_dict())
sat = x[x.SOURCE == "satcat"].groupby("NORAD_CAT_ID").DECAY_EPOCH.max()
dm = x[x.SOURCE == "decay_msg"].groupby("NORAD_CAT_ID").DECAY_EPOCH.max()
b = pd.concat([sat, dm], axis=1, keys=["sat", "dm"]).dropna()
print("objects with both satcat and decay_msg", len(b), "same calendar date", round(float((b.dm.dt.normalize() == b.sat.dt.normalize()).mean()), 3))
print("abs hour difference", ((b.dm - b.sat).dt.total_seconds().abs() / 3600).describe().round(1).to_dict())
