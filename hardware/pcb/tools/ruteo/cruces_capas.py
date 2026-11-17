"""Tabla de cruces entre capas: qué cobre de F.Cu queda encima (en planta) de cada pista de In2.Cu y B.Cu.

Regla del dueño (bloques 3-4, sigue vigente en 4 capas): ninguna pista de otra capa pasa debajo de un nodo SUM, del
nodo filtrado del DAC, de la cadena de 1 MΩ ni del nodo medio de la realimentación. Estos nodos van en PROTEGIDAS.
Se considera "encima" el cobre de F.Cu (pistas y pads) a menos de (ancho/2 + 0.2 mm) del eje de la pista, medido en
planta.
Uso (Python de KiCad): python cruces_capas.py [pcb]   -> tabla por pista; sale con código 1 si toca una protegida.
"""
import collections
import math
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
mm = pcbnew.ToMM
PROTEGIDAS = {
    'Net-(U3A--)', 'Net-(U9A--)',                                           # nodos SUM
    'Net-(U3B-+)', 'Net-(U9B-+)',                                           # nodo filtrado del DAC (entrada del buffer)
    'Net-(R13-Pad1)', 'Net-(R14-Pad1)', 'Net-(R16-Pad1)',                   # cadena de 1 MΩ CH1
    'Net-(R38-Pad1)', 'Net-(R39-Pad1)', 'Net-(R40-Pad1)',                   # cadena de 1 MΩ CH2
    'Net-(R7-Pad2)', 'Net-(R42-Pad2)',                                      # nodo medio de la realimentación
}
MARGEN = 0.2


def seg_dist(p, a, b):
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    t = 0 if L2 == 0 else max(0, min(1, ((p[0] - ax) * dx + (p[1] - ay) * dy) / L2))
    return math.hypot(p[0] - ax - t * dx, p[1] - ay - t * dy)


def seg_seg(a, b, c, d):
    def o(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
    if o(a, b, c) * o(a, b, d) < 0 and o(c, d, a) * o(c, d, b) < 0:
        return 0.0
    return min(seg_dist(a, c, d), seg_dist(b, c, d), seg_dist(c, a, b), seg_dist(d, a, b))


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, '..', '..', 'pcb.kicad_pcb')
    b = pcbnew.LoadBoard(path)
    pt = lambda v: (mm(v.x), mm(v.y))                                    # noqa: E731
    segs = [(pt(t.GetStart()), pt(t.GetEnd()), t.GetLayer(), t.GetNetname(), mm(t.GetWidth()))
            for t in b.GetTracks() if t.GetClass() == 'PCB_TRACK']
    arriba = [s for s in segs if s[2] == pcbnew.F_Cu]
    pads = [(p, p.GetNetname()) for fp in b.GetFootprints() for p in fp.Pads() if p.IsOnLayer(pcbnew.F_Cu)]
    abajo = [s for s in segs if s[2] in (pcbnew.In2_Cu, pcbnew.B_Cu)]
    filas = collections.defaultdict(lambda: [0.0, collections.Counter(), set()])
    malos = 0
    for a, c, layer, net, w in abajo:
        clave = (b.GetLayerName(layer), net)
        filas[clave][0] += math.dist(a, c)
        for e, f, _, n2, w2 in arriba:
            if n2 != net and seg_seg(a, c, e, f) < (w + w2) / 2 + MARGEN:
                filas[clave][1][n2] += 1
        for p, n2 in pads:
            if n2 == net or not n2:
                continue
            bb = p.GetBoundingBox()
            r = (mm(bb.GetLeft()), mm(bb.GetTop()), mm(bb.GetRight()), mm(bb.GetBottom()))
            # distancia del segmento al rectángulo del pad (muestreo)
            n = max(2, int(math.dist(a, c) / 0.1) + 1)
            dmin = min(math.hypot(max(r[0] - x, x - r[2], 0), max(r[1] - y, y - r[3], 0))
                       for k in range(n) for x, y in [(a[0] + (c[0] - a[0]) * k / (n - 1),
                                                       a[1] + (c[1] - a[1]) * k / (n - 1))])
            if dmin < w / 2 + MARGEN:
                filas[clave][1][f'{n2} (pad {p.GetParentFootprint().GetReference()}.{p.GetNumber()})'] += 1
    print(f"{'capa':7s} {'red':14s} {'largo':>6s}  F.Cu encima (PROTEGIDA = hallazgo)")
    for (capa, net), (L, cnt, _) in sorted(filas.items()):
        prot = [k for k in cnt if k.split(' (pad')[0] in PROTEGIDAS]
        malos += len(prot)
        txt = ', '.join(('PROTEGIDA ' if k in prot else '') + k for k in sorted(cnt)) or '-'
        print(f'{capa:7s} {net[:14]:14s} {L:6.1f}  {txt}')
    print(f'cruces bajo nodos protegidos: {malos}')
    sys.exit(1 if malos else 0)


if __name__ == '__main__':
    main()
