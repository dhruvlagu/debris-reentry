#!/usr/bin/env python3
"""Step 0C item 10 (PROTOCOL Sec 9.0C items 10, 11). Simulation-only power for the primary
contrast: density-model swap, resolved by DISTURBED regime, storm-level inference.

Training data only (centered Model A error distribution, Amendment 22). No validation or test
outcomes. Test-block COUNTS only (PREREG Sec 7: 13 storms / 327 disturbed objects at 30 d,
12 / 240 at 14 d, largest storm 70 at 30 d). Per-storm sizes are NOT known to this script;
two assumed layouts are run: 'skewed' (geometric, largest = 70 at 30 d, ~51 at 14 d) and
'balanced' (equal sizes). Both are assumptions, logged as such.

Unknowns this script cannot measure (so they are gridded, not estimated):
  rho   baseline vs candidate error correlation (two density models share most error)
  icc   shared within-storm error component
  absorb  fraction of a density difference that a BC refit absorbs (variant a vs b)
Rerun with real Model B/C errors after Step 4 (deviation D1/D2).

Test: paired bootstrap resampling STORMS, B = 199, one-sided alpha 0.025 (two-sided 95%, D3).
Effect statistic: 100 x (median|e_base| - median|e_cand|) / median|e_base|.

Usage: python3 src/00c_density_power.py --sims 200     (smoke)
       python3 src/00c_density_power.py                  (2000 sims)
"""
import argparse, hashlib, json, os
import numpy as np
import pandas as pd
from scipy.stats import norm

SEED = 20261114
B = 199
ALPHA = 0.025
SMALLEST = 5.0          # PROTOCOL 9.0C item 11, pre-stated
EFFECTS = [2.5, 5, 7.5, 10, 15, 25]
RHOS = [0.6, 0.8, 0.95]
ICCS = [0.0, 0.3, 0.6]
ABSORB = [0.5, 0.8]
LAYOUT = {30: dict(storms=13, total=327, maxsize=70), 14: dict(storms=12, total=240, maxsize=51)}


def skewed_sizes(n, total, mx):
    """Geometric sizes, first = mx, sum = total, each >= 1."""
    lo, hi = 1e-3, 1.0
    for _ in range(80):
        r = (lo + hi) / 2
        s = mx * r ** np.arange(n)
        lo, hi = (r, hi) if s.sum() < total else (lo, r)
    s = np.maximum(1, np.round(mx * ((lo + hi) / 2) ** np.arange(n))).astype(int)
    s[0] = mx
    s[1:] += 0
    diff = total - s.sum()
    i = 1
    while diff != 0:                      # absorb rounding drift in the smaller storms
        step = 1 if diff > 0 else -1
        if s[i] + step >= 1:
            s[i] += step
            diff -= step
        i = 1 + (i % (n - 1))
    return s


def wmedian(vals, order, W):
    cs = np.cumsum(W[:, order], axis=1)
    idx = (cs >= cs[:, -1:] / 2.0).argmax(axis=1)
    return vals[order][idx]


def power(es, sizes, rho, icc, eff, sims, rng):
    n, G = sizes.sum(), len(sizes)
    g = np.repeat(np.arange(G), sizes)
    a, c = np.sqrt(icc), np.sqrt(1 - icc)
    grid = np.arange(len(es))
    hit = 0
    for _ in range(sims):
        us = rng.standard_normal(G)
        eb, ez = rng.standard_normal(n), rng.standard_normal(n)
        ec = rho * eb + np.sqrt(1 - rho ** 2) * ez
        xb = np.interp(norm.cdf(a * us[g] + c * eb) * (len(es) - 1), grid, es)
        xc = np.interp(norm.cdf(a * us[g] + c * ec) * (len(es) - 1), grid, es) * (1 - eff / 100)
        ab, ac = np.abs(xb), np.abs(xc)
        ob, oc = np.argsort(ab), np.argsort(ac)
        cnt = rng.multinomial(G, np.full(G, 1.0 / G), size=B)
        W = cnt[:, g].astype(float)
        mb, mc = wmedian(ab, ob, W), wmedian(ac, oc, W)
        hit += ((mb - mc) / mb <= 0).mean() < ALPHA
    return hit / sims


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pq", default="data/frozen/modelA_train.parquet")
    ap.add_argument("--out", default="results/0c_density")
    ap.add_argument("--sims", type=int, default=2000)
    a = ap.parse_args()
    df = pd.read_parquet(a.pq)
    assert (df.block == "train").all()
    os.makedirs(a.out, exist_ok=True)
    rows = []
    for h, L in LAYOUT.items():
        d = df[df.horizon_d == h]
        e = np.log(d.pred_days.values / d.true_days.values)
        es = np.sort(e - np.median(e))
        layouts = {"skewed": skewed_sizes(L["storms"], L["total"], L["maxsize"]),
                   "balanced": np.full(L["storms"], L["total"] // L["storms"])}
        for lname, sizes in layouts.items():
            print(f"\n== {h} d, {lname}: sizes {sizes.tolist()} (n={sizes.sum()})")
            for icc in ICCS:
                for rho in RHOS:
                    rng = np.random.default_rng([SEED, h, len(lname), int(icc * 10), int(rho * 100)])
                    for eff in EFFECTS:
                        p = power(es, sizes, rho, icc, eff, a.sims, rng)
                        rows.append(dict(horizon=h, layout=lname, icc=icc, rho=rho, effect_pct=eff, power=p))
                    sub = [r for r in rows if r["horizon"] == h and r["layout"] == lname and r["icc"] == icc and r["rho"] == rho]
                    print(f"  icc={icc} rho={rho}: " + "  ".join(f"{r['effect_pct']}%:{r['power']:.2f}" for r in sub), flush=True)
    res = pd.DataFrame(rows)
    res.to_csv(f"{a.out}/density_power.csv", index=False)

    def mde(x):
        ok = x[x.power >= 0.80].effect_pct
        return ok.min() if len(ok) else np.nan
    m = res.groupby(["horizon", "layout", "icc", "rho"]).apply(mde).rename("MDE_pct_80").reset_index()
    print("\n=== Minimum detectable effect at 80% power (grid points; NaN = above 25%) ===")
    print(m.to_string(index=False))

    at5 = res[res.effect_pct == SMALLEST]
    print(f"\n=== Power at the pre-stated smallest meaningful difference ({SMALLEST}%), variant (b), BC frozen ===")
    print(at5.pivot_table(index=["horizon", "layout", "icc"], columns="rho", values="power").round(3).to_string())
    print("\nVariant (a), BC refit: a true unabsorbed difference X is seen as X x (1 - absorb).")
    for ab in ABSORB:
        print(f"  absorb {ab:.0%}: detecting a 5% variant-(b) difference needs the same power as a {SMALLEST*(1-ab):.1f}% effect; "
              f"read the {SMALLEST*(1-ab):.1f}%-equivalent from the table (nearest grid point 2.5%).")
    hi = at5[at5.rho >= 0.8]
    verdict = "INFERENTIAL (power >= 0.80 at 5% in every rho >= 0.8 condition)" if (hi.power >= 0.80).all() else "DESCRIPTIVE ONLY (fails the pre-set rule)"
    print(f"\nPre-set rule verdict for RQ2 on this simulation: {verdict}")
    json.dump(dict(seed=SEED, sims=a.sims, bootstrap=B, alpha_one_sided=ALPHA, smallest_pct=SMALLEST, effects=EFFECTS,
                   rhos=RHOS, iccs=ICCS, absorb=ABSORB, layout=LAYOUT, verdict=verdict, pq=a.pq,
                   pq_sha256=hashlib.sha256(open(a.pq, "rb").read()).hexdigest()),
              open(f"{a.out}/spec.json", "w"), indent=1)
    print(f"\nWrote {a.out}/density_power.csv and spec.json")


if __name__ == "__main__":
    main()
