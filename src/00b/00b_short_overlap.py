import sys, collections
import pandas as pd
L5 = 'ABCDEFGHJKLMNPQRSTUVWXYZ'
def key_of(i):
    return '%05d' % i if i < 100000 else L5[i // 10000 - 10] + '%04d' % (i % 10000)
cand = pd.read_csv('data/frozen/candidates.csv')
cls = set(key_of(int(i)) for i in cand.NORAD_CAT_ID)
for y in sys.argv[1:]:
    S = {'normal': {}, 'short': {}}
    with open('data/raw/tle_bundles/%s/tle%s.txt' % (y, y), errors='replace', buffering=1 << 24) as f:
        while True:
            a = f.readline()
            if not a: break
            if a[0] != '1': continue
            b = f.readline()
            k5 = a[2:7].replace(' ', '0')
            if k5 not in cls: continue
            a = a.rstrip('\\\r\n '); b = b.rstrip('\\\r\n ')
            k = 'short' if len(a) == 68 else 'normal' if len(a) == 69 else None
            if k is None: continue
            if k == 'short' and len(b) != 68: continue
            if k == 'normal' and len(b) != 69: continue
            try:
                v = (float(a[33:43]), float(b[8:16]), float(b[17:25]), float('0.' + b[26:33].strip()),
                     float(b[34:42]), float(b[43:51]), float(b[52:63]))
            except ValueError:
                continue
            S[k].setdefault((k5, a[18:32]), v)
    ov = set(S['normal']) & set(S['short'])
    same = sum(1 for k in ov if S['normal'][k] == S['short'][k])
    print('%s | normal %d | short %d | overlap %d | identical %d (%.2f%%)' % (
        y, len(S['normal']), len(S['short']), len(ov), same, 100.0 * same / max(1, len(ov))))
