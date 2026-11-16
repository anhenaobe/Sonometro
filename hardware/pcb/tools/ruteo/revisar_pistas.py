"""Revisa las pistas de la placa con la API de pcbnew y reporta todo lo que el DRC nativo no cubre.

Chequeos (pedido del dueño + REGLAS.md):
  A  orientación de cada segmento múltiplo de 45°
  B  ángulo entre segmentos unidos >= 135° (sin 90° ni agudos)  [también lo hace el DRC: track_angle]
  C  unión pista-pad: termina en el centro del pad y llega paralela a un eje del pad
  D  segmentos de menos de 0.1 mm
  E  extremos sueltos (stubs) y segmentos duplicados o superpuestos
  F  vías sin usar (menos de dos capas conectadas por pista o zona)
  G  B.Cu: solo redes permitidas y solo dentro de las zonas permitidas
  H  ninguna pista crítica pasa por encima de una pista de B.Cu
  I  GND continuo en B.Cu debajo de cada pista crítica (contra el relleno de la zona)
  J  analógica paralela a digital/reloj a menos de 1 mm por más de 2 mm
  K  desacoplo: vía GND junto al pad GND de cada condensador de desacoplo (<= 1.0 mm)
Uso (Python de KiCad):  python revisar_pistas.py [pcb] [--json salida.json]
Sale con código 1 si hay hallazgos.
"""
import json
import math
import os
import sys
import collections

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
TOL = 0.005                                      # mm

# --- política de capas (decisión 1 aprobada) --------------------------------------------------------------
BCU_NETS = {'I2C_SCL', 'I2C_SDA', 'DC_MON', 'DC_MON2'}
DIGITAL_ZONE = [(170.0, 100.0, 190.0, 164.0)]    # KiCad mm: x >= 70 mm desde el borde izquierdo
EXCEPCIONES_BCU = []                             # [(red, (x0, y0, x1, y1))] aprobadas en el punto de control 2
CRITICAL_CLASSES = {'Analogica', 'Reloj', 'Conmutado'}
DIGITAL_CLASSES = {'Reloj'}
DIGITAL_NETS = {'I2C_SCL', 'I2C_SDA'}


def mm(v):
    return pcbnew.ToMM(v)


def pt(v):
    return (mm(v.x), mm(v.y))


def ang_of(a, b):
    return math.degrees(math.atan2(b[1] - a[1], b[0] - a[0])) % 360


def near(a, b, tol=TOL):
    return abs(a[0] - b[0]) <= tol and abs(a[1] - b[1]) <= tol


def seg_dist(p, a, b):
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    t = 0 if L2 == 0 else max(0, min(1, ((p[0] - ax) * dx + (p[1] - ay) * dy) / L2))
    return math.hypot(p[0] - ax - t * dx, p[1] - ay - t * dy)


def seg_seg_dist(a, b, c, d):
    def inter(p1, p2, p3, p4):
        def o(p, q, r):
            return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
        return o(p1, p2, p3) * o(p1, p2, p4) < 0 and o(p3, p4, p1) * o(p3, p4, p2) < 0
    if inter(a, b, c, d):
        return 0.0
    return min(seg_dist(a, c, d), seg_dist(b, c, d), seg_dist(c, a, b), seg_dist(d, a, b))


def in_box(p, boxes):
    return any(x0 <= p[0] <= x1 and y0 <= p[1] <= y1 for x0, y0, x1, y1 in boxes)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    path = args[0] if args else os.path.join(HERE, '..', '..', 'pcb.kicad_pcb')
    out_json = sys.argv[sys.argv.index('--json') + 1] if '--json' in sys.argv else None
    b = pcbnew.LoadBoard(path)
    F = collections.defaultdict(list)            # hallazgos por chequeo
    tracks = [t for t in b.GetTracks() if t.GetClass() == 'PCB_TRACK']
    vias = [t for t in b.GetTracks() if t.GetClass() == 'PCB_VIA']
    pads = [p for fp in b.GetFootprints() for p in fp.Pads()]
    netclass = {}
    for t in tracks:
        netclass[t.GetNetname()] = t.GetNetClassName()
    segs = [(t, pt(t.GetStart()), pt(t.GetEnd()), t.GetLayer(), t.GetNetname(), mm(t.GetWidth())) for t in tracks]

    # A, D: orientación y largo
    for t, a, c, layer, net, w in segs:
        L = math.dist(a, c)
        if L < 0.1 - 1e-6:
            F['D_segmento_corto'].append(f'{net} {b.GetLayerName(layer)} {a}->{c} L={L:.3f} mm')
        if L > 1e-6:
            r = ang_of(a, c) % 45
            if min(r, 45 - r) > 0.01:
                F['A_angulo_no_45'].append(f'{net} {b.GetLayerName(layer)} {a}->{c} ang={ang_of(a, c):.2f}°')

    # índice de extremos
    ends = collections.defaultdict(list)          # (layer, x, y redondeado) -> [(seg, punta, otra punta)]
    for s in segs:
        t, a, c, layer, net, w = s
        for p, q in ((a, c), (c, a)):
            ends[(layer, round(p[0], 3), round(p[1], 3))].append((s, p, q))

    def pads_at(p, layer, net):
        res = []
        for pd in pads:
            if pd.GetNetname() == net and pd.IsOnLayer(layer) and pd.HitTest(pcbnew.VECTOR2I(
                    pcbnew.FromMM(p[0]), pcbnew.FromMM(p[1]))):
                res.append(pd)
        return res

    def via_at(p, net):
        return [v for v in vias if v.GetNetname() == net and near(pt(v.GetPosition()), p, 0.01)]

    def zone_at(p, layer, net):
        for z in b.Zones():
            if z.GetNetname() == net and z.IsOnLayer(layer):
                fp = z.GetFilledPolysList(layer)
                if fp.Contains(pcbnew.VECTOR2I(pcbnew.FromMM(p[0]), pcbnew.FromMM(p[1]))):
                    return True
        return False

    # B, C, E: uniones
    for key, lst in ends.items():
        layer = key[0]
        for (s, p, q) in lst:
            t, a, c, lay, net, w = s
            others = [o for o in lst if o[0] is not s and o[0][4] == net]
            # B: ángulo entre segmentos (vector saliente de cada uno desde el punto común)
            for (s2, p2, q2) in others:
                v1 = (q[0] - p[0], q[1] - p[1])
                v2 = (q2[0] - p2[0], q2[1] - p2[1])
                n1, n2 = math.hypot(*v1), math.hypot(*v2)
                if n1 > 0 and n2 > 0:
                    ang = math.degrees(math.acos(max(-1, min(1, (v1[0] * v2[0] + v1[1] * v2[1]) / (n1 * n2)))))
                    if ang < 135 - 0.01 and id(s) < id(s2):
                        F['B_angulo_union'].append(f'{net} en {p}: {ang:.1f}°')
            pd = pads_at(p, layer, net)
            if pd:
                for pdx in pd:
                    cpos = pt(pdx.GetPosition())
                    if not near(cpos, p, 0.01):
                        F['C_pad_fuera_de_centro'].append(
                            f'{net} pad {pdx.GetParentFootprint().GetReference()}.{pdx.GetNumber()} llega a {p}, '
                            f'centro {cpos}')
                    else:
                        rel = (ang_of(p, q) - pdx.GetOrientation().AsDegrees()) % 90
                        if min(rel, 90 - rel) > 0.01:
                            F['C_pad_entrada_oblicua'].append(
                                f'{net} pad {pdx.GetParentFootprint().GetReference()}.{pdx.GetNumber()} '
                                f'entra a {ang_of(p, q):.1f}° (pad a {pdx.GetOrientation().AsDegrees():.0f}°)')
            elif not others and not via_at(p, net) and not zone_at(p, layer, net):
                # ¿unión en T sobre el cuerpo de otro segmento de la misma red?
                tee = any(o[4] == net and o[3] == layer and o[0] is not t and seg_dist(p, o[1], o[2]) < 0.01
                          for o in segs)
                if not tee:
                    F['E_extremo_suelto'].append(f'{net} {b.GetLayerName(layer)} en {p}')
    # E: duplicados/superpuestos (colineales de la misma red y capa que se solapan)
    by = collections.defaultdict(list)
    for s in segs:
        by[(s[3], s[4])].append(s)
    for (layer, net), lst in by.items():
        for i in range(len(lst)):
            for j in range(i + 1, len(lst)):
                _, a, c, *_ = lst[i]
                _, d, e, *_ = lst[j]
                if seg_dist(d, a, c) < 0.005 and seg_dist(e, a, c) < 0.005 or \
                        seg_dist(a, d, e) < 0.005 and seg_dist(c, d, e) < 0.005:
                    F['E_superpuesto'].append(f'{net} {b.GetLayerName(layer)} {a}->{c} y {d}->{e}')
    # F: vías
    for v in vias:
        p = pt(v.GetPosition())
        net = v.GetNetname()
        layers = 0
        for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
            if ends.get((layer, round(p[0], 3), round(p[1], 3))) or zone_at(p, layer, net) or \
                    any(s[4] == net and s[3] == layer and seg_dist(p, s[1], s[2]) < 0.01 for s in segs) or \
                    pads_at(p, layer, net):
                layers += 1
        if layers < 2:
            F['F_via_sin_usar'].append(f'{net} en {p} ({layers} capa conectada)')
    # G: B.Cu
    for t, a, c, layer, net, w in segs:
        if layer != pcbnew.B_Cu:
            continue
        ok_zone = [z for n, z in EXCEPCIONES_BCU if n == net]
        if net in BCU_NETS:
            ok_zone += DIGITAL_ZONE
        if not ok_zone:
            F['G_bcu_red_no_permitida'].append(f'{net} {a}->{c}')
        elif not (in_box(a, ok_zone) and in_box(c, ok_zone)):
            F['G_bcu_fuera_de_zona'].append(f'{net} {a}->{c}')
    # H, I, J: críticas
    bsegs = [s for s in segs if s[3] == pcbnew.B_Cu]
    gnd_b = [z for z in b.Zones() if z.GetNetname() == 'GND' and z.IsOnLayer(pcbnew.B_Cu)]
    for t, a, c, layer, net, w in segs:
        if layer != pcbnew.F_Cu or netclass.get(net) not in CRITICAL_CLASSES:
            continue
        for s2 in bsegs:
            if seg_seg_dist(a, c, s2[1], s2[2]) < (w + s2[5]) / 2 + 0.3:
                F['H_critica_sobre_bcu'].append(f'{net} {a}->{c} sobre {s2[4]} {s2[1]}->{s2[2]}')
        if gnd_b:
            L = math.dist(a, c)
            n = max(2, int(L / 0.25) + 1)
            ux, uy = ((c[0] - a[0]) / L, (c[1] - a[1]) / L) if L else (0, 0)
            for k in range(n):
                f = k / (n - 1)
                x, y = a[0] + (c[0] - a[0]) * f, a[1] + (c[1] - a[1]) * f
                for off in (-(w / 2 + 0.2), 0.0, w / 2 + 0.2):
                    q = pcbnew.VECTOR2I(pcbnew.FromMM(x - uy * off), pcbnew.FromMM(y + ux * off))
                    if not any(z.GetFilledPolysList(pcbnew.B_Cu).Contains(q) for z in gnd_b):
                        F['I_sin_gnd_debajo'].append(f'{net} en ({x:.2f}, {y:.2f})')
                        break
                else:
                    continue
                break
    ana = [s for s in segs if s[3] == pcbnew.F_Cu and netclass.get(s[4]) == 'Analogica']
    dig = [s for s in segs if s[3] == pcbnew.F_Cu and (netclass.get(s[4]) in DIGITAL_CLASSES or s[4] in DIGITAL_NETS)]
    for s in ana:
        for d in dig:
            a, c, e, f = s[1], s[2], d[1], d[2]
            if seg_seg_dist(a, c, e, f) > 1.0 + (s[5] + d[5]) / 2:
                continue
            # largo en paralelo: proyección del segmento digital sobre el analógico cuando son paralelos
            if abs((ang_of(a, c) - ang_of(e, f)) % 180) > 1 and abs((ang_of(a, c) - ang_of(e, f)) % 180 - 180) > 1:
                continue
            L = math.dist(a, c)
            ux, uy = (c[0] - a[0]) / L, (c[1] - a[1]) / L
            t1 = (e[0] - a[0]) * ux + (e[1] - a[1]) * uy
            t2 = (f[0] - a[0]) * ux + (f[1] - a[1]) * uy
            ov = min(max(t1, t2), L) - max(min(t1, t2), 0)
            if ov > 2.0:
                F['J_paralelo_analogico_digital'].append(f'{s[4]} con {d[4]}: {ov:.1f} mm a < 1 mm')
    # K: desacoplo (condensador con un pad GND y otro a una red de alimentación)
    supplies = {'3V3', '5V', '5V_A', '24V_PROT', '/3V3_DAC', '/3V3_DAC_SV', '/IEPE_SUP', '/IEPE_SUP_SV'}
    for fp in b.GetFootprints():
        if not fp.GetReference().startswith('C'):
            continue
        nets = {p.GetNetname(): p for p in fp.Pads()}
        if 'GND' in nets and supplies & set(nets):
            gp = pt(nets['GND'].GetPosition())
            dmin = min([math.dist(gp, pt(v.GetPosition())) for v in vias if v.GetNetname() == 'GND'] + [99])
            pad_r = max(mm(nets['GND'].GetSize().x), mm(nets['GND'].GetSize().y)) / 2
            if dmin - pad_r > 1.0:
                F['K_desacoplo_sin_via_gnd'].append(f'{fp.GetReference()}: vía GND más cercana a {dmin:.2f} mm del pad')
    total = sum(len(v) for v in F.values())
    print(f'pistas: {len(tracks)}  vías: {len(vias)}  hallazgos: {total}')
    for k in sorted(F):
        print(f'  {k}: {len(F[k])}')
        for line in F[k][:12]:
            print('     ', line)
    if out_json:
        json.dump(F, open(out_json, 'w'), indent=1)
    sys.exit(1 if total else 0)


if __name__ == '__main__':
    main()
