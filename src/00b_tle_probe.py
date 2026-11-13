"""Probe the 2024 TLE bundle. Local, no network, read-only.
Part A (first 200k records): layout, trailing characters, catalog field, and whether the file is ordered by epoch.
Part B (one full pass, filtered to the 200 pilot objects): is the bundle complete vs the pilot gp_history rows, which sets it
contains (by epoch year or by creation year), and whether file order follows CREATION_DATE or EPOCH.
Usage: python3 src/00b_tle_probe.py [path]   Pass 1 takes a minute or two on a 2.8 GB file; progress prints every 5M lines."""
import sys, json, pathlib, itertools
import numpy as np, pandas as pd

F = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "data/raw/tle_bundles/2024/tle2024.txt")
ALPHA = "ABCDEFGHJKLMNPQRSTUVWXYZ"

def cat(c):
    c = c.strip()
    if c.isdigit(): return int(c)
    if c and c[0] in ALPHA and c[1:].isdigit(): return (ALPHA.index(c[0]) + 10) * 10000 + int(c[1:])
    return -1

def epoch_ts(l1):
    yy = int(l1[18:20]); y = 2000 + yy if yy < 57 else 1900 + yy
    return pd.Timestamp(year=y, month=1, day=1) + pd.to_timedelta(float(l1[20:32]) - 1, unit="D")

# ---------- Part A ----------
with F.open() as f:
    lines = list(itertools.islice(f, 400000))
l1s, l2s = lines[0::2], lines[1::2]
n = min(len(l1s), len(l2s))
bad = sum(not (a.startswith("1 ") and b.startswith("2 ")) for a, b in zip(l1s[:n], l2s[:n]))
print("PART A: records read", n, "| pairs not starting '1 ' then '2 ':", bad)
print("  trailing backslash: line1", round(np.mean([a.rstrip("\n").endswith("\\") for a in l1s[:n]]), 3),
      "| line2", round(np.mean([b.rstrip("\n").endswith("\\") for b in l2s[:n]]), 3))
print("  line1 length (without newline), top 3:", pd.Series([len(a.rstrip("\n")) for a in l1s[:n]]).value_counts().head(3).to_dict())
ids = [a[2:7] for a in l1s[:n]]
print("  catalog field: non-digit entries", sum(not c.strip().isdigit() for c in ids), "| examples:", [c for c in ids if not c.strip().isdigit()][:3])
key = np.array([int(a[18:20]) * 1000.0 + float(a[20:32]) for a in l1s[:n]])
d = np.diff(key); same = d > -300
print("  epoch order: share of consecutive records with EARLIER epoch:", round(float((d[same] < 0).mean()), 4),
      "| median size of those decreases (hours):", round(float(np.median(-d[same][d[same] < 0]) * 24), 2) if (d[same] < 0).any() else None)
print("  epoch range of first 200k records:", epoch_ts(l1s[int(np.argmin(key))]), "to", epoch_ts(l1s[int(np.argmax(key))]))

# ---------- Part B ----------
CACHE = pathlib.Path("data/frozen/tle2024_pilot_records.csv")   # derived from the bundle; lets reruns skip the 2-minute pass
if CACHE.exists():
    t = pd.read_csv(CACHE, parse_dates=["EPOCH"]); print("\nPART B: using cached bundle records", CACHE)
else:
    pil = pd.read_csv("data/frozen/pilot_ids.csv")["NORAD_CAT_ID"].astype(int)
    pset = {f"{i:05d}" for i in pil if i <= 99999}
    rec = []
    with F.open() as f:
        it = iter(f)
        for pos, l1 in enumerate(it):
            l2 = next(it, "")
            if l1[2:7] in pset:
                rec.append((pos, int(l1[2:7]), epoch_ts(l1), float(l2[52:63]), int(l2[26:33]) / 1e7))
            if pos % 2_500_000 == 0 and pos: print("  pass 1: records", pos, flush=True)
    t = pd.DataFrame(rec, columns=["pos", "NORAD_CAT_ID", "EPOCH", "n_tle", "e_tle"]); t.to_csv(CACHE, index=False)
print("PART B: bundle records for the 200 pilot objects:", len(t), "| objects:", t.NORAD_CAT_ID.nunique())
parts = []
for fp in sorted(pathlib.Path("data/raw/gp_history").glob("batch_*.json")):
    r = json.loads(fp.read_text())
    if r:
        g = pd.DataFrame(r)[["NORAD_CAT_ID", "EPOCH", "CREATION_DATE", "MEAN_MOTION"]]
        g["NORAD_CAT_ID"] = g.NORAD_CAT_ID.astype(int)
        for k in ("EPOCH", "CREATION_DATE"):
            try: g[k] = pd.to_datetime(g[k], format="ISO8601")   # robust to mixed fractional-second lengths
            except (ValueError, TypeError): g[k] = pd.to_datetime(g[k])
        g["MEAN_MOTION"] = pd.to_numeric(g.MEAN_MOTION, errors="coerce"); parts.append(g)
g = pd.concat(parts, ignore_index=True).sort_values("EPOCH")
m = pd.merge_asof(g, t.sort_values("EPOCH"), on="EPOCH", by="NORAD_CAT_ID", tolerance=pd.Timedelta("10ms"), direction="nearest")
m["found"] = m.pos.notna()
print("pilot gp rows", len(m), "| found in 2024 bundle:", round(float(m.found.mean()), 4))
print("  match rate by (epoch year, creation year):")
print(m.groupby([m.EPOCH.dt.year.rename("epoch_year"), m.CREATION_DATE.dt.year.rename("creation_year")]).found.agg(["size", "mean"]).round(4))
c24 = m[m.CREATION_DATE.dt.year == 2024]
print("bundle completeness for sets CREATED in 2024:", round(float(c24.found.mean()), 4), "| missing", int((~c24.found).sum()), "of", len(c24))

mm = m[m.found].sort_values("pos")
print("matched rows", len(mm), "| mean motion |tle - gp| median:", float((mm.MEAN_MOTION - mm.n_tle).abs().median()))
dc = mm.CREATION_DATE.diff().dt.total_seconds() / 3600
de = mm.EPOCH.diff().dt.total_seconds() / 3600
print("FILE ORDER among matched pilot rows (sparse sample, so only comparable across rows):")
print("  share of consecutive rows with EARLIER creation time:", round(float((dc < 0).mean()), 4),
      "| size of those inversions in hours, quantiles 50/90/99/max:", (-dc[dc < 0]).quantile([.5, .9, .99, 1]).round(1).tolist())
print("  share with earlier creation CALENDAR DATE:", round(float((mm.CREATION_DATE.dt.normalize().diff().dt.total_seconds() < 0).mean()), 4),
      "| earlier creation HOUR:", round(float((mm.CREATION_DATE.dt.floor("h").diff().dt.total_seconds() < 0).mean()), 4),
      "| earlier EPOCH:", round(float((de < 0).mean()), 4))
rk = lambda s_: s_.astype("int64").rank()
print("  Spearman rank correlation of file position with CREATION_DATE:", round(float(mm.pos.rank().corr(rk(mm.CREATION_DATE))), 4),
      "| with EPOCH:", round(float(mm.pos.rank().corr(rk(mm.EPOCH))), 4))

cand = pd.read_csv("data/frozen/candidates.csv", parse_dates=["DECAY"])[["NORAD_CAT_ID", "OBJECT_TYPE", "DECAY"]]
x = c24.merge(cand, on="NORAD_CAT_ID", how="left")
x["lag_h"] = (x.CREATION_DATE - x.EPOCH).dt.total_seconds() / 3600
x["dtd"] = (x.DECAY + pd.Timedelta(hours=12) - x.EPOCH).dt.total_seconds() / 86400
print("MISSING sets (created in 2024 but absent from the bundle): rate by")
for name, b in (("days to decay", pd.cut(x.dtd, [-1e9, 3, 14, 1e9], labels=["last 3 d", "3-14 d", ">14 d"])),
                ("class", x.OBJECT_TYPE), ("publication lag", pd.cut(x.lag_h, [-1e9, 12, 24, 72, 1e9], labels=["<=12h", "12-24h", "24-72h", ">72h"]))):
    print("  ", name, (~x.found).groupby(b, observed=True).mean().round(4).to_dict())
dup = x.duplicated(["NORAD_CAT_ID", "EPOCH"], keep=False)
print("  share of rows sharing an epoch with another row of the same object:", round(float(dup.mean()), 4),
      "| missing rate among them:", round(float((~x.found)[dup].mean()), 4) if dup.any() else "n/a")
