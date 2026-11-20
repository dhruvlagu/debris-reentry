import glob
import pandas as pd

cand = pd.read_csv('data/frozen/candidates.csv', parse_dates=['DECAY'])
info = cand.set_index('NORAD_CAT_ID')[['OBJECT_TYPE', 'DECAY']]
parts = [pd.read_csv(f, parse_dates=['EPOCH']) for f in sorted(glob.glob('data/frozen/tle_parsed/tle20*.csv'))]
d = pd.concat(parts, ignore_index=True)
d = d[d['NOCK'] == 0].copy()
d['ms'] = (d['EPOCH'].dt.round('ms') - pd.Timestamp('1970-01-01')) // pd.Timedelta('1ms')
agg = d.groupby(['NORAD_CAT_ID', 'ms']).agg(n=('SEMIMAJOR_AXIS', 'size'), amin=('SEMIMAJOR_AXIS', 'min'),
                                            amax=('SEMIMAJOR_AXIS', 'max'), nsrc=('SRC', 'nunique'),
                                            epoch=('EPOCH', 'first')).reset_index()
agg = agg[agg['n'] > 1]
agg['spread'] = agg['amax'] - agg['amin']
big = agg[agg['spread'] > 0.2158].merge(info, left_on='NORAD_CAT_ID', right_index=True)
print('groups over 0.2158 km: %d | objects: %d | both copies in same bundle: %d | different bundles: %d'
      % (len(big), big['NORAD_CAT_ID'].nunique(), (big['nsrc'] == 1).sum(), (big['nsrc'] > 1).sum()))
print('by class:', big['OBJECT_TYPE'].value_counts().to_dict())
s = agg.loc[agg['spread'] > 0.001, 'spread']
print('spread quantiles 50/90/99 (groups over 0.001 km):', [round(s.quantile(q), 4) for q in (.5, .9, .99)])
print(big.sort_values('spread', ascending=False).head(10)[['NORAD_CAT_ID', 'epoch', 'OBJECT_TYPE', 'DECAY', 'amin', 'amax', 'n', 'nsrc']].to_string(index=False))

m = pd.read_csv('data/frozen/tle_merged.csv', usecols=['NORAD_CAT_ID', 'SEMIMAJOR_AXIS', 'NOCK'])
med = m.groupby('NORAD_CAT_ID')['SEMIMAJOR_AXIS'].transform('median')
out = (m['SEMIMAJOR_AXIS'] - med).abs() > 500
print('merged rows more than 500 km from their object median a: %d | objects: %d | by NOCK: %s'
      % (out.sum(), m.loc[out, 'NORAD_CAT_ID'].nunique(), m.loc[out].groupby('NOCK').size().to_dict()))
