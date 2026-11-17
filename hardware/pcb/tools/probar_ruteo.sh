#!/bin/bash
# Prueba de ruteabilidad (NO es el ruteo final): copia la PCB, la exporta a Specctra DSN, la autorutea
# con Freerouting, importa el resultado y corre el DRC sobre esa copia. No toca hardware/pcb.
# Requiere Java 21 y el freerouting-2.5.0.jar (https://github.com/freerouting/freerouting/releases).
# Uso:  FREEROUTING_JAR=/ruta/freerouting-2.5.0.jar bash hardware/pcb/tools/probar_ruteo.sh
set -e
cd "$(dirname "$0")"
FR="${FREEROUTING_JAR:?Define FREEROUTING_JAR con la ruta del freerouting-2.5.0.jar}"
K="${KICAD_CLI:-/c/Program Files/KiCad/10.0/bin/kicad-cli.exe}"
KPY="${KICAD_PYTHON:-/c/Program Files/KiCad/10.0/bin/python.exe}"
rm -rf ruteo_prueba && mkdir ruteo_prueba
cp ../pcb.kicad_pcb ../pcb.kicad_pro ruteo_prueba/
"$KPY" -c "import pcbnew; b = pcbnew.LoadBoard('ruteo_prueba/pcb.kicad_pcb'); print('DSN:', pcbnew.ExportSpecctraDSN(b, 'ruteo_prueba/board.dsn'))"
java -jar "$FR" -de ruteo_prueba/board.dsn -do ruteo_prueba/board.ses -mp 30 --gui.enabled=false
"$KPY" -c "
import pcbnew
b = pcbnew.LoadBoard('ruteo_prueba/pcb.kicad_pcb')
print('SES:', pcbnew.ImportSpecctraSES(b, 'ruteo_prueba/board.ses'))
vias = sum(1 for t in b.GetTracks() if t.GetClass() == 'PCB_VIA')
length = sum(pcbnew.ToMM(t.GetLength()) for t in b.GetTracks() if t.GetClass() == 'PCB_TRACK')
print(f'vias: {vias}   largo de pistas: {length:.0f} mm')
pcbnew.SaveBoard('ruteo_prueba/ruteado.kicad_pcb', b)
"
"$K" pcb drc --severity-all --format json -o ruteo_prueba/drc.json ruteo_prueba/ruteado.kicad_pcb | tail -1
python -I -c "
import json, collections
d = json.load(open('ruteo_prueba/drc.json'))
print('sin rutear:', len(d['unconnected_items']))
print('violaciones:', dict(collections.Counter((v['type'], v['severity']) for v in d['violations'])))
"
echo "Revisa ruteo_prueba/ruteado.kicad_pcb en KiCad. Es solo una prueba: el ruteo real se hace a mano."
