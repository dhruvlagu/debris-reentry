"""Maneuver filter (PREREG Section 4). Run ONLY after the sigma lock is dated.
Reads downloaded gp_history batches (completed objects only), one file at a time. No network.
Output: results/0b_maneuver_flags.csv and results/0b_maneuver_summary.json"""
import json, pathlib
import numpy as np, pandas as pd

SIG_A, SIG_P = 0.2158, 0.2125      # km, drift-removed pilot estimates (locked in PREREG)
K, RUN, RATIO, EXCL_DAYS = 5, 3, 0.2, 3.0
HIST = pathlib.Path("data/raw/gp_history"); RES = pathlib.Path("results")
cand = pd.read_csv("data/frozen/candidates.csv", parse_dates=["DECAY"])[["NORAD_CAT_ID", "DECAY"]]
need = ["NORAD_CAT_ID", "EPOCH", "SEMIMAJOR_AXIS", "PERIAPSIS", "APOAPSIS"]
out = []

for f in sorted(HIST.glob("batch_*.json")):
    rows = json.loads(f.read_text())
    if not rows: continue
    df = pd.DataFrame(rows)
    miss = [c for c in need if c not in df.columns]
    if miss: print("MISSING COLUMNS", miss); raise SystemExit
    df = df[need].copy(); df["NORAD_CAT_ID"] = df.NORAD_CAT_ID.astype(int); df["EPOCH"] = pd.to_datetime(df.EPOCH)
    for c in need[2:]: df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.merge(cand, on="NORAD_CAT_ID").sort_values(["NORAD_CAT_ID", "EPOCH"])
    df["dtd"] = (df.DECAY + pd.Timedelta(hours=12) - df.EPOCH).dt.total_seconds() / 86400
    for oid, g in df.groupby("NORAD_CAT_ID"):
        g = g[g.dtd >= EXCL_DAYS].dropna(subset=need[2:])
        a = b = False
        if len(g) >= 2:
            prev_min = g.SEMIMAJOR_AXIS.cummin().shift(1)
            above = (g.SEMIMAJOR_AXIS - prev_min) > K * SIG_A
            a = bool((above.rolling(RUN).sum() == RUN).any())
            dt = g.EPOCH.diff().dt.total_seconds() / 86400
            dp, da = g.PERIAPSIS.diff(), g.APOAPSIS.diff()
            ok = (dt >= 0.25) & (dt <= 2) & (dp < -K * SIG_P) & (da.abs() < RATIO * dp.abs())
            b = bool(ok.any())
        out.append({"NORAD_CAT_ID": oid, "n_sets_checked": len(g), "flag_A_sma_rise": a, "flag_B_burn": b})

r = pd.DataFrame(out); RES.mkdir(exist_ok=True); r.to_csv(RES / "0b_maneuver_flags.csv", index=False)
summ = {"objects": len(r), "too_few_sets_to_check": int((r.n_sets_checked < 2).sum()),
        "flag_A": int(r.flag_A_sma_rise.sum()), "flag_B": int(r.flag_B_burn.sum()),
        "flag_either": int((r.flag_A_sma_rise | r.flag_B_burn).sum()),
        "constants": {"sigma_a": SIG_A, "sigma_p": SIG_P, "K": K, "run": RUN, "ratio": RATIO, "exclude_last_days": EXCL_DAYS}}
(RES / "0b_maneuver_summary.json").write_text(json.dumps(summ, indent=2)); print(json.dumps(summ, indent=2))
