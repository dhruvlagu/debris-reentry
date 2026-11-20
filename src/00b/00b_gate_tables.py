"""Step 0B tables and threshold verdict. Reads downloaded gp_history only. No network. Memory-safe (one batch file at a time).
Needs: results/0b_label_flags.csv (run 00b_label_check.py first). Uses results/0b_maneuver_flags.csv (Signature A) if present.
Pilot run = partial download: tables are a dry run, edges are PROVISIONAL, verdict is meaningless until the full pull."""
import json, pathlib, importlib.util
import numpy as np, pandas as pd

spec = importlib.util.spec_from_file_location("c", "src/00b_counts.py"); c = importlib.util.module_from_spec(spec); spec.loader.exec_module(c)
SEED, CAP, EXEMPT, HORIZONS, RE = 20261105, 30, {"1998-067"}, (30, 14, 7), 6378.135
BLOCKS = {"train": ("2015-01-01", "2022-12-31"), "validation": ("2023-01-31", "2024-12-31"), "test": ("2025-01-31", "2026-09-30")}
TH = dict(total=300, test=100, disturbed=40, disturbed_test=15, storms=3)
HIST = pathlib.Path("data/raw/gp_history")

cand = pd.read_csv("data/frozen/candidates.csv", parse_dates=["DECAY"]).merge(pd.read_csv("results/0b_label_flags.csv"), on="NORAD_CAT_ID", how="left")
try:
    cand = cand.merge(pd.read_csv("results/0b_maneuver_flags.csv")[["NORAD_CAT_ID", "flag_A_sma_rise"]], on="NORAD_CAT_ID", how="left")
except Exception:
    cand["flag_A_sma_rise"] = np.nan
cand["label"] = cand.DECAY + pd.Timedelta(hours=12)
cand["rand"] = np.random.default_rng(SEED).random(len(cand))
def block(d):
    for k, (a, b) in BLOCKS.items():
        if pd.Timestamp(a) <= d <= pd.Timestamp(b): return k
    return "embargo_or_outside"
cand["block"] = cand.DECAY.map(block)
cmap = cand.set_index("NORAD_CAT_ID")
done = set(json.loads((HIST / "completed.json").read_text()))
done &= set(cmap.index)

rec = {(o, H): dict(NORAD_CAT_ID=o, H=H, has_any=False, n14=0, alt=np.nan) for o in done for H in HORIZONS}
gaps = []
for f in sorted(HIST.glob("batch_*.json")):
    data = json.loads(f.read_text())
    if not data: continue
    df = pd.DataFrame(data)[["NORAD_CAT_ID", "EPOCH", "CREATION_DATE", "SEMIMAJOR_AXIS"]].copy()
    df["NORAD_CAT_ID"] = df.NORAD_CAT_ID.astype(int)
    for k in ("EPOCH", "CREATION_DATE"): df[k] = pd.to_datetime(df[k])
    df["SEMIMAJOR_AXIS"] = pd.to_numeric(df.SEMIMAJOR_AXIS, errors="coerce")
    for oid, g in df[df.NORAD_CAT_ID.isin(done)].groupby("NORAD_CAT_ID"):
        lt = cmap.at[oid, "label"]; g = g.sort_values("CREATION_DATE")
        gaps.append({"NORAD_CAT_ID": oid, "gap_h": (lt - g.EPOCH.max()).total_seconds() / 3600})
        for H in HORIZONS:
            issue = lt - pd.Timedelta(days=H); pub = g[g.CREATION_DATE <= issue]
            rec[(oid, H)].update(has_any=len(pub) > 0, n14=int((pub.CREATION_DATE > issue - pd.Timedelta(days=14)).sum()),
                                 alt=float(pub.SEMIMAJOR_AXIS.iloc[-1]) - RE if len(pub) else np.nan)
T = pd.DataFrame(rec.values()).merge(cand, on="NORAD_CAT_ID").merge(pd.DataFrame(gaps), on="NORAD_CAT_ID", how="left")
partial = len(done) < 0.9 * len(cand)
print(f"downloaded objects {len(done)} of {len(cand)} candidates", "| PARTIAL: dry run, edges provisional, verdict meaningless" if partial else "| full")

kp = c.load_kp(); kp = kp[kp.kp >= 0]; kt, kv = kp.t.to_numpy(), kp.kp.to_numpy()
def maxkp(a, b):
    i, j = np.searchsorted(kt, np.datetime64(a)), np.searchsorted(kt, np.datetime64(b))
    return kv[i:j].max() if j > i else np.nan
reg = lambda m: "n/a" if np.isnan(m) else "disturbed" if m >= 6 else "moderate" if m >= 5 else "quiet"
T["issue"] = T.label - pd.to_timedelta(T.H, unit="D")
T["regime_window"] = [reg(maxkp(a, b)) for a, b in zip(T.issue, T.label)]
T["regime_pre3d"] = [reg(maxkp(a - pd.Timedelta(days=3), a)) for a in T.issue]
ev = c.storm_events(kp, merge_hours=48)

print("\nTracking: last element set vs label (hours before label), by type; negative = last set after label")
gp = pd.DataFrame(gaps).merge(cand[["NORAD_CAT_ID", "OBJECT_TYPE"]], on="NORAD_CAT_ID")
print(gp.groupby("OBJECT_TYPE").gap_h.describe(percentiles=[.1, .5, .9]).round(1))

print("\nLabel-noise gate, gap-based (PREREG Amendment 3): noise = max(12 h, 0.2 x hours untracked before label); tolerance = 0.1 x horizon")
for H in (30, 14, 7, 3, 1):
    tol = 0.1 * H * 24
    noise = np.maximum(12.0, 0.2 * np.maximum(gp.gap_h, 0))
    over = noise > tol
    print(f"  {H:>2} d: tolerance {tol:5.1f} h | share over tolerance {over.mean():.2f} ->", "PASS" if over.mean() <= 0.25 else "FAIL (drop horizon)", "| by class", over.groupby(gp.OBJECT_TYPE).mean().round(2).to_dict())
print("  share with last element set within 24 h of label, by class:", (gp.gap_h.abs() <= 24).groupby(gp.OBJECT_TYPE).mean().round(2).to_dict())

edges = {}
for H in HORIZONS:
    t = T[T.H == H].copy(); has = t[t.has_any]
    q = has.alt.quantile([1 / 3, 2 / 3]).tolist(); edges[H] = [round(x, 1) for x in q]
    t["band"] = np.where(~t.has_any, "no_record", np.where(t.alt <= q[0], "low", np.where(t.alt <= q[1], "mid", "high")))
    t["trk"] = t.has_any & (t.n14 >= 3)
    ok = t.trk & ~t.mismatch.fillna(False) & ~(t.flag_A_sma_rise == True)
    kept = t[ok].sort_values("rand"); kept = kept[(kept.cluster.isin(EXEMPT)) | (kept.groupby("cluster").cumcount() < CAP)]
    print(f"\n===== horizon {H} d =====  altitude tercile edges (km, {'PROVISIONAL' if partial else 'freeze'}): {edges[H]}")
    print("attrition: downloaded", len(t), "| >=1 record before issue", int(t.has_any.sum()), "| >=3 in 14 d", int(t.trk.sum()),
          "| not label-mismatch", int((t.trk & ~t.mismatch.fillna(False)).sum()), "| not Signature A", int(ok.sum()),
          f"| after cap {CAP}/cluster", len(kept), "| A-unchecked", int(t.flag_A_sma_rise.isna().sum()))
    print("tracking requirement retention by tercile (of objects with a record):")
    print(t[t.has_any].groupby("band").trk.agg(["size", "sum", "mean"]).round(3))
    print("retention by class:"); print(t.groupby("OBJECT_TYPE").trk.agg(["size", "sum", "mean"]).round(3))
    print("kept set by class:", kept.OBJECT_TYPE.value_counts().to_dict(), "| by RCS size:", kept.rcs_size.value_counts().to_dict())
    print("kept set by year:", kept.DECAY.dt.year.value_counts().sort_index().to_dict())
    gb = pd.cut(kept.gap_h.abs(), [-1, 24, 72, 1e9], labels=["<=24h", "24-72h", ">72h"])
    print("kept set by gap bin (last element set to label), by class:"); print(pd.crosstab(kept.OBJECT_TYPE, gb))
    tl = kept[kept.gap_h.abs() <= 24]
    print("TIGHT-LABEL subset (gap <= 24 h):", len(tl), "| by block:", tl.block.value_counts().to_dict(), "| disturbed:", int((tl.regime_window == "disturbed").sum()), "| disturbed in test:", int(((tl.regime_window == "disturbed") & (tl.block == "test")).sum()))
    print("kept set, block x regime (window to decay):"); print(pd.crosstab(kept.block, kept.regime_window))
    print("kept set, regime in 3 days before issue:", kept.regime_pre3d.value_counts().to_dict())
    tot, te = len(kept), int((kept.block == "test").sum())
    dis, dte = int((kept.regime_window == "disturbed").sum()), int(((kept.regime_window == "disturbed") & (kept.block == "test")).sum())
    dtest = kept[(kept.regime_window == "disturbed") & (kept.block == "test")]
    hit = {i for a, b in zip(dtest.issue, dtest.label) for i, (s, e) in enumerate(ev) if s <= b and e >= a}
    for name, val, need_ in (("total", tot, TH["total"]), ("test block", te, TH["test"]), ("disturbed overall", dis, TH["disturbed"]),
                             ("disturbed in test", dte, TH["disturbed_test"]), ("independent storms in test disturbed windows", len(hit), TH["storms"])):
        print(f"  threshold {name}: {val} vs {need_} ->", "pass" if val >= need_ else "FAIL")

print("\nDistinct storm events per split block (Kp>=6 merged), by merge gap:")
for gap_h in (12, 24, 48):
    evs = c.storm_events(kp, merge_hours=gap_h)
    print(f"  {gap_h} h:", {k: sum(pd.Timestamp(a) <= s <= pd.Timestamp(b) + pd.Timedelta(days=1) for s, e in evs) for k, (a, b) in BLOCKS.items()})
pathlib.Path("results/0b_alt_edges_provisional.json").write_text(json.dumps(edges))
