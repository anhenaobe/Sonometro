# Fuente de corriente IEPE - investigación y simulaciones

**Estado: PROVISIONAL (simulaciones, no validación de banco).** Trabajo iniciado el 27/10/2026.

Candidato principal para prototipo: **LT3092EST#PBF**, alimentación de banco de 24 V, RSET=20 kΩ, ROUT=71,5 Ω, corriente objetivo 2,8 mA. Esta elección aún NO autoriza conectar el RG-50 ni fabricar PCB.

## Resultados aportados de LTspice
- LT3092 biblioteca nativa de LTspice, carga resistiva de 4,46 kΩ a 27 °C: **I(RLOAD)=2,80754 mA**, **V(IEPE)=12,5216 V**, diferencia relativa respecto de 2,8 mA de **+0,269 %**.
- Emulador eléctrico de micrófono: 12,5 V DC + seno de 50 mV pico a 1 kHz, resistencia serie de 50 Ω y capacitancia de cable de 1 nF. Medidas sobre RMIC: Iavg=2,807533 mA; Imax=2,807832 mA; Imin=2,807234 mA. V(IEPE)max=12,690376 V; min=12,590377 V.
- I(RMIC) varía con la corriente de carga del condensador del cable. **No es la misma magnitud que la corriente instantánea entregada por el regulador**. Para separarlas, revisar I(CCABLE) y las ramas de la fuente.
- Estas cifras proceden de capturas de ejecución del usuario; NO son mediciones físicas ni reproducen un modelo acústico certificado.

## Opciones evaluadas
1. **LT3092 básico:** seleccionado provisionalmente por sencillez, documentación del fabricante y simulaciones DC + 1 kHz favorables.
2. **LT3092 de bajo ruido:** alternativa por evaluar, RSET=120 kΩ, ROUT=430 Ω, CSET=10 µF propuesto a partir del enfoque documentado por CN0540. Esta **no es** la misma red experimental que aparece en 03_LT3092_FILTRADO_1kHz.cir (100 nF + RC); no usar aquella versión sin estudio de estabilidad y ruido.
3. **OPA192 + BSS84:** ruta de contingencia. Modelos comerciales candidatos pero pruebas físicas, realimentación y referencia flotante por validar.

Ver [informe técnico resumido](../../docs/iepe-current-source-selection.md), los archivos de [simulación](simulations/) y [las pruebas T1-T3 del proyecto](../../tests/README.md).

## Pendientes antes de utilizar el micrófono
- T1: cargas ficticias y corriente 2,4 / 2,8 / 4 mA, variación Vs y compliance, ruido y comportamiento en fallas.
- Verificar certificado/identificación del RG-50; cable, transitorios y margen.
- Filtro, acoplamiento AC y protección de ADC aún OPEN. No aplicar bias de ~12,5 V directamente al PCM1808.
- Documentar impedancia de salida en frecuencia, ruido e incertidumbre antes de aprobar la arquitectura.

Fuentes: [LT3092 Rev D](https://www.analog.com/media/en/technical-documentation/data-sheets/lt3092.pdf) · [CN0540](https://www.analog.com/en/resources/reference-designs/circuits-from-the-lab/cn0540.html) · [ROGA RG-50](https://www.roga-instruments.com/downloads/PDF/RG-50-EN.pdf).
