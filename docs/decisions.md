# Decisiones y riesgos

Fecha de revisión documental: 2026-10-24. **No hay mediciones, simulaciones, compras ni compatibilidad de la cadena demostradas en este repositorio.**

## Confirmado y provisional

| Elemento | Estado y evidencia | Acción / responsable |
| --- | --- | --- |
| Alcance de un canal, PC Python y desarrollo de un mes | CONFIRMED: requisito del proyecto | Integración/PCB mantiene alcance |
| Componentes instalados o disponibles en laboratorio | OPEN: ninguno confirmado por inventario | Cada rol verifica su material el 24–25/10 |
| RG-50 externo | PROVISIONAL: referencia. Datos aportados de la unidad: 55,6 mV/Pa; bias 12,5 V; corriente indicada 2,8 mA. No son un certificado | Electrónica IEPE obtiene identificación, ficha aplicable y certificado |
| Límites de catálogo RG-50 | CONFIRMED documentalmente en [ROGA](https://www.roga-instruments.com/downloads/PDF/RG-50-EN.pdf): corriente 2–20 mA, alimentación 18–30 V, bias aproximado 12,5 V y sensibilidad nominal aproximada 50 mV/Pa | OPEN: contrastar con la unidad concreta; 2,4/2,8/4 mA dentro del intervalo de catálogo no demuestra funcionamiento con nuestro cable y circuito |
| Fuente LT3092 | PROVISIONAL. [Datasheet Rev. D](https://www.analog.com/media/en/technical-documentation/data-sheets/lt3092.pdf): fuente ajustable; candidato LT3092EST#PBF en SOT-223, evitando DFN | Electrónica IEPE dimensiona resistencias, margen de tensión, ruido y disipación; ensaya 2,4/2,8/4 mA con cargas. [Simulación LTspice 2026-10-27](simulacion-lt3092.md): RSET 20 kΩ, ROUT 71,5 Ω (2,8 mA), CSET 100 nF, VIN 24 V; pendiente de T1 |
| MCU / placa | PROVISIONAL: [NUCLEO-F446RE](https://www.st.com/en/evaluation-tools/nucleo-f446re.html), con STM32F446RE; [datasheet STM32](https://www.st.com/resource/en/datasheet/stm32f446re.pdf): ADC de 12 bits, DMA, I2S/SAI y USB FS | Adquisición digital define pines, relojes y periféricos sin conflictos |
| ADC PCM1808PW | PROVISIONAL. [TI SLES177B, Rev. B](https://www.ti.com/lit/ds/symlink/pcm1808.pdf): estéreo, 24 bits, 8–96 kSPS, entrada single-ended nominal 3 Vpp, alimentación analógica 5 V/digital 3,3 V, TSSOP-14; I2S o justificado a izquierda | Adquisición digital valida formato estéreo y tratamiento del canal no usado según TI; IEPE adapta amplitud, bias y filtro |
| ADC interno | PROVISIONAL: ruta de respaldo para adquisición/USB, con offset y límites de entrada correctos | No usar su resolución nominal como prueba de rango dinámico acústico |
| Fabricación | CONFIRMED: preferir SMD convencional (SOT-223, TSSOP, SOIC, LQFP y pasivos accesibles); evitar QFN/BGA/via-in-pad cuando haya alternativa | Integración verifica MPN, footprint y reglas del fabricante antes de liberar |

## Decisiones abiertas y riesgos

| Tema | Estado / siguiente evidencia necesaria | Responsable |
| --- | --- | --- |
| Compliance y alimentación IEPE | OPEN: fuente de banco ajustable como primera opción; 24 V es solo candidato. Calcular `Vs >= bias + Vpico + caída de fuente/protección + margen`, revisar extremos y medir ruido, arranque, circuito abierto y disipación | Electrónica IEPE |
| Acoplamiento y protección | OPEN: seleccionar condensador por tensión máxima/transitorios, fuga y polaridad; resistencia de retorno, descarga y limitación hacia ADC. Calcular `fc = 1/(2*pi*Req*C)` con carga real. No conectar bias IEPE directamente al ADC | Electrónica IEPE |
| Ganancia, banda y ruido | OPEN: acordar banda útil, SPL mínimo/máximo y error admisible antes de fijar ganancia. Caracterizar saturación, respuesta y antialias; el filtro interno del ADC no valida toda la cadena | Integración + Electrónica IEPE |
| Relojes de audio | PROVISIONAL: iniciar a 48 kSPS; 96 kSPS solo tras validación. OPEN: asignar maestro/esclavo, MCLK/SCKI, BCK y LRCK y demostrar frecuencias válidas según TI; verificar mapa DMA y niveles eléctricos | Adquisición digital |
| Ruta USB | OPEN: CDC nativo como candidato; definir conector, VBUS, ESD, masa y reloj USB. El conector ST-LINK de Nucleo no conecta directamente el USB de aplicación: su VCP pasa por UART ([UM1724](https://www.st.com/resource/en/user_manual/um1724-stm32-nucleo64-boards-mb1136-stmicroelectronics.pdf)). VCP sirve para arranque a tasa reducida si se mide su capacidad | Adquisición digital |
| Caudal y pérdidas | PROVISIONAL calculado: mono 48k*3 = 144000 B/s; 96k*3 = 288000 B/s; con contenedor de 32 bits: 192000/384000 B/s, sin cabeceras. La trama estéreo del ADC puede duplicar carga interna. OPEN: medir caudal sostenido, buffers, secuencias y overruns | Adquisición digital |
| SPL y calibración | OPEN: conseguir calibrador con adaptador de 1/4 pulgada y certificado; estimar incertidumbre. Primero SPL de banda documentada sin ponderación; A/C y constantes temporales quedan posteriores y requieren validación propia | Adquisición digital + Electrónica IEPE |
| Compras y PCB | OPEN: stock, plazo local, costo y presupuesto sin verificar. Liberación de PCB el 18/11 condicionada a prototipo validado; confirmar entrega del fabricante. Si no llega, entregar prototipo y diseño con estado real | Integración/PCB |

## Referencias y reutilización

- [ADI CN0582](https://www.analog.com/en/resources/reference-designs/circuits-from-the-lab/cn0582.html): adquisición IEPE **de cuatro canales** por USB 3.0. Se consulta para excitación, protección y adaptación de señal; no implica implementar cuatro canales ni copiar su BOM.
- [ADI CN0579](https://www.analog.com/en/resources/reference-designs/circuits-from-the-lab/cn0579.html): referencia multicanal IEPE para estudiar protección y fuente.
- [ADI CN0561](https://www.analog.com/en/resources/reference-designs/circuits-from-the-lab/cn0561.html): referencia con acoplamiento AC y adquisición IEPE; sus resultados corresponden a su propia implementación.

Estas referencias no garantizan ruido, precisión, banda ni rendimiento acústico de nuestro sonómetro. Antes de reutilizar cualquier circuito, código o material, revisar la licencia/condiciones del archivo concreto y registrar atribución y modificaciones. GPL-3.0 del repositorio no sustituye esa revisión. Por ahora solo se incluyen enlaces y resúmenes técnicos originales.
