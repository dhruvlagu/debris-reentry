#!/usr/bin/env python3
"""Step 0C, uneven-effect stress test (PREREG deviation D6). TRAINING DATA ONLY.

Question: does the 0C power result (>= 80% power for a 15% improvement) survive when the
improvement is uneven across clusters, weeks, or eccentricity classes?

Design follows PREREG Sec 7 / Amendments 22, 23: centered Model A errors (per-horizon training
median log error subtracted), empirical-quantile generator, paired bootstrap by decay week AND by
parent cluster, detected only if BOTH reject at one-sided alpha 0.05, 199 resamples, seed 20261114.

NOTE: this is a standalone reconstruction of the 0C generator, not an import of 00c_power.py.
The 'uniform' scenario is a control: its power should land in the 0C range (0.904-1.000 at 30 d,
0.972-1.000 at 14 d). If it does not, the stress results are not comparable to 0C.

Usage:  python3 src/00c_stress.py --sims 200          # smoke run
        python3 src/00c_stress.py                       # full (2000 sims, reduced grid)
        python3 src/00c_stress.py --full                # full 3x3 grid, slow
"""
import argparse, hashlib, json, os, sys, time
import numpy as np
import pandas as pd
from scipy.stats import norm, rankdata

SEED = 20261114
B = 199
ALPHA = 0.05
ECC_CUT = 0.01
TARGET = 0.15
ICC_CAP = 0.95


def normal_scores(x):
    return norm.ppf((rankdata(x) - 0.5) / len(x))


def icc1(x, g):
    """One-way ANOVA ICC(1) on normal scores, clipped to [0, ICC_CAP]."""
    z = normal_scores(x)
    df = pd.DataFrame({"z": z, "g": g})
    n = len(df)
    grp = df.groupby("g")["z"]
    k = grp.size().values.astype(float)
    G = len(k)
    if G < 2 or n <= G:
        return 0.0
    gm = grp.mean().values
    msb = (k * (gm - z.mean()) ** 2).sum() / (G - 1)
    msw = ((z - grp.transform("mean").values) ** 2).sum() / (n - G)
    k0 = (n - (k ** 2).sum() / n) / (G - 1)
    return float(np.clip((msb - msw) / (msb + (k0 - 1) * msw), 0.0, ICC_CAP))


def wmedian(vals, order, W):
    """Weighted median of vals over each row of W (B x n), vals pre-sorted by `order`."""
    cs = np.cumsum(W[:, order], axis=1)
    half = cs[:, -1:] / 2.0
    idx = (cs >= half).argmax(axis=1)
    return vals[order][idx]


def delta_vector(scen, rng, ecc_mask, f, gw, gc, nw, nc):
    n = len(gw)
    if scen == "null":
        return np.zeros(n)
    if scen == "uniform":
        return np.full(n, TARGET)
    if scen == "cluster_half":
        t = rng.permutation(nc) < nc // 2
        return np.where(t[gc], 2 * TARGET, 0.0)
    if scen == "week_half":
        t = rng.permutation(nw) < nw // 2
        return np.where(t[gw], 2 * TARGET, 0.0)
    if scen == "ecc_scaled":
        d_c = max(0.0, (TARGET - f * 0.25) / (1 - f))
        return np.where(ecc_mask, 0.25, d_c)
    if scen == "circ_only":
        return np.where(ecc_mask, 0.0, min(0.6, TARGET / (1 - f)))
    raise ValueError(scen)


def simulate(es, gw, gc, ecc_mask, icc_w, icc_c, rho, mult, scen, sims, rng):
    n, nw, nc = len(es), gw.max() + 1, gc.max() + 1
    f = float(ecc_mask.mean())
    s = mult * (icc_w + icc_c)
    scale = min(1.0, ICC_CAP / s) if s > 0 else 0.0
    a = np.sqrt(mult * icc_w * scale)
    b = np.sqrt(mult * icc_c * scale)
    c = np.sqrt(max(1e-9, 1 - a * a - b * b))
    grid = np.arange(n)
    det = eff = 0
    effs = []
    for _ in range(sims):
        uw, uc = rng.standard_normal(nw), rng.standard_normal(nc)
        eb, ez = rng.standard_normal(n), rng.standard_normal(n)
        ec = rho * eb + np.sqrt(1 - rho ** 2) * ez
        zb = a * uw[gw] + b * uc[gc] + c * eb
        zc = a * uw[gw] + b * uc[gc] + c * ec
        xb = np.interp(norm.cdf(zb) * (n - 1), grid, es)
        xc = np.interp(norm.cdf(zc) * (n - 1), grid, es)
        d = delta_vector(scen, rng, ecc_mask, f, gw, gc, nw, nc)
        xc = xc * (1 - d)
        ab, ac = np.abs(xb), np.abs(xc)
        ob, oc = np.argsort(ab), np.argsort(ac)
        w1 = np.ones((1, n))
        mb0 = wmedian(ab, ob, w1)[0]
        mc0 = wmedian(ac, oc, w1)[0]
        effs.append(100 * (mb0 - mc0) / mb0)
        ok = True
        for grp_idx, G in ((gw, nw), (gc, nc)):
            cnt = rng.multinomial(G, np.full(G, 1.0 / G), size=B)
            W = cnt[:, grp_idx].astype(float)
            mb = wmedian(ab, ob, W)
            mc = wmedian(ac, oc, W)
            stat = (mb - mc) / mb
            if (stat <= 0).mean() >= ALPHA:  # one-sided: reject if lower tail clears zero
                ok = False
                break
        det += ok
    return det / sims, float(np.mean(effs)), float(np.std(effs))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pq", default="data/frozen/modelA_train.parquet")
    ap.add_argument("--out", default="results/0c_stress")
    ap.add_argument("--sims", type=int, default=2000)
    ap.add_argument("--alpha", type=float, default=ALPHA)
    ap.add_argument("--full", action="store_true", help="3x3 grid (rho 0.3/0.6/0.9 x mult 0/1/2)")
    a = ap.parse_args()
    globals()["ALPHA"] = a.alpha

    df = pd.read_parquet(a.pq)
    assert (df.block == "train").all(), "non-train rows present"
    rhos, mults = ([0.3, 0.6, 0.9], [0.0, 1.0, 2.0]) if a.full else ([0.3, 0.6], [0.0, 1.0])
    scens = ["null", "uniform", "cluster_half", "week_half", "ecc_scaled", "circ_only"]
    os.makedirs(a.out, exist_ok=True)
    rows, spec = [], {}
    t0 = time.time()
    for h in (30, 14):
        d = df[df.horizon_d == h].copy()
        e = np.log(d.pred_days.values / d.true_days.values)
        e = e - np.median(e)  # Amendment 22 centering
        es = np.sort(e)
        gw = pd.factorize(pd.to_datetime(d.decay_time).dt.to_period("W"))[0]
        gc = pd.factorize(d.cluster_id)[0]
        ecc_mask = (d.ecc.values > ECC_CUT)
        icc_w, icc_c = icc1(e, gw), icc1(e, gc)
        spec[h] = dict(n=len(d), n_weeks=int(gw.max() + 1), n_clusters=int(gc.max() + 1),
                       ecc_frac=float(ecc_mask.mean()), icc_week=icc_w, icc_cluster=icc_c,
                       mad_centered=float(np.median(np.abs(e))))
        print(f"\n== {h} d: n={len(d)}, weeks={gw.max()+1}, clusters={gc.max()+1}, "
              f"ecc frac={ecc_mask.mean():.3f}, ICC week={icc_w:.3f}, ICC cluster={icc_c:.3f} "
              f"(notebook cluster ICC: {'0.356' if h == 30 else '0.522'})")
        for si, scen in enumerate(scens):
            for rho in rhos:
                for mult in mults:
                    rng = np.random.default_rng([SEED, si, h, int(rho * 10), int(mult * 10)])
                    p, eff, effsd = simulate(es, gw, gc, ecc_mask, icc_w, icc_c, rho, mult, scen, a.sims, rng)
                    rows.append(dict(horizon=h, scenario=scen, rho=rho, icc_mult=mult, power=p,
                                     realized_effect_pct=eff, realized_effect_sd=effsd))
                    print(f"  {scen:13s} rho={rho} mult={mult}: rate={p:.3f}  realized effect {eff:5.1f}% (sd {effsd:.1f})  [{time.time()-t0:.0f}s]", flush=True)

    res = pd.DataFrame(rows)
    res.to_csv(f"{a.out}/stress_results.csv", index=False)
    json.dump(dict(seed=SEED, sims=a.sims, bootstrap=B, alpha=ALPHA, target=TARGET, rho_grid=rhos,
                   mult_grid=mults, scenarios=scens, per_horizon=spec,
                   numpy=np.__version__, pandas=pd.__version__, pq=a.pq,
                   pq_sha256=hashlib.sha256(open(a.pq, "rb").read()).hexdigest()),
              open(f"{a.out}/spec.json", "w"), indent=1, default=str)

    print("\n=== SUMMARY: min over grid (80% line = pass; 'null' row is false-alarm rate) ===")
    summ = res.groupby(["horizon", "scenario"]).agg(min_rate=("power", "min"), max_rate=("power", "max"),
                                                      mean_realized_effect=("realized_effect_pct", "mean")).round(3)
    print(summ.to_string())
    ctrl = res[res.scenario == "uniform"].groupby("horizon").power.agg(["min", "max"])
    print("\nControl check vs 0C (30 d: 0.904-1.000, 14 d: 0.972-1.000):\n", ctrl.round(3).to_string())
    bad = summ.drop("null", level="scenario")
    bad = bad[bad.min_rate < 0.80]
    print("\nScenarios below 80% at the worst grid point:" if len(bad) else "\nNo non-null scenario fell below 80%.")
    if len(bad):
        print(bad.to_string())
    print(f"\nWrote {a.out}/stress_results.csv and spec.json")


if __name__ == "__main__":
    main()
