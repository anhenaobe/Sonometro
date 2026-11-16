import olefile, struct, sys, collections, json

def read_records(path):
    o = olefile.OleFileIO(path)
    data = o.openstream('FileHeader').read()
    recs = []
    i = 0
    while i + 4 <= len(data):
        ln = struct.unpack('<H', data[i:i+2])[0]
        flag = data[i+2]; typ = data[i+3]
        body = data[i+4:i+4+ln]
        i += 4 + ln
        if typ != 0:
            recs.append({'__binary__': typ, '__len__': ln})
            continue
        txt = body.rstrip(b'\x00').decode('latin-1')
        d = {}
        for part in txt.split('|'):
            if '=' in part:
                k, v = part.split('=', 1)
                d[k.upper()] = v
        recs.append(d)
    return recs

if __name__ == '__main__':
    for f in sys.argv[1:]:
        recs = read_records(f)
        c = collections.Counter(r.get('RECORD', 'hdr') for r in recs)
        print(f, len(recs), dict(c))

def components(recs):
    # record index: recs[0] is header; OWNERINDEX refers to index in recs[1:]? test both
    body = recs[1:]
    comps = {}
    for idx, r in enumerate(body):
        if r.get('RECORD') == '1':
            comps[idx] = {'idx': idx, 'lib': r.get('LIBREFERENCE'), 'desc': r.get('COMPONENTDESCRIPTION'),
                          'part': r.get('CURRENTPARTID'), 'parts': r.get('PARTCOUNT'),
                          'x': r.get('LOCATION.X'), 'y': r.get('LOCATION.Y'), 'ori': r.get('ORIENTATION', '0'),
                          'mir': r.get('ISMIRRORED', 'F'), 'dmode': r.get('DISPLAYMODE', '0'),
                          'params': {}, 'pins': [], 'models': []}
    for idx, r in enumerate(body):
        o = r.get('OWNERINDEX')
        if o is None: continue
        o = int(o)
        if o in comps:
            c = comps[o]
            t = r.get('RECORD')
            if t == '34': c['ref'] = r.get('TEXT')
            elif t == '41': c['params'][r.get('NAME')] = r.get('TEXT')
            elif t == '2': c['pins'].append(r)
            elif t == '44':
                pass
        # implementation lists (45 owned by 44 owned by comp)
    for idx, r in enumerate(body):
        if r.get('RECORD') == '45':
            o44 = int(r['OWNERINDEX']); o = int(body[o44].get('OWNERINDEX', -1))
            if o in comps:
                comps[o]['models'].append((r.get('MODELNAME'), r.get('MODELTYPE'), r.get('ISCURRENT')))
    return comps

def num(r, k):
    v = int(r.get(k, '0') or 0); f = int(r.get(k + '_FRAC', '0') or 0)
    return v + f / 100000.0

def pin_end(p):
    x, y = num(p, 'LOCATION.X'), num(p, 'LOCATION.Y')
    L = num(p, 'PINLENGTH')
    o = int(p.get('PINCONGLOMERATE', '0')) & 3
    dx, dy = [(1, 0), (0, 1), (-1, 0), (0, -1)][o]
    return (round(x + dx * L, 3), round(y + dy * L, 3))

class UF:
    def __init__(s): s.p = {}
    def f(s, a):
        s.p.setdefault(a, a)
        while s.p[a] != a:
            s.p[a] = s.p[s.p[a]]; a = s.p[a]
        return a
    def u(s, a, b): s.p[s.f(a)] = s.f(b)

def on_seg(pt, a, b):
    (x, y), (x1, y1), (x2, y2) = pt, a, b
    if abs((x2 - x1) * (y - y1) - (y2 - y1) * (x - x1)) > 1e-6: return False
    return min(x1, x2) - 1e-6 <= x <= max(x1, x2) + 1e-6 and min(y1, y2) - 1e-6 <= y <= max(y1, y2) + 1e-6

def sheet_nodes(path, sheetname):
    """Return list of (node_id, kind, info, point) and union-find of local connectivity."""
    recs = read_records(path)
    body = recs[1:]
    comps = components(recs)
    items = []  # (key, point)
    uf = UF()
    segs = []
    for i, r in enumerate(body):
        if r.get('RECORD') == '27':
            n = int(r['LOCATIONCOUNT'])
            pts = [(round(num(r, f'X{k}'), 3), round(num(r, f'Y{k}'), 3)) for k in range(1, n + 1)]
            for a, b in zip(pts, pts[1:]):
                segs.append((a, b, f'W{i}'))
    for a, b, w in segs:
        uf.f(w)
    # wire-wire: endpoints touching other wires
    for a, b, w in segs:
        for c, d, w2 in segs:
            if w2 == w: continue
            for pt in (a, b):
                if on_seg(pt, c, d): uf.u(w, w2)
    def attach(key, pt):
        uf.f(key)
        for a, b, w in segs:
            if on_seg(pt, a, b): uf.u(key, w)
    pins = []
    for ci, c in comps.items():
        ref = c.get('ref') or f'?{ci}'
        if '?' in ref: ref = ref + str(ci)
        for p in c['pins']:
            if p.get('OWNERPARTID') not in (None, '-1', c['part']): continue
            if p.get('OWNERPARTDISPLAYMODE', '0') != c['dmode']: continue
            key = f"PIN:{ref}.{p.get('DESIGNATOR')}"
            pt = pin_end(p)
            pins.append((key, pt, p.get('NAME')))
            attach(key, pt)
    # pin-to-pin direct touching
    for k1, p1, _ in pins:
        for k2, p2, _ in pins:
            if k1 < k2 and p1 == p2: uf.u(k1, k2)
    labels = []
    for i, r in enumerate(body):
        t = r.get('RECORD')
        if t == '25':
            pt = (round(num(r, 'LOCATION.X'), 3), round(num(r, 'LOCATION.Y'), 3))
            key = f"LBL{i}"; attach(key, pt); labels.append((key, 'local:' + sheetname + ':' + r.get('TEXT', ''), pt))
        elif t == '17':
            pt = (round(num(r, 'LOCATION.X'), 3), round(num(r, 'LOCATION.Y'), 3))
            key = f"PWR{i}"; attach(key, pt); labels.append((key, 'global:' + r.get('TEXT', ''), pt))
            for k, pp, _ in pins:
                if pp == pt: uf.u(key, k)
        elif t == '18':
            x, y = num(r, 'LOCATION.X'), num(r, 'LOCATION.Y'); w = num(r, 'WIDTH')
            st = int(r.get('STYLE', '0'))
            ends = [(x, y), (x + w, y)] if st < 4 else [(x, y), (x, y - w)]
            key = f"PORT{i}"
            hit = False
            for e in ends:
                e = (round(e[0], 3), round(e[1], 3))
                uf.f(key)
                for a, b, wseg in segs:
                    if on_seg(e, a, b): uf.u(key, wseg); hit = True
                for k, pp, _ in pins:
                    if pp == e: uf.u(key, k); hit = True
            labels.append((key, 'port:' + r.get('NAME', ''), (x, y, w, st, hit)))
    return comps, pins, labels, uf, segs
