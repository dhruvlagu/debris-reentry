import glob
import pandas as pd

cand = pd.read_csv('data/frozen/candidates.csv', parse_dates=['DECAY'])
m = pd.read_csv('data/frozen/tle_merged.csv', usecols=['NORAD_CAT_ID'])
have = set(m['NORAD_CAT_ID'].unique())
cand['has_sets'] = cand['NORAD_CAT_ID'].isin(have)
cand['yr'] = cand['DECAY'].dt.year
print('candidates with no merged sets, by decay year and class:')
miss = cand[~cand['has_sets']]
print(pd.crosstab(miss['yr'], miss['OBJECT_TYPE'], margins=True).to_string())
print('share with no sets, by decay year:')
print(cand.groupby('yr')['has_sets'].mean().round(3).to_string())

parts = [pd.read_csv(f, parse_dates=['EPOCH']) for f in sorted(glob.glob('data/frozen/tle_parsed/tle20*.csv'))]
d = pd.concat(parts, ignore_index=True)
d = d[d['NOCK'] == 0]
d['ms'] = (d['EPOCH'].dt.round('ms') - pd.Timestamp('1970-01-01')) // pd.Timedelta('1ms')
g = d.groupby(['NORAD_CAT_ID', 'ms'])['SEMIMAJOR_AXIS']
n = g.transform('size')
dd = d[n > 1].copy()
spread = dd.groupby(['NORAD_CAT_ID', 'ms'])['SEMIMAJOR_AXIS'].agg(lambda s: s.max() - s.min())
print('checksum-valid duplicate groups: %d | spread in a > 0.001 km: %d | > 0.2158 km: %d | max %.3f km'
      % (len(spread), (spread > 0.001).sum(), (spread > 0.2158).sum(), spread.max()))
