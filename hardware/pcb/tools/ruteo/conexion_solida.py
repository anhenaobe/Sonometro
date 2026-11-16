"""Punto 8 de la revisión del bloque 1: los pads GND de CIN, CHF y COUT y los pines PGND de cada buck quedan unidos por
el relleno GND de F.Cu con conexión sólida (sin alivios térmicos).

Para cada pad se comprueba que el centro y dos esquinas interiores caen dentro de la misma isla del relleno GND_FCU
(pad cubierto entero = sin rayos de alivio) y que el pad no tiene una conexión a zona fijada localmente.
Uso (Python de KiCad): python conexion_solida.py [pcb]   -> sale con código 1 si algún pad no cumple.
"""
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
BUCKS = {'U6': ['C27', 'C28', 'C29', 'C30', 'C31', 'C32', 'C33', 'C34'],
         'U7': ['C37', 'C38', 'C39', 'C40', 'C41', 'C42', 'C43', 'C44']}
PGND = ('1', '11')


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, '..', '..', 'pcb.kicad_pcb')
    b = pcbnew.LoadBoard(path)
    z = [z for z in b.Zones() if z.GetZoneName() == 'GND_FCU'][0]
    fill = z.GetFilledPolysList(pcbnew.F_Cu)
    ok = True
    for buck, refs in BUCKS.items():
        filas = []
        for r in refs + [buck]:
            for q in b.FindFootprintByReference(r).Pads():
                if q.GetNetname() != 'GND' or (r == buck and q.GetNumber() not in PGND):
                    continue
                bb = q.GetBoundingBox()
                pts = [q.GetPosition(), pcbnew.VECTOR2I(bb.GetLeft() + 20000, bb.GetTop() + 20000),
                       pcbnew.VECTOR2I(bb.GetRight() - 20000, bb.GetBottom() - 20000)]
                isla = next((i for i in range(fill.OutlineCount()) if all(fill.Contains(p, i) for p in pts)), None)
                local = q.GetLocalZoneConnection() != pcbnew.ZONE_CONNECTION_INHERITED
                filas.append((f'{r}.{q.GetNumber()}', isla, local))
        islas = {i for _, i, _ in filas}
        bien = len(islas) == 1 and None not in islas and not any(l for *_, l in filas)
        ok &= bien
        print(f'{buck}: {len(filas)} pads GND (CIN, CHF, COUT, PGND 1/11) en la isla {sorted(islas)} del relleno; '
              f'{"sólida, sin alivios" if bien else "NO CUMPLE"}: ' + ', '.join(n for n, *_ in filas))
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
