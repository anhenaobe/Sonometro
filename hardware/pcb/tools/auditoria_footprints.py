"""Compara cada footprint de KiCad con el footprint de JLC/EasyEDA de la pieza LCSC exacta.

Correr con el Python de KiCad (necesita pcbnew) y con easyeda2kicad en el PATH:
  "C:/Program Files/KiCad/10.0/bin/python.exe" tools/auditoria_footprints.py [LCSC=LIB:FOOTPRINT ...]

Por cada par (LCSC, footprint de KiCad):
  1. Baja el footprint de EasyEDA con easyeda2kicad (caché en tools/out/easyeda/).
  2. Empareja los pads por número y busca el giro d en {0, 90, 180, 270} y la traslación t que mejor
     llevan los pads de KiCad sobre los de JLC: q ≈ R(d)·p + t (coordenadas con Y hacia arriba).
  3. Informa: giro d, traslación t, error residual por pad, diferencia de tamaño de pads, pad térmico, y
     si algún pad no tiene pareja (p. ej. polaridad de diodos numerada distinto).
Para el CPL: rotación JLC = rotación KiCad − d; posición JLC = posición KiCad − R(rot JLC)·t.
Salida: tools/out/auditoria_footprints.json + tabla en pantalla.
"""
import json
import math
import os
import subprocess
import sys
import time

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out', 'easyeda')
os.makedirs(OUT, exist_ok=True)
KLIB = 'C:/Program Files/KiCad/10.0/share/kicad/footprints'
PROJ_LIB = os.path.join(HERE, '..', 'lib', 'Sonometro.pretty')
EASYEDA = os.environ.get('EASYEDA2KICAD', 'easyeda2kicad')


def lib_path(lib):
    return PROJ_LIB if lib == 'Sonometro' else os.path.join(KLIB, lib + '.pretty')


def pads_of(fp):
    """Pads en coordenadas locales del footprint (giro 0), Y hacia arriba: {num: (x, y, sx, sy)}."""
    res = {}
    for p in fp.Pads():
        num = p.GetNumber()
        if not num:
            continue
        pos = p.GetFPRelativePosition()
        size = p.GetSize()
        ang = (p.GetOrientation().AsDegrees() - fp.GetOrientationDegrees()) % 180
        sx, sy = pcbnew.ToMM(size.x), pcbnew.ToMM(size.y)
        if abs(ang - 90) < 1:
            sx, sy = sy, sx
        res.setdefault(num, []).append((pcbnew.ToMM(pos.x), -pcbnew.ToMM(pos.y), sx, sy))
    return res


def easyeda_fp(lcsc):
    d = os.path.join(OUT, lcsc)
    pretty = os.path.join(d, 'jlc.pretty')
    for intento in range(4):                 # la API de EasyEDA corta con 403 si se le pide muy rápido
        if os.path.isdir(pretty) and os.listdir(pretty):
            break
        if intento:
            time.sleep(30 * intento)
        os.makedirs(d, exist_ok=True)
        subprocess.run([EASYEDA, '--footprint', f'--lcsc_id={lcsc}', '--output', os.path.join(d, 'jlc')],
                       capture_output=True, text=True, timeout=180)
        time.sleep(6)
    if not os.path.isdir(pretty) or not os.listdir(pretty):
        return None, None
    name = os.listdir(pretty)[0][:-len('.kicad_mod')]
    return pcbnew.FootprintLoad(pretty, name), name


def rot(x, y, deg):
    a = math.radians(deg)
    return x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a)


def match(ours, jlc):
    """Mejor giro d y traslación t con q ≈ R(d)·p + t, emparejando pads por número."""
    common = sorted(set(ours) & set(jlc))
    best = None
    for d in (0, 90, 180, 270):
        pairs = []
        for n in common:
            for (px, py, *_), (qx, qy, *_) in zip(sorted(ours[n]), sorted(jlc[n])):
                rx, ry = rot(px, py, d)
                pairs.append((rx, ry, qx, qy, n))
        if not pairs:
            continue
        tx = sum(q[2] - q[0] for q in pairs) / len(pairs)
        ty = sum(q[3] - q[1] for q in pairs) / len(pairs)
        err = max(math.hypot(q[0] + tx - q[2], q[1] + ty - q[3]) for q in pairs)
        if best is None or err < best[0] - 1e-6:
            best = (err, d, tx, ty)
    return best, common


def size_delta(ours, jlc, d):
    worst = 0.0
    for n in set(ours) & set(jlc):
        for (_, _, sx, sy), (_, _, jx, jy) in zip(sorted(ours[n]), sorted(jlc[n])):
            if d in (90, 270):
                sx, sy = sy, sx
            worst = max(worst, abs(sx - jx), abs(sy - jy))
    return worst


def audit(lcsc, fpid):
    lib, name = fpid.split(':')
    ours_fp = pcbnew.FootprintLoad(lib_path(lib), name)
    jfp, jname = easyeda_fp(lcsc)
    r = {'lcsc': lcsc, 'kicad': fpid, 'jlc': jname}
    if ours_fp is None or jfp is None:
        r['error'] = 'no se pudo cargar ' + ('KiCad' if ours_fp is None else 'EasyEDA')
        return r
    ours, jlc = pads_of(ours_fp), pads_of(jfp)
    (err, d, tx, ty), common = match(ours, jlc)
    r.update({'giro_d': d, 'tx': round(tx, 3), 'ty': round(ty, 3), 'error_pos_max': round(err, 3),
              'dif_tam_pad_max': round(size_delta(ours, jlc, d), 3),
              'pads_kicad': sorted(ours), 'pads_jlc': sorted(jlc),
              'sin_pareja': sorted((set(ours) ^ set(jlc)))})
    return r


if __name__ == '__main__':
    T = json.load(open(os.path.join(HERE, 'target.json')))
    extra = dict(a.split('=', 1) for a in sys.argv[1:])
    found = {}
    aud = os.path.join(HERE, 'out', 'auditoria_jlc.json')
    if os.path.exists(aud):
        for it in json.load(open(aud, encoding='utf-8')):
            if it['found']:
                for ref in it['refs']:
                    found[ref] = it['found']['lcsc']
    pairs = {}
    for ref, p in T.items():
        if p['mount'] != 'JLC':
            continue
        code = found.get(ref) or p['lcsc']
        if code:
            pairs.setdefault((code, p['fp']), []).append(ref)
    for code, fpid in extra.items():
        pairs.setdefault((code, fpid), []).append('(propuesta)')
    res = []
    for (code, fpid), refs in sorted(pairs.items(), key=lambda kv: kv[0][1]):
        r = audit(code, fpid)
        r['refs'] = refs
        res.append(r)
        if 'error' in r:
            print(f"{code:9s} {fpid[:45]:45s} ERROR {r['error']}")
        else:
            print(f"{code:9s} {fpid.split(':')[1][:38]:38s} d={r['giro_d']:3d} t=({r['tx']:+.2f},{r['ty']:+.2f}) "
                  f"pos_err={r['error_pos_max']:.3f} dtam={r['dif_tam_pad_max']:.3f} "
                  f"sin_pareja={r['sin_pareja']} jlc={r['jlc'][:30]}")
        sys.stdout.flush()
    json.dump(res, open(os.path.join(HERE, 'out', 'auditoria_footprints.json'), 'w'), indent=1)
