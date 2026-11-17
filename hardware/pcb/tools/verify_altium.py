"""Verifica TU dibujo en Altium contra el diseno acordado (target.json), pin por pin.

Uso:  python hardware/pcb/tools/verify_altium.py <carpeta_con_los_.SchDoc>

Lee los .SchDoc (proyecto plano: puertos y puertos de alimentacion globales, etiquetas locales por
hoja) y compara las conexiones contra target.json SIN importar como se llamen las redes: cada red del
diseno debe existir en Altium con exactamente los mismos pines. Las referencias deben coincidir
(R1, U4, A1...) y los numeros de pin tambien (zocalo NUCLEO A1: 1-15 = CN3-1..15, 16-30 = CN4-1..15).
"""
import os
import sys
import glob
import json
import collections

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from altparse import sheet_nodes, UF  # noqa: E402


def altium_nets(src):
    G = UF()
    refs = set()
    for f in sorted(glob.glob(os.path.join(src, '*.SchDoc'))):
        sname = os.path.basename(f)
        cs, pins, labels, uf, segs = sheet_nodes(f, sname)
        for ci, c in cs.items():
            refs.add(c.get('ref') or f'?{ci}')
        groups = collections.defaultdict(list)
        for k, pt, nm in pins:
            groups[uf.f(k)].append(k)
        for k, name, pt in labels:
            groups[uf.f(k)].append(name)
        for root, mem in groups.items():
            for m in mem:
                G.u('S:' + sname + ':' + root, m)
        portnames = {n[5:] for k, n, pt in labels if n.startswith('port:')}
        for k, name, pt in labels:
            if name.startswith('local:') and name.split(':', 2)[2] in portnames:
                G.u(name, 'port:' + name.split(':', 2)[2])
    nets = collections.defaultdict(set)
    for k in list(G.p):
        if k.startswith('PIN:'):
            nets[G.f(k)].add(k[4:])
    return refs, list(nets.values())


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    target = json.load(open(os.path.join(HERE, 'target.json')))
    refs, anets = altium_nets(sys.argv[1])
    pin_net = {}
    for i, s in enumerate(anets):
        for p in s:
            pin_net[p] = i
    errors = []
    for r in sorted(set(target) - refs):
        errors.append(f'falta el componente {r} ({target[r]["value"]})')
    tnets = collections.defaultdict(set)
    for ref, p in target.items():
        for num, net in p['pins'].items():
            if net:
                tnets[net].add(f'{ref}.{num}')
    for net, mem in sorted(tnets.items()):
        groups = collections.Counter(pin_net.get(p) for p in mem)
        if None in groups:
            errors.append(f'red {net}: pines sin conectar o inexistentes en Altium: '
                          f'{sorted(p for p in mem if p not in pin_net)}')
            continue
        if len(groups) > 1:
            errors.append(f'red {net}: en Altium esta partida en {len(groups)} redes: '
                          f'{[sorted(p for p in mem if pin_net[p] == g) for g in groups]}')
            continue
        extra = anets[next(iter(groups))] - mem
        if extra:
            errors.append(f'red {net}: en Altium tiene pines de mas: {sorted(extra)}')
    print(f'{len(target)} componentes y {len(tnets)} redes revisadas: {len(errors)} problemas')
    for e in errors:
        print('  ', e)
    sys.exit(1 if errors else 0)


if __name__ == '__main__':
    main()
