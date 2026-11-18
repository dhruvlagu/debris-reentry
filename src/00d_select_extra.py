"""Step 0D supplement (D7 gap). Adds 3 floor-status and 3 UNKNOWN-class objects, training block,
30 d horizon, excluding the original 25. Seed 20261117. Do not reroll after seeing the draw.
Run BEFORE any check on these ids. Output: results/0d/selection_extra.json
"""
import json, os, sys
import numpy as np
import pandas as pd

SEED, HORIZON = 20261117, 30
df = pd.read_parquet("data/frozen/modelA_train.parquet")
cand = pd.read_csv("data/frozen/candidates.csv", low_memory=False)
meta = cand[["NORAD_CAT_ID", "OBJECT_TYPE"]].drop_duplicates("NORAD_CAT_ID")
meta.columns = ["norad_id", "object_type"]
df = df.merge(meta, on="norad_id", how="left")
df = df[(df.horizon_d == HORIZON) & df.pred_days.notna() & (df.block == "train")].drop_duplicates("norad_id")
used = set(json.load(open("results/0d/selection.json"))["ids"])
df = df[~df.norad_id.isin(used)]
rng = np.random.default_rng(SEED)
picked = []
for name, mask in (("floor", df.status == "floor"),
                   ("unknown", df.object_type.astype(str).str.upper().str.contains("UNKNOWN"))):
    pool = df[mask & ~df.norad_id.isin(picked)].norad_id.to_numpy()
    print(f"{name}: pool {len(pool)}")
    if len(pool) < 3:
        sys.exit(f"{name}: need 3, have {len(pool)}")
    picked += [int(i) for i in rng.choice(pool, 3, replace=False)]
sel = df[df.norad_id.isin(picked)][["norad_id", "object_type", "status", "ecc"]]
print(sel.to_string(index=False))
os.makedirs("results/0d", exist_ok=True)
json.dump({"seed": SEED, "horizon_days": HORIZON, "quota": {"floor": 3, "unknown": 3}, "ids": picked},
          open("results/0d/selection_extra.json", "w"), indent=1)
print("Wrote results/0d/selection_extra.json")
