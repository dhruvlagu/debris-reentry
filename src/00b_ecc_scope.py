import glob
import numpy as np
import pandas as pd

RE = 6378.135
cand = pd.read_csv('data/frozen/candidates.csv')
cls = cand.set_index('NORAD_CAT_ID')['OBJECT_TYPE']
m = pd.read_csv('data/frozen/tle_merged.csv',
                usecols=['NORAD_CAT_ID', 'SEMIMAJOR_AXIS', 'PERIAPSIS', 'APOAPSIS', 'NOCK', 'flag_jump'])
m['e'] = (m['APOAPSIS'] - m['PERIAPSIS']) / (m['APOAPSIS'] + m['PERIAPSIS'] + 2 * RE)
ob = m.groupby('NORAD_CAT_ID').agg(e_med=('e', 'median'), apo_max=('APOAPSIS', 'max'), n=('e', 'size'))
ob['cls'] = cls.reindex(ob.index).values
ob['ebin'] = pd.cut(ob['e_med'], [-1, 0.01, 0.05, 0.1, 0.3, 1.0], labels=['<=0.01', '0.01-0.05', '0.05-0.1', '0.1-0.3', '>0.3'])
print('objects by median eccentricity and class:')
print(pd.crosstab(ob['ebin'], ob['cls'], margins=True).to_string())
print('objects with max apogee altitude above 2000 km:', int((ob['apo_max'] > 2000).sum()), 'of', len(ob))

med = m.groupby('NORAD_CAT_ID')['SEMIMAJOR_AXIS'].transform('median')
out = (m['SEMIMAJOR_AXIS'] - med).abs() > 500
oo = ob.loc[m.loc[out, 'NORAD_CAT_ID'].unique()]
print('500 km outlier objects: %d | by ecc bin: %s' % (len(oo), oo['ebin'].value_counts().sort_index().to_dict()))

parts = [pd.read_csv(f, parse_dates=['EPOCH']) for f in sorted(glob.glob('data/frozen/tle_parsed/tle20*.csv'))]
d = pd.concat(parts, ignore_index=True)
d = d[d['NOCK'] == 0].copy()
d['ms'] = (d['EPOCH'].dt.round('ms') - pd.Timestamp('1970-01-01')) // pd.Timedelta('1ms')
g = d.groupby(['NORAD_CAT_ID', 'ms'])['SEMIMAJOR_AXIS'].agg(['size', 'min', 'max']).reset_index()
g = g[g['size'] > 1]
g['spread'] = g['max'] - g['min']
big = g[g['spread'] > 0.2158].join(ob['ebin'], on='NORAD_CAT_ID')
print('duplicate groups over 0.2158 km: %d | by ecc bin: %s' % (len(big), big['ebin'].value_counts().sort_index().to_dict()))
low = ob.index[ob['e_med'] <= 0.01]
gl = g[g['NORAD_CAT_ID'].isin(low)]
print('near-circular objects (e<=0.01): duplicate groups %d | spread >0.2158 km: %d | >1 km: %d | max %.3f km'
      % (len(gl), (gl['spread'] > 0.2158).sum(), (gl['spread'] > 1).sum(), gl['spread'].max()))
nc = m[m['NORAD_CAT_ID'].isin(low)]
print('near-circular jump-flag rate by NOCK:')
print(nc.groupby('NOCK')['flag_jump'].agg(['size', 'sum', 'mean']).to_string())
