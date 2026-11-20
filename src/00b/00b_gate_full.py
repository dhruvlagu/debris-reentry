import sys, json, os
import numpy as np
import pandas as pd

L_H = float(sys.argv[1]) if len(sys.argv) > 1 else 24.0
NOCK0 = len(sys.argv) > 2 and sys.argv[2] == 'nock0'
tag = 'L%g%s' % (L_H, '_nock0' if NOCK0 else '')
if os.environ.get('DUPFILT'): tag += '_dupfilt'
RE, SIG_A, HOR, SEED = 6378.135, 0.2158, [30, 14, 7], 20261105
EDGE_FILE = 'results/0b_tercile_edges.json'
EP0 = pd.Timestamp('1970-01-01')

def find(cols, words):
    for c in cols:
        if all(w in c.lower() for w in words):
            return c
    return None

cand = pd.read_csv('data/frozen/candidates.csv', parse_dates=['DECAY'])
lf = pd.read_csv('results/0b_label_flags.csv')
c_int = find(cand.columns, ['intldes'])
c_mm = find(lf.columns, ['mismatch'])
c_sg = find(lf.columns, ['single'])
if not (c_int and c_mm and c_sg):
    sys.exit('column not found. candidates: %s | label flags: %s' % (list(cand.columns), list(lf.columns)))
print('using', c_int, c_mm, c_sg, '| L =', L_H, 'h | nock0 only:', NOCK0)

def tobool(s):
    return s.astype(str).str.lower().isin(['true', '1', '1.0'])
lf['mismatch'] = tobool(lf[c_mm]); lf['single'] = tobool(lf[c_sg])
cand = cand.merge(lf[['NORAD_CAT_ID', 'mismatch', 'single']], on='NORAD_CAT_ID', how='left')
cand[['mismatch', 'single']] = cand[['mismatch', 'single']].fillna(False).astype(bool)

def ckey(r):
    k = str(r[c_int])[:8]
    if k in ('1993-036', '1997-051'): return 'COLL2009'
    if k == '1998-067': return 'ISS%d' % r['NORAD_CAT_ID']
    return k
cand['cluster'] = cand.apply(ckey, axis=1)
cand = cand[(cand.DECAY >= '2015-01-01') & (cand.DECAY <= '2025-12-31')].copy()
cand['label_h'] = ((cand.DECAY.dt.normalize() + pd.Timedelta(hours=12)) - EP0) / pd.Timedelta(hours=1)
print('candidates in scope (decay 2015 to 2025):', len(cand))

def block(d):
    if pd.Timestamp('2015-01-01') <= d <= pd.Timestamp('2022-12-31'): return 'train'
    if pd.Timestamp('2023-01-31') <= d <= pd.Timestamp('2024-12-31'): return 'validation'
    if pd.Timestamp('2025-01-31') <= d <= pd.Timestamp('2025-12-31'): return 'test'
    return 'embargo'
cand['block'] = cand.DECAY.apply(block)

m = pd.read_csv(('data/frozen/tle_merged_dupfilt.csv' if os.environ.get('DUPFILT') else 'data/frozen/tle_merged.csv'), parse_dates=['EPOCH'],
                usecols=['NORAD_CAT_ID', 'EPOCH', 'SEMIMAJOR_AXIS', 'PERIAPSIS', 'APOAPSIS', 'NOCK'])
if NOCK0: m = m[m.NOCK == 0]
m = m.sort_values(['NORAD_CAT_ID', 'EPOCH']).reset_index(drop=True)
t_all = (m['EPOCH'] - EP0) / pd.Timedelta(hours=1)
t_all = t_all.values
a_all = m['SEMIMAJOR_AXIS'].values
e_all = ((m['APOAPSIS'] - m['PERIAPSIS']) / (m['APOAPSIS'] + m['PERIAPSIS'] + 2 * RE)).values
ids = m['NORAD_CAT_ID'].values
cut = np.flatnonzero(np.diff(ids)) + 1
starts = np.r_[0, cut]; ends = np.r_[cut, len(ids)]
span = {int(ids[s]): (s, e) for s, e in zip(starts, ends)}

def sig_a(aw):
    if len(aw) < 4: return False
    ab = (aw[1:] - np.minimum.accumulate(aw)[:-1]) > 5 * SIG_A
    run = 0
    for v in ab:
        run = run + 1 if v else 0
        if run >= 3: return True
    return False

rows = []
for r in cand.itertuples():
    base = dict(NORAD_CAT_ID=r.NORAD_CAT_ID)
    if r.NORAD_CAT_ID not in span:
        for H in HOR: rows.append(dict(base, H=H, has_set=False, n14=0))
        continue
    s, e_ = span[r.NORAD_CAT_ID]
    t, a, ee = t_all[s:e_], a_all[s:e_], e_all[s:e_]
    e_med = float(np.median(ee))
    j = np.searchsorted(t, r.label_h, side='right') - 1
    gap = r.label_h - t[j] if j >= 0 else np.nan
    A = np.nan
    if e_med <= 0.01:
        A = float(sig_a(a[t <= r.label_h - 72]))
    av = t + L_H
    for H in HOR:
        issue = r.label_h - 24 * H
        k = np.searchsorted(av, issue, side='right') - 1
        n14 = k + 1 - np.searchsorted(av, issue - 336, side='right')
        rows.append(dict(base, H=H, has_set=k >= 0, n14=int(max(n14, 0)),
                         alt=a[k] - RE if k >= 0 else np.nan, e_issue=ee[k] if k >= 0 else np.nan,
                         gap_h=gap, flagA=A, e_med=e_med))
R = pd.DataFrame(rows).merge(cand, on='NORAD_CAT_ID')

if os.path.exists(EDGE_FILE):
    edges = {int(k): v for k, v in json.load(open(EDGE_FILE)).items()}
    print('tercile edges loaded (frozen):', edges)
else:
    edges = {}
    for H in HOR:
        x = R[(R.H == H) & R.has_set]['alt']
        edges[H] = [float(x.quantile(1 / 3)), float(x.quantile(2 / 3))]
    json.dump({str(k): v for k, v in edges.items()}, open(EDGE_FILE, 'w'))
    print('tercile edges computed once and frozen:', edges)

c_size = find(R.columns, ['rcs'])
out = []
for H in HOR:
    X = R[R.H == H].copy()
    lo, hi = edges[H]
    X['band'] = np.where(X.alt <= lo, 'low', np.where(X.alt <= hi, 'mid', 'high'))
    print('\n===== horizon %d d (edges %.1f, %.1f km) =====' % (H, lo, hi))
    s1 = X[X.has_set]; s2 = s1[s1.n14 >= 3]; s3 = s2[~s2.mismatch]
    s4 = s3[~(s3.flagA == 1.0)]
    print('attrition: in scope %d | >=1 set %d | >=3 in 14 d %d | not label mismatch %d | not Signature A %d | A-unchecked (kept) %d'
          % (len(X), len(s1), len(s2), len(s3), len(s4), int(s4.flagA.isna().sum())))
    print('retention (>=3 sets) of objects with a set, by band:')
    print(s1.groupby('band')['n14'].apply(lambda v: (v >= 3).mean()).round(3).to_string())
    print('by class:')
    print(s1.groupby('OBJECT_TYPE')['n14'].apply(lambda v: (v >= 3).mean()).round(3).to_string())
    print('by block (>=3 sets share):')
    print(s1.groupby('block')['n14'].apply(lambda v: (v >= 3).mean()).round(3).to_string())
    Y = s4[s4.block != 'embargo']
    n_emb = len(s4) - len(Y)
    n_pre = len(Y)
    Y = Y.groupby('cluster', group_keys=False).apply(lambda g: g.sample(min(len(g), 30), random_state=SEED))
    print('embargo removed %d | before cap %d | cap removed %d | after %d' % (n_emb, n_pre, n_pre - len(Y), len(Y)))
    print('by block:', Y.block.value_counts().to_dict())
    print('by class:', Y.OBJECT_TYPE.value_counts().to_dict())
    print('by band:', Y.band.value_counts().to_dict())
    if c_size: print('by size:', Y[c_size].value_counts().to_dict())
    print('e at issue <= 0.01: %d | > 0.01: %d | single-source labels: %d'
          % ((Y.e_issue <= 0.01).sum(), (Y.e_issue > 0.01).sum(), Y.single.sum()))
    g = s3.gap_h.dropna()
    noise = np.maximum(12.0, 0.2 * g)
    frac = float((noise > 0.1 * H * 24).mean())
    print('label-noise gate: %.1f%% of objects over tolerance (%.1f h) -> %s | last set within 24 h of label: %d'
          % (100 * frac, 0.1 * H * 24, 'PASS' if frac <= 0.25 else 'FAIL', int((g <= 24).sum())))
    print('gap hours by class (median):', s3.groupby('OBJECT_TYPE').gap_h.median().round(1).to_dict())
    nt = int((Y.block == 'test').sum())
    print('threshold total %d vs 300 -> %s | test %d vs 100 -> %s' % (
        len(Y), 'PASS' if len(Y) >= 300 else 'FAIL', nt, 'PASS' if nt >= 100 else 'FAIL'))
    Y.to_csv('results/0b_gate_rows_H%d_%s.csv' % (H, tag), index=False)
print('\nwrote results/0b_gate_rows_H*_%s.csv' % tag)
