import json, os, sys
import numpy as np
import pandas as pd

SEED = 20261116
N_TOTAL = 25
HORIZON = 30
SRC = "data/frozen/modelA_train.parquet"
CAND = "data/frozen/candidates.csv"
OUT = "results/0d/selection.json"

df = pd.read_parquet(SRC)
cand = pd.read_csv(CAND, low_memory=False)
low = {c.lower(): c for c in cand.columns}

def find(*names):
    for n in names:
        if n in low:
            return low[n]
    sys.exit(f"None of {names} in candidates.csv.\nAvailable: {list(cand.columns)}")

c_id = find("norad_cat_id", "norad_id", "norad")
c_type = find("object_type", "type")
c_intl = find("intldes", "intl_des", "cospar_id")

meta = cand[[c_id, c_type, c_intl]].drop_duplicates(c_id)
meta.columns = ["norad_id", "object_type", "intldes"]
meta["norad_id"] = pd.to_numeric(meta["norad_id"], errors="coerce")
df["norad_id"] = pd.to_numeric(df["norad_id"], errors="coerce")
df = df.merge(meta, on="norad_id", how="left")
print("No candidates.csv match:", int(df["object_type"].isna().sum()), "rows")

print("\nblock values:", df["block"].value_counts().to_dict())
print("status values:", df["status"].value_counts().to_dict())
print("horizon_d values:", df["horizon_d"].value_counts().to_dict())

df = df[(df["horizon_d"] == HORIZON) & df["pred_days"].notna()]
df = df[df["block"].astype(str).str.lower().str.startswith("train")]
df = df.drop_duplicates("norad_id").reset_index(drop=True)
print(f"\nPool: {len(df)} objects at {HORIZON} d, train block, with a prediction")
if len(df) < N_TOTAL:
    sys.exit("Pool too small. Check the block/status values printed above.")

ISS = lambda d: d["intldes"].astype(str).str.startswith("1998-067")
QUOTA = [
    ("iss", ISS, 3),
    ("rocket", lambda d: d["object_type"].astype(str).str.upper().str.contains("ROCKET"), 3),
    ("eccentric", lambda d: d["ecc"] > 0.01, 5),
    ("debris", lambda d: d["object_type"].astype(str).str.upper().str.contains("DEBRIS"), 5),
]

rng = np.random.default_rng(SEED)
picked = []
for name, fn, n in QUOTA:
    pool = df[fn(df) & ~df["norad_id"].isin(picked)]["norad_id"].to_numpy()
    if len(pool) < n:
        sys.exit(f"Stratum {name}: only {len(pool)} available, need {n}")
    picked += [int(i) for i in rng.choice(pool, n, replace=False)]

rest = df[~df["norad_id"].isin(picked)]["norad_id"].to_numpy()
picked += [int(i) for i in rng.choice(rest, N_TOTAL - len(picked), replace=False)]

sel = df[df["norad_id"].isin(picked)]
print("\nSelected", len(sel))
print("eccentric:", int((sel["ecc"] > 0.01).sum()))
print("ISS:", int(ISS(sel).sum()))
print(sel["object_type"].value_counts().to_string())
print("status:", sel["status"].value_counts().to_dict())

os.makedirs(os.path.dirname(OUT), exist_ok=True)
json.dump({"seed": SEED, "horizon_days": HORIZON, "source": SRC,
           "quota": {n: k for n, _, k in QUOTA}, "ids": picked},
          open(OUT, "w"), indent=1)
print(f"\nWrote {OUT} ({len(picked)} ids)")
