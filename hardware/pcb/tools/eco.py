"""Cambios en sitio sobre la placa (tipo ECO), sin regenerarla: conserva todo lo demás (pistas, zonas, textos).

Funciones:
  swap_footprint(b, ref, lib_path, name): cambia el footprint conservando posición, giro, cara, campos,
      enlace al esquemático (KIID path) y la red de cada pad por número.
  move(b, ref, dx, dy): mueve una pieza (mm; +y hacia abajo, como KiCad).
  add_fiducial(b, ref, x, y): fiducial 1 mm / máscara 2 mm como pieza solo de placa (fuera de BOM y CPL).
Uso como script (Python de KiCad), sobre la placa dada:
  python eco.py <pcb> sync | tsot | serigrafia | j1j7 | fiduciales | todo   (todo = sync + j1j7 + fiduciales)
"""
import math
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ_LIB = os.path.join(HERE, '..', 'lib', 'Sonometro.pretty')
KLIB = 'C:/Program Files/KiCad/10.0/share/kicad/footprints'
TSOT_NEW = 'TSOT-23-8_Pad0.40x1.22mm_P0.65mm_ADI'
BOARD_X0, BOARD_Y1 = 100.0, 164.0                    # esquina inferior izquierda de la placa (KiCad mm)
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


FIDUCIALES = {'FID1': (4.5, 5.0), 'FID2': (82.0, 6.0), 'FID3': (16.0, 44.0)}   # mm desde abajo-izquierda


def swap_footprint(b, ref, lib_path, name, lib_nick='Sonometro'):
    old = b.FindFootprintByReference(ref)
    new = _load(lib_path, name)
    if old is None or new is None:
        raise SystemExit(f'no se pudo cambiar {ref} -> {name}')
    new.SetFPID(pcbnew.LIB_ID(lib_nick, name))
    new.SetParent(b)
    new.SetLayer(old.GetLayer())
    new.SetOrientation(old.GetOrientation())
    new.SetPosition(old.GetPosition())
    new.SetPath(old.GetPath())
    new.SetReference(old.GetReference())
    new.SetValue(old.GetValue())
    new.SetAttributes(old.GetAttributes())
    for f in old.GetFields():
        if f.GetName() in ('Reference', 'Value', 'Footprint'):
            continue
        new.SetField(f.GetName(), f.GetText())
        new.GetField(f.GetName()).SetVisible(False)
    nets = {p.GetNumber(): p.GetNet() for p in old.Pads()}
    for p in new.Pads():
        if p.GetNumber() in nets:
            p.SetNet(nets[p.GetNumber()])
    # el designador conserva la posición y el giro del anterior
    new.Reference().SetPosition(old.Reference().GetPosition())
    new.Reference().SetTextAngle(old.Reference().GetTextAngle())
    b.Remove(old)
    b.Add(new)
    return new


def move(b, ref, dx, dy):
    fp = b.FindFootprintByReference(ref)
    p = fp.GetPosition()
    fp.SetPosition(pcbnew.VECTOR2I(p.x + pcbnew.FromMM(dx), p.y + pcbnew.FromMM(dy)))


def add_fiducial(b, ref, x, y):
    if b.FindFootprintByReference(ref):
        b.Remove(b.FindFootprintByReference(ref))
    fp = _load(os.path.join(KLIB, 'Fiducial.pretty'), 'Fiducial_1mm_Mask2mm')
    fp.SetFPID(pcbnew.LIB_ID('Fiducial', 'Fiducial_1mm_Mask2mm'))
    fp.SetParent(b)
    fp.SetReference(ref)
    fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(BOARD_X0 + x), pcbnew.FromMM(BOARD_Y1 - y)))
    fp.SetBoardOnly(True)
    fp.SetExcludedFromBOM(True)
    fp.SetExcludedFromPosFiles(True)
    fp.Reference().SetVisible(False)
    b.Add(fp)
    return fp


def sync(b):
    """Iguala los footprints de la placa a target.json y recarga los de la librería del proyecto."""
    import json
    T = json.load(open(os.path.join(HERE, 'target.json')))
    n = 0
    for fp in list(b.GetFootprints()):
        ref = fp.GetReference()
        if ref not in T:
            continue
        lib, name = T[ref]['fp'].split(':')
        if lib == 'Sonometro' or fp.GetFPIDAsString() != T[ref]['fp']:
            path = PROJ_LIB if lib == 'Sonometro' else os.path.join(KLIB, lib + '.pretty')
            swap_footprint(b, ref, path, name, lib)
            n += 1
    return n


def _netlist(xml_path):
    import xml.etree.ElementTree as ET
    root = ET.parse(xml_path).getroot()
    comps, padnet = {}, {}
    for c in root.iter('comp'):
        comps[c.get('ref')] = dict(value=c.findtext('value'), fp=c.findtext('footprint'),
                                   tstamp=c.findtext('tstamps').split()[0],
                                   fields={f.get('name'): (f.text or '') for f in c.iter('field')})
    for n in root.iter('net'):
        name = n.get('name')
        if name.startswith(('unconnected-(', 'Net-(')):      # KiCad escapa la '/' de los nombres de pin
            name = name.replace('/', '{slash}')
        for nd in n.iter('node'):
            padnet[(nd.get('ref'), nd.get('pin'))] = name
    return comps, padnet


def _bbox_mm(bb):
    return (pcbnew.ToMM(bb.GetLeft()), pcbnew.ToMM(bb.GetTop()), pcbnew.ToMM(bb.GetRight()), pcbnew.ToMM(bb.GetBottom()))


def buscar_lugar(b, fp, objetivos, radio=5.0, paso=0.25, margen=0.05):
    """Posición libre (sin solapar courtyards, dentro de la placa) más cerca de los puntos objetivo (mm)."""
    otros = []
    for f in b.GetFootprints():
        if f is fp:
            continue
        cy = f.GetCourtyard(pcbnew.F_CrtYd)
        if cy.OutlineCount():
            otros.append(_bbox_mm(cy.BBox()))
    edge = _bbox_mm(b.GetBoardEdgesBoundingBox())
    cx = sum(p[0] for p in objetivos) / len(objetivos)
    cy0 = sum(p[1] for p in objetivos) / len(objetivos)
    mejor = None
    n = int(radio / paso)
    for rot in (0, 90):
        fp.SetOrientationDegrees(rot)
        for i in range(-n, n + 1):
            for j in range(-n, n + 1):
                x, y = cx + i * paso, cy0 + j * paso
                fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y)))
                fp.BuildCourtyardCaches()
                r = _bbox_mm(fp.GetCourtyard(pcbnew.F_CrtYd).BBox())
                if r[0] < edge[0] + 0.5 or r[2] > edge[2] - 0.5 or r[1] < edge[1] + 0.5 or r[3] > edge[3] - 0.5:
                    continue
                if any(r[0] < o[2] + margen and o[0] < r[2] + margen and r[1] < o[3] + margen and o[1] < r[3] + margen
                       for o in otros):
                    continue
                pads = {p.GetNumber(): (pcbnew.ToMM(p.GetPosition().x), pcbnew.ToMM(p.GetPosition().y))
                        for p in fp.Pads()}
                costo = sum(math.dist(pads[k], q) for k, q in objetivos_por_pad(objetivos, pads))
                if mejor is None or costo < mejor[0]:
                    mejor = (costo, x, y, rot)
    return mejor


def objetivos_por_pad(objetivos, pads):
    """objetivos = [(x, y), (x, y)] en el orden de los pads '1', '2'."""
    return list(zip(sorted(pads), objetivos))


def sync_netlist(b, xml_path, nuevos):
    """Valor, campos y red de cada pad desde la netlist del esquemático; agrega las piezas que faltan.
    nuevos = {ref: [(x, y) objetivo del pad 1, (x, y) del pad 2]} para ubicarlas junto a sus pines."""
    comps, padnet = _netlist(xml_path)
    nets = {str(k): v for k, v in b.GetNetsByName().items()}

    def net(name):
        if name not in nets:
            ni = pcbnew.NETINFO_ITEM(b, name)
            b.Add(ni)
            nets[name] = ni
        return nets[name]
    have = {fp.GetReference(): fp for fp in b.GetFootprints()}
    added = []
    for ref, c in comps.items():
        fp = have.get(ref)
        if fp is None:
            lib, name = c['fp'].split(':')
            fp = _load(PROJ_LIB if lib == 'Sonometro' else os.path.join(KLIB, lib + '.pretty'), name)
            fp.SetFPID(pcbnew.LIB_ID(lib, name))
            fp.SetParent(b)
            fp.SetReference(ref)
            fp.SetPath(pcbnew.KIID_PATH('/' + c['tstamp']))
            fp.SetSheetname('/')
            fp.SetSheetfile('pcb.kicad_sch')
            b.Add(fp)
            added.append(ref)
        fp.SetValue(c['value'])
        for fname, val in c['fields'].items():
            if fname in ('Footprint', 'Reference', 'Value'):
                continue
            fp.SetField(fname, val)
            f = fp.GetField(fname)
            if f is not None:
                f.SetVisible(False)
                f.SetLayer(pcbnew.F_Fab)
        for pad in fp.Pads():
            n = padnet.get((ref, pad.GetNumber()))
            if n and pad.GetNetname() != n:
                pad.SetNet(net(n))
    for ref in added:
        if ref in nuevos:
            fp = b.FindFootprintByReference(ref)
            mejor = buscar_lugar(b, fp, nuevos[ref])
            if mejor is None:
                raise SystemExit(f'no hay lugar libre para {ref}')
            fp.SetOrientationDegrees(mejor[3])
            fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(mejor[1]), pcbnew.FromMM(mejor[2])))
            print(f'  {ref} ubicado en ({mejor[1]:.2f}, {mejor[2]:.2f}) giro {mejor[3]}')
    return added


def mover_bucks(b):
    """Punto de control (aprobado): CHF C29/C39 suben 0.3 mm; CBOOT C35/C45 a la izquierda del integrado, girados."""
    for ref, (x, y, rot) in {'C29': (126.15, 107.7, 90), 'C39': (147.75, 107.7, 90),
                             'C35': (126.4, 111.2, 90), 'C45': (148.0, 111.2, 90)}.items():
        fp = b.FindFootprintByReference(ref)
        fp.SetOrientationDegrees(rot)
        fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y)))


def main():
    path, what = sys.argv[1], sys.argv[2]
    b = pcbnew.LoadBoard(path)
    if what == 'colocar':                          # movimientos aprobados por el dueño: {ref: [x, y, giro, 'aprobación']}
        import json
        for ref, (x, y, rot, nota) in json.load(open(sys.argv[3], encoding='utf-8')).items():
            fp = b.FindFootprintByReference(ref)
            fp.SetOrientationDegrees(rot)
            fp.SetPosition(pcbnew.VECTOR2I(int(round(x * 1e6)), int(round(y * 1e6))))
            print(f'  {ref} -> ({x}, {y}) giro {rot}: {nota}')
    if what == 'alinear':                          # micro-alineación de pads (aprobada): {ref: [dx, dy]} en mm
        import json
        movs = json.load(open(sys.argv[3]))
        for ref, (dx, dy) in movs.items():
            if abs(dx) > 0.1 or abs(dy) > 0.1:
                raise SystemExit(f'{ref}: {dx}, {dy} supera 0.1 mm (requiere aprobación aparte)')
            fp = b.FindFootprintByReference(ref)
            p = fp.GetPosition()
            fp.SetPosition(pcbnew.VECTOR2I(p.x + int(round(dx * 1e6)), p.y + int(round(dy * 1e6))))
        print(f'alineadas {len(movs)} piezas')
    if what == 'cp2':                              # cambios del punto de control (bucks, CF, piezas)
        mover_bucks(b)
        pads = lambda r, n: (pcbnew.ToMM(b.FindFootprintByReference(r).FindPadByNumber(n).GetPosition().x),  # noqa
                             pcbnew.ToMM(b.FindFootprintByReference(r).FindPadByNumber(n).GetPosition().y))
        nuevos = {'C56': [pads('U3', '2'), pads('U3', '1')], 'C57': [pads('U9', '2'), pads('U9', '1')]}
        print('agregados:', sync_netlist(b, sys.argv[3], nuevos))
    if what in ('sync', 'todo'):
        print('footprints actualizados:', sync(b))
    if what == 'tsot':
        for ref in ('U1', 'U3', 'U8', 'U9'):
            swap_footprint(b, ref, PROJ_LIB, TSOT_NEW)
    if what == 'serigrafia':                    # footprints con serigrafía recortada al borde
        for ref in ('J1', 'J5', 'J7'):
            swap_footprint(b, ref, PROJ_LIB, 'TerminalBlock_MaiXu_MX126-5.0-02P_1x02_P5.00mm_Borde')
        for ref in ('J2', 'J8'):
            swap_footprint(b, ref, PROJ_LIB, 'BNC_Kinghelm_KH-BNC75-3511_Horizontal')
        swap_footprint(b, 'A1', PROJ_LIB, 'NUCLEO-32_Socket_2x15_P2.54mm_Row15.24mm')
    if what == 'j1j7':
        for ref in ('J1', 'J7'):
            move(b, ref, 0, 0.6)
    if what in ('fiduciales', 'todo'):
        for ref, (x, y) in FIDUCIALES.items():
            add_fiducial(b, ref, x, y)
    pcbnew.SaveBoard(path, b)
    print('ECO aplicado:', what, '->', path)


if __name__ == '__main__':
    main()
