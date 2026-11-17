"""Exporta el placement (cajas de courtyard, pads, refs) de pcb.kicad_pcb a guia/placement.json.
Corre con el Python de KiCad: "C:/Program Files/KiCad/10.0/bin/python.exe" tools/dump_placement.py"""
import json
import os
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
b = pcbnew.LoadBoard(os.path.join(HERE, '..', 'pcb.kicad_pcb'))
out = {'edge': None, 'fps': []}
bb = b.GetBoardEdgesBoundingBox()
out['edge'] = [pcbnew.ToMM(bb.GetLeft()), pcbnew.ToMM(bb.GetTop()), pcbnew.ToMM(bb.GetRight()), pcbnew.ToMM(bb.GetBottom())]
for fp in b.GetFootprints():
    fp.BuildCourtyardCaches()
    cy = fp.GetCourtyard(pcbnew.F_CrtYd)
    if cy.OutlineCount():
        r = cy.BBox()
        box = [pcbnew.ToMM(r.GetLeft()), pcbnew.ToMM(r.GetTop()), pcbnew.ToMM(r.GetRight()), pcbnew.ToMM(r.GetBottom())]
    else:
        r = fp.GetBoundingBox(False)
        box = [pcbnew.ToMM(r.GetLeft()), pcbnew.ToMM(r.GetTop()), pcbnew.ToMM(r.GetRight()), pcbnew.ToMM(r.GetBottom())]
    fab = fp.GetBoundingBox(False)
    pads = []
    for p in fp.Pads():
        pr = p.GetBoundingBox()
        pads.append([pcbnew.ToMM(pr.GetLeft()), pcbnew.ToMM(pr.GetTop()), pcbnew.ToMM(pr.GetRight()),
                     pcbnew.ToMM(pr.GetBottom()), p.GetNumber(), p.GetNetname()])
    pos = fp.GetPosition()
    out['fps'].append({'ref': fp.GetReference(), 'value': fp.GetValue(), 'x': pcbnew.ToMM(pos.x), 'y': pcbnew.ToMM(pos.y),
                       'rot': fp.GetOrientationDegrees(), 'box': box,
                       'body': [pcbnew.ToMM(fab.GetLeft()), pcbnew.ToMM(fab.GetTop()), pcbnew.ToMM(fab.GetRight()), pcbnew.ToMM(fab.GetBottom())],
                       'pads': pads})
json.dump(out, open(os.path.join(HERE, 'guia', 'placement.json'), 'w'), indent=0)
print(len(out['fps']), 'footprints; borde', out['edge'])
