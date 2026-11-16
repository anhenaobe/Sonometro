"""Verificación después de cada bloque de ruteo (pedido del dueño): DRC con paridad, ERC, revisar_pistas.py e imágenes.

1. Placa real: DRC con paridad (todas las severidades) y ERC del esquemático. Mientras no existan los polígonos de
   tierra (bloque 9) las vías GND puestas junto a los pads figuran como colgantes: se reportan aparte.
2. Copia con relleno GND temporal en B.Cu (zona_gnd_temporal.py): DRC sin esas vías colgantes y revisar_pistas.py.
3. Imágenes de capas (exportar_capas.py) de la placa real.
Uso (Python del sistema, con pypdfium2):  python verificar_bloque.py <nombre_bloque>
Salida en tools/out/verif_<bloque>/ y un resumen en pantalla. Sale con código 1 si hay algo fuera de lo esperado.
"""
import collections
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PCB_DIR = os.path.abspath(os.path.join(HERE, '..', '..'))
KBIN = os.environ.get('KICAD_BIN', r'C:\Program Files\KiCad\10.0\bin')
KCLI = os.path.join(KBIN, 'kicad-cli.exe')
KPY = os.path.join(KBIN, 'python.exe')
COPIAR = ('pcb.kicad_pcb', 'pcb.kicad_pro', 'pcb.kicad_dru', 'pcb.kicad_sch', 'fp-lib-table', 'sym-lib-table')


def run(args, **kw):
    r = subprocess.run(args, capture_output=True, text=True, encoding='utf-8', errors='replace', **kw)
    return r.returncode, (r.stdout or '') + (r.stderr or '')


def drc(pcb, out):
    code, txt = run([KCLI, 'pcb', 'drc', '--schematic-parity', '--severity-all', '--format', 'json', '-o', out, pcb])
    if not os.path.exists(out):
        raise SystemExit('kicad-cli drc falló: ' + txt)
    return json.load(open(out, encoding='utf-8'))


def resumen_drc(d):
    c = collections.Counter((v['type'], v['severity']) for v in d['violations'])
    return {f'{t} ({s})': n for (t, s), n in sorted(c.items())}


def main():
    bloque = sys.argv[1]
    out = os.path.join(PCB_DIR, 'tools', 'out', 'verif_' + bloque)
    if os.path.isdir(out):
        shutil.rmtree(out, ignore_errors=True)       # en Windows una carpeta abierta por otro proceso queda en pie
    os.makedirs(out, exist_ok=True)
    if any(f.endswith('.lck') for f in os.listdir(PCB_DIR)):
        raise SystemExit('KiCad tiene la placa abierta (.lck): ciérralo antes de verificar')
    real = os.path.join(PCB_DIR, 'pcb.kicad_pcb')
    malo = False

    # 1. placa real
    d = drc(real, os.path.join(out, 'drc_real.json'))
    colg = [v for v in d['violations'] if v['type'] == 'via_dangling'
            and all('[GND]' in i['description'] for i in v['items'])]
    otros = [v for v in d['violations'] if v not in colg]
    print(f'[placa real] DRC: {resumen_drc(d) or "sin violaciones"}')
    print(f'             vías GND colgantes hasta el bloque 9 (esperadas): {len(colg)}; otras violaciones: {len(otros)}')
    print(f'             paridad: {len(d["schematic_parity"])}; sin conectar: {len(d["unconnected_items"])}')
    malo |= bool(otros) or bool(d['schematic_parity'])
    for v in otros:
        print('   ', v['type'], '|', v['description'][:90], '|', ' / '.join(i['description'][:50] for i in v['items']))
    code, txt = run([KCLI, 'sch', 'erc', '--severity-all', '--format', 'json', '-o', os.path.join(out, 'erc.json'),
                     os.path.join(PCB_DIR, 'pcb.kicad_sch')])
    e = json.load(open(os.path.join(out, 'erc.json'), encoding='utf-8'))
    n_erc = sum(len(s['violations']) for s in e['sheets'])
    print(f'[esquemático] ERC: {n_erc}')
    malo |= n_erc > 0

    # 2. copia con GND temporal
    cp = os.path.join(out, 'copia')
    shutil.rmtree(cp, ignore_errors=True)
    os.makedirs(cp, exist_ok=True)
    for f in COPIAR:
        if os.path.exists(os.path.join(PCB_DIR, f)):
            shutil.copy2(os.path.join(PCB_DIR, f), cp)
    shutil.copytree(os.path.join(PCB_DIR, 'lib'), os.path.join(cp, 'lib'))
    cpcb = os.path.join(cp, 'pcb.kicad_pcb')
    code, txt = run([KPY, os.path.join(HERE, 'zona_gnd_temporal.py'), cpcb])
    if code:
        raise SystemExit('zona_gnd_temporal.py falló: ' + txt)
    d2 = drc(cpcb, os.path.join(out, 'drc_copia_gnd.json'))
    print(f'[copia + GND temporal en B.Cu] DRC: {resumen_drc(d2) or "sin violaciones"}; '
          f'sin conectar: {len(d2["unconnected_items"])}')
    malo |= bool(d2['violations'])
    for v in d2['violations']:
        print('   ', v['type'], '|', v['description'][:90], '|', ' / '.join(i['description'][:50] for i in v['items']))
    code, txt = run([KPY, os.path.join(HERE, 'revisar_pistas.py'), cpcb, '--json', os.path.join(out, 'revisar.json')])
    print('[copia + GND temporal] revisar_pistas.py:')
    print('   ' + '\n   '.join(l for l in txt.splitlines() if l.strip() and 'memory leak' not in l))
    malo |= code != 0

    # 3. imágenes
    code, txt = run([sys.executable, os.path.join(HERE, 'exportar_capas.py'), real, os.path.join(out, 'capas')])
    print('[imágenes]', 'en ' + os.path.join(out, 'capas') if code == 0 else 'fallaron: ' + txt[-300:])
    sys.exit(1 if malo else 0)


if __name__ == '__main__':
    main()
