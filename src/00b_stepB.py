"""Amended Signature B: sustained step in perigee with apogee roughly unchanged (PREREG Amendment 1).
Modes:  python3 src/00b_stepB.py sigma   -> prints sigma values for the step statistic (no flags counted)
        python3 src/00b_stepB.py apply   -> applies the rule, prints flags by object type and the debris check
Local only, no network. Fill SIG_SP and SIG_SA from 'sigma' mode, date the lock in PREREG, then run 'apply'."""
import sys, json, pathlib
import numpy as np, pandas as pd

M, K, RATIO, EXCL, MAX_GAP = 3, 5, 0.2, 3.0, 3.0   # 3-set medians, 5 sigma, 20%, skip last 3 days, window gap <= 3 days
SIG_SP, SIG_SA = 0.4036, 0.4809                     # km; drift-removed step SDs locked 2026-11-07
CRITERION = 0.05                                    # pre-set: debris false-positive rate must be <= 5%, else B is dropped
HIST = pathlib.Path("data/raw/gp_history")
cand = pd.read_csv("data/frozen/candidates.csv", parse_dates=["DECAY"])[["NORAD_CAT_ID", "OBJECT_TYPE", "DECAY"]]
need = ["NORAD_CAT_ID", "EPOCH", "PERIAPSIS", "APOAPSIS"]
try:
    pilot = set(pd.read_csv("data/frozen/pilot_ids.csv").NORAD_CAT_ID)
except Exception:
    pilot = None


def objects():
    for f in sorted(HIST.glob("batch_*.json")):
        rows = json.loads(f.read_text())
        if not rows: continue
        df = pd.DataFrame(rows)[need].copy(); df["NORAD_CAT_ID"] = df.NORAD_CAT_ID.astype(int)
        if pilot is not None: df = df[df.NORAD_CAT_ID.isin(pilot)]   # pilot objects only
        if df.empty: continue
        df["EPOCH"] = pd.to_datetime(df.EPOCH)
        for c in need[2:]: df[c] = pd.to_numeric(df[c], errors="coerce")
        df = df.merge(cand, on="NORAD_CAT_ID").sort_values(["NORAD_CAT_ID", "EPOCH"])
        df["dtd"] = (df.DECAY + pd.Timedelta(hours=12) - df.EPOCH).dt.total_seconds() / 86400
        for oid, g in df.groupby("NORAD_CAT_ID"):
            g = g[g.dtd >= EXCL].dropna(subset=need[2:])
            if len(g) >= 20: yield oid, g.OBJECT_TYPE.iloc[0], g


def step_stats(g):
    s = pd.DataFrame({"e": (g.EPOCH - g.EPOCH.iloc[0]).dt.total_seconds().to_numpy() / 86400,
                      "P": g.PERIAPSIS.to_numpy(), "A": g.APOAPSIS.to_numpy(), "dtd": g.dtd.to_numpy()})
    dt = s.e.diff(); ok = (dt >= 0.25) & (dt <= 2)
    if ok.sum() < 5: return None
    rp, ra = (s.P.diff() / dt)[ok].median(), (s.A.diff() / dt)[ok].median()   # object's own median drift rates
    before = {c: s[c].rolling(M).median().shift(1) for c in "ePA"}
    after = {c: s[c][::-1].rolling(M).median()[::-1] for c in "ePA"}
    dtm = after["e"] - before["e"]
    st = pd.DataFrame({"dP": (after["P"] - before["P"]) - rp * dtm, "dA": (after["A"] - before["A"]) - ra * dtm,
                       "dtm": dtm, "dtd": s.dtd}).dropna()
    return st[(st.dtm > 0) & (st.dtm <= MAX_GAP)]


mode = sys.argv[1] if len(sys.argv) > 1 else ""
rsd = lambda x: 1.4826 * np.median(np.abs(x - np.median(x)))
if mode == "sigma":
    dp, da, n = [], [], 0
    for oid, typ, g in objects():
        st = step_stats(g)
        if st is None: continue
        st = st[st.dtd >= 14]; dp.append(st.dP); da.append(st.dA); n += 1
    dp, da = pd.concat(dp), pd.concat(da)
    print("objects", n, "| windows", len(dp))
    print("SIG_SP (perigee step, drift removed) km:", round(float(rsd(dp)), 4))
    print("SIG_SA (apogee step, drift removed) km:", round(float(rsd(da)), 4))
elif mode == "apply":
    if SIG_SP is None or SIG_SA is None: print("Fill SIG_SP and SIG_SA from sigma mode first"); raise SystemExit
    out = []
    for oid, typ, g in objects():
        st = step_stats(g)
        if st is None: out.append({"id": oid, "type": typ, "flag": False, "checked": False}); continue
        hit = (st.dP < -K * SIG_SP) & (st.dA.abs() < RATIO * st.dP.abs())
        out.append({"id": oid, "type": typ, "flag": bool(hit.any()), "checked": True})
    r = pd.DataFrame(out); r.to_csv("results/0b_stepB_flags.csv", index=False)
    t = r[r.checked].groupby("type").agg(n=("flag", "size"), flagged=("flag", "sum")); t["rate"] = (t.flagged / t.n).round(3)
    print(t); d = t.loc["DEBRIS"] if "DEBRIS" in t.index else None
    if d is not None: print("DEBRIS false-positive rate", d.rate, "criterion <=", CRITERION, "->", "PASS" if d.rate <= CRITERION else "FAIL: drop Signature B")
else:
    print("usage: sigma | apply")
