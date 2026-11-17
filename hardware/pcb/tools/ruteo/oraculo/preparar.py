"""Prepara un caso del oráculo en una carpeta: placa real + movimientos -> DSN de etapa 1 (redes críticas).

Uso (Python de KiCad): python preparar.py <carpeta_caso> <movs.json|-> <etapa>
  movs.json: {ref: [x, y, giro]} (posiciones absolutas, mm KiCad)
  etapa 1: solo redes Analogica/Reloj (menos DC_MON/DC_MON2); salidas del DAC con B.Cu permitido; el resto, obstáculo.
Cada paso que borra cosas se hace en un proceso aparte (SWIG se rompe tras Remove).
"""
import json
import os
import shutil
import subprocess
import sys

PCB = r'C:/Users/voxte/code/Sonometro/hardware/pcb'
KPY = r'C:/Program Files/KiCad/10.0/bin/python.exe'


def paso(codigo, *args):
    r = subprocess.run([KPY, '-c', codigo] + list(args), capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(r.stdout + r.stderr)
    return r.stdout


def main():
    caso, movs, etapa = sys.argv[1], sys.argv[2], sys.argv[3]
    os.makedirs(caso, exist_ok=True)
    shutil.copy(os.path.join(PCB, 'pcb.kicad_pcb'), os.path.join(caso, 'a.kicad_pcb'))
    for f in ('pcb.kicad_pro', 'pcb.kicad_dru'):
        shutil.copy(os.path.join(PCB, f), os.path.join(caso, 'a' + os.path.splitext(f)[1]))
    shutil.copy(os.path.join(PCB, 'fp-lib-table'), caso)
    if not os.path.isdir(os.path.join(caso, 'lib')):
        shutil.copytree(os.path.join(PCB, 'lib'), os.path.join(caso, 'lib'))
    c = caso.replace('\\', '/')
    paso(f"""
import pcbnew, json
b=pcbnew.LoadBoard('{c}/a.kicad_pcb')
movs={{}} if '{movs}'=='-' else json.load(open('{movs}'))
for ref,(x,y,r) in movs.items():
    f=b.FindFootprintByReference(ref); f.SetOrientationDegrees(r); f.SetPosition(pcbnew.VECTOR2I(int(round(x*1e6)),int(round(y*1e6))))
pcbnew.SaveBoard('{c}/m.kicad_pcb',b)""")
    shutil.copy(os.path.join(caso, 'a.kicad_pro'), os.path.join(caso, 'm.kicad_pro'))
    shutil.copy(os.path.join(caso, 'a.kicad_dru'), os.path.join(caso, 'm.kicad_dru'))
    paso(f"""
import pcbnew
b=pcbnew.LoadBoard('{c}/m.kicad_pcb')
for z in list(b.Zones()): b.Remove(z)
pcbnew.SaveBoard('{c}/b.kicad_pcb',b)""")
    paso(f"""
import pcbnew
b=pcbnew.LoadBoard('{c}/b.kicad_pcb')
for t in list(b.GetTracks()):
    if t.GetNetname()=='GND': b.Remove(t)
pcbnew.SaveBoard('{c}/c.kicad_pcb',b)""")
    print(paso(f"""
import pcbnew
b=pcbnew.LoadBoard('{c}/c.kicad_pcb'); nets=b.GetNetsByName()
def pista(net,a,cc,w):
    t=pcbnew.PCB_TRACK(b); t.SetStart(pcbnew.VECTOR2I(int(a[0]*1e6),int(a[1]*1e6))); t.SetEnd(pcbnew.VECTOR2I(int(cc[0]*1e6),int(cc[1]*1e6)))
    t.SetWidth(int(w*1e6)); t.SetLayer(pcbnew.F_Cu); t.SetNet(nets[net]); b.Add(t)
pista('24V_PROT',(121.3,117.325),(158.3,117.325),0.85)
pista('3V3',(119.4,101.9),(138.6,101.9),2.7); pista('5V',(141.0,101.9),(161.9,101.9),2.7)
pista('/SW_3',(128.1,108.975),(129.0,108.975),0.25); pista('/SW_5',(149.7,108.975),(150.6,108.975),0.25)
CRIT={{'Analogica','Reloj'}}; PUENTE={{'Net-(U2-VOUT)','Net-(U10-VOUT)'}}; FUERA={{'DC_MON','DC_MON2'}}
etapa={etapa}
n=0
for fp in b.GetFootprints():
    for p in fp.Pads():
        nm=p.GetNetname()
        if not nm or nm.startswith('unconnected'): continue
        if nm=='GND' or (etapa==1 and not ((p.GetNetClassName() in CRIT and nm not in FUERA) or nm in PUENTE)):
            p.SetNetCode(0); n+=1
print('pads sin red', n)
pcbnew.SaveBoard('{c}/d.kicad_pcb',b); print('DSN', pcbnew.ExportSpecctraDSN(b,'{c}/d.dsn'))"""))
    s = open(os.path.join(caso, 'd.dsn')).read()
    P = ['"Net-(U2-VOUT)"', '"Net-(U10-VOUT)"']
    out, pos = [], 0
    while True:
        k = s.find('(class ', pos)
        if k < 0:
            out.append(s[pos:])
            break
        cc = s.find('(circuit', k)
        toks = [t for t in s[k:cc].split() if t not in P]
        out.append(s[pos:k])
        out.append(' '.join(toks) + '\n      ')
        pos = cc
    s = ''.join(out).replace('(circuit\n        (use_via', '(circuit\n        (use_layer F.Cu)\n        (use_via')
    i = s.rfind('(wiring')
    j = s.rfind(')', 0, i)
    s = s[:j] + ('  (class PuenteDAC %s\n      (circuit\n        (use_via "Via[0-1]_600:300_um")\n      )\n'
                 '      (rule\n        (width 200)\n        (clearance 300)\n      )\n    )\n  ' % ' '.join(P)) + s[j:]
    s = s.replace('(type route))', '(type fix))')
    open(os.path.join(caso, 'e.dsn'), 'w').write(s)
    print('listo', os.path.join(caso, 'e.dsn'))


if __name__ == '__main__':
    main()
