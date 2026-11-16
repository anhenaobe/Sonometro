"""Agrega a una COPIA de la placa un relleno GND en B.Cu que cubre toda la placa y lo rellena.

Sirve solo para verificar un bloque antes de que existan los polígonos de tierra definitivos (bloque 9): con el plano
presente, las vías GND puestas junto a los pads dejan de figurar como colgantes y el chequeo I de revisar_pistas.py
(GND continuo bajo las pistas críticas) tiene contra qué medir. Nunca se aplica a pcb.kicad_pcb.
Uso (Python de KiCad): python zona_gnd_temporal.py <copia.kicad_pcb>
"""
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    path = os.path.abspath(sys.argv[1])
    real = os.path.abspath(os.path.join(HERE, '..', '..', 'pcb.kicad_pcb'))
    if os.path.normcase(path) == os.path.normcase(real):
        raise SystemExit('esto es solo para copias, no para la placa real')
    b = pcbnew.LoadBoard(path)
    bb = b.GetBoardEdgesBoundingBox()
    z = pcbnew.ZONE(b)
    z.SetLayer(pcbnew.B_Cu)
    z.SetNet(b.GetNetsByName()['GND'])
    z.SetZoneName('GND_TEMPORAL')
    z.SetAssignedPriority(0)
    z.SetLocalClearance(pcbnew.FromMM(0.2))
    z.SetMinThickness(pcbnew.FromMM(0.2))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    ol = z.Outline()
    ol.NewOutline()
    for x, y in ((bb.GetLeft(), bb.GetTop()), (bb.GetRight(), bb.GetTop()),
                 (bb.GetRight(), bb.GetBottom()), (bb.GetLeft(), bb.GetBottom())):
        ol.Append(x, y)
    b.Add(z)
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    pcbnew.SaveBoard(path, b)
    print('relleno GND temporal en B.Cu ->', path)


if __name__ == '__main__':
    main()
