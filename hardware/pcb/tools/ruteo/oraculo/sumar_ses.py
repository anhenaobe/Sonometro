"""Agrega a d.kicad_pcb (que conserva el ruteo fijo de los bloques 1-3) las pistas y vías nuevas del SES.
Unidades del SES: 0.1 um (resolution um 10); y invertida."""
import os
import re
import sys

import pcbnew

T = os.path.dirname(os.path.abspath(__file__))
ses = open(os.path.join(T, sys.argv[1] if len(sys.argv) > 1 else 'e.ses')).read()
b = pcbnew.LoadBoard(os.path.join(T, sys.argv[2] if len(sys.argv) > 2 else 'd.kicad_pcb'))
nets = b.GetNetsByName()
k = ses.index('(network_out')
body = ses[k:]
n_w = n_v = 0
for m in re.finditer(r'\(net ("[^"]*"|\S+)\s*(.*?)\n      \)', body, re.S):
    name = m.group(1).strip('"')
    blk = m.group(2)
    net = nets[name]
    for w in re.finditer(r'\(path (\S+) (\d+)\s+([-\d\s]+)\)', blk):
        layer = b.GetLayerID(w.group(1))
        width = int(w.group(2)) * 100
        nums = [int(v) for v in w.group(3).split()]
        pts = [(nums[i] * 100, -nums[i + 1] * 100) for i in range(0, len(nums), 2)]
        for a, c in zip(pts, pts[1:]):
            t = pcbnew.PCB_TRACK(b)
            t.SetStart(pcbnew.VECTOR2I(*a))
            t.SetEnd(pcbnew.VECTOR2I(*c))
            t.SetWidth(width)
            t.SetLayer(layer)
            t.SetNet(net)
            b.Add(t)
            n_w += 1
    for v in re.finditer(r'\(via "[^"]*" (-?\d+) (-?\d+)', blk):
        via = pcbnew.PCB_VIA(b)
        via.SetPosition(pcbnew.VECTOR2I(int(v.group(1)) * 100, -int(v.group(2)) * 100))
        via.SetWidth(600000)
        via.SetDrill(300000)
        via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        via.SetNet(net)
        b.Add(via)
        n_v += 1
pcbnew.SaveBoard(os.path.join(T, sys.argv[3] if len(sys.argv) > 3 else 's.kicad_pcb'), b)
print('agregados', n_w, 'segmentos y', n_v, 'vías')
