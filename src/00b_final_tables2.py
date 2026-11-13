import json
import pandas as pd

rows = []
for line in open('data/raw/Kp_ap_Ap_SN_F107_since_1932.txt'):
    if line.startswith('#') or not line.strip():
        continue
    tk = line.split()
    rows.append((pd.Timestamp(int(tk[0]), int(tk[1]), int(tk[2])), float(tk[25]), max(float(x) for x in tk[7:15])))
g = pd.DataFrame(rows, columns=['day', 'f107', 'kpmax']).set_index('day').loc['2014-10-01':'2026-09-30']
n_bad = int((g.f107 <= 0).sum())
g.loc[g.f107 <= 0, 'f107'] = float('nan')
print('F10.7 flag days set to missing:', n_bad, '| range now %.1f to %.1f' % (g.f107.min(), g.f107.max()))
print('block: mean F10.7 | share of days Kp>=6')
for nm, a, b in [('train', '2015-01-01', '2022-12-31'), ('validation', '2023-01-31', '2024-12-31'), ('test', '2025-01-31', '2025-12-31')]:
    s = g.loc[a:b]
    print('  %-10s %6.1f | %.3f' % (nm, s.f107.mean(), (s.kpmax >= 6).mean()))

d = json.load(open('data/raw/satcat_decayed.json'))
if isinstance(d, dict):
    d = next(v for v in d.values() if isinstance(v, list))
s = pd.DataFrame(d)
rc = [c for c in s.columns if 'rcs' in c.lower()]
print('SATCAT columns containing rcs:', rc)
if rc:
    s['NORAD_CAT_ID'] = s['NORAD_CAT_ID'].astype(int)
    size = s.set_index('NORAD_CAT_ID')['RCS_SIZE']
    for H in (30, 14):
        Y = pd.read_csv('results/0b_gate_rows_H%d_L24.csv' % H)
        Y['rcs'] = Y.NORAD_CAT_ID.map(size).fillna('MISSING')
        print('\nhorizon %d d, RCS size by class:' % H)
        print(pd.crosstab(Y.OBJECT_TYPE, Y.rcs, margins=True).to_string())
        print('RCS size by block:')
        print(pd.crosstab(Y.block, Y.rcs).to_string())
