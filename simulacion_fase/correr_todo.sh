#!/usr/bin/env bash
# Corre las 4 simulaciones de ngspice y genera las figuras en resultados/.
# Uso:  bash correr_todo.sh            (voz sintetica)
#       bash correr_todo.sh mi_voz.wav [inicio_s] [duracion_s]   (voz grabada)
set -euo pipefail
cd "$(dirname "$0")"
NGSPICE="${NGSPICE:-ngspice}"
PYTHON="${PYTHON:-python3}"

mkdir -p resultados
"$PYTHON" generar_senal_voz.py "$@"

for f in 01_fuente_corriente.cir 02_ac_fase.cir 03_tran_barrido.cir 04_tran_voz.cir; do
  echo ">> ngspice -b $f"
  "$NGSPICE" -b "$f" > "resultados/${f%.cir}.log" 2>&1 || { echo "Fallo $f (ver resultados/${f%.cir}.log)"; exit 1; }
done

"$PYTHON" graficar.py
