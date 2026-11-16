"""Coloca (o solo mide) los designadores de serigrafía.

Reglas (REGLAS.md / pedido del dueño):
  - alto 1.0 mm, trazo 0.15 mm, solo 0° y 90° (legibles desde abajo y desde la derecha);
  - nunca sobre pads (con 0.15 mm de separación), vías, máscara abierta ni sobre el cuerpo (F.Fab) de ninguna
    pieza; sin solaparse con otra serigrafía; a >= 0.5 mm del borde;
  - sin ambigüedad: el texto queda más cerca de su pieza que de cualquier otra;
  - si no cabe, el designador se omite (queda en F.Fab y en el PDF de montaje), EXCEPTO conectores (J*, A1, JP*)
    y puntos de prueba (TP*), que nunca se omiten: si no caben se reporta como problema.

Uso (Python de KiCad):
  python serigrafia.py --solo-medir [pcb]     informe, no modifica nada
  python serigrafia.py --aplicar [pcb]        escribe posiciones y oculta los que no caben (KiCad cerrado)
"""
import math
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
H, W, TH = 1.0, 0.8, 0.15          # alto, ancho de carácter, trazo (mm); JLC: alto >= 1.0
PAD_CLR, EDGE_CLR, TXT_CLR = 0.15, 0.5, 0.15
MUST = ('J', 'A', 'JP', 'TP')


def mm(v):
    return pcbnew.ToMM(v)


def box(bb, grow=0.0):
    return (mm(bb.GetLeft()) - grow, mm(bb.GetTop()) - grow, mm(bb.GetRight()) + grow, mm(bb.GetBottom()) + grow)


def inter(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def dist(a, b):
    dx = max(b[0] - a[2], a[0] - b[2], 0)
    dy = max(b[1] - a[3], a[1] - b[3], 0)
    return math.hypot(dx, dy)


def prefix(ref):
    return ref.rstrip('0123456789')


def body_box(fp):
    fab = [g for g in fp.GraphicalItems() if g.GetLayer() == pcbnew.F_Fab and g.GetClass() == 'PCB_SHAPE']
    if not fab:
        return box(fp.GetBoundingBox(False))
    bb = fab[0].GetBoundingBox()
    for g in fab[1:]:
        bb.Merge(g.GetBoundingBox())
    return box(bb)


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else '--solo-medir'
    path = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, '..', '..', 'pcb.kicad_pcb')
    b = pcbnew.LoadBoard(path)
    edge = box(b.GetBoardEdgesBoundingBox(), -EDGE_CLR)
    fps = list(b.GetFootprints())
    bodies = {fp.GetReference(): body_box(fp) for fp in fps}
    obst = []                                    # obstáculos fijos: pads, cuerpos, serigrafía gráfica, vías
    for fp in fps:
        for p in fp.Pads():
            obst.append(box(p.GetBoundingBox(), PAD_CLR))
        obst.append(bodies[fp.GetReference()])
        for g in fp.GraphicalItems():
            if g.GetLayer() == pcbnew.F_SilkS and g.GetClass() == 'PCB_SHAPE':
                obst.append(box(g.GetBoundingBox(), TXT_CLR))
    for t in b.GetTracks():
        if t.GetClass() == 'PCB_VIA':
            obst.append(box(t.GetBoundingBox(), PAD_CLR))
    placed = []
    result = {}
    # primero los obligatorios, luego los más difíciles (pieza pequeña rodeada)
    PRIO = {'U': 0, 'Y': 0, 'D': 0, 'L': 0}          # integrados, cristal, diodos, bobinas antes que pasivos

    def candidates(ref):
        bx = bodies[ref]
        cx, cy = (bx[0] + bx[2]) / 2, (bx[1] + bx[3]) / 2
        tw = W * len(ref) + TH                      # ancho aproximado del texto (paso de carácter ~= W)
        out = []
        for ang in (0, 90):
            lw, lh = (tw, H + TH) if ang == 0 else (H + TH, tw)
            for gap in (0.1, 0.2, 0.35, 0.5, 0.8, 1.2, 1.6):
                for side in ('arriba', 'abajo', 'izq', 'der'):
                    for shift in (0, -0.4, 0.4, -0.8, 0.8, -1.2, 1.2, -1.8, 1.8):
                        if side == 'arriba':
                            x, y = cx + shift, bx[1] - gap - lh / 2
                        elif side == 'abajo':
                            x, y = cx + shift, bx[3] + gap + lh / 2
                        elif side == 'izq':
                            x, y = bx[0] - gap - lw / 2, cy + shift
                        else:
                            x, y = bx[2] + gap + lw / 2, cy + shift
                        r = (x - lw / 2, y - lh / 2, x + lw / 2, y + lh / 2)
                        if not (edge[0] <= r[0] and r[2] <= edge[2] and edge[1] <= r[1] and r[3] <= edge[3]):
                            continue
                        if any(inter(r, o) for o in obst):
                            continue
                        mine = dist(r, bx)
                        if any(dist(r, bodies[o]) <= mine + 0.1 for o in bodies if o != ref):
                            continue                  # ambiguo: queda igual o más cerca de otra pieza
                        out.append((gap + abs(shift) * 0.5 + (0.05 if ang else 0), ang, x, y, r))
        out.sort(key=lambda c: c[0])
        return out

    cand = {fp.GetReference(): candidates(fp.GetReference()) for fp in fps}
    todo = set(cand)
    while todo:
        live = {r: [c for c in cand[r] if not any(inter(c[4], p) for p in placed)] for r in todo}
        # el más restringido primero (menos candidatos vivos), obligatorios y no pasivos antes
        ref = min(todo, key=lambda r: (prefix(r) not in MUST, PRIO.get(prefix(r)[:1], 1) if len(live[r]) else 9,
                                       len(live[r]) if live[r] else 10 ** 6))
        todo.discard(ref)
        if not live[ref]:
            result[ref] = None
            continue
        # entre los mejores 6, el que menos candidatos les quita a los demás pendientes
        def cost(c):
            g = tuple(v + d for v, d in zip(c[4], (-TXT_CLR, -TXT_CLR, TXT_CLR, TXT_CLR)))
            return sum(1 for r in todo for o in live[r] if inter(o[4], g)) + c[0]
        best = min(live[ref][:6], key=cost)
        ok = (best[1], best[2], best[3], best[4])
        placed.append(tuple(v + d for v, d in zip(ok[3], (-TXT_CLR, -TXT_CLR, TXT_CLR, TXT_CLR))))
        result[ref] = ok
    must_fail = [r for r, v in result.items() if v is None and prefix(r) in MUST]
    omit = sorted([r for r, v in result.items() if v is None and prefix(r) not in MUST],
                  key=lambda r: (prefix(r), int(r[len(prefix(r)):])))
    print(f'designadores: {len(result)}  caben: {sum(1 for v in result.values() if v)}  '
          f'se omiten: {len(omit)}  obligatorios sin lugar: {must_fail}')
    print('omitidos:', ' '.join(omit))
    if mode == '--aplicar':
        for fp in fps:
            ref = fp.GetReference()
            f = fp.Reference()
            f.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(W), pcbnew.FromMM(H)))
            f.SetTextThickness(pcbnew.FromMM(TH))
            v = result[ref]
            if v is None:
                f.SetVisible(False)
                continue
            f.SetVisible(True)
            f.SetLayer(pcbnew.F_SilkS)
            f.SetTextAngle(pcbnew.EDA_ANGLE(v[0], pcbnew.DEGREES_T))
            f.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_CENTER)
            f.SetVertJustify(pcbnew.GR_TEXT_V_ALIGN_CENTER)
            f.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(v[1]), pcbnew.FromMM(v[2])))
        pcbnew.SaveBoard(path, b)
        print('guardado', path)
    return result


if __name__ == '__main__':
    main()
