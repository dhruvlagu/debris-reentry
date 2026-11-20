import glob, json, sys
import pandas as pd, numpy as np

HOR = [30, 14, 7]
LAG = pd.Timedelta(hours=24)
EP0 = pd.Timestamp('1970-01-01')

def ms(s):
    return (s.dt.round('ms') - EP0) // pd.Timedelta('1ms')

def pick(cols, keys, what):
    for c in cols:
        if any(k in c.upper() for k in keys):
            return c
    sys.exit('no %s column; columns are: %s' % (what, list(cols)))

cp = glob.glob('**/candidates.csv', recursive=True)
if not cp:
    sys.exit('candidates.csv not found')
print('candidates file:', cp[0])
cand = pd.read_csv(cp[0])
c_id = pick(cand.columns, ['NORAD', 'OBJECT_NUMBER'], 'id')
c_dec = [c for c in cand.columns if 'DECAY' in c.upper() and 'MSG' not in c.upper()]
if not c_dec:
    sys.exit('no decay column; columns are: %s' % list(cand.columns))
c_dec = c_dec[0]
c_cls = pick(cand.columns, ['OBJECT_TYPE', 'CLASS'], 'class')
print('using id=%s decay=%s class=%s' % (c_id, c_dec, c_cls))
cand = cand[[c_id, c_dec, c_cls]].copy()
cand.columns = ['id', 'decay', 'cls']
cand['id'] = cand['id'].astype(int)
cand['label'] = pd.to_datetime(cand['decay']).dt.normalize() + pd.Timedelta(hours=12)

rows = []
for f in sorted(glob.glob('data/raw/gp_history/batch_*.json')):
    d = json.load(open(f))
    if isinstance(d, dict):
        d = list(d.values())[0] if len(d) == 1 else [d]
    rows += d
gp = pd.DataFrame(rows)
for need in ['NORAD_CAT_ID', 'EPOCH', 'CREATION_DATE']:
    if need not in gp.columns:
        sys.exit('gp field missing %s; fields: %s' % (need, list(gp.columns)))
gp['id'] = gp['NORAD_CAT_ID'].astype(int)
gp['epoch'] = pd.to_datetime(gp['EPOCH'])
gp['created'] = pd.to_datetime(gp['CREATION_DATE'])
gp = gp.drop_duplicates(['id', 'epoch'], keep='first')
truth = gp[gp['created'].dt.year == 2024].copy()
print('gp rows %d | created in 2024: %d' % (len(gp), len(truth)))

b = pd.read_csv('data/frozen/tle2024_pilot_records.csv', parse_dates=['EPOCH'])
b = b.rename(columns={'NORAD_CAT_ID': 'id', 'EPOCH': 'epoch'})
b = b.drop_duplicates(['id', 'epoch'], keep='first')
bkeys = set(zip(b['id'].astype(int), ms(b['epoch'])))
truth['k'] = list(zip(truth['id'], ms(truth['epoch'])))
bund = truth[truth['k'].isin(bkeys)].copy()
print('truth sets %d | present in bundle %d (%.4f)' % (len(truth), len(bund), len(bund) / len(truth)))

objs = cand[cand['id'].isin(truth['id'].unique())].copy()

def metrics(sets):
    g = {k: v['epoch'].values for k, v in sets.groupby('id')}
    out = []
    for r in objs.itertuples():
        ep = pd.to_datetime(g.get(r.id, np.array([], dtype='datetime64[ns]')))
        av = ep + LAG
        rec = {'id': r.id, 'cls': r.cls}
        for h in HOR:
            issue = r.label - pd.Timedelta(days=h)
            rec['n%d' % h] = int(((av > issue - pd.Timedelta(days=14)) & (av <= issue)).sum())
        pre = ep[ep <= r.label]
        rec['gap_h'] = (r.label - pre.max()).total_seconds() / 3600 if len(pre) else np.nan
        out.append(rec)
    return pd.DataFrame(out).set_index('id')

T = metrics(truth)
B = metrics(bund)
res = []
for h in HOR:
    for cls in list(T['cls'].unique()) + ['ALL']:
        m = (T['cls'] == cls) if cls != 'ALL' else (T['cls'] == T['cls'])
        t, bb = T.loc[m, 'n%d' % h], B.loc[m, 'n%d' % h]
        res.append({'h': h, 'cls': cls, 'objs': int(m.sum()),
                    'pass_truth': int((t >= 3).sum()), 'pass_bundle': int((bb >= 3).sum()),
                    'flipped': int(((t >= 3) & (bb < 3)).sum()),
                    'exact3_truth': int((t == 3).sum()), 'exact3_bundle': int((bb == 3).sum())})
R = pd.DataFrame(res)
print(R.to_string(index=False))
d = (B['gap_h'] - T['gap_h']).dropna()
print('last-gap hours: truth median %.2f | bundle median %.2f | objects changed >1 h: %d of %d | max increase %.1f h'
      % (T['gap_h'].median(), B['gap_h'].median(), int((d.abs() > 1).sum()), len(d), d.max()))
print('objects with no sets: truth %d, bundle %d' % (int(T['gap_h'].isna().sum()), int(B['gap_h'].isna().sum())))
R.to_csv('results/0b_bundle_bias.csv', index=False)
