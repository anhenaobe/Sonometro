"""Cambios en sitio sobre la placa (tipo ECO), sin regenerarla: conserva todo lo demás (pistas, zonas, textos).

Funciones:
  swap_footprint(b, ref, lib_path, name): cambia el footprint conservando posición, giro, cara, campos,
      enlace al esquemático (KIID path) y la red de cada pad por número.
  move(b, ref, dx, dy): mueve una pieza (mm; +y hacia abajo, como KiCad).
  add_fiducial(b, ref, x, y): fiducial 1 mm / máscara 2 mm como pieza solo de placa (fuera de BOM y CPL).
Uso como script (Python de KiCad), sobre la placa dada:
  python eco.py <pcb> sync | tsot | serigrafia | j1j7 | fiduciales | todo   (todo = sync + j1j7 + fiduciales)
"""
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


def main():
    path, what = sys.argv[1], sys.argv[2]
    b = pcbnew.LoadBoard(path)
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
