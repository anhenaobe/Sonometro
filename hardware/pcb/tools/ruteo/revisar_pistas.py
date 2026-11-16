"""Revisa las pistas de la placa con la API de pcbnew y reporta todo lo que el DRC nativo no cubre.

Chequeos (pedido del dueño + REGLAS.md):
  A  orientación de cada segmento múltiplo de 45°
  B  ángulo entre segmentos unidos >= 135° (sin 90° ni agudos)  [también lo hace el DRC: track_angle]. En el centro
     de un pad o de una vía se calcula la esquina interior entre los bordes de las dos pistas: si cae dentro del cobre
     del pad o de la vía no hay esquina de pista (se lista aparte, como información); si cae fuera, es hallazgo.
  C  unión pista-pad: termina en el centro del pad y llega paralela a un eje del pad
  D  segmentos de menos de 0.1 mm
  E  extremos sueltos (stubs) y segmentos duplicados o superpuestos
  F  vías sin usar (menos de dos capas conectadas por pista o zona)
  G  B.Cu: solo redes permitidas y solo dentro de las zonas permitidas
  H  ninguna pista crítica pasa por encima de una pista de B.Cu
  I  GND continuo en B.Cu debajo de cada pista crítica (contra el relleno de la zona). Los puntos que caen en el anillo
     libre del plano alrededor de un pad THT de la misma red (donde la pista termina) se listan aparte: ese anillo
     existe siempre alrededor de un pad pasante que no es GND.
  J  analógica paralela a digital/reloj a menos de 1 mm por más de 2 mm
  K  vía GND a <= 1.0 mm (borde a borde) del pad GND de cada condensador de desacoplo y de cada pin GND SMD de los
     integrados; solo en piezas que ya tienen alguna pista (las demás se cuentan aparte como pendientes)
  L  condensador de desacoplo pegado a su pin: <= 1.0 mm borde a borde entre su pad y el pin (tabla DESACOPLO)
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
EXCEPCIONES_BCU = [                              # [(red, (x0, y0, x1, y1))] aprobadas en el punto de control 2
    ('3V3', (139.4, 115.9, 140.2, 118.9)),       # tronco de 3V3 bajo el bus de 24 V, entre los bloques de los bucks
    ('3V3', (132.3, 115.9, 133.1, 118.9)),       # sensado de FB de U6 bajo el bus de 24 V
    ('5V', (153.9, 115.9, 154.7, 118.9)),        # sensado de FB de U7 bajo el bus de 24 V
]
CRITICAL_CLASSES = {'Analogica', 'Reloj', 'Conmutado'}
DIGITAL_CLASSES = {'Reloj'}
DIGITAL_NETS = {'I2C_SCL', 'I2C_SDA'}
VIA_GND_MAX = 1.0                                # mm, borde del pad a borde de la vía (chequeo K)
DESACOPLO_MAX = 1.0                              # mm, borde a borde condensador-pin (chequeo L)
ACEPTADOS = {                                    # (chequeo, pieza): motivo; aceptados por el dueño, se listan aparte
    ('L', 'C36'): 'aceptado tras el bloque 1 (VCC 0.3 mm, vía GND pegada y retorno corto a AGND)',
    ('L', 'C46'): 'aceptado tras el bloque 1 (VCC 0.3 mm, vía GND pegada y retorno corto a AGND)',
    ('L', 'C2'): 'aceptado tras el bloque 3 (entrada del LT3092, ubicación del equipo)',
    ('L', 'C3'): 'aceptado tras el bloque 3 (entrada del LT3092, ubicación del equipo)',
    ('L', 'C49'): 'aceptado tras el bloque 3 (entrada del LT3092, ubicación del equipo)',
    ('L', 'C50'): 'aceptado tras el bloque 3 (entrada del LT3092, ubicación del equipo)',
}
DESACOPLO = {                                    # condensador: (integrado, pin) que desacopla; se completa por bloque
    'C29': ('U6', '2'), 'C30': ('U6', '10'), 'C36': ('U6', '5'),
    'C39': ('U7', '2'), 'C40': ('U7', '10'), 'C46': ('U7', '5'),
    'D2': ('D1', '1'),                           # TVS junto al cátodo de D1 (bloque 2)
    'C2': ('U1', '8'), 'C3': ('U1', '8'),        # entrada del LT3092 CH1 (bloque 3)
    'C49': ('U8', '8'), 'C50': ('U8', '7'),      # entrada del LT3092 CH2 (bloque 3)
}
# Redes que el dueño pidió tratar como alimentación (no como señal crítica) en la regla de cruces H:
# IEPE_FEED e IEPE_FEED_SV son el riel DC de 24 V antes del filtro RC de cada fuente.
NO_CRITICAS_EN_CRUCES = {'Net-(J1-Pin_2)', 'Net-(J7-Pin_2)'}


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


def pad_gap(p1, p2):
    """Separación borde a borde entre dos pads (cajas alineadas a los ejes; pads a 0°/90°)."""
    b1, b2 = p1.GetBoundingBox(), p2.GetBoundingBox()
    dx = max(mm(b1.GetLeft()) - mm(b2.GetRight()), mm(b2.GetLeft()) - mm(b1.GetRight()), 0)
    dy = max(mm(b1.GetTop()) - mm(b2.GetBottom()), mm(b2.GetTop()) - mm(b1.GetBottom()), 0)
    return math.hypot(dx, dy)


def pad_via_gap(pad, via):
    bb = pad.GetBoundingBox()
    x, y = pt(via.GetPosition())
    dx = max(mm(bb.GetLeft()) - x, x - mm(bb.GetRight()), 0)
    dy = max(mm(bb.GetTop()) - y, y - mm(bb.GetBottom()), 0)
    return math.hypot(dx, dy) - mm(via.GetWidth(pcbnew.F_Cu)) / 2


def esquina_interior(p, q1, w1, q2, w2):
    """Esquina interior entre los bordes de dos pistas que salen de p hacia q1 y q2 (anchos w1, w2)."""
    u1 = ((q1[0] - p[0]), (q1[1] - p[1]))
    u2 = ((q2[0] - p[0]), (q2[1] - p[1]))
    n = math.hypot(*u1), math.hypot(*u2)
    u1, u2 = (u1[0] / n[0], u1[1] / n[0]), (u2[0] / n[1], u2[1] / n[1])
    d = u1[0] * u2[0] + u1[1] * u2[1]
    if abs(abs(d) - 1) < 1e-9:
        return None
    n1 = (u2[0] - d * u1[0], u2[1] - d * u1[1])
    n2 = (u1[0] - d * u2[0], u1[1] - d * u2[1])
    l1, l2 = math.hypot(*n1), math.hypot(*n2)
    n1, n2 = (n1[0] / l1, n1[1] / l1), (n2[0] / l2, n2[1] / l2)
    a = (p[0] + n1[0] * w1 / 2, p[1] + n1[1] * w1 / 2)          # p + h1·n1 + s·u1 = p + h2·n2 + t·u2
    c = (p[0] + n2[0] * w2 / 2, p[1] + n2[1] * w2 / 2)
    det = u1[0] * (-u2[1]) - u1[1] * (-u2[0])
    s = ((c[0] - a[0]) * (-u2[1]) - (c[1] - a[1]) * (-u2[0])) / det
    return (a[0] + s * u1[0], a[1] + s * u1[1])


def in_box(p, boxes):
    return any(x0 <= p[0] <= x1 and y0 <= p[1] <= y1 for x0, y0, x1, y1 in boxes)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    path = args[0] if args else os.path.join(HERE, '..', '..', 'pcb.kicad_pcb')
    out_json = sys.argv[sys.argv.index('--json') + 1] if '--json' in sys.argv else None
    b = pcbnew.LoadBoard(path)
    F = collections.defaultdict(list)            # hallazgos por chequeo
    INFO = collections.defaultdict(list)         # lo que se revisó y cumple, para mostrarlo
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
    ruteados = set()
    for key, lst in ends.items():
        layer = key[0]
        for (s, p, q) in lst:
            t, a, c, lay, net, w = s
            others = [o for o in lst if o[0] is not s and o[0][4] == net]
            pd = pads_at(p, layer, net)
            cobre = via_at(p, net) + [x for x in pd if near(pt(x.GetPosition()), p, 0.01)]
            # B: ángulo entre segmentos (vector saliente de cada uno desde el punto común)
            for (s2, p2, q2) in others:
                v1 = (q[0] - p[0], q[1] - p[1])
                v2 = (q2[0] - p2[0], q2[1] - p2[1])
                n1, n2 = math.hypot(*v1), math.hypot(*v2)
                if n1 > 0 and n2 > 0:
                    ang = math.degrees(math.acos(max(-1, min(1, (v1[0] * v2[0] + v1[1] * v2[1]) / (n1 * n2)))))
                    if ang < 135 - 0.01 and id(s) < id(s2):
                        e = esquina_interior(p, q, w, q2, s2[5]) if cobre else None
                        dentro = False
                        if e is not None:
                            k = math.dist(e, p)
                            e2 = (e[0] + (p[0] - e[0]) * 0.01 / k, e[1] + (p[1] - e[1]) * 0.01 / k) if k else e
                            dentro = any(c.HitTest(pcbnew.VECTOR2I(int(round(e2[0] * 1e6)), int(round(e2[1] * 1e6))))
                                         for c in cobre)
                        donde = ('pad ' + ', '.join(f'{x.GetParentFootprint().GetReference()}.{x.GetNumber()}'
                                                    for x in cobre if isinstance(x, pcbnew.PAD))) if cobre else ''
                        if dentro:
                            INFO['B_union_dentro_del_pad'].append(f'{net} en {p} ({donde or "vía"}): {ang:.0f}°, '
                                                                  f'esquina interior dentro del cobre')
                        else:
                            F['B_angulo_union'].append(f'{net} en {p}: {ang:.1f}°' +
                                                       (f' (esquina fuera del cobre de {donde or "la vía"})'
                                                        if cobre else ''))
            if pd:
                for pdx in pd:
                    ruteados.add(pdx.GetParentFootprint().GetReference())
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
                tees = [o for o in segs if o[4] == net and o[3] == layer and o[0] is not t
                        and seg_dist(p, o[1], o[2]) < 0.01]
                if not tees:
                    F['E_extremo_suelto'].append(f'{net} {b.GetLayerName(layer)} en {p}')
                for o in tees:                   # unión en T sobre pista desnuda: el DRC (track_angle) también la ve
                    v1 = (q[0] - p[0], q[1] - p[1])
                    for e in (o[1], o[2]):
                        v2 = (e[0] - p[0], e[1] - p[1])
                        if math.hypot(*v2) < 1e-6:
                            continue
                        ang = math.degrees(math.acos(max(-1, min(1, (v1[0] * v2[0] + v1[1] * v2[1]) /
                                                          (math.hypot(*v1) * math.hypot(*v2))))))
                        if ang < 135 - 0.01:
                            F['B_angulo_union'].append(f'{net} en {p}: unión en T a {ang:.0f}°')
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
    tht = [(pt(p.GetPosition()), max(mm(p.GetSize().x), mm(p.GetSize().y)) / 2, p.GetNetname(),
            f'{p.GetParentFootprint().GetReference()}.{p.GetNumber()}')
           for p in pads if p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH]

    def en_anillo_propio(x, y, net):
        for c, r, n, nombre in tht:
            if n == net and math.dist(c, (x, y)) <= r + 0.3 + 0.45:     # radio + separación de la clase + margen
                return nombre
        return None
    for t, a, c, layer, net, w in segs:
        if layer != pcbnew.F_Cu or netclass.get(net) not in CRITICAL_CLASSES:
            continue
        for s2 in ([] if net in NO_CRITICAS_EN_CRUCES else bsegs):
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
                        propio = en_anillo_propio(mm(q.x), mm(q.y), net)
                        if propio:
                            INFO['I_anillo_de_su_pad_THT'].append(f'{net} en ({x:.2f}, {y:.2f}) junto a {propio}')
                            continue
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
    # K: vía GND junto al pad GND (condensadores de desacoplo y pines GND SMD de los integrados)
    supplies = {'3V3', '5V', '5V_A', '24V_PROT', '/3V3_DAC', '/3V3_DAC_SV', '/IEPE_SUP', '/IEPE_SUP_SV'}
    pendientes = []
    gvias = [v for v in vias if v.GetNetname() == 'GND']
    for fp in b.GetFootprints():
        ref = fp.GetReference()
        es_c = ref.startswith('C') and 'GND' in {p.GetNetname() for p in fp.Pads()} and \
            supplies & {p.GetNetname() for p in fp.Pads()}
        es_u = ref.startswith('U')
        if not (es_c or es_u):
            continue
        if ref not in ruteados:
            pendientes.append(ref)
            continue
        for pad in fp.Pads():
            if pad.GetNetname() != 'GND' or pad.GetAttribute() != pcbnew.PAD_ATTRIB_SMD:
                continue
            dmin = min([pad_via_gap(pad, v) for v in gvias] + [99])
            linea = f'{ref}.{pad.GetNumber()}: vía GND a {dmin:.2f} mm del pad'
            (INFO['K_via_gnd'] if dmin <= VIA_GND_MAX else F['K_sin_via_gnd_junto_al_pad']).append(linea)
    # L: condensador de desacoplo pegado al pin que desacopla
    for cref, (uref, pin) in DESACOPLO.items():
        cf, uf = b.FindFootprintByReference(cref), b.FindFootprintByReference(uref)
        if cf is None or uf is None or cref not in ruteados:
            continue
        up = uf.FindPadByNumber(pin)
        cp = [p for p in cf.Pads() if p.GetNetname() == up.GetNetname()]
        g = min(pad_gap(p, up) for p in cp) if cp else 99
        linea = f'{cref} -> {uref}.{pin} ({up.GetNetname()}): {g:.2f} mm borde a borde'
        if g <= DESACOPLO_MAX:
            INFO['L_desacoplo_pegado'].append(linea)
        elif ('L', cref) in ACEPTADOS:
            INFO['L_aceptado_por_el_dueño'].append(linea + ': ' + ACEPTADOS[('L', cref)])
        else:
            F['L_desacoplo_lejos_del_pin'].append(linea)
    total = sum(len(v) for v in F.values())
    print(f'pistas: {len(tracks)}  vías: {len(vias)}  hallazgos: {total}')
    print(f'  (piezas sin ninguna pista todavía, chequeo K pendiente: {len(pendientes)})')
    for k in sorted(F):
        print(f'  {k}: {len(F[k])}')
        for line in F[k][:40]:
            print('     ', line)
    for k in sorted(INFO):
        print(f'  [cumple] {k}: {len(INFO[k])}')
        for line in INFO[k][:40]:
            print('     ', line)
    if out_json:
        json.dump({'hallazgos': F, 'cumple': INFO, 'pendientes_K': pendientes}, open(out_json, 'w'), indent=1)
    sys.exit(1 if total else 0)


if __name__ == '__main__':
    main()
