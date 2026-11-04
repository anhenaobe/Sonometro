# Captura PC mínima

`capture.py` recibe muestras reales por VCP o reprocesa un archivo recibido. No genera capturas ni implementa filtros, cancelación de offset o SPL. Datos sintéticos existen únicamente en pruebas unitarias y no son mediciones.

Desde raíz, Python3.11 o posterior:

```powershell
python -m pip install -r software/requirements.txt
python -m serial.tools.list_ports -v
python software/capture.py --port COM5 --rate 48000 --output software/captures/ensayo001 --plot
python software/capture.py --replay software/captures/ensayo001.iep --output software/captures/revision001 --plot
python -m unittest discover -s tests -p "test_*.py" -v
```

Identificar ST-LINK VCP y sustituir COM5; programar y cablear según [firmware](../firmware/README.md). Timeout inicial incluye8192/fs; a1k la adquisición tarda8,192s. Transferencia posterior, no streaming. USART115200 8N1 coincide con firmware.

Salidas con prefijo nuevo, sin sobrescribir: `.iep` conserva bytes originales (también parciales ante fallo), `.json` conserva configuración/errores, `.csv` cuentas/tiempo/fs nominal/voltaje con VREF asumida; `--plot` añade PNG. Rechaza cabeceras inválidas, CRC, secuencias faltantes/duplicadas, cambios de formato, muestras fuera de12 bits y errores MCU. No ressincroniza descartando datos; falla y conserva evidencia. No concatena ráfagas como continuas.

RMS incluye DC: `sqrt(mean(V²))`, escala `cuenta*VREF/4095`. La media se informa y no se resta. FFT Hann periódica solo para visualizar, corrección de ganancia coherente, amplitud de tono en **V RMS/bin**, DC en V; guarda muestras sin ventana. No es PSD ni suma RMS de ruido. Detector de seno busca desde bin3 excluyendo DC y su lóbulo inmediato; no sirve por debajo de3*fs/N ni demuestra presencia de tono cuando solo hay ruido. Resolución48k/8192=5,859375Hz; tonos no coherentes sufren fuga espectral.

`received_crc_and_continuity_valid` significa recepción digital coherente, no calibración/reloj/aliasing/rendimiento acústico. `fs_measured_Hz` queda null hasta medir. Validación física OPEN.
