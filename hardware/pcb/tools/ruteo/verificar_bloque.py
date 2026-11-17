"""Verificación después de cada bloque de ruteo (pedido del dueño): DRC con paridad, ERC, revisar_pistas.py e imágenes.

1. DRC con paridad (todas las severidades) rellenando las zonas y guardando el relleno (el plano GND de B.Cu existe
   desde el bloque 1: el DRC de la placa real debe dar 0 en cada parada).
2. ERC del esquemático.
3. revisar_pistas.py sobre la placa real.
4. Imágenes de capas (exportar_capas.py).
Uso (Python del sistema, con pypdfium2):  python verificar_bloque.py <nombre_bloque>
Salida en tools/out/verif_<bloque>/ y un resumen en pantalla. Sale con código 1 si hay algo fuera de lo esperado.
"""
import collections
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PCB_DIR = os.path.abspath(os.path.join(HERE, '..', '..'))
KBIN = os.environ.get('KICAD_BIN', r'C:\Program Files\KiCad\10.0\bin')
KCLI = os.path.join(KBIN, 'kicad-cli.exe')
KPY = os.path.join(KBIN, 'python.exe')


def run(args, **kw):
    r = subprocess.run(args, capture_output=True, text=True, encoding='utf-8', errors='replace', **kw)
    return r.returncode, (r.stdout or '') + (r.stderr or '')


def drc(pcb, out):
    if os.path.exists(out):
        os.remove(out)                               # nunca leer un informe viejo
    code, txt = run([KCLI, 'pcb', 'drc', '--schematic-parity', '--severity-all', '--format', 'json', '-o', out, pcb])
    if code or not os.path.exists(out):
        raise SystemExit(f'kicad-cli drc falló (código {code}): ' + txt)
    return json.load(open(out, encoding='utf-8'))


def resumen_drc(d):
    c = collections.Counter((v['type'], v['severity']) for v in d['violations'])
    return {f'{t} ({s})': n for (t, s), n in sorted(c.items())}


def main():
    bloque = sys.argv[1]
    out = os.path.join(PCB_DIR, 'tools', 'out', 'verif_' + bloque)
    os.makedirs(out, exist_ok=True)
    if any(f.endswith('.lck') for f in os.listdir(PCB_DIR)):
        raise SystemExit('KiCad tiene la placa abierta (.lck): ciérralo antes de verificar')
    real = os.path.join(PCB_DIR, 'pcb.kicad_pcb')
    malo = False

    # 1. DRC con paridad, rellenando las zonas (plano GND de B.Cu incluido) y guardando el relleno en la placa
    out_drc = os.path.join(out, 'drc.json')
    if os.path.exists(out_drc):
        os.remove(out_drc)                           # nunca leer un informe viejo
    code, txt = run([KCLI, 'pcb', 'drc', '--schematic-parity', '--severity-all', '--refill-zones', '--save-board',
                     '--format', 'json', '-o', out_drc, real])
    if code or not os.path.exists(out_drc):
        raise SystemExit(f'kicad-cli drc falló (código {code}): ' + txt)
    d = json.load(open(out_drc, encoding='utf-8'))
    print(f'[placa] DRC (zonas rellenadas): {resumen_drc(d) or "0 violaciones"}; paridad: '
          f'{len(d["schematic_parity"])}; sin conectar: {len(d["unconnected_items"])}')
    malo |= bool(d['violations']) or bool(d['schematic_parity'])
    for v in d['violations']:
        print('   ', v['type'], '|', v['description'][:90], '|', ' / '.join(i['description'][:50] for i in v['items']))

    # 2. ERC
    erc = os.path.join(out, 'erc.json')
    if os.path.exists(erc):
        os.remove(erc)
    code, txt = run([KCLI, 'sch', 'erc', '--severity-all', '--format', 'json', '-o', erc,
                     os.path.join(PCB_DIR, 'pcb.kicad_sch')])
    if code or not os.path.exists(erc):
        raise SystemExit(f'kicad-cli erc falló (código {code}): ' + txt)
    e = json.load(open(erc, encoding='utf-8'))
    n_erc = sum(len(s['violations']) for s in e['sheets'])
    print(f'[esquemático] ERC: {n_erc}')
    malo |= n_erc > 0

    # 3. revisar_pistas.py sobre la placa real (ya con el plano GND rellenado)
    rj = os.path.join(out, 'revisar.json')
    if os.path.exists(rj):
        os.remove(rj)
    code, txt = run([KPY, os.path.join(HERE, 'revisar_pistas.py'), real, '--json', rj])
    if not os.path.exists(rj):
        raise SystemExit('revisar_pistas.py no terminó: ' + txt[-800:])
    print('[placa] revisar_pistas.py:')
    print('   ' + '\n   '.join(l for l in txt.splitlines() if l.strip() and 'memory leak' not in l
                               and 'image handler' not in l and 'swig/python' not in l))
    malo |= code != 0

    # 4. imágenes
    code, txt = run([sys.executable, os.path.join(HERE, 'exportar_capas.py'), real, os.path.join(out, 'capas')])
    print('[imágenes]', 'en ' + os.path.join(out, 'capas') if code == 0 else 'fallaron: ' + txt[-300:])
    sys.exit(1 if malo else 0)


if __name__ == '__main__':
    main()
