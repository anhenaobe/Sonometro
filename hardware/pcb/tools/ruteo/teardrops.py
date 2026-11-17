"""Bloque 10: activa los teardrops en todos los pads y vías de la placa (parámetros por defecto de KiCad 10).

KiCad guarda los teardrops como zonas de tipo teardrop. No hace falta la GUI: `kicad-cli pcb drc --refill-zones
--save-board` (lo que corre verificar_bloque.py) los genera para cada pad o vía que los tenga activados. Comprobado
en una copia tras el bloque 9: 440 zonas teardrop, DRC 0 y revisar_pistas 0.
Uso (Python de KiCad, KiCad cerrado): python teardrops.py <pcb>
"""
import sys

import pcbnew


def main():
    path = sys.argv[1]
    b = pcbnew.LoadBoard(path)
    n_p = n_v = 0
    for fp in b.GetFootprints():
        for p in fp.Pads():
            if p.GetNetname():                  # los fiduciales no tienen red ni pistas
                p.SetTeardropsEnabled(True)
                n_p += 1
    for t in b.GetTracks():
        if t.GetClass() == 'PCB_VIA':
            t.SetTeardropsEnabled(True)
            n_v += 1
    pcbnew.SaveBoard(path, b)
    print(f'teardrops activados: {n_p} pads, {n_v} vías -> {path}')


if __name__ == '__main__':
    main()
