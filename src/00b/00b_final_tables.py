import numpy as np
import pandas as pd

cand = pd.read_csv('data/frozen/candidates.csv', parse_dates=['DECAY'])
cand = cand[(cand.DECAY >= '2015-01-01') & (cand.DECAY <= '2025-12-31')]
in_cls = cand.OBJECT_TYPE.value_counts()
in_yr = cand.groupby(cand.DECAY.dt.year).size()

rows = []
for line in open('data/raw/Kp_ap_Ap_SN_F107_since_1932.txt'):
    if line.startswith('#') or not line.strip():
        continue
    tk = line.split()
    rows.append((pd.Timestamp(int(tk[0]), int(tk[1]), int(tk[2])), float(tk[25]), max(float(x) for x in tk[7:15])))
g = pd.DataFrame(rows, columns=['day', 'f107', 'kpmax']).set_index('day').loc['2014-10-01':'2026-09-30']
print('F10.7 range %.1f to %.1f (sanity: about 60 to 300)' % (g.f107.min(), g.f107.max()))
print('solar-cycle check by block, calendar days: mean F10.7 | share of days with Kp>=6')
for nm, a, b in [('train', '2015-01-01', '2022-12-31'), ('validation', '2023-01-31', '2024-12-31'), ('test', '2025-01-31', '2025-12-31')]:
    s = g.loc[a:b]
    print('  %-10s %6.1f | %.3f' % (nm, s.f107.mean(), (s.kpmax >= 6).mean()))

for H in (30, 14):
    Y = pd.read_csv('results/0b_gate_rows_H%d_L24.csv' % H, parse_dates=['DECAY'])
    Y['f107w'] = [g.f107.loc[d - pd.Timedelta(days=H):d].mean() for d in Y.DECAY]
    print('\n===== horizon %d d =====' % H)
    print('scored share of in-scope candidates, by class:', (Y.OBJECT_TYPE.value_counts() / in_cls).round(3).to_dict())
    yr = pd.DataFrame({'in_scope': in_yr, 'scored': Y.groupby(Y.DECAY.dt.year).size()}).fillna(0)
    yr['share'] = (yr.scored / yr.in_scope).round(3)
    print(yr.to_string())
    print('median sets in 14 d before issue and median gap to label (h), by class:')
    print(Y.groupby('OBJECT_TYPE')[['n14', 'gap_h']].median().round(1).to_string())
    print('window-mean F10.7 by block (median):', Y.groupby('block').f107w.median().round(1).to_dict())
    print('eccentric share (e at issue > 0.01) by class:', Y.groupby('OBJECT_TYPE').e_issue.apply(lambda v: round((v > 0.01).mean(), 3)).to_dict())
    print('eccentric share by block:', Y.groupby('block').e_issue.apply(lambda v: round((v > 0.01).mean(), 3)).to_dict())
    t = Y[Y.block == 'test']
    wk = t.DECAY.dt.to_period('W').value_counts()
    print('test: %d objects | %d distinct decay weeks | max in one week %d | %d clusters | max in one cluster %d'
          % (len(t), len(wk), wk.max(), t.cluster.nunique(), t.cluster.value_counts().max()))
