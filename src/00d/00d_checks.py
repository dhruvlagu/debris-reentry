#!/usr/bin/env python3
"""Step 0D walking skeleton, checks 1 to 6. TRAINING DATA ONLY. Deviation D7:
Model A + fixed +/-20% interval only (no conformal, no physics model).

Usage (repo root):
    python3 src/00d_checks.py [--scored FILE [FILE ...]]
--scored = the same gate-rows files you gave 00c_build_modelA.py. Optional; enables the
full builder rerun in check 2. Without it, check 2 reruns this script only.

Independent re-implementation of the Model A fit: if it disagrees with the frozen parquet,
either the builder or this file is wrong. That disagreement is the point of check 1.
"""
import argparse, hashlib, json, os, subprocess, sys, tempfile, time
import numpy as np
import pandas as pd
from scipy.stats import theilslopes

PQ = "data/frozen/modelA_train.parquet"
TLE = "data/frozen/tle_merged_dupfilt.csv"
CAND = "data/frozen/candidates.csv"
SEL = "results/00d/selection.json"
BUILDER = "src/00c_build_modelA.py"
P = dict(window_d=10.0, lag_h=24.0, min_sets=3, decay_alt_km=120.0, ecc_cut=0.01,
         re_km=6378.137, min_days=0.5, cap_days=365.0)
THR_A, THR_P = 1.08, 1.06  # PREREG Sec 4 maneuver thresholds (5 x sigma)
REF = pd.Timestamp("2000-01-01")
SEED = 20261116
N_FULL = {30: 3332, 14: 3468}  # full-scale scored counts, PREREG Sec 7


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def days(s):
    return ((s - REF).dt.total_seconds() / 86400).values


def refit(g, T0):
    """Independent Model A. g = one object's TLE rows sorted by EPOCH."""
    t = days(g.EPOCH)
    t0 = (T0 - REF).total_seconds() / 86400
    lag = P["lag_h"] / 24
    m = (t <= t0 - lag) & (t > t0 - P["window_d"])
    r = dict(n_window=int(m.sum()), slope=np.nan, pred=np.nan, status="insufficient",
             ecc=np.nan, age=np.nan, margin_h=np.nan)
    if m.sum() < P["min_sets"]:
        return r
    w = g[m]
    tt = t[m]
    sma, pe, ap = (w[c].values.astype(float) for c in ("SEMIMAJOR_AXIS", "PERIAPSIS", "APOAPSIS"))
    ecc = (ap - pe) / (2 * sma)
    el = ecc[-1]
    y = sma - P["re_km"] if el <= P["ecc_cut"] else pe
    t_last = tt[-1]
    r["margin_h"] = (t0 - (t_last + lag)) * 24  # must be >= 0 (point-in-time)
    sl, ic, _, _ = theilslopes(y, tt - t_last)
    age = t0 - t_last
    r.update(slope=sl, ecc=el, age=age)
    if sl >= 0:
        r.update(pred=P["cap_days"], status="cap")
    else:
        rem = (ic - P["decay_alt_km"]) / (-sl) - age
        if rem < P["min_days"]:
            r.update(pred=P["min_days"], status="floor")
        elif rem > P["cap_days"]:
            r.update(pred=P["cap_days"], status="cap")
        else:
            r.update(pred=rem, status="ok")
    r["ic"], r["t_last"] = ic, t_last
    return r


def alt_series(g):
    ecc = ((g.APOAPSIS - g.PERIAPSIS) / (2 * g.SEMIMAJOR_AXIS)).values
    return np.where(ecc <= P["ecc_cut"], g.SEMIMAJOR_AXIS - P["re_km"], g.PERIAPSIS)


def maneuver_flags(g, dec):
    """Signature A (SMA rise) and B (burn), PREREG Sec 4. 90 d window, last 3 d ignored."""
    g = g[(g.EPOCH >= dec - pd.Timedelta(days=90)) & (g.EPOCH <= dec - pd.Timedelta(days=3))]
    if len(g) < 4:
        return False, False
    sma, pe, ap, t = (g.SEMIMAJOR_AXIS.values, g.PERIAPSIS.values, g.APOAPSIS.values, days(g.EPOCH))
    prevmin = np.r_[np.inf, np.minimum.accumulate(sma)[:-1]]
    above = (sma - prevmin) > THR_A
    a, run = False, 0
    for x in above:
        run = run + 1 if x else 0
        if run >= 3:
            a = True
    dt, fall, dap = np.diff(t), -np.diff(pe), np.abs(np.diff(ap))
    b = bool(((dt >= 0.25) & (dt <= 2) & (fall > THR_P) & (dap < 0.2 * fall)).any())
    return a, b


def run_core(outdir, ids, pq, tle, cand):
    """Deterministic part: refit + compare + date checks + flags. Writes CSVs only (hashable)."""
    os.makedirs(outdir, exist_ok=True)
    G = {o: g for o, g in tle.groupby("NORAD_CAT_ID")}
    rows, fails = [], []
    for o in ids:
        for h in (30, 14):
            pr = pq[(pq.norad_id == o) & (pq.horizon_d == h)]
            if pr.empty:
                rows.append(dict(norad_id=o, h=h, note="not in parquet (insufficient records)"))
                continue
            pr = pr.iloc[0]
            g = G.get(o)
            r = refit(g, pd.Timestamp(pr.issue_time)) if g is not None else dict(status="no_tle", n_window=0)
            row = dict(norad_id=o, h=h, pq_status=pr.status, my_status=r["status"],
                       pq_nwin=int(pr.n_window), my_nwin=r["n_window"],
                       pq_pred=pr.pred_days, my_pred=r.get("pred", np.nan),
                       pq_slope=pr.slope_km_d, my_slope=r.get("slope", np.nan),
                       margin_h=r.get("margin_h", np.nan), true_days=pr.true_days)
            ok = (row["pq_status"] == row["my_status"] and row["pq_nwin"] == row["my_nwin"]
                  and np.isclose(row["pq_pred"], row["my_pred"], rtol=1e-9, equal_nan=True)
                  and np.isclose(row["pq_slope"], row["my_slope"], rtol=1e-9, equal_nan=True))
            row["match"] = bool(ok)
            row["pit_ok"] = bool(np.isnan(row["margin_h"]) or row["margin_h"] >= -1e-9)
            lo, hi = 0.8 * row["pq_pred"], 1.2 * row["pq_pred"]
            row["int_covers"] = bool(lo <= row["true_days"] <= hi)
            rows.append(row)
    df = pd.DataFrame(rows)
    df.to_csv(f"{outdir}/refit.csv", index=False)

    fl = []
    for o in ids:
        pr = pq[(pq.norad_id == o) & (pq.horizon_d == 30)]
        g = G.get(o)
        if pr.empty or g is None:
            continue
        a, b = maneuver_flags(g, pd.Timestamp(pr.iloc[0].decay_time))
        fl.append(dict(norad_id=o, ecc=pr.iloc[0].ecc, sigA=a, sigB=b))
    pd.DataFrame(fl).to_csv(f"{outdir}/flags.csv", index=False)
    return df, pd.DataFrame(fl), G


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scored", nargs="+")
    ap.add_argument("--outdir", default="results/00d/checks")
    ap.add_argument("--sel", default=SEL)
    ap.add_argument("--no-check2", action="store_true")
    a = ap.parse_args()

    ids = json.load(open(a.sel))["ids"]
    t_start = time.time()
    pq = pd.read_parquet(PQ)
    assert (pq.block == "train").all(), "non-train rows in parquet"
    t1 = time.time()
    tle = pd.read_csv(TLE, usecols=["NORAD_CAT_ID", "EPOCH", "SEMIMAJOR_AXIS", "PERIAPSIS", "APOAPSIS"])
    tle = tle[tle.NORAD_CAT_ID.isin(ids)].copy()
    tle["EPOCH"] = pd.to_datetime(tle["EPOCH"])
    tle = tle.sort_values(["NORAD_CAT_ID", "EPOCH"]).reset_index(drop=True)
    t_load = time.time() - t1
    cand = pd.read_csv(CAND, low_memory=False)

    t2 = time.time()
    df, fl, G = run_core(a.outdir, ids, pq, tle, cand)
    t_core = time.time() - t2
    res = {}

    # CHECK 1: point-in-time + independent refit agrees with frozen parquet
    d = df[df.get("note").isna()] if "note" in df else df
    res["1 point-in-time"] = bool(d.pit_ok.all())
    res["1 refit matches parquet"] = bool(d["match"].astype(bool).all())
    print(f"\nCHECK 1: {len(d)} (object,horizon) rows checked; min margin {d.margin_h.min():.2f} h (must be >= 0)")
    bad = d[~d["match"].astype(bool)]
    if len(bad):
        print("  MISMATCH rows:\n", bad[["norad_id", "h", "pq_status", "my_status", "pq_pred", "my_pred"]].to_string())
    miss = df[df.get("note").notna()] if "note" in df else df.iloc[0:0]
    print(f"  not in parquet at some horizon: {len(miss)} rows (dropped as insufficient by builder)")

    # CHECK 4: dates and time zones
    c4 = []
    p30 = pq[pq.horizon_d.isin([30, 14])]
    p25 = p30[p30.norad_id.isin(ids)]
    dec = pd.to_datetime(p25.decay_time)
    c4.append(("decay_time is 12:00:00 UTC (date-only label convention)", bool(((dec.dt.hour == 12) & (dec.dt.minute == 0) & (dec.dt.second == 0)).all())))
    c4.append(("issue_time == decay_time - horizon exactly", bool(((dec - pd.to_datetime(p25.issue_time)) == pd.to_timedelta(p25.horizon_d, unit="D")).all())))
    c4.append(("TLE EPOCH tz-naive, no NaT", bool(tle.EPOCH.dt.tz is None and tle.EPOCH.notna().all())))
    c4.append(("TLE EPOCH within 2014..2026", bool(tle.EPOCH.between("2014-01-01", "2026-12-31").all())))
    mono = all(g.EPOCH.is_monotonic_increasing for _, g in G.items())
    c4.append(("TLE EPOCH sorted per object", bool(mono)))
    dcol = [c for c in cand.columns if "decay" in c.lower()]
    icol = [c for c in cand.columns if c.lower() in ("norad_cat_id", "norad_id")]
    if dcol and icol:
        m = cand[[icol[0], dcol[0]]].drop_duplicates(icol[0]).rename(columns={icol[0]: "norad_id", dcol[0]: "satcat"})
        m["satcat"] = pd.to_datetime(m["satcat"], errors="coerce").dt.normalize()
        x = p25.drop_duplicates("norad_id").merge(m, on="norad_id", how="left")
        ok = (pd.to_datetime(x.decay_time).dt.normalize() == x.satcat)
        c4.append((f"decay_time date == candidates.csv '{dcol[0]}' date ({int(ok.sum())}/{len(x)})", bool(ok.all())))
    else:
        c4.append(("candidates.csv decay column not found, SATCAT date check SKIPPED", False))
    after = 0
    for o in ids:
        pr = pq[(pq.norad_id == o) & (pq.horizon_d == 30)]
        if len(pr) and o in G and (G[o].EPOCH > pd.Timestamp(pr.iloc[0].decay_time) + pd.Timedelta(days=1)).any():
            after += 1
    c4.append((f"objects with TLE epochs >1 d after decay label (info, expect few): {after}", True))
    print("\nCHECK 4:")
    for k, v in c4:
        print(f"  {'PASS' if v else 'FAIL'}  {k}")
    res["4 dates/timezones"] = all(v for _, v in c4)

    # CHECK 3 helper: maneuver flags + 10 objects for eyeball inspection
    rng = np.random.default_rng(SEED)
    insp = [int(i) for i in rng.choice(ids, min(10, len(ids)), replace=False)]
    print(f"\nCHECK 3 (human): inspect these 10: {insp}")
    print("  automated Signature A/B flags on all 25 (30 d rows):")
    print(fl.to_string(index=False))
    json.dump({"inspect_ids": insp, "seed": SEED}, open(f"{a.outdir}/inspect10.json", "w"))

    # CHECK 5 + 3 plots
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        ok_rows = df[df.my_status.isin(["ok", "cap"]) & (df.h == 30)] if "my_status" in df else df.iloc[0:0]
        pick = []
        for cond in (ok_rows.my_status == "cap", ok_rows.pq_status.eq("ok") & (ok_rows.norad_id.map(lambda o: pq[(pq.norad_id == o) & (pq.horizon_d == 30)].iloc[0].ecc) > 0.01),
                     ok_rows.pq_status.eq("ok")):
            for o in ok_rows[cond].norad_id:
                if o not in pick:
                    pick.append(o)
                    if len(pick) >= 5 and cond is not None:
                        break
        pick = pick[:5]

        def draw(ax, o, h=30):
            pr = pq[(pq.norad_id == o) & (pq.horizon_d == h)].iloc[0]
            g = G[o]
            decd = pd.Timestamp(pr.decay_time)
            gg = g[g.EPOCH >= decd - pd.Timedelta(days=90)]
            x = (gg.EPOCH - decd).dt.total_seconds().values / 86400
            ax.plot(x, alt_series(gg), ".", ms=2)
            r = refit(g, pd.Timestamp(pr.issue_time))
            if r["status"] in ("ok", "cap") and not np.isnan(r["slope"]):
                tl_ = r["t_last"] - (decd - REF).total_seconds() / 86400
                xs = np.linspace(tl_ - P["window_d"], min(0, tl_ + 30), 50)
                ax.plot(xs, r["ic"] + r["slope"] * (xs - tl_), "r-", lw=1)
            ax.axvline(-h, color="g", lw=0.8)
            ax.axvline(0, color="k", lw=0.8)
            ax.axhline(P["decay_alt_km"], color="gray", ls=":")
            ax.set_title(f"{o} {pr.status} e={pr.ecc:.3f}", fontsize=7)
            ax.tick_params(labelsize=6)

        for o in pick:
            fig, ax = plt.subplots(figsize=(5, 3))
            draw(ax, o)
            ax.set_xlabel("days rel. decay (green=issue, red=Model A fit)")
            ax.set_ylabel("alt km")
            fig.savefig(f"{a.outdir}/alt_{o}.png", dpi=110, bbox_inches="tight")
            plt.close(fig)
        fig, axs = plt.subplots(2, 5, figsize=(16, 6))
        for ax, o in zip(axs.ravel(), insp):
            if len(pq[(pq.norad_id == o) & (pq.horizon_d == 30)]):
                draw(ax, o)
        fig.savefig(f"{a.outdir}/inspect10.png", dpi=110, bbox_inches="tight")
        plt.close(fig)
        print(f"\nCHECK 5 (human): view {a.outdir}/alt_<id>.png for {pick}; CHECK 3: view {a.outdir}/inspect10.png")
    except ImportError:
        print("\nmatplotlib missing: pip3 install matplotlib. Checks 3 and 5 plots SKIPPED.")

    # CHECK 6: runtime
    per_obj = t_core / max(1, len(d))
    est = {h: t_load * 0 + per_obj * n for h, n in N_FULL.items()}
    print(f"\nCHECK 6: parquet+TLE load {t_load:.1f}s for 25 ids (full file read once); refit {per_obj*1000:.1f} ms per (object,horizon)")
    print(f"  extrapolated refit-only cost: 30 d {est[30]:.0f}s, 14 d {est[14]:.0f}s (excludes physics model and conformal)")
    json.dump(dict(load_s=t_load, core_s=t_core, per_row_s=per_obj, est_s=est), open(f"{a.outdir}/timing.json", "w"))

    # CHECK 2: rerun from frozen inputs, diff
    if not a.no_check2:
        tmp = tempfile.mkdtemp()
        subprocess.run([sys.executable, __file__, "--no-check2", "--outdir", tmp, "--sel", a.sel], check=True, stdout=subprocess.DEVNULL)
        same = all(sha(f"{a.outdir}/{f}") == sha(f"{tmp}/{f}") for f in ("refit.csv", "flags.csv"))
        res["2 rerun identical (this script)"] = same
        print(f"\nCHECK 2: script rerun identical: {same}")
        if a.scored:
            out_tmp = f"{tmp}/modelA_rerun.parquet"
            subprocess.run([sys.executable, BUILDER, "--scored", *a.scored, "--tle", TLE,
                            "--out", out_tmp, "--log", f"{tmp}/build.json"], check=True, stdout=subprocess.DEVNULL)
            k = ["norad_id", "horizon_d"]
            n = pd.read_parquet(out_tmp).sort_values(k).reset_index(drop=True)
            o = pd.read_parquet(PQ).sort_values(k).reset_index(drop=True)
            res["2 builder rerun identical"] = bool(n.equals(o))
            print(f"  builder rerun vs frozen parquet identical: {res['2 builder rerun identical']} ({len(n)} vs {len(o)} rows)")
        else:
            print("  builder rerun SKIPPED (pass --scored to include it)")

    print("\nSUMMARY (checks 3 and 5 need human sign-off):")
    for k, v in res.items():
        print(f"  {'PASS' if v else 'FAIL'}  {k}")
    sys.exit(0 if all(res.values()) else 1)


if __name__ == "__main__":
    main()
