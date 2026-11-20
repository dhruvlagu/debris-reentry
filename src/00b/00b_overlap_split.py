import sys, collections
import pandas as pd

L5 = 'ABCDEFGHJKLMNPQRSTUVWXYZ'
def key_of(i):
    return '%05d' % i if i < 100000 else L5[i // 10000 - 10] + '%04d' % (i % 10000)

names = ['ndot', 'incl', 'raan', 'ecc', 'argp', 'mean_anom', 'mean_motion']
tol = [2.5e-8, 2.5e-4, 2.5e-4, 2.5e-7, 2.5e-4, 2.5e-4, 2.5e-8]
cand = pd.read_csv('data/frozen/candidates.csv')
keys = set(key_of(int(i)) for i in cand.NORAD_CAT_ID)

for y in sys.argv[1:]:
    S = {'normal': {}, 'short': {}}
    with open('data/raw/tle_bundles/%s/tle%s.txt' % (y, y), errors='replace', buffering=1 << 24) as f:
        while True:
            a = f.readline()
            if not a: break
            if a[0] != '1': continue
            b = f.readline()
            while b and b.strip(' \\\r\n') == '':
                b = f.readline()
            k5 = a[2:7].replace(' ', '0')
            if k5 not in keys: continue
            a = a.rstrip('\\\r\n '); b = b.rstrip('\\\r\n ')
            k = 'short' if len(a) == 68 else 'normal' if len(a) == 69 else None
            if k is None: continue
            if (k == 'short') != (len(b) == 68): continue
            try:
                v = (float(a[33:43]), float(b[8:16]), float(b[17:25]), float('0.' + b[26:33].strip()),
                     float(b[34:42]), float(b[43:51]), float(b[52:63]))
            except ValueError:
                continue
            S[k].setdefault((k5, a[18:32]), v)
    ov = set(S['normal']) & set(S['short'])
    rnd = 0; big = 0; fields = collections.Counter(); ex = []
    for key in ov:
        n_, s_ = S['normal'][key], S['short'][key]
        if n_ == s_: continue
        bad = [names[i] for i in range(7) if abs(n_[i] - s_[i]) > tol[i]]
        if not bad:
            rnd += 1
        else:
            big += 1
            fields.update(bad)
            if len(ex) < 3: ex.append((key, bad))
    print('%s | overlap %d | differ %d | rounding-level %d | large %d' % (y, len(ov), rnd + big, rnd, big))
    print('   fields in large mismatches:', dict(fields))
    for e in ex: print('   example:', e)
