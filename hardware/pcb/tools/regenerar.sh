#!/bin/bash
# Regenera desde cero, en tools/out/ (NUNCA en hardware/pcb/), el esquemático y la PCB:
#   Altium Sonometro_2CH/*.SchDoc -> altium.json -> design.py (+ docs) -> target.json
#   -> out/pcb.kicad_sch (verificado pin a pin + ERC) -> out/pcb.kicad_pcb (placement + paridad)
# Requiere KiCad 10 (Windows) y Python con olefile. Uso:  bash hardware/pcb/tools/regenerar.sh
set -e
cd "$(dirname "$0")"
K="${KICAD_CLI:-/c/Program Files/KiCad/10.0/bin/kicad-cli.exe}"
KPY="${KICAD_PYTHON:-/c/Program Files/KiCad/10.0/bin/python.exe}"
PY="${PYTHON:-python}"
rm -rf out && mkdir -p out/lib
"$PY" -I export_json.py ../../Sonometro_2CH altium.json
"$PY" -I design.py
"$PY" -I buildlib.py out/lib
"$PY" -I gen_sch_wired.py out
cp lib_tables/* out/
printf '{\n  "meta": {\n    "version": 1\n  }\n}\n' > out/pcb.kicad_pro
"$K" sch export netlist --format kicadxml -o out/check.xml out/pcb.kicad_sch > /dev/null
"$PY" -I verify.py target.json out/check.xml
"$K" sch erc --severity-all --format json -o out/erc.json out/pcb.kicad_sch | tail -1
"$KPY" gen_pcb.py out
"$PY" -I fix_pro.py out/pcb.kicad_pro
"$K" pcb drc --schematic-parity --severity-all --format json -o out/drc.json out/pcb.kicad_pcb | tail -1
echo "Listo: revisa tools/out/. Copia a hardware/pcb solo si quieres descartar lo editado a mano."
