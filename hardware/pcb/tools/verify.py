"""Compare a KiCad XML netlist (kicad-cli sch export netlist --format kicadxml) with target.json.

Checks, for every part in target.json:
  * the component exists with the same value and footprint
  * every pin is on a net whose members equal the target net members, and the KiCad net name
    equals the target name (nets without a label get KiCad's automatic 'Net-(...)' name: allowed)
  * pins that the target leaves unconnected are alone in KiCad
Usage: python verify.py target.json netlist.xml
"""
import sys
import json
import collections
import xml.etree.ElementTree as ET

target = json.load(open(sys.argv[1]))
root = ET.parse(sys.argv[2]).getroot()

kcomps = {}
for c in root.iter('comp'):
    fp = c.findtext('footprint') or ''
    kcomps[c.get('ref')] = dict(value=c.findtext('value'), fp=fp)
kpin = {}
knet_members = {}
for n in root.iter('net'):
    name = n.get('name').lstrip('/')
    mem = frozenset(f"{nd.get('ref')}.{nd.get('pin')}" for nd in n.iter('node'))
    for m in mem:
        kpin[m] = name
    knet_members[name] = mem

tnets = collections.defaultdict(set)
for ref, p in target.items():
    for num, net in p['pins'].items():
        if net:
            tnets[net].add(f'{ref}.{num}')

errors = []
for ref, p in target.items():
    if ref not in kcomps:
        errors.append(f'missing component {ref}')
        continue
    if kcomps[ref]['value'] != p['value']:
        errors.append(f'{ref}: value {kcomps[ref]["value"]!r} != {p["value"]!r}')
    if kcomps[ref]['fp'] != p['fp']:
        errors.append(f'{ref}: footprint {kcomps[ref]["fp"]!r} != {p["fp"]!r}')
    for num, net in p['pins'].items():
        key = f'{ref}.{num}'
        kn = kpin.get(key)
        if net is None:
            if kn is not None and len(knet_members[kn]) > 1:
                errors.append(f'{key}: should be unconnected, is on {kn} {sorted(knet_members[kn])}')
            continue
        if kn is None:
            errors.append(f'{key}: not in KiCad netlist (target {net})')
            continue
        if kn != net and not kn.startswith('Net-('):
            errors.append(f'{key}: net name {kn!r} != {net!r}')
        if set(knet_members[kn]) != tnets[net]:
            extra = sorted(set(knet_members[kn]) - tnets[net])
            miss = sorted(tnets[net] - set(knet_members[kn]))
            errors.append(f'{key}: net {net} membership differs; extra={extra} missing={miss}')
extra_comps = sorted(set(kcomps) - set(target))
if extra_comps:
    errors.append(f'extra components in KiCad: {extra_comps}')
uniq = sorted(set(errors))
print(f'{len(target)} parts, {len(tnets)} nets checked; {len(uniq)} problems')
for e in uniq[:80]:
    print('  ', e)
sys.exit(1 if uniq else 0)
