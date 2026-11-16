"""Revisa los Gerber y taladros de fabricacion/gerber con una biblioteca existente (gerbonara), sin lector propio.

Correr con un Python que tenga gerbonara (entorno aparte, `pip install gerbonara`):
  <python con gerbonara> tools/revisar_gerber.py [carpeta_gerber]  -> fabricacion/revision_gerber.md + vistas SVG
Comprueba:
  1. capas reconocidas (4 de cobre, máscaras, serigrafías, pastas, borde, taladros);
  2. borde: caja de 90 × 64 mm y contorno cerrado;
  3. cada agujero PTH cae en un pad o vía flasheado en F.Cu y en B.Cu, con anillo >= 0.15 mm;
  4. máscara: ninguna apertura sobre una vía (agujeros de 0.3 mm);
  5. serigrafía: ningún trazo dentro de una apertura de máscara.
"""
import math
import os
import sys
import warnings

from gerbonara import LayerStack
from gerbonara.graphic_objects import Flash, Line, Arc, Region
from gerbonara.utils import MM

HERE = os.path.dirname(os.path.abspath(__file__))
FAB = os.path.join(HERE, '..', 'fabricacion')


def caja(obj):
    (x0, y0), (x1, y1) = obj.bounding_box(MM)
    return x0, y0, x1, y1


def main():
    gdir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(FAB, 'gerber')
    avisos = []
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter('always')
        s = LayerStack.open(gdir)
        avisos = sorted({str(x.message)[-80:] for x in w})
    out = []
    p = out.append
    p('# Revisión de los Gerber con gerbonara\n')
    p('Generado por `tools/revisar_gerber.py` (gerbonara, biblioteca existente; sin lector propio).\n')
    p('## 1. Capas reconocidas\n')
    p('| Capa | Archivo | Objetos |\n|---|---|---|')
    for (lado, uso), g in sorted(s.graphic_layers.items(), key=lambda kv: str(kv[0])):
        p(f'| {lado} {uso} | {os.path.basename(str(g.original_path))} | {len(g.objects)} |')
    for d in s.drill_layers:
        p(f'| taladro | {os.path.basename(str(d.original_path))} | {len(d.objects)} |')
    if avisos:
        p('\nAvisos del lector: ' + '; '.join(avisos))
    npth = os.path.join(gdir, 'pcb-NPTH.drl')
    if os.path.exists(npth) and not any('NPTH' in str(d.original_path) for d in s.drill_layers):
        p('\n`pcb-NPTH.drl` no tiene agujeros (la placa no lleva NPTH); se envía igual, como pide JLC.')
    # ---------------- 2. borde
    ol = s.outline
    segs = [o for o in ol.objects if isinstance(o, (Line, Arc))]
    xs, ys = [], []
    extremos = {}
    for o in segs:
        for (x, y) in ((o.x1, o.y1), (o.x2, o.y2)):
            k = (round(o.unit.convert_to(MM, x), 3), round(o.unit.convert_to(MM, y), 3))
            extremos[k] = extremos.get(k, 0) + 1
            xs.append(k[0])
            ys.append(k[1])
    cerrado = all(v % 2 == 0 for v in extremos.values())
    p('\n## 2. Borde\n')
    p(f'- {len(segs)} segmentos; caja {max(xs) - min(xs):.2f} × {max(ys) - min(ys):.2f} mm; '
      f'contorno {"cerrado" if cerrado else "ABIERTO"}.')
    # ---------------- 3. agujeros sobre pads
    def flashes(g):
        res = []
        for o in g.objects:
            if isinstance(o, Flash):
                x0, y0, x1, y1 = caja(o)
                res.append(((x0 + x1) / 2, (y0 + y1) / 2, min(x1 - x0, y1 - y0)))
        return res
    top = flashes(s.graphic_layers[('top', 'copper')])
    bot = flashes(s.graphic_layers[('bottom', 'copper')])
    holes = []
    for d in s.drill_layers:
        for o in d.objects:
            if isinstance(o, Flash):
                x0, y0, x1, y1 = caja(o)
                holes.append(((x0 + x1) / 2, (y0 + y1) / 2, x1 - x0, 'npth' if 'NPTH' in str(d.original_path) else 'pth'))
    malos = []
    anillo_min = 9.0
    for x, y, dia, kind in holes:
        if kind != 'pth':
            continue
        for nombre, fl in (('F.Cu', top), ('B.Cu', bot)):
            m = [f for f in fl if math.hypot(f[0] - x, f[1] - y) < 0.01]
            if not m:
                malos.append(f'agujero de {dia:.2f} mm en ({x:.2f}, {y:.2f}) sin pad en {nombre}')
                continue
            anillo = (max(f[2] for f in m) - dia) / 2
            anillo_min = min(anillo_min, anillo)
    tam = {}
    for x, y, dia, kind in holes:
        tam[(kind, round(dia, 2))] = tam.get((kind, round(dia, 2)), 0) + 1
    p('\n## 3. Agujeros\n')
    p('- ' + ', '.join(f'{n} {k} de {d} mm' for (k, d), n in sorted(tam.items())))
    p(f'- PTH sobre un pad o vía flasheado en F.Cu y B.Cu: {"todos" if not malos else f"{len(malos)} sin pad"}; '
      f'anillo mínimo {anillo_min:.3f} mm.')
    for m in malos[:20]:
        p(f'  - {m}')
    # ---------------- 4. máscara sobre vías
    vias = [(x, y) for x, y, dia, kind in holes if kind == 'pth' and abs(dia - 0.3) < 0.01]
    p('\n## 4. Máscara sobre las vías\n')
    for lado in ('top', 'bottom'):
        mk = flashes(s.graphic_layers[(lado, 'mask')])
        en = sum(1 for v in vias if any(math.hypot(f[0] - v[0], f[1] - v[1]) < 0.01 for f in mk))
        p(f'- {lado}: {len(mk)} aperturas, **{en}** sobre alguna de las {len(vias)} vías.')
    # ---------------- 5. serigrafía dentro de aperturas de máscara
    p('\n## 5. Serigrafía sobre aperturas de máscara\n')
    for lado in ('top', 'bottom'):
        mk = [caja(o) for o in s.graphic_layers[(lado, 'mask')].objects if isinstance(o, (Flash, Region))]
        n = 0
        claras = 0
        for o in s.graphic_layers[(lado, 'silk')].objects:
            if not getattr(o, 'polarity_dark', True):
                claras += 1                          # recorte de máscara (--subtract-soldermask), no es serigrafía
                continue
            if isinstance(o, Line):
                pts = [(o.unit.convert_to(MM, o.x1 + (o.x2 - o.x1) * k / 4), o.unit.convert_to(MM, o.y1 + (o.y2 - o.y1) * k / 4))
                       for k in range(5)]
            elif isinstance(o, Flash):
                x0, y0, x1, y1 = caja(o)
                pts = [((x0 + x1) / 2, (y0 + y1) / 2)]
            else:
                continue
            if any(r[0] + 0.02 < q[0] < r[2] - 0.02 and r[1] + 0.02 < q[1] < r[3] - 0.02 for q in pts for r in mk):
                n += 1
        p(f'- {lado}: {n} trazos de serigrafía (polaridad oscura) con un punto dentro de la caja de una apertura de '
          f'máscara; {claras} objetos de polaridad clara = recorte de la máscara que hace KiCad con '
          f'--subtract-soldermask.')
    # ---------------- vistas
    for lado, nombre in (('top', 'superior'), ('bottom', 'inferior')):
        try:
            svg = s.to_pretty_svg(side=lado)
            open(os.path.join(FAB, f'vista_gerber_{nombre}.svg'), 'w', encoding='utf-8').write(str(svg))
            p(f'\nVista {nombre}: `vista_gerber_{nombre}.svg` (abrir en el navegador).')
        except Exception as e:                       # la vista es ayuda visual; la revisión no depende de ella
            p(f'\nVista {nombre}: no se pudo generar ({e}).')
    open(os.path.join(FAB, 'revision_gerber.md'), 'w', encoding='utf-8').write('\n'.join(out) + '\n')
    print('\n'.join(out))


if __name__ == '__main__':
    main()
