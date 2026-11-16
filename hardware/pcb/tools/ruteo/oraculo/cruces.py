"""Tabla de cruces del oráculo: cada tramo en B.Cu (red, largo, zona) y qué pistas de F.Cu pasan por encima.

Uso (Python de KiCad): python cruces.py <placa_con_ses.kicad_pcb>
"""
import collections
import math
import sys

import pcbnew

mm = pcbnew.ToMM
b = pcbnew.LoadBoard(sys.argv[1])
CRIT = {'Analogica', 'Reloj', 'Conmutado'}
NO_CRIT = {'Net-(J1-Pin_2)', 'Net-(J7-Pin_2)'}
segs = []
for t in b.GetTracks():
    if t.GetClass() != 'PCB_TRACK':
        continue
    a, c = t.GetStart(), t.GetEnd()
    segs.append(((mm(a.x), mm(a.y)), (mm(c.x), mm(c.y)), t.GetLayer(), t.GetNetname(), t.GetNetClassName(),
                 mm(t.GetWidth())))


def inter(p1, p2, p3, p4):
    def o(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
    return o(p1, p2, p3) * o(p1, p2, p4) < 0 and o(p3, p4, p1) * o(p3, p4, p2) < 0


# agrupa los tramos de B.Cu en "puentes" (componentes conexas por extremos)
bsegs = [s for s in segs if s[2] == pcbnew.B_Cu]
grupos = []
for s in bsegs:
    g = next((g for g in grupos if g['net'] == s[3] and any(math.dist(e, p) < 0.01 for e in (s[0], s[1])
                                                               for q in g['segs'] for p in (q[0], q[1]))), None)
    if g is None:
        g = {'net': s[3], 'segs': []}
        grupos.append(g)
    g['segs'].append(s)
fsegs = [s for s in segs if s[2] == pcbnew.F_Cu]
print(f"{'red':16s} {'largo':>6s}  {'x':>13s} {'y':>13s}  zona dig.  cruza por encima (F.Cu)")
for g in grupos:
    L = sum(math.dist(s[0], s[1]) for s in g['segs'])
    xs = [p[0] for s in g['segs'] for p in (s[0], s[1])]
    ys = [p[1] for s in g['segs'] for p in (s[0], s[1])]
    sobre = collections.Counter()
    for s in g['segs']:
        for f in fsegs:
            if f[3] != g['net'] and inter(s[0], s[1], f[0], f[1]):
                tipo = 'CRÍTICA' if f[4] in CRIT and f[3] not in NO_CRIT else f[4]
                sobre[f'{f[3]} ({tipo})'] += 1
    dig = 'sí' if min(xs) >= 170 else 'no'
    print(f"{g['net'][:16]:16s} {L:6.1f}  {min(xs):6.1f}-{max(xs):6.1f} {min(ys):6.1f}-{max(ys):6.1f}  {dig:9s}"
          f"  {', '.join(sobre) or '-'}")
