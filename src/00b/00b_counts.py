"""Step 0B, stage 1: SATCAT decays, exclusion counts, Kp regimes, storm events.

UNTESTED against live services. Verify Space-Track class/field names and the
GFZ file layout against current documentation before trusting any output.
Space-Track terms: raw data is gitignored, never redistributed.
Usage: ST_USER=... ST_PASS=... python 00b_counts.py
"""
import os, re, json, time, hashlib, pathlib
import requests
import pandas as pd

ST = "https://www.space-track.org"
START, END = "2015-01-01", "2026-09-30"  # Kp definitive through this date (D=0 begins 2026-10-01)
RAW = pathlib.Path("data/raw"); RAW.mkdir(parents=True, exist_ok=True)
LOG = {}  # every exclusion is counted here

# FIXED BEFORE COUNTING: lock this list in PREREG.md first.
CUBESAT_FLEETS = re.compile(r"FLOCK|LEMUR|DOVE|SPACEBEE", re.I)  # main rule excludes; Test Plan C alternative includes
CONSTELLATION = re.compile(
    r"STARLINK|ONEWEB|IRIDIUM|GLOBALSTAR|ORBCOMM|KUIPER|GUOWANG|QIANFAN", re.I)


def sha256(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def st_login():
    s = requests.Session()
    r = s.post(f"{ST}/ajaxauth/login",
               data={"identity": os.environ["ST_USER"],
                     "password": os.environ["ST_PASS"]})
    r.raise_for_status()
    return s


def pull_satcat(s):
    p = RAW / "satcat_decayed.json"
    if p.exists():  # raw files are never overwritten; reuse the frozen pull
        return pd.read_json(p), sha256(p)
    url = (f"{ST}/basicspacedata/query/class/satcat/"
           f"DECAY/{START}--{END}/orderby/NORAD_CAT_ID asc/format/json")
    r = s.get(url); r.raise_for_status()
    p = RAW / "satcat_decayed.json"; p.write_bytes(r.content)
    time.sleep(3)  # respect rate limits
    return pd.read_json(p), sha256(p)


def step(name, df):
    LOG[name] = int(len(df)); return df


def filter_satcat(df):
    df = step("1_all_decayed_2015_2026", df)
    df["DECAY"] = pd.to_datetime(df["DECAY"], errors="coerce")
    df = step("2_valid_decay_date", df.dropna(subset=["DECAY"]))
    df = df[df["OBJECT_TYPE"].isin(["PAYLOAD", "ROCKET BODY", "DEBRIS", "UNKNOWN"])]
    df = step("3_object_type_kept", df)
    names = df["OBJECT_NAME"].fillna("")
    for rx in (CONSTELLATION, CUBESAT_FLEETS):  # per-pattern matches, split by object type
        for pat in rx.pattern.split("|"):
            hit = names.str.contains(pat, case=False)
            LOG[f"4_match_{pat}_by_type"] = df[hit].OBJECT_TYPE.value_counts().to_dict()
    # Name filter applies to PAYLOAD only: breakup debris named after a fleet is uncontrolled and in scope.
    fleet = (names.str.contains(CONSTELLATION) | names.str.contains(CUBESAT_FLEETS)) & (df["OBJECT_TYPE"] == "PAYLOAD")
    LOG["4_excluded_fleet_payloads"] = int(fleet.sum())
    df = step("4_not_fleet_payload", df[~fleet])
    # Maneuver signature and controlled-decay flags need gp_history (stage 2).
    return df


def load_kp(path="data/raw/Kp_ap_Ap_SN_F107_since_1932.txt"):
    cols = (["y", "m", "d", "days", "days_m", "bsr", "db"]
            + [f"kp{i}" for i in range(1, 9)] + [f"ap{i}" for i in range(1, 9)]
            + ["Ap", "SN", "f107obs", "f107adj", "D"])
    k = pd.read_csv(path, sep=r"\s+", comment="#", names=cols)
    k["date"] = pd.to_datetime(dict(year=k.y, month=k.m, day=k.d))
    rows = []
    for i in range(8):  # 3-hour blocks; file gives Kp in decimal thirds
        t = k["date"] + pd.Timedelta(hours=3 * i)
        rows.append(pd.DataFrame({"t": t, "kp": k[f"kp{i+1}"]}))
    return pd.concat(rows).sort_values("t").reset_index(drop=True)


def storm_events(kp, thresh=6.0, merge_hours=48):
    """Distinct events: Kp>=thresh blocks closer than merge_hours merge. Locked: 48h primary; 12h and 24h reported as sensitivity."""
    hi = kp[kp.kp >= thresh].t.reset_index(drop=True)
    if hi.empty: return []
    ev, s, last = [], hi[0], hi[0]
    for t in hi[1:]:
        if (t - last) > pd.Timedelta(hours=merge_hours):
            ev.append((s, last)); s = t
        last = t
    ev.append((s, last)); return ev


def regime(kp, t0, t1):
    mx = kp[(kp.t >= t0) & (kp.t < t1)].kp.max()
    return "disturbed" if mx >= 6 else "moderate" if mx >= 5 else "quiet"


if __name__ == "__main__":
    s = None if (RAW / "satcat_decayed.json").exists() else st_login()
    sat, h = pull_satcat(s)
    kept = filter_satcat(sat)
    LOG["satcat_sha256"] = h
    kp = load_kp()
    for gap in (12, 24, 48):
        ev = storm_events(kp[(kp.t >= START)], merge_hours=gap)
        LOG[f"storm_events_by_year_gap{gap}h"] = pd.Series([e[0].year for e in ev]).value_counts().sort_index().to_dict()
    LOG["kp6_blocks_by_year"] = kp[(kp.kp >= 6) & (kp.t >= START)].t.dt.year.value_counts().sort_index().to_dict()
    kept["parent"] = kept["INTLDES"].astype(str).str[:8]  # launch id: breakup debris shares it
    LOG["distinct_parents_all"] = int(kept.parent.nunique())
    LOG["distinct_parents_debris"] = int(kept[kept.OBJECT_TYPE == "DEBRIS"].parent.nunique())
    LOG["top10_parents_by_decays"] = kept.parent.value_counts().head(10).to_dict()
    pc = kept.parent.value_counts()
    for cap in (10, 30, 50):
        LOG[f"total_if_capped_{cap}_per_parent"] = int(pc.clip(upper=cap).sum())
    kept["decay_year"] = kept["DECAY"].dt.year
    LOG["kept_by_year"] = kept["decay_year"].value_counts().sort_index().to_dict()
    LOG["kept_by_type"] = kept["OBJECT_TYPE"].value_counts().to_dict()
    pathlib.Path("results").mkdir(exist_ok=True)
    pathlib.Path("results/0b_stage1.json").write_text(json.dumps(LOG, indent=2, default=str))
    print(json.dumps(LOG, indent=2, default=str))
