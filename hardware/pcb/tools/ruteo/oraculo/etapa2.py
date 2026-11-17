"""Etapa 2 del oráculo: congela el ruteo de la etapa 1 y rutea el resto de las redes con las dos capas.

Uso: python etapa2.py <carpeta_caso>    (necesita m.kicad_pcb y e.ses de la etapa 1 en la carpeta)
Produce e2.dsn: todo lo ya ruteado (bloques 1-3 + etapa 1) como cableado fijo; redes críticas solo F.Cu;
el resto (alimentación, I2C, DC_MON*, MD/FMT) con F.Cu y B.Cu; GND fuera.
"""
import os
import subprocess
import sys

KPY = r'C:/Program Files/KiCad/10.0/bin/python.exe'
HERE = os.path.dirname(os.path.abspath(__file__)).replace('\\', '/')


def paso(codigo):
    r = subprocess.run([KPY, '-c', codigo], capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(r.stdout + r.stderr)
    return r.stdout


def main():
    c = sys.argv[1].replace('\\', '/')
    # c.kicad_pcb (zonas y GND fuera, pads con su red) + pistas fijas equivalentes a las zonas
    print(paso(f"""
import pcbnew
b=pcbnew.LoadBoard('{c}/c.kicad_pcb'); nets=b.GetNetsByName()
def pista(net,a,cc,w):
    t=pcbnew.PCB_TRACK(b); t.SetStart(pcbnew.VECTOR2I(int(a[0]*1e6),int(a[1]*1e6))); t.SetEnd(pcbnew.VECTOR2I(int(cc[0]*1e6),int(cc[1]*1e6)))
    t.SetWidth(int(w*1e6)); t.SetLayer(pcbnew.F_Cu); t.SetNet(nets[net]); b.Add(t)
pista('24V_PROT',(121.3,117.325),(158.3,117.325),0.85)
pista('3V3',(119.4,101.9),(138.6,101.9),2.7); pista('5V',(141.0,101.9),(161.9,101.9),2.7)
pista('/SW_3',(128.1,108.975),(129.0,108.975),0.25); pista('/SW_5',(149.7,108.975),(150.6,108.975),0.25)
pcbnew.SaveBoard('{c}/c2.kicad_pcb',b); print('ok c2')"""))
    r = subprocess.run([KPY, f'{HERE}/sumar_ses.py', f'{c}/e.ses', f'{c}/c2.kicad_pcb', f'{c}/s1.kicad_pcb'],
                       capture_output=True, text=True)
    print(r.stdout[-200:], r.stderr[-300:] if r.returncode else '')
    print(paso(f"""
import pcbnew
b=pcbnew.LoadBoard('{c}/s1.kicad_pcb')
n=0
for fp in b.GetFootprints():
    for p in fp.Pads():
        if p.GetNetname()=='GND': p.SetNetCode(0); n+=1
print('pads GND sin red', n)
pcbnew.SaveBoard('{c}/s2.kicad_pcb',b); print('DSN', pcbnew.ExportSpecctraDSN(b,'{c}/d2.dsn'))"""))
    s = open(f'{c}/d2.dsn').read()
    # críticas: solo F.Cu; Potencia/Default/Conmutado: las dos capas. DC_MON* pasan a una clase propia con dos capas.
    LIBRES = ['DC_MON', 'DC_MON2']
    out, pos = [], 0
    while True:
        k = s.find('(class ', pos)
        if k < 0:
            out.append(s[pos:])
            break
        cc = s.find('(circuit', k)
        head = s[k:cc]
        name = head.split()[1]
        toks = [t for t in head.split() if t not in LIBRES]
        out.append(s[pos:k])
        out.append(' '.join(toks) + '\n      ')
        pos = cc
        if name in ('Analogica', 'Reloj'):
            out.append('(circuit\n        (use_layer F.Cu)')
            pos = cc + len('(circuit')
    s = ''.join(out)
    i = s.rfind('(wiring')
    j = s.rfind(')', 0, i)
    s = s[:j] + ('  (class Lenta %s\n      (circuit\n        (use_via "Via[0-1]_600:300_um")\n      )\n'
                 '      (rule\n        (width 200)\n        (clearance 300)\n      )\n    )\n  ' % ' '.join(LIBRES)) + s[j:]
    s = s.replace('(type route))', '(type fix))')
    open(f'{c}/e2.dsn', 'w').write(s)
    print('listo', f'{c}/e2.dsn', s.count('use_layer F.Cu'), 'clases solo F.Cu;', s.count('(type fix)'), 'pistas fijas')


if __name__ == '__main__':
    main()
