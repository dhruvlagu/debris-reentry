"""Step 0B, stage 2. Modes: candidates | decay | pilot | full
UNTESTED against live Space-Track. Verify field names against current docs.
Space-Track rules: gp_history and decay are download-once-and-store. NEVER delete data/raw/.
Config below holds the post-count clarifications (log them in the notebook with today's date).
"""
import os, sys, json, time, hashlib, pathlib, importlib.util
import requests, pandas as pd

ST = "https://www.space-track.org"
SEED = 20261105
PARENT_CAP_PREPULL = 100          # pre-pull safety cap per cluster; the analysis cap (30) is applied after all filters
EXEMPT_PARENTS = {"1998-067"}     # ISS-deployed objects: unrelated deployments, each its own cluster
MERGE = {"1993-036": "2009COLL", "1997-051": "2009COLL"}  # Cosmos 2251 + Iridium 33, one collision
HISTORY_DAYS = 90                 # days before decay; fixed because gp_history is download-once
PILOT_N = 200
PILOT_WINDOW = ("2024-01-01", "2024-03-31")  # dense in decay time so batches are full (few requests); a feasibility pilot, not a result set
PILOT_MAX_REQUESTS = 20
BATCH_MAX, BATCH_SPAN_DAYS = 40, 14
SLEEP_S, HOURLY_MAX = 3, 250

RAW = pathlib.Path("data/raw"); HIST = RAW / "gp_history"; HIST.mkdir(parents=True, exist_ok=True)
FROZEN = pathlib.Path("data/frozen"); FROZEN.mkdir(parents=True, exist_ok=True)
RES = pathlib.Path("results"); RES.mkdir(exist_ok=True)

spec = importlib.util.spec_from_file_location("c", "src/00b_counts.py")
c = importlib.util.module_from_spec(spec); spec.loader.exec_module(c)


def sha(p): return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def login():
    s = requests.Session()
    r = s.post(f"{ST}/ajaxauth/login", data={"identity": os.environ["ST_USER"], "password": os.environ["ST_PASS"]})
    r.raise_for_status(); return s


def build_candidates():
    sat = pd.read_json(RAW / "satcat_decayed.json")
    kept = c.filter_satcat(sat).copy()
    kept["parent"] = kept["INTLDES"].astype(str).str[:8]
    kept["cluster"] = kept["parent"].map(MERGE).fillna(kept["parent"])
    parts = []
    for cl, g in kept.groupby("cluster"):
        parts.append(g if (cl in EXEMPT_PARENTS or len(g) <= PARENT_CAP_PREPULL)
                     else g.sample(PARENT_CAP_PREPULL, random_state=SEED))
    cand = pd.concat(parts).sort_values("DECAY")
    cand = cand[["NORAD_CAT_ID", "OBJECT_NAME", "OBJECT_TYPE", "INTLDES", "parent", "cluster", "DECAY"]]
    p = FROZEN / "candidates.csv"; cand.to_csv(p, index=False)
    info = {"after_filters": len(kept), "candidates": len(cand), "clusters": int(cand.cluster.nunique()),
            "by_type": cand.OBJECT_TYPE.value_counts().to_dict(), "seed": SEED,
            "cap": PARENT_CAP_PREPULL, "sha256": sha(p)}
    (RES / "0b_candidates.json").write_text(json.dumps(info, indent=2)); print(json.dumps(info, indent=2))


def load_cand():
    d = pd.read_csv(FROZEN / "candidates.csv", parse_dates=["DECAY"]); return d


def pull_decay():
    p = RAW / "decay_msgs.json"
    if p.exists(): print("decay file exists, not re-pulling:", sha(p)); return
    s = login()
    r = s.get(f"{ST}/basicspacedata/query/class/decay/DECAY_EPOCH/2015-01-01--2026-09-30/orderby/NORAD_CAT_ID asc/format/json", timeout=300)
    r.raise_for_status(); p.write_bytes(r.content)
    d = pd.read_json(p); print("rows", len(d), "sha256", sha(p), "columns", list(d.columns))


def make_batches(df):
    batches, cur = [], []
    for _, r in df.sort_values("DECAY").iterrows():
        if cur and (len(cur) >= BATCH_MAX or (r.DECAY - cur[0].DECAY).days > BATCH_SPAN_DAYS):
            batches.append(cur); cur = []
        cur.append(r)
    if cur: batches.append(cur)
    return batches


def pull_history(objs, max_req=None):
    dp = HIST / "completed.json"
    done = set(json.loads(dp.read_text())) if dp.exists() else set()
    todo = objs[~objs.NORAD_CAT_ID.isin(done)]
    batches = make_batches(todo); print(len(todo), "objects,", len(batches), "requests planned")
    if not batches: return
    if max_req and len(batches) > max_req:
        print("ABORT: planned requests exceed the cap of", max_req); return
    if input("Type yes to start the download (each object can only be downloaded once): ").strip() != "yes":
        print("cancelled"); return
    s = login(); sent = []
    for b in batches:
        ids = [int(r.NORAD_CAT_ID) for r in b]
        lo = (min(r.DECAY for r in b) - pd.Timedelta(days=HISTORY_DAYS)).date()
        hi = (max(r.DECAY for r in b) + pd.Timedelta(days=2)).date()
        now = time.time(); sent = [t for t in sent if now - t < 3600]
        if len(sent) >= HOURLY_MAX: time.sleep(3600 - (now - sent[0]) + 5)
        url = (f"{ST}/basicspacedata/query/class/gp_history/NORAD_CAT_ID/{','.join(map(str, ids))}"
               f"/EPOCH/{lo}--{hi}/orderby/NORAD_CAT_ID asc,EPOCH asc/format/json")
        r = s.get(url, timeout=300); sent.append(time.time())
        try: rows = json.loads(r.content)
        except Exception: rows = None
        if r.status_code != 200 or not isinstance(rows, list):
            print("STOP: HTTP", r.status_code, r.text[:300]); return   # no blind retries
        (HIST / f"batch_{ids[0]}_{ids[-1]}_{lo}.json").write_bytes(r.content)
        done |= set(ids); dp.write_text(json.dumps(sorted(done)))
        time.sleep(SLEEP_S)
    print("pull complete")


def summarize(objs):
    cols, parts = ["NORAD_CAT_ID", "EPOCH", "CREATION_DATE"], []
    for f in sorted(HIST.glob("batch_*.json")):  # one file at a time, keep 3 columns only (memory)
        rows = json.loads(f.read_text())
        if not rows: continue
        df = pd.DataFrame(rows)
        for col in cols:
            if col not in df.columns: print("MISSING COLUMN", col, "have", list(df.columns)); return
        parts.append(df[cols]); del rows, df
    if not parts: print("no rows"); return
    h = pd.concat(parts, ignore_index=True)
    h["NORAD_CAT_ID"] = h.NORAD_CAT_ID.astype(int)
    h["EPOCH"] = pd.to_datetime(h.EPOCH); h["CREATION_DATE"] = pd.to_datetime(h.CREATION_DATE)
    g = {k: v for k, v in h.groupby("NORAD_CAT_ID")}
    out = {"objects": len(objs), "zero_rows": 0, "rows_median": None, "pass_3rec_14d_by_horizon": {}}
    counts = []; ok = {H: 0 for H in (30, 14, 7, 3, 1)}
    for _, o in objs.iterrows():
        x = g.get(int(o.NORAD_CAT_ID)); n = 0 if x is None else len(x); counts.append(n)
        if n == 0: out["zero_rows"] += 1; continue
        for H in ok:
            issue = o.DECAY - pd.Timedelta(days=H)
            w = x[(x.CREATION_DATE <= issue) & (x.CREATION_DATE > issue - pd.Timedelta(days=14))]
            ok[H] += int(len(w) >= 3)
    out["rows_median"] = float(pd.Series(counts).median())
    out["pass_3rec_14d_by_horizon"] = {H: round(v / len(objs), 3) for H, v in ok.items()}
    out["note"] = "PREVIEW only: SATCAT decay is date-only; formal count needs decay-class time and altitude bands"
    (RES / "0b_pilot_summary.json").write_text(json.dumps(out, indent=2)); print(json.dumps(out, indent=2))


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode == "candidates": build_candidates()
    elif mode == "decay": pull_decay()
    elif mode in ("pilot", "full"):
        cand = load_cand()
        if mode == "pilot":
            w = cand[(cand.DECAY >= PILOT_WINDOW[0]) & (cand.DECAY <= PILOT_WINDOW[1])]
            objs = w.sample(min(PILOT_N, len(w)), random_state=SEED); objs.to_csv(FROZEN / "pilot_ids.csv", index=False)
            print("pilot window", PILOT_WINDOW, "candidates in window", len(w), "pilot objects", len(objs))
            pull_history(objs, max_req=PILOT_MAX_REQUESTS)
        else:
            objs = cand; pull_history(objs)
        summarize(objs)
    else: print("usage: python3 src/00b_stage2.py candidates|decay|pilot|full")
