#!/usr/bin/env python3
"""
src/00c_power.py | Protocol Step 0C, PREREG Sec 7. TRAINING DATA ONLY.

Input: one row per (object, horizon): Model A forecast made from pre-issue data only.
The script cannot verify point-in-time integrity (Rule 1). You must.

Effect statistic: relative reduction in median |log(pred/true)|, candidate vs baseline.
Test: paired block bootstrap by decay week, one-sided, alpha from --alpha.
Generator: crossed week and parent-cluster random effects from training ICCs,
paired baseline/candidate errors with correlation r, candidate rescaled so the
population median |error| ratio equals 1 - effect.
effect = 0 cells are the false-positive check.
"""
import argparse, hashlib, json, os, subprocess, sys, time
import numpy as np, pandas as pd
from scipy.stats import norm, rankdata
from scipy.special import ndtr, ndtri

# MAP TO YOUR SCHEMA. ecc is optional.
COL = dict(hor="horizon_d", decay="decay_time", pred="pred_days",
           true="true_days", cluster="cluster_id", block="block", ecc="ecc")


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def icc_oneway(x, g):
    x = np.asarray(x, float)
    g = pd.factorize(g)[0]
    k, N = g.max() + 1, len(x)
    if k < 2 or N <= k:
        return float("nan")
    n_i = np.bincount(g)
    m_i = np.bincount(g, x) / n_i
    msb = (n_i * (m_i - x.mean()) ** 2).sum() / (k - 1)
    msw = ((x - m_i[g]) ** 2).sum() / (N - k)
    n0 = (N - (n_i ** 2).sum() / N) / (k - 1)
    rho = (msb - msw) / (msb + (n0 - 1) * msw)
    return float(np.clip(rho, 0, 1))


def draw(rng, size, df):
    z = rng.standard_normal(size)
    if df is None:
        return z
    return z * np.sqrt((df - 2) / df) / np.sqrt(rng.chisquare(df, size) / df)


def structure(d, center=False):
    e = np.log(d[COL["pred"]].values / d[COL["true"]].values)
    raw_med = float(np.median(e))
    if center:
        e = e - raw_med
    wk = pd.to_datetime(d[COL["decay"]], utc=True).dt.tz_convert(None).dt.to_period("W").astype(str).values
    cl = d[COL["cluster"]].values
    n = len(d)
    out = dict(raw_median_e=raw_med, centered=center, n=n, k_week=len(set(wk)), k_cluster=len(set(cl)),
               mean_e=float(e.mean()), sd_e=float(e.std(ddof=1)),
               med_abs_e=float(np.median(np.abs(e))),
               icc_week_e=icc_oneway(e, wk), icc_cluster_e=icc_oneway(e, cl),
               icc_week_abs=icc_oneway(np.abs(e), wk), icc_cluster_abs=icc_oneway(np.abs(e), cl))
    zr = ndtri((rankdata(e) - 0.5) / n)
    out["icc_week_rank"], out["icc_cluster_rank"] = icc_oneway(zr, wk), icc_oneway(zr, cl)
    out["DE_week"] = 1 + (n / out["k_week"] - 1) * out["icc_week_e"]
    out["DE_cluster"] = 1 + (n / out["k_cluster"] - 1) * out["icc_cluster_e"]
    out["n_eff"] = n / max(out["DE_week"], out["DE_cluster"])
    if COL["ecc"] in d:
        ec = d[COL["ecc"]].values > 0.01
        out["frac_eccentric"] = float(ec.mean())
        if ec.sum() > 5 and (~ec).sum() > 5:
            out["med_abs_e_ecc"] = float(np.median(np.abs(e[ec])))
            out["med_abs_e_circ"] = float(np.median(np.abs(e[~ec])))
    return out, e, pd.factorize(wk)[0], pd.factorize(cl)[0]


def qtrans(z, Q):
    return np.interp(ndtr(z), np.linspace(0, 1, len(Q)), Q)


def make_gen(st, k, r, a, Q):
    z = lambda x: 0.0 if np.isnan(x) else x
    iw, ic = (z(st["icc_week_rank"]), z(st["icc_cluster_rank"])) if Q is not None else (z(st["icc_week_e"]), z(st["icc_cluster_e"]))
    fw, fc = k * iw, k * ic
    cap = 0.95 if Q is not None else 0.9
    if fw + fc > cap:
        fw, fc = fw * cap / (fw + fc), fc * cap / (fw + fc)
    s_ = np.sqrt(1 - fw - fc)
    V, mu = st["sd_e"] ** 2, st["mean_e"]

    def gen(rng, G):
        n = len(G)
        e1, e2 = (draw(rng, n, a.df), draw(rng, n, a.df)) if Q is None else (rng.standard_normal(n), rng.standard_normal(n))
        zb, zc = G + s_ * e1, G + s_ * (r * e1 + np.sqrt(1 - r * r) * e2)
        if Q is None:
            sd = np.sqrt(V)
            return mu + sd * zb, mu + sd * zc
        return qtrans(zb, Q), qtrans(zc, Q)
    return gen, fw, fc


def wmed(v, order, W):
    cs = np.cumsum(W[:, order], axis=1)
    idx = (cs >= 0.5 * cs[:, -1:]).argmax(1)
    return v[order][idx]


def run_cell(st, wk, cl, delta, kmult, r, a, rng, Q=None):
    n, K, Kc = st["n"], wk.max() + 1, cl.max() + 1
    gen, fw, fc = make_gen(st, kmult, r, a, Q)
    b, c = gen(rng, np.sqrt(fw + fc) * rng.standard_normal(400_000))
    kap = (1 - delta) * np.median(np.abs(b)) / np.median(np.abs(c))
    blocks = {"week": (wk, K), "cluster": (cl, Kc)}
    use = ["week", "cluster"] if a.block == "both" else [a.block]
    Ws = {}
    for nm in use:
        codes, KK = blocks[nm]
        Ws[nm] = rng.multinomial(KK, np.full(KK, 1 / KK), size=a.nboot)[:, codes].astype(np.float32)
    mid = (n - 1) // 2
    rej, rh = 0, []
    for _ in range(a.nsim):
        G = rng.standard_normal(K)[wk] * np.sqrt(fw) + rng.standard_normal(Kc)[cl] * np.sqrt(fc)
        b, c = gen(rng, G)
        ab, ac = np.abs(b), np.abs(kap * c)
        ob, oc = np.argsort(ab), np.argsort(ac)
        rh.append(1 - ac[oc][mid] / ab[ob][mid])
        ok = True
        for nm in use:
            Rb = 1 - wmed(ac, oc, Ws[nm]) / wmed(ab, ob, Ws[nm])
            ok &= bool(np.quantile(Rb, a.alpha) > 0)
        rej += ok
    return rej / a.nsim, float(np.mean(rh))


def cov_precision(n_eff, p0=0.9, p1=0.8, alpha=0.05):
    se0, se1 = np.sqrt(p0 * (1 - p0) / n_eff), np.sqrt(p1 * (1 - p1) / n_eff)
    return se0, float(norm.cdf(((p0 - p1) - norm.ppf(1 - alpha) * se0) / se1))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--data", required=True)
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--out", default="results/0c")
    p.add_argument("--nsim", type=int, default=2000)
    p.add_argument("--nboot", type=int, default=199)
    p.add_argument("--alpha", type=float, default=0.05)
    p.add_argument("--effects", type=float, nargs="+", default=[0.0, 0.10, 0.15, 0.25])
    p.add_argument("--corr_mult", type=float, nargs="+", default=[0, 1, 2])
    p.add_argument("--pair_r", type=float, nargs="+", default=[0.3, 0.6, 0.9])
    p.add_argument("--center", action="store_true", help="subtract per-horizon training median log error (bias-removed stand-in baseline)")
    p.add_argument("--empirical", action="store_true", help="simulate through the empirical error quantiles (primary)")
    p.add_argument("--block", choices=["week", "cluster", "both"], default="both")
    p.add_argument("--df", type=float, default=None, help="Student-t df for tails (>2); default normal")
    p.add_argument("--horizons", type=int, nargs="+", default=[30, 14])
    p.add_argument("--storms", type=int, nargs="+", default=[13, 12], help="test storms, same order as --horizons")
    p.add_argument("--disturbed_n", type=int, nargs="+", default=[327, 240])
    a = p.parse_args()
    os.makedirs(a.out, exist_ok=True)
    t0 = time.time()

    d = pd.read_parquet(a.data) if a.data.endswith(".parquet") else pd.read_csv(a.data)
    miss = [c for k, c in COL.items() if k != "ecc" and c not in d]
    assert not miss, f"missing columns {miss}; edit COL"
    d = d[d[COL["block"]] == "train"]
    assert len(d), "no training rows"
    for c in (COL["pred"], COL["true"]):
        assert d[c].notna().all() and (d[c] > 0).all(), f"bad values in {c}"

    stats, power, mde, covp = {}, [], [], []
    for hi, h in enumerate(a.horizons):
        dh = d[d[COL["hor"]] == h]
        assert len(dh), f"no rows at horizon {h}"
        st, e, wk, cl = structure(dh, a.center)
        stats[h] = st
        rng = np.random.default_rng([a.seed, h])
        Q = np.sort(e) if a.empirical else None
        for km in a.corr_mult:
            for r in a.pair_r:
                for dl in a.effects:
                    pw, rh = run_cell(st, wk, cl, dl, km, r, a, rng, Q)
                    power.append(dict(horizon=h, corr_mult=km, pair_r=r, effect=dl, power=pw, mean_R_hat=rh))
                    print(f"h={h} k={km} r={r} eff={dl:.2f} power={pw:.3f}", flush=True)
        pdf = pd.DataFrame(power)
        pdf = pdf[(pdf.horizon == h)]
        for (km, r), g in pdf[pdf.effect > 0].groupby(["corr_mult", "pair_r"]):
            g = g.sort_values("effect")
            m = float(np.interp(0.8, g.power.values, g.effect.values)) if g.power.max() >= 0.8 and g.power.is_monotonic_increasing else float("nan")
            mde.append(dict(horizon=h, corr_mult=km, pair_r=r, mde_80=m))
        if hi < len(a.storms):
            for lab, ne in (("storm_count", a.storms[hi]),
                            ("n_over_DE_train", a.disturbed_n[hi] / max(st["DE_week"], st["DE_cluster"]))):
                se, pw = cov_precision(ne)
                covp.append({"horizon": h, "n_eff_basis": lab, "n_eff": ne, "se_at_90": se,
                             "power_detect_80_vs_90": pw})

    pd.DataFrame(power).to_csv(f"{a.out}/power.csv", index=False)
    pd.DataFrame(mde).to_csv(f"{a.out}/mde.csv", index=False)
    pd.DataFrame(covp).to_csv(f"{a.out}/coverage_precision.csv", index=False)
    try:
        gh = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        gh = None
    json.dump(dict(args=vars(a), cols=COL, data_sha256=sha256(a.data), git=gh,
                   numpy=np.__version__, pandas=pd.__version__, python=sys.version,
                   runtime_s=time.time() - t0, structure=stats),
              open(f"{a.out}/spec.json", "w"), indent=2, default=float)
    print(json.dumps(stats, indent=2, default=float))


if __name__ == "__main__":
    main()
