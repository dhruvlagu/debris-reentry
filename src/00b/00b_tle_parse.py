import sys, csv, os, time, collections
from datetime import datetime, timedelta
import pandas as pd

MU, RE = 398600.4418, 6378.135
L5 = 'ABCDEFGHJKLMNPQRSTUVWXYZ'

def key_of(i):
    return '%05d' % i if i < 100000 else L5[i // 10000 - 10] + '%04d' % (i % 10000)

def checksum_ok(s):
    t = 0
    for ch in s[:68]:
        if ch.isdigit():
            t += int(ch)
        elif ch == '-':
            t += 1
    return s[68].isdigit() and int(s[68]) == t % 10

path = sys.argv[1]
stem = os.path.splitext(os.path.basename(path))[0]
os.makedirs('data/frozen/tle_parsed', exist_ok=True)
out_path = 'data/frozen/tle_parsed/%s.csv' % stem

cand = pd.read_csv('data/frozen/candidates.csv', parse_dates=['DECAY'])
win = {}
for r in cand.itertuples():
    lab = r.DECAY.normalize().to_pydatetime() + timedelta(hours=12)
    win[key_of(int(r.NORAD_CAT_ID))] = (int(r.NORAD_CAT_ID), lab - timedelta(days=90), lab + timedelta(days=2))
print('candidates:', len(win))

st = collections.Counter()
rej = collections.Counter()
rejrows = []
hi_ids = collections.Counter()
t0 = time.time()
with open(path, 'r', buffering=1 << 24, errors='replace') as f, open(out_path, 'w', newline='') as fo:
    w = csv.writer(fo)
    w.writerow(['NORAD_CAT_ID', 'EPOCH', 'SEMIMAJOR_AXIS', 'PERIAPSIS', 'APOAPSIS', 'SRC', 'NOCK'])
    while True:
        l1 = f.readline()
        if not l1:
            break
        if l1[0] != '1':
            st['desync_lines'] += 1
            continue
        l2 = f.readline()
        while l2 and l2.strip(' \\\r\n') == '':
            st['blank_lines_skipped'] += 1
            l2 = f.readline()
        st['pairs'] += 1
        if st['pairs'] % 2000000 == 0:
            print('pairs', st['pairs'], 'kept', st['kept'], 'sec', int(time.time() - t0), flush=True)
        l1 = l1.rstrip('\\\r\n ')
        l2 = l2.rstrip('\\\r\n ')
        if len(l1) != 69:
            st['line1_len_not_69_all_objects'] += 1
            tk = l1.split()
            if len(tk) > 1 and tk[1][:5] in win:
                st['short_line_candidate_lost'] += 1
        k = l1[2:7].replace(' ', '0')
        if k not in win:
            continue
        st['cand_pairs'] += 1
        oid, lo, hi = win[k]
        why = None
        nock = 0
        if len(l1) == 68 and len(l2) == 68:
            nock = 1
            if l2[0] != '2':
                why = 'line2_bad'
            elif l2[2:7].replace(' ', '0') != k:
                why = 'id_mismatch'
        elif len(l1) != 69:
            why = 'line1_len_%d' % len(l1)
        elif len(l2) != 69 or l2[0] != '2':
            why = 'line2_bad'
        elif l2[2:7].replace(' ', '0') != k:
            why = 'id_mismatch'
        elif not checksum_ok(l1) or not checksum_ok(l2):
            why = 'checksum'
        if why:
            rej[why] += 1
            rejrows.append((stem, oid, why))
            continue
        try:
            yy = int(l1[18:20])
            year = 2000 + yy if yy < 57 else 1900 + yy
            ep = datetime(year, 1, 1) + timedelta(days=float(l1[20:32]) - 1)
            n = float(l2[52:63])
            e = float('0.' + l2[26:33].strip())
        except ValueError:
            rej['fields_unparsable'] += 1
            rejrows.append((stem, oid, 'fields_unparsable'))
            continue
        if ep < lo or ep > hi:
            st['outside_window'] += 1
            continue
        wr = n * 6.283185307179586 / 86400.0
        a = (MU / wr ** 2) ** (1.0 / 3.0)
        w.writerow([oid, ep.isoformat(sep=' ', timespec='microseconds'),
                    '%.4f' % a, '%.4f' % (a * (1 - e) - RE), '%.4f' % (a * (1 + e) - RE), stem, nock])
        st['kept'] += 1
        if oid >= 100000:
            hi_ids[oid] += 1

pd.DataFrame(rejrows, columns=['src', 'NORAD_CAT_ID', 'reason']).to_csv(
    'results/0b_tle_rejects_%s.csv' % stem, index=False)
print('file:', path, '| seconds:', int(time.time() - t0))
for k_, v in sorted(st.items()):
    print('  %s: %d' % (k_, v))
print('  rejects among candidate pairs:', dict(rej))
print('  candidate IDs above 99999 with kept records:', dict(hi_ids))
print('output:', out_path)
