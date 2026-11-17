"""Propone las vías de cosido GND (relleno de F.Cu con In1.Cu y B.Cu) y las guarda en un JSON para el bloque 9.

Candidatos: anillo a 1.2 mm del borde cada 5 mm y una grilla interior (2.5 mm en la zona del AFE y del ADC, 5 mm en
el resto). Se descarta el candidato que no cumple en todas las capas, porque la vía las atraviesa todas:
- >= 0.35 mm de todo pad (vía taponada, regla via_tapada_lejos_de_pad); >= 0.9 mm de los fiduciales (sin red);
- separación a pistas de otras redes en cualquier capa: 0.35 mm a Analogica/Reloj/Conmutado, 0.25 mm al resto;
- separación a vías de otras redes 0.3 mm (borde a borde) y >= 1.0 mm entre centros con las vías GND;
- fuera de las zonas de F.Cu de otras redes (5V, 3V3, 24 V, SW) más 0.4 mm; >= 0.8 mm del borde;
- >= 0.15 mm de toda la serigrafía, designadores incluidos (orden: serigrafia.py -> cosido.py -> teardrops.py).
Uso (Python de KiCad): python cosido.py [pcb] [salida.json]
"""
import json
import math
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
mm = pcbnew.ToMM
R = 0.3                                   # radio de la vía de 0.6 mm
X0, Y0, X1, Y1 = 100.0, 100.0, 190.0, 164.0
DENSA = (138.0, 116.0, 172.0, 162.0)      # AFE CH1/CH2 y ADC


def d_pt_seg(p, a, b):
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    t = 0 if L2 == 0 else max(0, min(1, ((p[0] - ax) * dx + (p[1] - ay) * dy) / L2))
    return math.hypot(p[0] - ax - t * dx, p[1] - ay - t * dy)


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, '..', '..', 'pcb.kicad_pcb')
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, 'cosido.json')
    b = pcbnew.LoadBoard(path)
    pt = lambda v: (mm(v.x), mm(v.y))                                   # noqa: E731
    pads = []
    for fp in b.GetFootprints():
        for p in fp.Pads():
            bb = p.GetBoundingBox()
            redondo = p.GetShape() == pcbnew.PAD_SHAPE_CIRCLE
            pads.append((redondo, pt(p.GetPosition()), mm(p.GetSize().x) / 2,
                         (mm(bb.GetLeft()), mm(bb.GetTop()), mm(bb.GetRight()), mm(bb.GetBottom())), p.GetNetname()))
    segs = [(pt(t.GetStart()), pt(t.GetEnd()), mm(t.GetWidth()), t.GetNetname(), t.GetNetClassName())
            for t in b.GetTracks() if t.GetClass() == 'PCB_TRACK']
    vias = [(pt(v.GetPosition()), v.GetNetname()) for v in b.GetTracks() if v.GetClass() == 'PCB_VIA']
    # serigrafía (contornos, marcas de pin 1 y designadores): ninguna vía debajo, medido al trazo real
    # (geom_serigrafia.py). Orden: serigrafia.py -> cosido.py -> teardrops.py -> verificar_bloque.py, para que las vías
    # de cosido no quiten lugar a los designadores.
    sys.path.insert(0, HERE)
    from geom_serigrafia import items_serigrafia
    silk = [f for _, f in items_serigrafia(b)]                  # incluye los designadores ya ubicados
    zonas = []
    for z in b.Zones():
        if z.GetNetname() != 'GND':
            bb = z.GetBoundingBox()
            zonas.append((mm(bb.GetLeft()) - 0.4, mm(bb.GetTop()) - 0.4, mm(bb.GetRight()) + 0.4, mm(bb.GetBottom()) + 0.4))

    def sep(cls):
        return 0.35 if cls in ('Analogica', 'Reloj', 'Conmutado') else 0.25

    def libre(q, puestos):
        x, y = q
        if not (X0 + 0.8 <= x <= X1 - 0.8 and Y0 + 0.8 <= y <= Y1 - 0.8):
            return False
        for z in zonas:
            if z[0] <= x <= z[2] and z[1] <= y <= z[3]:
                return False
        for redondo, c, r, rc, net in pads:
            d = (math.dist(q, c) - r) if redondo else math.hypot(max(rc[0] - x, x - rc[2], 0),
                                                                  max(rc[1] - y, y - rc[3], 0))
            if d - R < (0.9 if not net else 0.35):      # fiduciales: separación 0.6 y fuera de su apertura de máscara
                return False
        for a, c, w, net, cls in segs:
            if net != 'GND' and d_pt_seg(q, a, c) - w / 2 - R < sep(cls):
                return False
        if any(f(q) - R < 0.15 for f in silk):
            return False
        for c, net in vias:
            dd = math.dist(q, c)
            if (net != 'GND' and dd - 2 * R < 0.3) or (net == 'GND' and dd < 1.0):
                return False
        return all(math.dist(q, p2) >= 1.0 for p2 in puestos)

    cand = []
    # anillo perimetral cada 5 mm a 1.2 mm del borde
    for k in range(int((X1 - X0) / 5) + 1):
        cand += [(X0 + 1.2 + k * 5, Y0 + 1.2), (X0 + 1.2 + k * 5, Y1 - 1.2)]
    for k in range(int((Y1 - Y0) / 5) + 1):
        cand += [(X0 + 1.2, Y0 + 1.2 + k * 5), (X1 - 1.2, Y0 + 1.2 + k * 5)]
    # grilla interior; en cada nodo se prueban corrimientos chicos si el centro no sirve
    for gx in [X0 + 2.5 + 2.5 * i for i in range(int((X1 - X0) / 2.5))]:
        for gy in [Y0 + 2.5 + 2.5 * j for j in range(int((Y1 - Y0) / 2.5))]:
            densa = DENSA[0] <= gx <= DENSA[2] and DENSA[1] <= gy <= DENSA[3]
            if densa or (round((gx - X0) / 2.5) % 2 == 0 and round((gy - Y0) / 2.5) % 2 == 0):
                cand.append((gx, gy))
    puestos = []
    for q in cand:
        for dx, dy in [(0, 0), (0.4, 0), (-0.4, 0), (0, 0.4), (0, -0.4), (0.4, 0.4), (-0.4, -0.4), (0.4, -0.4),
                       (-0.4, 0.4)]:
            q2 = (round(q[0] + dx, 3), round(q[1] + dy, 3))
            if libre(q2, puestos):
                puestos.append(q2)
                break
    json.dump(puestos, open(out, 'w'), indent=0)
    print(f'candidatos: {len(cand)}  vías de cosido: {len(puestos)} -> {out}')


if __name__ == '__main__':
    main()
