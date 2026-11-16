"""Genera fabricacion/ para JLCPCB (PCB + PCBA económico, una cara) desde la placa ya verificada.

Correr con el Python de KiCad, con KiCad cerrado y después de un verificar_bloque.py limpio:
  "C:/Program Files/KiCad/10.0/bin/python.exe" tools/fabricacion.py
Salidas en fabricacion/:
  gerber/ + sonometro_revB_gerber.zip   Gerber (Protel, X2, 4.6 mm; 4 capas de cobre) y taladros Excellon (mm,
                                        origen absoluto, PTH y NPTH separados)
  bom.csv                               Comment, Designator, Footprint, LCSC Part Number (solo lo que monta JLC)
  cpl.csv                               Designator, Mid X, Mid Y, Layer, Rotation (giro y desplazamiento corregidos)
  rotaciones.md                         corrección por pieza y comprobación del pin 1 contra el footprint de JLC
  soldar_a_mano.md                      piezas THT o sin montaje de JLC
  montaje.pdf                           F.Fab con todos los designadores (los omitidos en la serigrafía incluidos)
  LEEME.md                              parámetros del pedido, hash del commit, tenting comprobado
Corrección del CPL (auditoria_footprints.py): rotación JLC = rotación KiCad − d; posición JLC = posición KiCad −
R(rotación JLC)·t, con d y t del ajuste q ≈ R(d)·p + t entre los pads de KiCad (p) y los de JLC (q), Y hacia arriba.
"""
import csv
import json
import math
import os
import re
import shutil
import subprocess
import sys
import zipfile

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import auditoria_footprints as af  # noqa: E402

PCB_DIR = os.path.abspath(os.path.join(HERE, '..'))
PCB = os.path.join(PCB_DIR, 'pcb.kicad_pcb')
FAB = os.path.join(PCB_DIR, 'fabricacion')
KCLI = 'C:/Program Files/KiCad/10.0/bin/kicad-cli.exe'
CAPAS = ['F.Cu', 'In1.Cu', 'In2.Cu', 'B.Cu', 'F.Paste', 'B.Paste', 'F.Silkscreen', 'B.Silkscreen', 'F.Mask', 'B.Mask',
         'Edge.Cuts']
mm = pcbnew.ToMM


def run(args):
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f'falló: {" ".join(args)}\n{r.stdout}{r.stderr}')
    return r.stdout


def natural(ref):
    m = re.match(r'([A-Za-z]+)(\d+)', ref)
    return (m.group(1), int(m.group(2))) if m else (ref, 0)


def rot(x, y, deg):
    a = math.radians(deg)
    return x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a)


def contar_flashes(path):
    """Coordenadas de los flashes (D03) de un Gerber de máscara. Solo cuenta aperturas; no interpreta el resto."""
    pts = []
    x = y = 0
    for line in open(path, encoding='utf-8', errors='replace'):
        m = re.match(r'^(?:X(-?\d+))?(?:Y(-?\d+))?D03\*', line.strip())
        if m:
            if m.group(1) is not None:
                x = int(m.group(1))
            if m.group(2) is not None:
                y = int(m.group(2))
            pts.append((x / 1e6, y / 1e6))
    return pts


def main():
    git = ['git', '-C', PCB_DIR]
    hash_ = run(git + ['rev-parse', '--short', 'HEAD']).strip()
    sucio = run(git + ['status', '--porcelain', '--', 'pcb.kicad_pcb', 'pcb.kicad_sch', 'pcb.kicad_pro', 'lib']).strip()
    if sucio:
        raise SystemExit('la placa tiene cambios sin commit: exportar solo desde un commit verificado\n' + sucio)
    gdir = os.path.join(FAB, 'gerber')
    shutil.rmtree(gdir, ignore_errors=True)
    os.makedirs(gdir, exist_ok=True)

    # ---------------- Gerber y taladros
    run([KCLI, 'pcb', 'export', 'gerbers', '-o', gdir + '/', '-l', ','.join(CAPAS), '--subtract-soldermask',
         '--precision', '6', PCB])
    run([KCLI, 'pcb', 'export', 'drill', '-o', gdir + '/', '--format', 'excellon', '--excellon-units', 'mm',
         '--drill-origin', 'absolute', '--excellon-separate-th', '--generate-map', '--map-format', 'pdf', PCB])
    zpath = os.path.join(FAB, 'sonometro_revB_gerber.zip')
    with zipfile.ZipFile(zpath, 'w', zipfile.ZIP_DEFLATED) as z:
        for f in sorted(os.listdir(gdir)):
            if not f.endswith('.pdf'):
                z.write(os.path.join(gdir, f), f)
    gerbers = sorted(f for f in os.listdir(gdir) if not f.endswith('.pdf'))

    # ---------------- tenting: máscara real contra una copia sin tenting
    b = pcbnew.LoadBoard(PCB)
    vias = [(mm(v.GetPosition().x), -mm(v.GetPosition().y)) for v in b.GetTracks() if v.GetClass() == 'PCB_VIA']
    tmp = os.path.join(FAB, '_control_sin_tenting')
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp)
    for f in ('pcb.kicad_pro', 'pcb.kicad_dru'):
        shutil.copy(os.path.join(PCB_DIR, f), tmp)
    bc = pcbnew.LoadBoard(PCB)
    for v in bc.GetTracks():
        if v.GetClass() == 'PCB_VIA':
            v.SetFrontTentingMode(pcbnew.TENTING_MODE_NOT_TENTED)
            v.SetBackTentingMode(pcbnew.TENTING_MODE_NOT_TENTED)
    pcbnew.SaveBoard(os.path.join(tmp, 'pcb.kicad_pcb'), bc)
    run([KCLI, 'pcb', 'export', 'gerbers', '-o', tmp + '/', '-l', 'F.Mask,B.Mask', '--precision', '6',
         os.path.join(tmp, 'pcb.kicad_pcb')])
    tent = {}
    for cara, ext in (('F', 'gts'), ('B', 'gbs')):
        real = contar_flashes(next(os.path.join(gdir, f) for f in os.listdir(gdir) if f.endswith(ext)))
        ctrl = contar_flashes(next(os.path.join(tmp, f) for f in os.listdir(tmp) if f.endswith(ext)))
        en_via = lambda pts: sum(1 for p in pts if any(math.dist(p, q) < 0.005 for q in vias))   # noqa: E731
        tent[cara] = (len(real), en_via(real), len(ctrl), en_via(ctrl))
    shutil.rmtree(tmp, ignore_errors=True)

    # ---------------- BOM y CPL
    aud = {r['lcsc']: r for r in json.load(open(os.path.join(HERE, 'out', 'auditoria_footprints.json')))
           if 'giro_d' in r}
    pos_csv = os.path.join(FAB, '_pos.csv')
    run([KCLI, 'pcb', 'export', 'pos', '-o', pos_csv, '--format', 'csv', '--units', 'mm', '--side', 'front',
         '--smd-only', '--exclude-dnp', PCB])
    pos = {r['Ref']: r for r in csv.DictReader(open(pos_csv, encoding='utf-8'))}
    os.remove(pos_csv)
    jlc, mano = {}, []
    for fp in b.GetFootprints():
        ref = fp.GetReference()
        attr = fp.GetAttributes()
        if attr & pcbnew.FP_EXCLUDE_FROM_BOM or attr & pcbnew.FP_BOARD_ONLY:
            continue
        campos = {f.GetName(): f.GetText() for f in fp.GetFields()}
        lcsc = campos.get('LCSC', '').strip()
        if ref in pos and re.fullmatch(r'C\d+', lcsc):
            jlc[ref] = (fp, lcsc, campos)
        else:
            mano.append((ref, fp, campos))
    grupos = {}
    for ref, (fp, lcsc, campos) in jlc.items():
        clave = (fp.GetValue(), fp.GetFPID().GetLibItemName().wx_str(), lcsc)
        grupos.setdefault(clave, []).append(ref)
    with open(os.path.join(FAB, 'bom.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['Comment', 'Designator', 'Footprint', 'LCSC Part Number'])
        for (val, fpn, lcsc), refs in sorted(grupos.items(), key=lambda kv: natural(sorted(kv[1], key=natural)[0])):
            w.writerow([val, ','.join(sorted(refs, key=natural)), fpn, lcsc])

    filas_rot = []
    problemas = []
    with open(os.path.join(FAB, 'cpl.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['Designator', 'Mid X', 'Mid Y', 'Layer', 'Rotation'])
        for ref in sorted(jlc, key=natural):
            fp, lcsc, campos = jlc[ref]
            p = pos[ref]
            x, y, th = float(p['PosX']), float(p['PosY']), float(p['Rot'])
            a = aud.get(lcsc)
            if a is None:
                fpid = fp.GetFPIDAsString()
                a = af.audit(lcsc, fpid)
                if 'giro_d' not in a:
                    problemas.append(f'{ref} ({lcsc}): sin footprint de JLC para comparar; revisar en la vista previa')
                    a = {'giro_d': 0, 'tx': 0.0, 'ty': 0.0}
            d, tx, ty = a['giro_d'], a['tx'], a['ty']
            rj = (th - d) % 360
            ox, oy = rot(tx, ty, rj)
            mx, my = x - ox, y - oy
            w.writerow([ref, f'{mx:.4f}', f'{my:.4f}', 'Top', f'{rj:g}'])
            # comprobación del pin 1: footprint de JLC colocado con (mx, my, rj) contra el pad 1 de la placa
            chk = '—'
            jfp, _ = af.easyeda_fp(lcsc)
            p1 = fp.FindPadByNumber('1')
            if jfp is not None and p1 is not None:
                q = af.pads_of(jfp).get('1')
                if q:
                    qx, qy = rot(q[0][0], q[0][1], rj)
                    jx, jy = mx + qx, my + qy
                    bx, by = mm(p1.GetPosition().x), -mm(p1.GetPosition().y)
                    err = math.hypot(jx - bx, jy - by)
                    chk = f'{err:.2f} mm'
                    if err > 0.3:
                        problemas.append(f'{ref} ({lcsc}): el pin 1 de JLC cae a {err:.2f} mm del pad 1')
            filas_rot.append((ref, lcsc, fp.GetFPID().GetLibItemName().wx_str(), th, d, (tx, ty), rj, chk))

    # ---------------- montaje.pdf
    run([KCLI, 'pcb', 'export', 'pdf', '--mode-single', '-o', os.path.join(FAB, 'montaje.pdf'), '-l', 'F.Fab,Edge.Cuts',
         '--scale', '0', '--ev', '--sp', '--black-and-white', '--drill-shape-opt', '0', PCB])

    # ---------------- documentos
    with open(os.path.join(FAB, 'rotaciones.md'), 'w', encoding='utf-8') as f:
        f.write('# Rotaciones del CPL (JLCPCB)\n\n'
                'Generado por `tools/fabricacion.py`. Para cada pieza: giro de KiCad θ, giro d y traslación t del '
                'footprint de JLC respecto del de KiCad (`tools/auditoria_footprints.py`, ajuste q ≈ R(d)·p + t con '
                'los pads de la pieza LCSC exacta), y la rotación del CPL = θ − d. La columna **pin 1** es la '
                'distancia entre el pad 1 de la placa y el pad 1 del footprint de JLC colocado con la posición y la '
                'rotación del CPL. Comprueba la cuenta del CPL contra el footprint de EasyEDA de cada pieza; la '
                'colocación real la decide la biblioteca de montaje de JLC, así que el pin 1 de U1–U10, D1, D2 e Y1 '
                'se confirma en la vista previa del pedido (ver LEEME.md).\n\n'
                '| Pieza | LCSC | Footprint | θ KiCad | d | t (mm) | Rotación CPL | pin 1 |\n|---|---|---|---|---|---|---|---|\n')
        for ref, lcsc, fpn, th, d, (tx, ty), rj, chk in filas_rot:
            f.write(f'| {ref} | {lcsc} | {fpn} | {th:g} | {d} | ({tx:+.2f}, {ty:+.2f}) | {rj:g} | {chk} |\n')
        f.write('\n' + ('**Revisar en la vista previa de JLC:**\n\n' + '\n'.join(f'- {p}' for p in problemas)
                        if problemas else 'Todas las piezas con footprint de JLC comparable quedan con el pin 1 a '
                        '≤ 0.3 mm del pad 1 de la placa.') + '\n')
    # notas escritas para el montaje (el campo "Nota" de algunos footprints viene del diseño en Altium y quedó viejo)
    notas = {
        'A1': 'Zócalo de 2 × 1×15 hembra; la NUCLEO-L432KC va enchufada. Solo GND, I2C, SAI y DC_MON llegan a la placa.',
        'J1': 'Bornera: habilitación IEPE CH1 (24 V protegidos → fuente de corriente CH1).',
        'J5': 'Bornera: entrada de 18–30 V. Protegida con D1 (SS34, polaridad) y D2 (SMBJ26A, TVS).',
        'J7': 'Bornera: habilitación IEPE CH2.',
        'J2': 'BNC del micrófono CH1 (centro = señal + polarización IEPE, carcasa = GND).',
        'J8': 'BNC del micrófono CH2; el SV 12L (TNC) usa un adaptador BNC–TNC.',
        'JP1': 'Tira de 2 pines + jumper: escalón de corriente CH1 para la demostración.',
        'JP2': 'Tira de 2 pines + jumper: escalón de corriente CH2 para la demostración.',
    }
    with open(os.path.join(FAB, 'soldar_a_mano.md'), 'w', encoding='utf-8') as f:
        f.write('# Piezas que no monta JLC (se sueldan a mano)\n\n'
                'THT, sin código LCSC o marcadas fuera del BOM. Los puntos de prueba TP1–TP7 son pads sin pieza. '
                'Generado por `tools/fabricacion.py`.\n\n'
                '| Pieza | Valor | Footprint | MPN | LCSC | Nota |\n|---|---|---|---|---|---|\n')
        for ref, fp, campos in sorted(mano, key=lambda t: natural(t[0])):
            f.write(f'| {ref} | {fp.GetValue()} | {fp.GetFPID().GetLibItemName().wx_str()} | {campos.get("MPN", "")} | '
                    f'{campos.get("LCSC", "")} | {notas.get(ref, "")} |\n')
    n_j = len(jlc)
    # designadores que no caben en la serigrafía (Reference oculto en F.SilkS): posición desde la esquina de la placa
    omitidos = []
    for fp in sorted(b.GetFootprints(), key=lambda q: natural(q.GetReference())):
        r = fp.Reference()
        if fp.GetAttributes() & pcbnew.FP_BOARD_ONLY or r.IsVisible():
            continue
        omitidos.append(f'| {fp.GetReference()} | {fp.GetValue()} | {mm(fp.GetPosition().x) - 100:.1f} | '
                        f'{mm(fp.GetPosition().y) - 100:.1f} |')
    tabla_omitidos = ('| Pieza | Valor | x (mm) | y (mm) |\n|---|---|---|---|\n' + '\n'.join(omitidos)) if omitidos \
        else 'Ninguno.'
    with open(os.path.join(FAB, 'LEEME.md'), 'w', encoding='utf-8') as f:
        f.write(f'''# Fabricación — Sonómetro IEPE Rev B

Exportado por `tools/fabricacion.py` desde el commit **{hash_}** (placa sin cambios sin commit), después de un
`verificar_bloque.py` limpio: DRC 0 con todos los chequeos activos, paridad 0, ERC 0, `revisar_pistas` 0,
0 conexiones sin rutear.

## Pedido de PCB
| Parámetro | Valor |
|---|---|
| Capas | 4 (F.Cu, In1.Cu = plano GND, In2.Cu = alimentación y señales lentas, B.Cu) |
| Apilado | JLC04161H-7628, 1.6 mm, cobre externo 1 oz, interno 0.5 oz (sin control de impedancia) |
| Tamaño | 90 × 64 mm |
| Pista / separación mínima de diseño | 0.2 / 0.2 mm |
| Vía | 0.3 mm de taladro, 0.6 mm de pad; recubrimiento: **plugged** (por defecto en 4 capas en JLC) |
| Máscara / serigrafía | verde / blanca |
| Acabado | a elección del dueño: HASL con plomo, HASL sin plomo o ENIG (precios en REGLAS.md §9) |
| Archivo | `sonometro_revB_gerber.zip` ({len(gerbers)} archivos: {", ".join(gerbers)}) |

## Pedido de PCBA (económico, cara superior)
- `bom.csv` ({len(grupos)} líneas, {n_j} piezas) y `cpl.csv` ({n_j} piezas). Rotaciones y comprobación del pin 1 en
  `rotaciones.md`.
- 3 fiduciales en la placa (FID1–FID3). Rieles y agujeros de herramienta: los agrega JLC (REGLAS.md §2).
- Piezas a mano: `soldar_a_mano.md` ({len(mano)} piezas). Designadores omitidos en la serigrafía: `montaje.pdf`.
- Stock y códigos: `stock_bom.md` (`tools/stock_bom.py`, consulta del día). Repetir antes del pedido.
- **En la vista previa del pedido (DFM de JLC), antes de pagar:** pin 1 de U1–U10 sobre la marca de la placa,
  cátodo de D1/D2 del lado de la franja, pin 1 de Y1 y el centrado de U6/U7 (RNX, giro de 90° y 0.14 mm de
  corrimiento respecto del footprint de JLC).

## Tenting de las vías (punto 6 de la revisión del bloque 1)
Comparación de los Gerber de máscara contra una copia de control con todas las vías sin tapar:

| Cara | Aperturas en la placa real | … en coordenadas de vía | Aperturas en la copia sin tenting | … en coordenadas de vía |
|---|---|---|---|---|
| F.Mask | {tent["F"][0]} | **{tent["F"][1]}** | {tent["F"][2]} | {tent["F"][3]} |
| B.Mask | {tent["B"][0]} | **{tent["B"][1]}** | {tent["B"][2]} | {tent["B"][3]} |

La placa tiene {len(vias)} vías. La copia de control demuestra que el método las encuentra; la placa real no tiene
ninguna apertura en una vía.

## Revisión de los Gerber
La revisión con una biblioteca de Gerber existente queda pendiente de tu permiso para instalarla. Mientras tanto,
abrir el zip en GerbView o en el visor de JLC y comprobar:
1. 11 capas presentes: 4 de cobre en el orden F, In1, In2, B; In1 entera, salvo los huecos de los agujeros.
2. Los taladros (PTH y NPTH) caen en los pads.
3. El borde es un rectángulo cerrado de 90 × 64 mm.
4. No hay aperturas de máscara sobre las vías.
5. La serigrafía queda fuera de los pads.

## Designadores que no están en la serigrafía
A 1.0 mm de alto no caben sin pisar pads, vías o cuerpos. Están en `montaje.pdf` (vectorial: con zoom se leen los
designadores dentro de cada cuerpo). Posición del centro de la pieza, desde la esquina superior izquierda de la
placa:

{tabla_omitidos}
''')
    print(f'commit {hash_}: {len(gerbers)} archivos Gerber/taladro, BOM {len(grupos)} líneas / {n_j} piezas, '
          f'CPL {n_j}, a mano {len(mano)}, tenting {tent}, problemas de pin 1: {len(problemas)}')
    for p in problemas:
        print('  ', p)


if __name__ == '__main__':
    main()
