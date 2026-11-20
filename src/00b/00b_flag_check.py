import pandas as pd
f = pd.read_csv("results/0b_maneuver_flags.csv")
c = pd.read_csv("data/frozen/candidates.csv")[["NORAD_CAT_ID", "OBJECT_NAME", "OBJECT_TYPE", "DECAY"]]
m = f.merge(c, on="NORAD_CAT_ID")
m["either"] = m.flag_A_sma_rise | m.flag_B_burn
print(m.groupby("OBJECT_TYPE").agg(n=("either", "size"), A=("flag_A_sma_rise", "sum"), B=("flag_B_burn", "sum"), either=("either", "sum")))
print(m[m.either & (m.OBJECT_TYPE == "DEBRIS")][["NORAD_CAT_ID", "OBJECT_NAME", "DECAY", "flag_A_sma_rise", "flag_B_burn"]].to_string(index=False))
