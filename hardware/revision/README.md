# Reproducción de la revisión 2026-11-05

Propuesta, no validación física. Informe y fuentes: [docs/revision-arquitectura.md](../../docs/revision-arquitectura.md). Resumen para presentar: [PDF](../../output/pdf/propuesta-revisada-iepe.pdf).

Desde la raíz del repositorio:

```powershell
.venv/Scripts/python.exe -m pip install -r hardware/revision/requirements.txt
.venv/Scripts/python.exe hardware/revision/simulate.py
.venv/Scripts/python.exe -m unittest discover -s tests/revision -v
.venv/Scripts/python.exe hardware/revision/presentation.py
```

`models.py`: ecuaciones originales de redes equivalentes; no macromodelos de fabricantes. `simulate.py`: diez figuras PNG/SVG, tablas CSV y resultados JSON. Entradas eléctricas **sintéticas**, nunca capturas de laboratorio. `results/summary.json` registra versiones, hipótesis y hashes de scripts. `results/adc_comparison.csv` conserva bandas/ponderaciones; no sumar ruido de cuantización otra vez al ruido ADC.

`chain.cir`: A3 con TI OPAx192, sensor equivalente ideal Rs=50 Ω y carga PCM equivalente. Modelo separado, sin redistribuir. Para obtenerlo consultar `../afe/fetch_model.py` y condiciones de TI. SHA256 esperado: `1c438e45e978ffaf5aa13c7e2bb18ad5da70259775522ec41f47633a5db99033`.

```powershell
.venv/Scripts/python.exe hardware/revision/spice.py --dll 'C:/Program Files/KiCad/10.0/bin/ngspice.dll' --case ac
```

**Resultado actual: fallo explícito**, no curva SPICE aceptada. Log y manifiesto versionados; archivos grandes e intermedios en `runs/` ignorados. Casos preparados `tran`, `overload`, `startup`, `unplug`, `poweroff`, `supply`, `tolerance` **no ejecutados ni aceptados después del fallo inicial AC**. El caso poweroff solo cambia la polarización de carga; no representa diodos internos de ADC apagado, por lo que no demuestra protección. LTspice no disponible. No modificar un modelo oficial para forzar convergencia.

La respuesta ADS8681 usa un Bessel de segundo orden ajustado al dato de 15 kHz; sus coeficientes internos no son públicos. Los FIR de los ADC no se inventan: se usan banda publicada, retardo y una aproximación explícita del HP del PCM. THD de opamps, protección, alias completo y ruido de fuente permanecen OPEN.

`procurement.csv`: instantánea de páginas consultadas, USD unitario sin envío/impuestos. Stock publicado no garantiza entrega ni inventario del laboratorio.
