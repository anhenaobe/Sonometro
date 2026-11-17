#!/bin/bash
# Verifica el esquemático y la PCB ACTUALES de hardware/pcb contra la netlist objetivo
# (Altium Sonometro_2CH + docs/connection_matrix.md) guardada en target.json.
# No modifica nada. Uso:  bash hardware/pcb/tools/verificar.sh
set -e
cd "$(dirname "$0")"
K="${KICAD_CLI:-/c/Program Files/KiCad/10.0/bin/kicad-cli.exe}"
PY="${PYTHON:-python}"
mkdir -p out
"$K" sch export netlist --format kicadxml -o out/actual.xml ../pcb.kicad_sch > /dev/null
"$PY" -I verify.py target.json out/actual.xml || true
"$K" sch erc --severity-all --format json -o out/erc.json ../pcb.kicad_sch | tail -1
"$K" pcb drc --schematic-parity --severity-all --format json -o out/drc.json ../pcb.kicad_pcb | tail -1
"$PY" -I - <<'PY'
import json, collections
e = json.load(open('out/erc.json'))
print('ERC:', sum(len(s['violations']) for s in e['sheets']), 'violaciones')
d = json.load(open('out/drc.json'))
for k in ('violations', 'unconnected_items', 'schematic_parity'):
    v = d.get(k, [])
    print('DRC', k, len(v), dict(collections.Counter((x['type'], x['severity']) for x in v)))
PY
