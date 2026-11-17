"""Distancia de un punto a la serigrafía real (el trazo, no la caja envolvente). Lo usan cosido.py y revisar_pistas.py.

Gráficos (PCB_SHAPE): segmento, rectángulo, círculo, arco y polígono. Se mide al trazo menos el medio ancho de la
línea; si la forma está rellena, el interior también cuenta. Textos y campos visibles: caja de los trazos reales
(GetEffectiveTextShape). Todo en mm.
"""
import math

import pcbnew

mm = pcbnew.ToMM


def _seg(p, a, b):
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    t = 0 if L2 == 0 else max(0, min(1, ((p[0] - ax) * dx + (p[1] - ay) * dy) / L2))
    return math.hypot(p[0] - ax - t * dx, p[1] - ay - t * dy)


def _dentro(p, poly):
    x, y = p
    c = False
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            c = not c
    return c


def items_serigrafia(board, capa=pcbnew.F_SilkS, campos=True):
    """Lista de (nombre, función distancia(p) -> mm) de la serigrafía de los footprints y de la placa.

    campos=False deja fuera los campos (designadores): cosido.py los ignora porque serigrafia.py los reubica después.
    """
    out = []

    def agregar(nombre, g):
        if g.GetLayer() != capa:
            return
        if g.GetClass() in ('PCB_FIELD', 'PCB_TEXT', 'PCB_TEXTBOX'):
            if hasattr(g, 'IsVisible') and not g.IsVisible():
                return
            bb = g.GetEffectiveTextShape().BBox()
            r = (mm(bb.GetLeft()), mm(bb.GetTop()), mm(bb.GetRight()), mm(bb.GetBottom()))
            out.append((nombre, lambda p, r=r: math.hypot(max(r[0] - p[0], p[0] - r[2], 0),
                                                         max(r[1] - p[1], p[1] - r[3], 0))))
            return
        if g.GetClass() != 'PCB_SHAPE':
            return
        w2 = mm(g.GetWidth()) / 2
        st = g.GetShape()
        lleno = g.IsSolidFill()
        if st == pcbnew.SHAPE_T_SEGMENT:
            a, b = (mm(g.GetStart().x), mm(g.GetStart().y)), (mm(g.GetEnd().x), mm(g.GetEnd().y))
            out.append((nombre, lambda p, a=a, b=b: _seg(p, a, b) - w2))
        elif st in (pcbnew.SHAPE_T_RECT, pcbnew.SHAPE_T_POLY):
            if st == pcbnew.SHAPE_T_RECT:
                x0, y0, x1, y1 = mm(g.GetStart().x), mm(g.GetStart().y), mm(g.GetEnd().x), mm(g.GetEnd().y)
                poly = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
            else:
                ps = g.GetPolyShape()
                poly = [(mm(ps.CVertex(i).x), mm(ps.CVertex(i).y)) for i in range(ps.TotalVertices())]
            segs = list(zip(poly, poly[1:] + poly[:1]))
            out.append((nombre, lambda p, segs=segs, poly=poly, lleno=lleno:
                        0.0 if (lleno and _dentro(p, poly)) else min(_seg(p, a, b) for a, b in segs) - w2))
        elif st == pcbnew.SHAPE_T_CIRCLE:
            c = (mm(g.GetCenter().x), mm(g.GetCenter().y))
            r = mm(g.GetRadius())
            out.append((nombre, lambda p, c=c, r=r, lleno=lleno:
                        max(0.0, math.dist(p, c) - r - w2) if lleno else abs(math.dist(p, c) - r) - w2))
        elif st == pcbnew.SHAPE_T_ARC:
            # arco: muestreo de 32 puntos entre el inicio y el fin pasando por el punto medio
            c = (mm(g.GetCenter().x), mm(g.GetCenter().y))
            r = mm(g.GetRadius())
            a0 = math.atan2(mm(g.GetStart().y) - c[1], mm(g.GetStart().x) - c[0])
            am = math.atan2(mm(g.GetArcMid().y) - c[1], mm(g.GetArcMid().x) - c[0])
            a1 = math.atan2(mm(g.GetEnd().y) - c[1], mm(g.GetEnd().x) - c[0])
            d1 = (am - a0) % (2 * math.pi)
            d2 = (a1 - a0) % (2 * math.pi)
            span = d2 if d1 <= d2 else d2 - 2 * math.pi
            pts = [(c[0] + r * math.cos(a0 + span * k / 32), c[1] + r * math.sin(a0 + span * k / 32))
                   for k in range(33)]
            segs = list(zip(pts, pts[1:]))
            out.append((nombre, lambda p, segs=segs: min(_seg(p, a, b) for a, b in segs) - w2))
        else:
            bb = g.GetBoundingBox()
            r = (mm(bb.GetLeft()), mm(bb.GetTop()), mm(bb.GetRight()), mm(bb.GetBottom()))
            out.append((nombre, lambda p, r=r: math.hypot(max(r[0] - p[0], p[0] - r[2], 0),
                                                         max(r[1] - p[1], p[1] - r[3], 0))))

    for fp in board.GetFootprints():
        for g in list(fp.GraphicalItems()) + (list(fp.GetFields()) if campos else []):
            agregar(f'{fp.GetReference()} {g.GetClass()}', g)
    for g in board.GetDrawings():
        agregar(f'placa {g.GetClass()}', g)
    return out
