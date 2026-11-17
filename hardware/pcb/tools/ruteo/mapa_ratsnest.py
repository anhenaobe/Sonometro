"""Dibuja el placement con el ratsnest (árbol mínimo por red) coloreado por clase, para planear corredores.
Uso: python mapa_ratsnest.py [salida.png] [corredores.json]   (lee tools/guia/placement.json; sin GND)
Si se da corredores.json ({"red": [[x, y], ...], ...} en mm desde abajo a la izquierda) los dibuja encima.
"""
import json
import math
import os
import sys
import collections

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
D = json.load(open(os.path.join(HERE, '..', 'guia', 'placement.json')))
S, M = 22, 60
X0, Y0, BW, BH = 100.0, 100.0, 90.0, 64.0
CLASS = {
    'pot': (('24V', '3V3', '5V', '5V_A', 'IEPE_SUP', '3V3_DAC', 'Net-(D1'), (230, 120, 0)),
    'sw': (('SW_',), (200, 0, 160)),
    'reloj': (('SAI_', 'PCM_MCLK', 'MCLK', 'PCM_BCK', 'PCM_LRCK', 'PCM_DOUT'), (220, 0, 0)),
    'i2c': (('I2C',), (120, 60, 0)),
    'mon': (('DC_MON',), (0, 140, 140)),
}


def cls(net):
    n = net.lstrip('/')
    for k, (pref, col) in CLASS.items():
        if any(n.startswith(p) or ('/' + p) in net or p in n for p in pref):
            if k == 'pot' and (n.startswith('3V3_DAC') or n.startswith('IEPE_SUP')):
                return k, col
            if k == 'pot' and n not in ('24V_IN', '24V_PROT', '3V3', '5V', '5V_A') and not n.startswith('Net-(D1'):
                continue
            return k, col
    return 'analog', (0, 90, 220)


def font(sz):
    for f in ('C:/Windows/Fonts/arialbd.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'):
        if os.path.exists(f):
            return ImageFont.truetype(f, sz)
    return ImageFont.load_default(size=sz)


def P(x, y):                      # coordenadas KiCad (mm) -> píxel
    return (M + (x - X0) * S, M + (y - Y0) * S)


def Q(x, y):                      # mm desde abajo-izquierda -> píxel
    return P(X0 + x, Y0 + BH - y)


def mst(pts):
    n = len(pts)
    if n < 2:
        return []
    inT = [False] * n
    inT[0] = True
    best = [(math.dist(pts[0], pts[i]), 0) for i in range(n)]
    E = []
    for _ in range(n - 1):
        j = min((i for i in range(n) if not inT[i]), key=lambda i: best[i][0])
        inT[j] = True
        E.append((pts[best[j][1]], pts[j]))
        for i in range(n):
            if not inT[i]:
                d = math.dist(pts[j], pts[i])
                if d < best[i][0]:
                    best[i] = (d, j)
    return E


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, '..', 'out', 'ratsnest_mapa.png')
    corr = json.load(open(sys.argv[2])) if len(sys.argv) > 2 else {}
    W, H = int(BW * S + 2 * M), int(BH * S + 2 * M + 30 * S)
    img = Image.new('RGB', (W, H), 'white')
    dr = ImageDraw.Draw(img, 'RGBA')
    dr.rectangle([*P(X0, Y0), *P(X0 + BW, Y0 + BH)], fill=(250, 250, 245), outline='black', width=3)
    for t in range(0, 91, 5):
        px, py = P(X0 + t, Y0 + BH)
        dr.line([px, Y0, px, py], fill=(225, 225, 225), width=1)
        dr.text((px, py + 6), str(t), fill='black', font=font(14), anchor='mt')
    for t in range(0, 65, 5):
        px, py = P(X0, Y0 + BH - t)
        dr.line([M, py, px + BW * S, py], fill=(225, 225, 225), width=1)
        dr.text((px - 8, py), str(t), fill='black', font=font(14), anchor='rm')
    nets = collections.defaultdict(list)
    for f in D['fps']:
        b = f['box']
        dr.rectangle([*P(b[0], b[1]), *P(b[2], b[3])], outline=(150, 150, 150), width=1)
        for p in f['pads']:
            dr.rectangle([*P(p[0], p[1]), *P(p[2], p[3])], fill=(170, 170, 170) if p[5] != 'GND' else (90, 200, 90))
            if p[5] and p[5] != 'GND' and not p[5].startswith('unconnected'):
                nets[p[5]].append(((p[0] + p[2]) / 2, (p[1] + p[3]) / 2))
        x, y = P((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)
        dr.text((x, y), f['ref'], fill=(40, 40, 40), font=font(13), anchor='mm')
    for net, pts in nets.items():
        k, col = cls(net)
        for a, c in mst(pts):
            dr.line([*P(*a), *P(*c)], fill=col + (200,), width=2)
    for net, pts in corr.items():
        k, col = cls(net)
        dr.line([Q(*p) for p in pts], fill=col + (255,), width=6)
    y = BH * S + 2 * M
    for i, (k, (pref, col)) in enumerate(list(CLASS.items()) + [('analog', ((), (0, 90, 220)))]):
        dr.line([M + i * 150, y, M + i * 150 + 40, y], fill=col, width=5)
        dr.text((M + i * 150 + 48, y), k, fill='black', font=font(16), anchor='lm')
    img.save(out)
    print('guardado', out)


if __name__ == '__main__':
    main()
