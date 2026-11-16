"""Recorta la serigrafía de los footprints que quedan contra el borde de la placa (REGLAS.md §7).

La serigrafía debe quedar a >= 0.5 mm del borde. Para cada footprint se toma su posición y giro reales en la
placa, se recortan las líneas a la región permitida, se borra lo que queda afuera y se guarda en la librería
del proyecto:
  - BNC (J2/J8): el barril sale por el borde inferior. Se recorta su contorno.
  - Borneras MX126 (J1/J5/J7): el contorno toca el borde izquierdo (y el superior en J5) y la marca de pin 1
    (flecha) quedaba fuera de la placa. Se crea `..._Borde` con el contorno recortado y la flecha de pin 1 en el
    lado derecho del cuerpo, a la altura del pin 1.
Uso (Python de KiCad, después de buildlib.py): python recortar_serigrafia.py <pcb> <dir de lib .pretty>
"""
import math
import os
import sys

import pcbnew

KLIB = 'C:/Program Files/KiCad/10.0/share/kicad/footprints'
MARGEN = 0.5                          # mm de serigrafía a borde
def _load(lib, name):
    """Instancia nueva del plugin en cada llamada: con una sola, pcbnew devuelve a veces un SwigPyObject
    sin envolver después de un FootprintSave (falla intermitente de los enlaces SWIG de KiCad 10)."""
    io = pcbnew.PCB_IO_KICAD_SEXPR()
    fp = io.FootprintLoad(lib, name)
    if not hasattr(fp, 'Pads'):
        raise SystemExit(f'no se pudo cargar {name} de {lib}')
    return fp


def _save(lib, fp):
    io = pcbnew.PCB_IO_KICAD_SEXPR()
    io.FootprintSave(lib, fp)


TB_STD = ('TerminalBlock', 'TerminalBlock_MaiXu_MX126-5.0-02P_1x02_P5.00mm')
TB_NEW = 'TerminalBlock_MaiXu_MX126-5.0-02P_1x02_P5.00mm_Borde'
BNC = 'BNC_Kinghelm_KH-BNC75-3511_Horizontal'


def clip(p0, p1, r):
    """Liang–Barsky: recorta el segmento p0-p1 al rectángulo r=(x0,y0,x1,y1). None si queda afuera."""
    x0, y0 = p0
    dx, dy = p1[0] - x0, p1[1] - y0
    t0, t1 = 0.0, 1.0
    for p, q in ((-dx, x0 - r[0]), (dx, r[2] - x0), (-dy, y0 - r[1]), (dy, r[3] - y0)):
        if p == 0:
            if q < 0:
                return None
        else:
            t = q / p
            if p < 0:
                t0 = max(t0, t)
            else:
                t1 = min(t1, t)
    if t0 > t1:
        return None
    return (x0 + t0 * dx, y0 + t0 * dy), (x0 + t1 * dx, y0 + t1 * dy)


def mm2(v):
    return pcbnew.ToMM(v.x), pcbnew.ToMM(v.y)


def iu2(p):
    return pcbnew.VECTOR2I(pcbnew.FromMM(p[0]), pcbnew.FromMM(p[1]))


def place_like(fp, ref_fp, board):
    fp.SetParent(board)
    fp.SetOrientation(ref_fp.GetOrientation())
    fp.SetPosition(ref_fp.GetPosition())


def trim(fp, edge, keep=()):
    for g in list(fp.GraphicalItems()):
        if g.GetLayer() != pcbnew.F_SilkS or g.GetClass() != 'PCB_SHAPE' or g in keep:
            continue
        w = pcbnew.ToMM(g.GetWidth()) / 2 + 0.01
        r = (edge[0] + MARGEN + w, edge[1] + MARGEN + w, edge[2] - MARGEN - w, edge[3] - MARGEN - w)
        if g.GetShape() == pcbnew.SHAPE_T_SEGMENT:
            c = clip(mm2(g.GetStart()), mm2(g.GetEnd()), r)
            if c is None or abs(c[0][0] - c[1][0]) + abs(c[0][1] - c[1][1]) < 0.05:
                fp.Remove(g)
            else:
                g.SetStart(iu2(c[0]))
                g.SetEnd(iu2(c[1]))
        else:
            bb = g.GetBoundingBox()
            if not (r[0] <= pcbnew.ToMM(bb.GetLeft()) and pcbnew.ToMM(bb.GetRight()) <= r[2] and
                    r[1] <= pcbnew.ToMM(bb.GetTop()) and pcbnew.ToMM(bb.GetBottom()) <= r[3]):
                fp.Remove(g)


def unplace_and_save(fp, lib, name, lib_nick='Sonometro'):
    fp.SetOrientation(pcbnew.EDA_ANGLE(0, pcbnew.DEGREES_T))
    fp.SetPosition(pcbnew.VECTOR2I(0, 0))
    fp.SetFPID(pcbnew.LIB_ID(lib_nick, name))
    _save(lib, fp)


def tsot_adi(lib):
    """TSOT-23-8 con el land pattern de ADI (LTC DWG 05-08-1637): pads 0.40 x 1.22 mm, filas a 2.62 mm."""
    fp = _load(os.path.join(KLIB, 'Package_TO_SOT_SMD.pretty'), 'TSOT-23-8')
    for p in fp.Pads():
        sgn = 1 if p.GetPosition().x > 0 else -1
        p.SetPosition(pcbnew.VECTOR2I(sgn * pcbnew.FromMM(1.31), p.GetPosition().y))
        p.SetSize(pcbnew.VECTOR2I(pcbnew.FromMM(1.22), pcbnew.FromMM(0.40)))
    name = 'TSOT-23-8_Pad0.40x1.22mm_P0.65mm_ADI'
    fp.SetFPID(pcbnew.LIB_ID('Sonometro', name))
    fp.SetLibDescription('TSOT-23-8 (ADI TS8 / TI DDF). Land pattern ADI LTC DWG 05-08-1637 Rev A: pads 0.40 x 1.22 '
                         'mm, paso 0.65, filas 2.62 c-c. Separacion entre pads 0.25 mm.')
    _save(lib, fp)


PAD_SILK = 0.15                     # JLC: serigrafía a >= 0.15 mm de los pads


def clip_out(p0, p1, rects):
    """Partes del segmento p0-p1 que quedan fuera de todos los rectángulos (lista de segmentos)."""
    cut = []
    for r in rects:
        c = clip(p0, p1, r)
        if c:
            L = math.dist(p0, p1) or 1.0
            cut.append((math.dist(p0, c[0]) / L, math.dist(p0, c[1]) / L))
    cut.sort()
    out, t = [], 0.0
    for a, b_ in cut:
        if a > t:
            out.append((t, a))
        t = max(t, b_)
    if t < 1.0:
        out.append((t, 1.0))
    return [((p0[0] + (p1[0] - p0[0]) * a, p0[1] + (p1[1] - p0[1]) * a),
             (p0[0] + (p1[0] - p0[0]) * b_, p0[1] + (p1[1] - p0[1]) * b_)) for a, b_ in out
            if math.dist(p0, p1) * (b_ - a) >= 0.1]


def _rects(pads, w2, extra=()):
    rects = []
    for p in pads:
        bb = p.GetBoundingBox()
        m = PAD_SILK + w2 + 0.005
        rects.append((pcbnew.ToMM(bb.GetLeft()) - m, pcbnew.ToMM(bb.GetTop()) - m,
                      pcbnew.ToMM(bb.GetRight()) + m, pcbnew.ToMM(bb.GetBottom()) + m))
    return rects + [(x0 - w2, y0 - w2, x1 + w2, y1 + w2) for x0, y0, x1, y1 in extra]


def _alejar_item(fp, g, pads, extra=(), p0=None, p1=None):
    """Una sola pasada por ítem (los enlaces SWIG fallan si se vuelve a pedir GraphicalItems() tras un Remove)."""
    w2 = pcbnew.ToMM(g.GetWidth()) / 2
    rects = _rects(pads, w2, extra)
    if g.GetShape() == pcbnew.SHAPE_T_SEGMENT:
        a0, a1 = p0 or mm2(g.GetStart()), p1 or mm2(g.GetEnd())
        parts = clip_out(a0, a1, rects)
        width = g.GetWidth()
        fp.Remove(g)
        for a, c in parts:
            ng = pcbnew.PCB_SHAPE(fp, pcbnew.SHAPE_T_SEGMENT)
            ng.SetStart(iu2(a))
            ng.SetEnd(iu2(c))
            ng.SetLayer(pcbnew.F_SilkS)
            ng.SetWidth(width)
            fp.Add(ng)
    elif g.GetShape() == pcbnew.SHAPE_T_CIRCLE:
        c = mm2(g.GetCenter())
        r = pcbnew.ToMM(g.GetRadius())
        ring = [p for p in pads if math.dist(mm2(p.GetPosition()), c) < 0.05]
        if ring:                                      # círculo alrededor de un pad (punto de prueba)
            pr = max(pcbnew.ToMM(ring[0].GetSize().x), pcbnew.ToMM(ring[0].GetSize().y)) / 2
            if r - w2 - pr < PAD_SILK:
                g.SetEnd(iu2((c[0] + pr + PAD_SILK + w2 + 0.01, c[1])))
        elif any(math.dist(c, mm2(p.GetPosition())) <= 3 for p in pads):
            fp.Remove(g)                              # punto suelto cerca de un pad: se borra


def alejar_de_pads(fp, extra=()):
    """Recorta las líneas de serigrafía a >= 0.15 mm de los pads propios (y de rectángulos extra, en mm);
    agranda los círculos que rodean un pad y borra los demás que queden cerca."""
    pads = [p for p in fp.Pads()]
    for g in list(fp.GraphicalItems()):
        if g.GetLayer() == pcbnew.F_SilkS and g.GetClass() == 'PCB_SHAPE':
            _alejar_item(fp, g, pads, extra)


def copia_local(lib, src_lib, name, new_name, extra=()):
    fp = _load(src_lib, name)
    alejar_de_pads(fp, extra)
    fp.SetFPID(pcbnew.LIB_ID('Sonometro', new_name))
    _save(lib, fp)


def oscilador(lib, pcb):
    """Y1: el punto de pin 1 cae sobre el pad 1 (debajo del cuerpo) -> se borra; queda la escuadra exterior.
    El lado izquierdo del contorno corre a 0.11 mm de los pads de C11/C12 -> se quita. Arriba/abajo a 0.15."""
    name = 'Oscillator_YXC_SMD3225-4Pin_3.2x2.5mm'
    fp = _load(lib, name)
    pads = [p for p in fp.Pads()]
    # pads de las piezas vecinas (C11/C12 quedan a ~0.1 mm del contorno) en coordenadas locales de Y1 (giro 0)
    b = pcbnew.LoadBoard(pcb)
    y1 = b.FindFootprintByReference('Y1')
    ox, oy = mm2(y1.GetPosition())
    extra = []
    for f in b.GetFootprints():
        if f.GetReference() == 'Y1':
            continue
        for p in f.Pads():
            bb = p.GetBoundingBox()
            r = (pcbnew.ToMM(bb.GetLeft()) - ox, pcbnew.ToMM(bb.GetTop()) - oy,
                 pcbnew.ToMM(bb.GetRight()) - ox, pcbnew.ToMM(bb.GetBottom()) - oy)
            if r[2] > -4 and r[0] < 4 and r[3] > -4 and r[1] < 4:
                extra.append((r[0] - PAD_SILK, r[1] - PAD_SILK, r[2] + PAD_SILK, r[3] + PAD_SILK))
    for g in list(fp.GraphicalItems()):
        if g.GetLayer() != pcbnew.F_SilkS or g.GetClass() != 'PCB_SHAPE':
            continue
        if g.GetShape() == pcbnew.SHAPE_T_CIRCLE:
            fp.Remove(g)
            continue
        s, e = mm2(g.GetStart()), mm2(g.GetEnd())
        if abs(s[0] + 2.03) < 0.01 and abs(e[0] + 2.03) < 0.01:          # lado izquierdo
            fp.Remove(g)
            continue
        if abs(s[1] - e[1]) < 0.01 and abs(abs(s[1]) - 1.7) < 0.05:      # arriba / abajo
            y = 1.71 if s[1] > 0 else -1.75
            s, e = (s[0], y), (e[0], y)
        _alejar_item(fp, g, pads, extra, p0=s, p1=e)
    _save(lib, fp)


TAREAS = ('tsot', 'r0402', 'c0402', 'tp', 'osc', 'bnc', 'bornera')


def tarea(pcb, lib, t):
    if t == 'tsot':
        tsot_adi(lib)
    elif t in ('r0402', 'c0402', 'tp'):
        src, name = {'r0402': ('Resistor_SMD', 'R_0402_1005Metric'), 'c0402': ('Capacitor_SMD', 'C_0402_1005Metric'),
                     'tp': ('TestPoint', 'TestPoint_THTPad_D2.0mm_Drill1.0mm')}[t]
        copia_local(lib, KLIB + '/' + src + '.pretty', name, name + '_JLC')
    elif t == 'osc':
        oscilador(lib, pcb)
    else:
        b = pcbnew.LoadBoard(pcb)
        bb = b.GetBoardEdgesBoundingBox()
        edge = (pcbnew.ToMM(bb.GetLeft()) + 0.05, pcbnew.ToMM(bb.GetTop()) + 0.05,
                pcbnew.ToMM(bb.GetRight()) - 0.05, pcbnew.ToMM(bb.GetBottom()) - 0.05)   # quita el ancho de la línea
        if t == 'bnc':                    # mismo footprint y misma altura en J2 y J8
            fp = _load(lib, BNC)
            place_like(fp, b.FindFootprintByReference('J2'), b)
            trim(fp, edge)
            unplace_and_save(fp, lib, BNC)
        else:                             # bornera, en el contexto de J5 (esquina superior izquierda)
            fp = _load(KLIB + '/' + TB_STD[0] + '.pretty', TB_STD[1])
            place_like(fp, b.FindFootprintByReference('J5'), b)
            # pad 1 y cuerpo ANTES de recortar (tras un Remove, los enlaces SWIG dejan de responder)
            p1 = mm2(fp.FindPadByNumber('1').GetPosition())
            body_right = max(pcbnew.ToMM(g.GetBoundingBox().GetRight()) for g in fp.GraphicalItems()
                             if g.GetLayer() == pcbnew.F_Fab and g.GetClass() == 'PCB_SHAPE')
            # flecha de pin 1 en el lado derecho del cuerpo, apuntando al cuerpo, a la altura del pin 1.
            # Se agrega ANTES de recortar: después de un Remove, cualquier llamada SWIG puede tumbar KiCad 10.
            tri = pcbnew.PCB_SHAPE(fp, pcbnew.SHAPE_T_POLY)
            x_tip = body_right + 0.25
            pts = pcbnew.VECTOR_VECTOR2I()      # una lista de Python aquí también hace que KiCad 10 se caiga
            for q in ((x_tip, p1[1]), (x_tip + 0.45, p1[1] - 0.3), (x_tip + 0.45, p1[1] + 0.3)):
                pts.append(iu2(q))
            tri.SetPolyPoints(pts)
            tri.SetLayer(pcbnew.F_SilkS)
            tri.SetFilled(True)
            tri.SetWidth(pcbnew.FromMM(0.15))
            fp.Add(tri)
            trim(fp, edge)                      # la flecha queda dentro de la región permitida: no se toca
            unplace_and_save(fp, lib, TB_NEW)


def main():
    pcb, lib = sys.argv[1], sys.argv[2]
    if len(sys.argv) > 3:
        tarea(pcb, lib, sys.argv[3])
        return
    import subprocess
    for t in TAREAS:                      # un proceso por tarea: evita la falla intermitente de SWIG
        r = subprocess.run([sys.executable, os.path.abspath(__file__), pcb, lib, t], capture_output=True, text=True)
        if r.returncode:
            raise SystemExit(f'falló la tarea {t}: ' + r.stdout + r.stderr)
    print('footprints de fabricación generados en', lib, ':', ', '.join(TAREAS))


if __name__ == '__main__':
    main()
