"""Verifica que cada red de la placa quedó en la clase de red que le corresponde según su nombre en target.json.

Las clases se asignan por patrón sobre el nombre de red de KiCad, y las redes internas tienen nombres automáticos
(Net-(R13-Pad1)...) que cambian si cambia el esquemático. Este chequeo traduce cada red de la placa a su nombre
del diseño (por los pines que contiene) y compara la clase esperada con la asignada.
Uso (Python de KiCad): python verificar_clases.py [pcb]   -> sale con código 1 si alguna red está mal clasificada.
"""
import json
import os
import re
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
ESPERADA = [  # (expresión regular sobre el nombre de red del diseño, clase)
    (r'^(24V_IN|24V_PROT|3V3|5V|5V_A|GND|IEPE_SUP|IEPE_SUP_SV|3V3_DAC|3V3_DAC_SV)$', 'Potencia'),
    (r'^SW_[35]$', 'Conmutado'),
    (r'^(SAI_.*|PCM_MCLK|MCLK_SOURCE|PCM_BCK|PCM_LRCK|PCM_DOUT)$', 'Reloj'),
    (r'^(I2C_.*|MD0|MD1|FMT|BOOT_[35]|FB_[35]|VCC_[35])$', 'Default'),
    (r'.*', 'Analogica'),     # todo lo demás: IEPE*, REST*, DC_MON*, SUM*, divisores, DAC_F/RAW, VSHIFT, AC/ADC_IN,
                              # PCM_VREF, SET/OUT de los LT3092, STEP, IEPE_FEED
]


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, '..', '..', 'pcb.kicad_pcb')
    T = json.load(open(os.path.join(HERE, '..', 'target.json')))
    pin2net = {f'{r}.{n}': net for r, p in T.items() for n, net in p['pins'].items() if net}
    b = pcbnew.LoadBoard(path)
    nets = {}
    for fp in b.GetFootprints():
        for p in fp.Pads():
            kn = p.GetNetname()
            if kn and not kn.startswith('unconnected'):
                nets.setdefault(kn, (p.GetNetClassName(), pin2net.get(f'{fp.GetReference()}.{p.GetNumber()}')))
    mal = []
    for kn, (cls, dn) in sorted(nets.items()):
        if dn is None:
            mal.append(f'{kn}: no está en target.json')
            continue
        want = next(c for rx, c in ESPERADA if re.match(rx, dn))
        if cls != want:
            mal.append(f'{kn} (diseño {dn}): clase {cls}, debería ser {want}')
    print(f'{len(nets)} redes revisadas, {len(mal)} mal clasificadas')
    for m in mal:
        print('  ', m)
    sys.exit(1 if mal else 0)


if __name__ == '__main__':
    main()
