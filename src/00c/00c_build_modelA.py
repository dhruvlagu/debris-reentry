#!/usr/bin/env python3
"""
src/00c_build_modelA.py | Step 0C input. Builds frozen Model A baseline forecasts.
TRAINING DECAYS ONLY: validation/test decays and all TLE epochs after train_end are
dropped before any computation. Model A = Protocol Step 4 baseline.

Issue time T0 = official decay time - horizon. true_days = horizon by construction.
Point-in-time (Rule 1): a record is usable only if epoch + lag <= T0.
Model A: Theil-Sen line through altitude vs time over records in (T0 - window, T0 - lag].
  near-circular (ecc_last <= ecc_cut): altitude = sma - R_E
  eccentric: perigee altitude = sma*(1-ecc) - R_E
  remaining = (fitted_alt_at_last_record - decay_alt) / (-slope) - (T0 - t_last)
Failure handling (counted, never silent):
  insufficient (< min_sets in window): row excluded
  slope >= 0 or remaining > cap_days: pred = cap_days, status 'cap'
  remaining < min_days: pred = min_days, status 'floor'
"""
import argparse, hashlib, json, os
import numpy as np, pandas as pd
from scipy.stats import theilslopes

# MAP TO YOUR SCHEMA
SC = dict(obj="NORAD_CAT_ID", hor="H", decay="label_h", cluster="cluster", block="block")  # gate-rows files
TL = dict(obj="NORAD_CAT_ID", epoch="EPOCH", sma="SEMIMAJOR_AXIS", peri="PERIAPSIS",
          apo="APOAPSIS", jump="flag_jump")                                              # tle_merged_dupfilt.csv
# label_h = decay label in hours since 1970-01-01 UTC (inferred from two rows; asserted against DECAY below)
# PARAMETERS: must match PREREG Step 4 entry for Model A before running
P = dict(window_d=10.0, lag_h=24.0, min_sets=3, decay_alt_km=120.0, ecc_cut=0.01,
         re_km=6378.137, min_days=0.5, cap_days=365.0, train_end="2022-12-31")
REF = pd.Timestamp("2000-01-01")


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def naive_utc(s):
    return pd.to_datetime(s, utc=True).dt.tz_convert(None)


def rd(p):
    return pd.read_parquet(p) if p.endswith(".parquet") else pd.read_csv(p)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scored", required=True, nargs="+")
    ap.add_argument("--drop_jump", action="store_true", help="NON-CAUSAL DIAGNOSTIC ONLY: flag_jump uses post-issue neighbors (Rule 1). Never a forecast result.")
    ap.add_argument("--tle", required=True)
    ap.add_argument("--out", default="data/frozen/modelA_train.parquet")
    ap.add_argument("--log", default="results/0c/modelA_build.json")
    ap.add_argument("--seed", type=int, default=20261114)
    a = ap.parse_args()

    if a.drop_jump:
        print("WARNING: --drop_jump is a non-causal diagnostic. Do not report as forecast performance.")
    end = pd.Timestamp(P["train_end"]) + pd.Timedelta(days=1)
    sc = pd.concat([rd(f) for f in a.scored], ignore_index=True)
    sc = sc[sc[SC["block"]] == "train"].copy()  # structural guard 1: train block only
    dt = pd.to_datetime(sc["label_h"], unit="h")
    assert (dt.dt.normalize() == pd.to_datetime(sc["DECAY"]).dt.normalize()).all(), "label_h is not hours since 1970 matching DECAY"
    sc[SC["decay"]] = dt
    sc = sc[sc[SC["decay"]] < end].copy()  # structural guard 2: decay date
    assert len(sc), "no training rows"
    tl = rd(a.tle)
    tl[TL["epoch"]] = pd.to_datetime(tl[TL["epoch"]])  # naive, treated as UTC
    tl = tl[tl[TL["epoch"]] < end]  # structural guard: nothing after train_end can enter
    tl = tl.sort_values([TL["obj"], TL["epoch"]])
    G = {}
    for o, g in tl.groupby(TL["obj"]):
        sm, pe, ap = (g[TL[k]].values.astype(float) for k in ("sma", "peri", "apo"))
        G[o] = ((g[TL["epoch"]] - REF).dt.total_seconds().values / 86400, sm, pe,
                (ap - pe) / (2 * sm), g[TL["jump"]].values.astype(bool))

    lag = P["lag_h"] / 24
    out = []
    for r in sc.itertuples(index=False):
        o, h, dec, cl = (getattr(r, SC[k]) for k in ("obj", "hor", "decay", "cluster"))
        T0 = dec - pd.Timedelta(days=float(h))
        t0 = (T0 - REF).total_seconds() / 86400
        row = dict(norad_id=o, horizon_d=h, decay_time=dec, issue_time=T0, true_days=float(h),
                   cluster_id=cl, block="train", pred_days=np.nan, ecc=np.nan, status="insufficient",
                   n_window=0, n_jump=0, slope_km_d=np.nan, last_epoch_age_d=np.nan)
        g = G.get(o)
        if g is not None:
            t, sma, peri, ecc, jmp = g
            hi = np.searchsorted(t, t0 - lag, side="right")
            lo = np.searchsorted(t, t0 - P["window_d"], side="right")
            row["n_window"] = hi - lo
            if hi - lo >= 1:
                el = ecc[hi - 1]
                tt = t[lo:hi]
                y = (sma[lo:hi] - P["re_km"]) if el <= P["ecc_cut"] else peri[lo:hi]
                jj = jmp[lo:hi]
                row["n_jump"] = int(jj.sum())
                if a.drop_jump:
                    tt, y = tt[~jj], y[~jj]
                row["n_window"] = len(tt)
            if hi - lo >= 1 and len(tt) >= P["min_sets"]:
                t_last = tt[-1]
                assert t_last + lag <= t0 + 1e-9, "point-in-time violation"
                sl, ic, _, _ = theilslopes(y, tt - t_last)
                age = t0 - t_last
                row.update(ecc=el, slope_km_d=sl, last_epoch_age_d=age)
                if sl >= 0:
                    row.update(pred_days=P["cap_days"], status="cap")
                else:
                    rem = (ic - P["decay_alt_km"]) / (-sl) - age
                    if rem < P["min_days"]:
                        row.update(pred_days=P["min_days"], status="floor")
                    elif rem > P["cap_days"]:
                        row.update(pred_days=P["cap_days"], status="cap")
                    else:
                        row.update(pred_days=rem, status="ok")
        out.append(row)

    df = pd.DataFrame(out)
    assert df.decay_time.max() < end
    keep = df[df.status != "insufficient"]
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    os.makedirs(os.path.dirname(a.log) or ".", exist_ok=True)
    keep.to_parquet(a.out, index=False) if a.out.endswith(".parquet") else keep.to_csv(a.out, index=False)
    audit = keep.sample(min(10, len(keep)), random_state=a.seed)
    audit.to_csv(os.path.splitext(a.log)[0] + "_audit10.csv", index=False)
    counts = df.groupby(["horizon_d", "status"]).size().unstack(fill_value=0)
    print(counts)
    print(f"\n{a.out}\nsha256 {sha256(a.out)}")
    json.dump(dict(params=P, drop_jump_noncausal_diagnostic=a.drop_jump, cols=dict(SC=SC, TL=TL), counts=counts.to_dict(),
                   scored_sha256={f: sha256(f) for f in a.scored}, tle_sha256=sha256(a.tle),
                   out_sha256=sha256(a.out), n_in=len(df), n_out=len(keep)),
              open(a.log, "w"), indent=2, default=str)


if __name__ == "__main__":
    main()
