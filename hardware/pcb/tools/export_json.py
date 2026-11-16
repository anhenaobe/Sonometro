"""Extract components + pin->net map from the team's Altium SchDoc files (flat project).

Rules applied (Altium 'Automatic' net scope with ports and no sheet symbols = flat):
  * wires / junctions / pin hot-spots connect geometrically on each sheet
  * net labels are local to a sheet; ports and power ports are global
  * a net label and a port with the same name on the same sheet are one net
Usage: python export_json.py <Sonometro_2CH dir> <out.json>
"""
import sys, os, glob, json, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from altparse import read_records, components, sheet_nodes, UF

src, out = sys.argv[1], sys.argv[2]
G = UF()
comps = {}
pinname = {}
for f in sorted(glob.glob(os.path.join(src, '*.SchDoc'))):
    sname = os.path.basename(f).replace('.SchDoc', '')
    cs, pins, labels, uf, segs = sheet_nodes(f, sname)
    for ci, c in cs.items():
        ref = c.get('ref') or '?'
        if '?' in ref:
            ref = ref + str(ci)
        comps[ref] = dict(sheet=sname, lib=c['lib'], params=c['params'],
                          footprints=[m[0] for m in c['models'] if m[1] == 'PCBLIB' and m[2] == 'T'] or
                                     [m[0] for m in c['models'] if m[1] == 'PCBLIB'])
    groups = collections.defaultdict(list)
    for k, pt, nm in pins:
        groups[uf.f(k)].append(k)
        pinname[k] = nm
    for k, name, pt in labels:
        groups[uf.f(k)].append(name)
    for root, mem in groups.items():
        for m in mem:
            G.u('S:' + sname + ':' + root, m)
    portnames = {n[5:] for k, n, pt in labels if n.startswith('port:')}
    for k, name, pt in labels:
        if name.startswith('local:') and name.split(':', 2)[2] in portnames:
            G.u(name, 'port:' + name.split(':', 2)[2])

members = collections.defaultdict(list)
names = collections.defaultdict(set)
for k in list(G.p):
    r = G.f(k)
    if k.startswith('PIN:'):
        members[r].append(k[4:])
    elif k.startswith(('local:', 'global:', 'port:')):
        names[r].add(k.split(':')[-1])
nets = []
for r, mem in members.items():
    nm = sorted(names.get(r, []))
    nets.append(dict(names=nm, pins=sorted(mem)))
json.dump(dict(components=comps, nets=nets,
               pin_names={k[4:]: v for k, v in pinname.items()}),
          open(out, 'w'), indent=1, ensure_ascii=False)
print(len(comps), 'components,', len(nets), 'nets ->', out)
