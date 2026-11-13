import glob
import numpy as np
import pandas as pd

SIG_A = 0.2158
K = 5.0

fs = sorted(glob.glob('data/frozen/tle_parsed/tle20*.csv'))
print('files:', [f.split('/')[-1] for f in fs])
parts = []
for i, f in enumerate(fs):
    d = pd.read_csv(f, parse_dates=['EPOCH'])
    d['order'] = i
    parts.append(d)
df = pd.concat(parts, ignore_index=True)
n0 = len(df)
df['ms'] = (df['EPOCH'].dt.round('ms') - pd.Timestamp('1970-01-01')) // pd.Timedelta('1ms')

df = df.sort_values(['NORAD_CAT_ID', 'ms', 'NOCK', 'order'], kind='mergesort')
dup = df.duplicated(['NORAD_CAT_ID', 'ms'], keep='first')
print('rows read %d | duplicates dropped %d | kept %d' % (n0, dup.sum(), (~dup).sum()))
print('duplicates by dropped NOCK flag:', df.loc[dup, 'NOCK'].value_counts().to_dict())
df = df[~dup].sort_values(['NORAD_CAT_ID', 'EPOCH']).reset_index(drop=True)

def jump(g):
    a = g['SEMIMAJOR_AXIS'].values
    t = (g['EPOCH'] - g['EPOCH'].iloc[0]).dt.total_seconds().values / 86400.0
    out = np.zeros(len(a), dtype=bool)
    for i in range(len(a)):
        lo, hi = max(0, i - 2), min(len(a), i + 3)
        idx = [j for j in range(lo, hi) if j != i]
        if len(idx) < 3:
            continue
        p = np.polyfit(t[idx], a[idx], 1)
        out[i] = abs(a[i] - np.polyval(p, t[i])) > K * SIG_A
    return pd.Series(out, index=g.index)

df['flag_jump'] = np.concatenate([jump(g).values for _, g in df.groupby('NORAD_CAT_ID', sort=True)])
print('flag_jump rate by NOCK (0 = checksum-valid, 1 = short):')
print(df.groupby('NOCK')['flag_jump'].agg(['size', 'sum', 'mean']).to_string())

df.drop(columns=['ms', 'order']).to_csv('data/frozen/tle_merged.csv', index=False)
print('wrote data/frozen/tle_merged.csv rows', len(df), '| objects', df['NORAD_CAT_ID'].nunique())
print('rows per bundle year (SRC):')
print(df.groupby('SRC').size().to_string())
