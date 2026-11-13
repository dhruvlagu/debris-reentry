import glob
import numpy as np
import pandas as pd

RE, SIG = 6378.135, 0.2158
EP0 = pd.Timestamp('1970-01-01')

def ms(s):
    return (s.dt.round('ms') - EP0) // pd.Timedelta('1ms')

m = pd.read_csv('data/frozen/tle_merged.csv', parse_dates=['EPOCH'])
m['ms'] = ms(m['EPOCH'])
m['e'] = (m['APOAPSIS'] - m['PERIAPSIS']) / (m['APOAPSIS'] + m['PERIAPSIS'] + 2 * RE)
emed = m.groupby('NORAD_CAT_ID')['e'].median()
low = set(emed.index[emed <= 0.01])

d = pd.concat([pd.read_csv(f, parse_dates=['EPOCH']) for f in sorted(glob.glob('data/frozen/tle_parsed/tle20*.csv'))],
              ignore_index=True)
d = d[d['NOCK'] == 0].copy()
d['ms'] = ms(d['EPOCH'])
g = d.groupby(['NORAD_CAT_ID', 'ms'])['SEMIMAJOR_AXIS'].agg(['size', 'min', 'max']).reset_index()
g = g[g['size'] > 1]
g['spread'] = g['max'] - g['min']
bad = g[(g['spread'] > SIG) & g['NORAD_CAT_ID'].isin(low)]
print('near-circular duplicate groups over %.4f km: %d | objects %d | over 1 km: %d'
      % (SIG, len(bad), bad['NORAD_CAT_ID'].nunique(), (bad['spread'] > 1).sum()))
bk = set(zip(bad['NORAD_CAT_ID'], bad['ms']))
drop = np.array([k in bk for k in zip(m['NORAD_CAT_ID'], m['ms'])])
print('merged rows removed: %d of %d' % (drop.sum(), len(m)))
m.loc[~drop].drop(columns=['ms', 'e']).to_csv('data/frozen/tle_merged_dupfilt.csv', index=False)
bad.to_csv('results/0b_dup_excluded.csv', index=False)
print('wrote data/frozen/tle_merged_dupfilt.csv and results/0b_dup_excluded.csv')

for H in (30, 14):
    Y = pd.read_csv('results/0b_gate_rows_H%d_L24.csv' % H)
    t = Y[Y['gap_h'] <= 24]
    print('\n===== horizon %d d: tight-label subset (last set within 24 h of label), post-cap rows =====' % H)
    print(pd.crosstab(t['OBJECT_TYPE'], t['block'], margins=True).to_string())
    print('share of scored set that is tight-label: %.3f' % (len(t) / len(Y)))
