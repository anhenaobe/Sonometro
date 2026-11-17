"""Sugiere una nueva posición para cada vía que viola 'via_tapada_lejos_de_pad' (>= 0.35 mm de todo pad).

Para cada vía con un tramo recto desde el centro de su pad (patrón del ruteo): prueba posiciones sobre los cuatro ejes
del pad, desde 0.35 mm hasta 1.0 mm del borde (chequeo K), y se queda con la más cercana que cumple:
- >= 0.35 mm de cualquier pad (física, cualquier red);
- separación de la clase a pistas y vías de otras redes (0.2, o 0.3 si la otra red es Analogica/Reloj);
- taladro a taladro >= 0.25 mm; borde de placa >= 0.5 mm;
- el tramo nuevo (pad -> vía) también respeta las separaciones.
Uso (Python de KiCad): python sugerir_vias.py [pcb] -> imprime vía actual -> vía sugerida y el tramo.
"""
import math
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
mm = pcbnew.ToMM
R_VIA, PHYS, KMAX = 0.3, 0.35, 1.0
X0, Y0, X1, Y1 = 100.0, 100.0, 190.0, 164.0


def rect(p):
    bb = p.GetBoundingBox()
    return mm(bb.GetLeft()), mm(bb.GetTop()), mm(bb.GetRight()), mm(bb.GetBottom())


def d_pt_rect(x, y, r):
    dx = max(r[0] - x, x - r[2], 0)
    dy = max(r[1] - y, y - r[3], 0)
    return math.hypot(dx, dy)


def d_pt_seg(p, a, b):
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    t = 0 if L2 == 0 else max(0, min(1, ((p[0] - ax) * dx + (p[1] - ay) * dy) / L2))
    return math.hypot(p[0] - ax - t * dx, p[1] - ay - t * dy)


def d_seg_rect(a, b, r, n=12):
    return min(d_pt_rect(a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n, r) for k in range(n + 1))


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, '..', '..', 'pcb.kicad_pcb')
    b = pcbnew.LoadBoard(path)
    pads = [(p, rect(p), p.GetNetname(), p.GetNetClassName()) for fp in b.GetFootprints() for p in fp.Pads()]
    tracks = [(t, (mm(t.GetStart().x), mm(t.GetStart().y)), (mm(t.GetEnd().x), mm(t.GetEnd().y)), mm(t.GetWidth()),
               t.GetNetname(), t.GetNetClassName(), t.GetLayer()) for t in b.GetTracks() if t.GetClass() == 'PCB_TRACK']
    vias = [(v, (mm(v.GetPosition().x), mm(v.GetPosition().y)), v.GetNetname()) for v in b.GetTracks()
            if v.GetClass() == 'PCB_VIA']
    sep = lambda cls: 0.3 if cls in ('Analogica', 'Reloj') else 0.2   # noqa: E731

    def viola(v):
        x, y = v[1]
        return any(d_pt_rect(x, y, r) - R_VIA < PHYS - 1e-6 for p, r, n, c in pads)

    for v in vias:
        if not viola(v):
            continue
        x, y = v[1]
        net = v[2]
        # tramo: pista F.Cu con un extremo en la vía y el otro en el centro de un pad de la misma red
        stub = None
        for t, a, c, w, n, cls, lay in tracks:
            if n != net or lay != pcbnew.F_Cu:
                continue
            for e, o in ((a, c), (c, a)):
                if math.dist(e, (x, y)) < 0.01:
                    own = [pp for pp in pads if pp[2] == net and math.dist(o, (mm(pp[0].GetPosition().x),
                                                                                mm(pp[0].GetPosition().y))) < 0.01]
                    if own:
                        stub = (t, o, w, own[0])
        if stub is None:
            print(f'{net} vía {(x, y)}: sin tramo simple desde un pad -> a mano')
            continue
        t0, c, w, own = stub
        hx = (own[1][2] - own[1][0]) / 2
        hy = (own[1][3] - own[1][1]) / 2
        mejor = None
        for dx, dy, h in ((1, 0, hx), (-1, 0, hx), (0, 1, hy), (0, -1, hy)):
            for k in range(0, 66):
                tt = h + PHYS + R_VIA + k * 0.01
                if tt - h - R_VIA > KMAX:
                    break
                q = (round(c[0] + dx * tt, 3), round(c[1] + dy * tt, 3))
                if not (X0 + 0.5 + R_VIA <= q[0] <= X1 - 0.5 - R_VIA and Y0 + 0.5 + R_VIA <= q[1] <= Y1 - 0.5 - R_VIA):
                    continue
                ok = all(d_pt_rect(q[0], q[1], r) - R_VIA >= PHYS - 1e-6 for p, r, n, cls in pads if p is not own[0]
                         ) and d_pt_rect(q[0], q[1], own[1]) - R_VIA >= PHYS - 1e-6
                if ok:
                    for p, r, n, cls in pads:
                        if n != net and d_seg_rect(c, q, r) - w / 2 < sep(cls):
                            ok = False
                            break
                if ok:
                    for tt2, a, cc, w2, n, cls, lay in tracks:
                        if n == net or lay != pcbnew.F_Cu or tt2 is t0:
                            continue
                        if d_pt_seg(q, a, cc) - R_VIA - w2 / 2 < sep(cls) or \
                                min(d_pt_seg(a, c, q), d_pt_seg(cc, c, q), d_pt_seg(c, a, cc), d_pt_seg(q, a, cc)) \
                                - w / 2 - w2 / 2 < sep(cls):
                            ok = False
                            break
                if ok:
                    for v2, p2, n2 in vias:
                        if v2 is v[0]:
                            continue
                        dd = math.dist(q, p2)
                        if dd - 0.3 < 0.25 or (n2 != net and dd - 2 * R_VIA < 0.2):
                            ok = False
                            break
                if ok:
                    if mejor is None or tt < mejor[0]:
                        mejor = (tt, q)
                    break
        if mejor:
            print(f'{net} vía {(x, y)} desde pad {own[0].GetParentFootprint().GetReference()}.{own[0].GetNumber()} '
                  f'{c} -> {mejor[1]}  (a {mejor[0] - (hx if mejor[1][1] == c[1] else hy) - R_VIA:.2f} mm del pad)')
        else:
            print(f'{net} vía {(x, y)} desde pad {own[0].GetParentFootprint().GetReference()}.{own[0].GetNumber()}: '
                  f'SIN LUGAR sobre los ejes -> a mano')


if __name__ == '__main__':
    main()
