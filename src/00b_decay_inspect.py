import pandas as pd
d = pd.read_json("data/raw/decay_msgs.json", dtype=False)
d["NORAD_CAT_ID"] = pd.to_numeric(d.NORAD_CAT_ID, errors="coerce")
d["DECAY_EPOCH"] = pd.to_datetime(d.DECAY_EPOCH, errors="coerce")
d["MSG_EPOCH"] = pd.to_datetime(d.MSG_EPOCH, errors="coerce")
print("rows", len(d), "objects", d.NORAD_CAT_ID.nunique())
for col in ("MSG_TYPE", "SOURCE", "PRECEDENCE"):
    print(col, d[col].value_counts(dropna=False).head(10).to_dict())
print("null DECAY_EPOCH", int(d.DECAY_EPOCH.isna().sum()))
tod = (d.DECAY_EPOCH.dt.hour + d.DECAY_EPOCH.dt.minute + d.DECAY_EPOCH.dt.second) > 0
print("share with a time of day", round(float(tod.mean()), 3))
print("msgs per object", d.groupby("NORAD_CAT_ID").size().describe().round(1).to_dict())
print(d.groupby("MSG_TYPE").DECAY_EPOCH.agg(["min", "max", "count"]))
c = pd.read_csv("data/frozen/candidates.csv")
print("candidates with a message", int(c.NORAD_CAT_ID.isin(d.NORAD_CAT_ID).sum()), "of", len(c))
ex = d[d.NORAD_CAT_ID == d.NORAD_CAT_ID.dropna().iloc[-1]].sort_values("MSG_EPOCH")
print(ex[["NORAD_CAT_ID", "MSG_EPOCH", "DECAY_EPOCH", "SOURCE", "MSG_TYPE", "PRECEDENCE"]].to_string())
