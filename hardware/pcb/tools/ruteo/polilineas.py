"""Escribe pistas, vías y zonas de un bloque a partir de puntos dados a mano (ruteo por polilíneas).

Cada bloque se guarda en un grupo de KiCad ("ruteo:<bloque>"): al volver a aplicarlo se borra primero lo que ese
grupo tenía, así se puede corregir un bloque sin tocar los demás ni el resto de la placa.

Formato de un bloque (módulo Python en tools/ruteo/bloques/<nombre>.py) con estas listas:
  PISTAS = [ (red, ancho_mm, 'F.Cu'|'B.Cu', [(x, y), (x, y), ...]), ... ]     coordenadas KiCad en mm
  VIAS   = [ (red, (x, y), diametro_mm, taladro_mm), ... ]
  ZONAS  = [ dict(red=..., capa='F.Cu', prioridad=2, puntos=[(x, y), ...], conexion='solida'|'alivio'|'alivio_tht',
                  separacion=0.2, ancho_min=0.2), ... ]
Antes de escribir se valida: cada segmento múltiplo de 45°, largo >= 0.1 mm, giro entre segmentos de 0° o 45°.
Uso (Python de KiCad): python polilineas.py <pcb> <bloque>   (KiCad cerrado)
"""
import importlib.util
import math
import os
import subprocess
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))


def iu(p):
    # redondeo al nm: FromMM trunca (132.7 -> 132699999 nm) y eso tuerce 45° en 1e-4° (falla track_angle)
    return pcbnew.VECTOR2I(int(round(p[0] * 1e6)), int(round(p[1] * 1e6)))


def validar(red, pts):
    errs = []
    for a, b in zip(pts, pts[1:]):
        L = math.dist(a, b)
        if L < 0.1 - 1e-9:
            errs.append(f'{red}: segmento de {L:.3f} mm en {a}->{b}')
        ang = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0])) % 45
        if min(ang, 45 - ang) > 0.01:
            errs.append(f'{red}: segmento no múltiplo de 45° en {a}->{b}')
    for a, b, c in zip(pts, pts[1:], pts[2:]):
        v1 = (b[0] - a[0], b[1] - a[1])
        v2 = (c[0] - b[0], c[1] - b[1])
        cosang = (v1[0] * v2[0] + v1[1] * v2[1]) / (math.hypot(*v1) * math.hypot(*v2))
        giro = math.degrees(math.acos(max(-1, min(1, cosang))))
        if giro > 45.01:
            errs.append(f'{red}: giro de {giro:.0f}° en {b} (máximo 45°)')
    return errs


def cargar_bloque(nombre):
    path = nombre if nombre.endswith('.py') else os.path.join(HERE, 'bloques', nombre + '.py')
    nombre = os.path.splitext(os.path.basename(path))[0]
    spec = importlib.util.spec_from_file_location(nombre, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def borrar_grupo(b, nombre):
    for g in list(b.Groups()):
        if g.GetName() == 'ruteo:' + nombre:
            for it in list(g.GetItems()):
                b.Remove(it)
            b.Remove(g)


def aplicar(b, nombre, mod):
    errs = []
    for red, w, capa, pts in getattr(mod, 'PISTAS', []):
        errs += validar(red, pts)
    if errs:
        raise SystemExit('el bloque no cumple las reglas de trazado:\n  ' + '\n  '.join(errs))
    todas = b.GetNetsByName()

    def existe(red):
        try:
            todas[red]
            return True
        except (IndexError, KeyError):
            return False
    faltan = sorted(r for r in {x[0] for x in getattr(mod, 'PISTAS', []) + getattr(mod, 'VIAS', [])} |
                    {z['red'] for z in getattr(mod, 'ZONAS', [])} if not existe(r))
    if faltan:
        raise SystemExit('redes que no existen en la placa: ' + ', '.join(faltan))
    grupo = pcbnew.PCB_GROUP(b)
    grupo.SetName('ruteo:' + nombre)
    b.Add(grupo)
    nets = b.GetNetsByName()
    n_p = n_v = n_z = 0
    for red, w, capa, pts in getattr(mod, 'PISTAS', []):
        net = nets[red]
        for a, c in zip(pts, pts[1:]):
            t = pcbnew.PCB_TRACK(b)
            t.SetStart(iu(a))
            t.SetEnd(iu(c))
            t.SetWidth(pcbnew.FromMM(w))
            t.SetLayer(b.GetLayerID(capa))
            t.SetNet(net)
            b.Add(t)
            grupo.AddItem(t)
            n_p += 1
    for red, p, d, h in getattr(mod, 'VIAS', []):
        v = pcbnew.PCB_VIA(b)
        v.SetPosition(iu(p))
        v.SetWidth(pcbnew.FromMM(d))
        v.SetDrill(pcbnew.FromMM(h))
        v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        v.SetNet(nets[red])
        b.Add(v)
        grupo.AddItem(v)
        n_v += 1
    for z in getattr(mod, 'ZONAS', []):
        zone = pcbnew.ZONE(b)
        zone.SetLayer(b.GetLayerID(z.get('capa', 'F.Cu')))
        zone.SetNet(nets[z['red']])
        zone.SetAssignedPriority(z.get('prioridad', 0))
        zone.SetLocalClearance(pcbnew.FromMM(z.get('separacion', 0.2)))
        zone.SetMinThickness(pcbnew.FromMM(z.get('ancho_min', 0.2)))
        zone.SetPadConnection({'solida': pcbnew.ZONE_CONNECTION_FULL, 'alivio': pcbnew.ZONE_CONNECTION_THERMAL,
                               'alivio_tht': pcbnew.ZONE_CONNECTION_THT_THERMAL}[z.get('conexion', 'solida')])
        zone.SetThermalReliefGap(pcbnew.FromMM(z.get('alivio_gap', 0.3)))
        zone.SetThermalReliefSpokeWidth(pcbnew.FromMM(z.get('alivio_rayo', 0.4)))
        zone.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
        if z.get('nombre'):
            zone.SetZoneName(z['nombre'])
        ol = zone.Outline()
        ol.NewOutline()
        for p in z['puntos']:
            ol.Append(int(round(p[0] * 1e6)), int(round(p[1] * 1e6)))
        b.Add(zone)
        grupo.AddItem(zone)
        n_z += 1
    return n_p, n_v, n_z


def rellenar(b):
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())


def main():
    path, nombre = sys.argv[1], sys.argv[2]
    mod = cargar_bloque(nombre)
    nombre = os.path.splitext(os.path.basename(nombre))[0]
    if '--solo-borrar' in sys.argv:
        b = pcbnew.LoadBoard(path)
        borrar_grupo(b, nombre)
        pcbnew.SaveBoard(path, b)
        return
    # SWIG: después de b.Remove() la tabla de redes queda inservible y una segunda LoadBoard en el mismo proceso
    # también: el grupo viejo se borra en un proceso aparte y aquí se carga la placa limpia
    r = subprocess.run([sys.executable, os.path.abspath(__file__), path, sys.argv[2], '--solo-borrar'],
                       capture_output=True, text=True)
    if r.returncode:
        raise SystemExit('no se pudo borrar el grupo anterior: ' + r.stdout + r.stderr)
    b = pcbnew.LoadBoard(path)
    if any(g.GetName() == 'ruteo:' + nombre for g in b.Groups()):
        raise SystemExit('el grupo anterior sigue en la placa')
    n = aplicar(b, nombre, mod)
    rellenar(b)
    pcbnew.SaveBoard(path, b)
    print(f'bloque {nombre}: {n[0]} segmentos, {n[1]} vías, {n[2]} zonas -> {path}')


if __name__ == '__main__':
    main()
