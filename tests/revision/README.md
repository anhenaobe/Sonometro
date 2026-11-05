# Pruebas de la revisión: software y laboratorio

Pruebas numéricas reproducibles, con datos sintéticos identificados:

```powershell
.venv/Scripts/python.exe -m unittest discover -s tests/revision -v
.venv/Scripts/python.exe -m unittest discover -s tests -p test_capture.py -v
```

Verifican unidades RMS/pico, acoplamiento cargado frente a impedancias complejas, filtro frente a solución nodal independiente, retardo de grupo, conservación RMS ante fase sola, respuesta shelving de Voxter y margen nominal. Su éxito no es un PASS físico.

## Siguiente prueba física exacta

Fuente 24 V limitada; sin micrófono ni ADC. Carga de 4,46 kΩ, luego 5,72 kΩ, ≥0,25 W. Medir corriente y voltaje estacionarios, encendido, desconexión y temperatura; repetir 2,4/2,8/4 mA. Scope de alta impedancia, masa correcta, no conectar tierra de instrumento arbitrariamente al nodo de corriente. Recalcular cargas al cambiar corriente: a4 mA,3,125/4,0 kΩ dan aproximadamente12,5/16 V;5,72 kΩ a4 mA entra en el ensayo de dropout, no es un punto garantizado de regulación. Confirmar límites del sensor antes de conectarlo.

| Prueba posterior | Condición | Criterio propuesto / evidencia requerida |
|---|---|---|
| AFE sin ADC | Generador real, offset12,5 V, Rs50 Ω, seno1 kHz/55,73 mV RMS; carga60 kΩ a2,5 V | Ganancia0,371747±0,3% a temperatura ambiente; registrar DC, amplitud, fase, THD y ancho de banda del instrumento |
| Barrido |20/100/1k/4k/10k/20k Hz; amplitud constante medida | Respuesta eléctrica calibrada dentro de±0,2 dB propuesta; fase registrada, sin declarar plana por inspección visual |
| Saturación |Hasta3,516 V pico desde sensor equivalente | Sin clipping nominal; medir margen con VCC y sensibilidad reales |
| Protección |24V/5V en ambos órdenes; sensor abierto; ADC apagado; selección de rango | Vpin e Iinyectada dentro de límites oficiales en todo momento; **no conectar ADC hasta obtener evidencia** |
| ADC interno |PA0,1,65 V+100 mV pico,1 kHz real;8192 muestras | Sin saltos/CRC inválido; fs medida; frecuencia FFT dentro de fs/N más error de reloj; RMS con VDDA medida |
| PCM1808 |Oscilador24,576 MHz;96kSPS;SAI24bit en32 | Medir BCK6,144 MHz/LRCK96k; signos/LR correctos; ráfagas sin overruns; transporte continuo OPEN |
| Ruido y acústica |Entrada equivalente correcta, banda20–20k; calibrador certificado | Guardar señal cruda; reportar ponderación, banda, ventana y piso del instrumental; no comparar dBA con dB sin ponderación |
| Aliasing |Generador fuera de banda con amplitud definida, barrido hasta límite de instrumentación | Registrar componentes replegadas; acordar umbral con profesor; filtro75k por sí solo no basta |

Formato CSV de registro (campos vacíos hasta medir):

```csv
fecha,operador,revision,prueba,instrumentos_certificados,temperatura_C,MPN_real,VIN_V,VCC_V,VDDA_V,carga_ohm,Rs_ohm,fs_medida_Hz,frecuencia_Hz,entrada_Vrms,salida_Vrms,fase_deg,ruido_Vrms,banda_Hz,ponderacion,pico_max_V,corriente_inyectada_A,overruns,archivo_crudo,criterio,resultado,observaciones
```

Todas las pruebas físicas: **OPEN**. Fuente, acoplamiento, amplificación, ADC y transporte deben validarse por separado antes de liberar PCB. La protoboard solo es preliminar; entrega final sobre PCB convencional.
