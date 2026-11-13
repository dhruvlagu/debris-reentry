import sys
import numpy as np
import pandas as pd

TAG = sys.argv[1] if len(sys.argv) > 1 else 'L24'
HOR = [30, 14, 7]
EP0 = pd.Timestamp('1970-01-01')

recs = []
for line in open('data/raw/Kp_ap_Ap_SN_F107_since_1932.txt'):
    if line.startswith('#') or not line.strip():
        continue
    tk = line.split()
    if len(tk) != 28:
        sys.exit('unexpected column count %d in line: %s' % (len(tk), line[:120]))
    day = pd.Timestamp(int(tk[0]), int(tk[1]), int(tk[2]))
    for k in range(8):
        recs.append((day + pd.Timedelta(hours=3 * k), float(tk[7 + k]), int(float(tk[27]))))
kp = pd.DataFrame(recs, columns=['t', 'kp', 'D'])
kp = kp[(kp.t >= '2014-10-01') & (kp.t < '2026-10-01')].reset_index(drop=True)
kp['h'] = (kp.t - EP0) / pd.Timedelta(hours=1)
print('Kp rows %d | Kp missing (<0): %d | non-definitive D != 1 or 2 rows: %d'
      % (len(kp), (kp.kp < 0).sum(), (~kp.D.isin([1, 2])).sum()))
print('D value counts:', kp.D.value_counts().to_dict())

hi = kp[kp.kp >= 6].reset_index(drop=True)

def events(merge_h):
    ev = np.zeros(len(hi), dtype=int)
    cur = 0
    for i in range(1, len(hi)):
        if hi.h[i] - hi.h[i - 1] >= merge_h:
            cur += 1
        ev[i] = cur
    return ev
for mh in (12, 24, 48):
    hi['ev%d' % mh] = events(mh)
    print('storm events (Kp>=6 blocks merged within %d h) in 2015 to 2025: %d'
          % (mh, hi[(hi.t >= '2015-01-01') & (hi.t < '2026-01-01')]['ev%d' % mh].nunique()))

kh = kp.h.values; kk = kp.kp.values
hh = hi.h.values

def maxkp(a, b):
    m = (kh + 3 > a) & (kh < b)
    return kk[m].max() if m.any() else np.nan

def regime(v):
    return 'disturbed' if v >= 6 else 'moderate' if v >= 5 else 'quiet'

for H in HOR:
    Y = pd.read_csv('results/0b_gate_rows_H%d_%s.csv' % (H, TAG), parse_dates=['DECAY'])
    lab = ((Y.DECAY.dt.normalize() + pd.Timedelta(hours=12)) - EP0) / pd.Timedelta(hours=1)
    iss = lab - 24 * H
    Y['reg_win'] = [regime(maxkp(a, b)) for a, b in zip(iss, lab)]
    Y['reg_pre'] = [regime(maxkp(a - 72, a)) for a in iss]
    ev = []
    for a, b in zip(iss, lab):
        m = (hh + 3 > a) & (hh < b)
        ev.append(set(hi.loc[m, 'ev48'].tolist()))
    Y['events'] = ev
    print('\n===== horizon %d d (%s) =====' % (H, TAG))
    print('regime to decay by block:')
    print(pd.crosstab(Y.block, Y.reg_win, margins=True).to_string())
    print('regime in 3 days before issue:', Y.reg_pre.value_counts().to_dict())
    d = Y[Y.reg_win == 'disturbed']
    dt = d[d.block == 'test']
    storms_test = set().union(*dt.events.tolist()) if len(dt) else set()
    storms_all = set().union(*d.events.tolist()) if len(d) else set()
    print('disturbed overall %d vs 40 -> %s' % (len(d), 'PASS' if len(d) >= 40 else 'FAIL'))
    print('disturbed in test %d vs 15 -> %s' % (len(dt), 'PASS' if len(dt) >= 15 else 'FAIL'))
    print('distinct storm events in test disturbed windows: %d vs 3 -> %s'
          % (len(storms_test), 'PASS' if len(storms_test) >= 3 else 'FAIL'))
    print('distinct storm events across all disturbed windows:', len(storms_all))
    if len(dt):
        print('test disturbed objects per storm event (top 5):',
              pd.Series([e for s in dt.events for e in s]).value_counts().head(5).to_dict())
    g = Y.gap_h.dropna()
    frac = float((np.maximum(12.0, 0.2 * g) > 0.1 * H * 24).mean())
    print('gate on post-cap rows: %.1f%% over tolerance (limit 25%%)' % (100 * frac))
