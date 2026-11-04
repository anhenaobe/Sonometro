# Etapa de amplitud y adaptación — PROVISIONAL, 2026-11-04

Recomendación del primer incremento: **A, divisor 16,9 kΩ/10,0 kΩ + buffer OPA2192ID a 5 V**. Ganancia ideal `100/269 = 0,3717472`; con fuente resistiva de 50 Ω, 0,3710575. Preparar C como rango alto opcional; no utilizar B para cubrir todo el rango acústico. Ninguna de estas propuestas está medida físicamente.

## Evidencia y límites de interfaz

Se auditaron todas las referencias remotas disponibles: `main` bbe481b integra `docs/lt3092-simulacion-2026-10-27` b4142ea; `feature/iepe-current-source` c7da0b3 sigue sin integrar. No contienen firmware ni esquemas AFE terminados. Se conserva la fuente IEPE y su simulación.

La [simulación anterior](simulacion-lt3092.md) reporta 12,69 V de arranque en `acout`, 485,1 ms hasta bajar de 0,1 V y 24 V en el nodo IEPE abierto. Son resultados previos de un modelo, no mediciones. En su netlist `05_arranque.net`, 50 Ω están **antes** del condensador existente de 1 µF; el retorno es 100 kΩ a masa. Por tanto, después del condensador no hay una fuente resistiva ideal de 50 Ω ni una interfaz protegida confirmada.

Contrato que debe cerrar Electrónica IEPE antes de conectar:

- Entregar tensión DC y equivalente de Thévenin DC/AC **bajo nuestra carga**; no basta indicar sensibilidad del micrófono. Carga de A/C: 26,9 kΩ hacia una referencia, que también inyecta corriente DC al retorno existente.
- Confirmar protección ante arranque, sensor desconectado, apagado parcial y sobretensión. La etapa no es un limitador ni admite conectar directamente los 12,5 V del sensor. La alimentación de 24 V pertenece al bloque anterior.
- Acordar polarización, tiempo de establecimiento y capacidad de tensión/polaridad del condensador ya existente. La referencia de adaptación aquí calculada no elimina el bias IEPE.
- Acordar banda y atenuación antialias para el ADC elegido. Aquí **no se diseñan filtros ni nuevos condensadores de acoplamiento**. Los 20 pF del banco SPICE representan carga parásita supuesta, no un componente propuesto.

El [PCM1808, SLES177B](https://www.ti.com/lit/ds/symlink/pcm1808.pdf), tablas eléctricas y §8.2, confirma: 24 bits nominales, hasta 96 kSPS, entrada single-ended 3 Vpp a VCC=5 V, centro 2,5 V, impedancia típica 60 kΩ, alimentación digital 3,3 V e I²S/justificado a izquierda. SNR típico 99 dB **ponderado A**, mínimo 95 dB en condiciones de ficha: no equivale a 24 bits efectivos. TI recomienda acoplamiento AC en su circuito de aplicación: resolver con el propietario de acoplamiento cómo mantener ese requisito y la polarización interna al insertar el AFE; conexión DC directa queda **OPEN** hasta revisar/medir la interfaz completa. No cargar VREF del ADC como referencia externa sin comprobarlo.

## Tres alternativas y ecuaciones

Definiciones: fuente anterior `Vu=V0+v`, impedancia `Zs(f)`; `Vb` referencia de polarización del divisor; `Vc` centro deseado a la salida (2,5 V PCM, 1,65 V ADC interno). Referencias de baja impedancia y alimentación/masa comunes. Las ecuaciones ideales ignoran corriente de entrada; los errores se presupuestan después.

```text
A: Vu ─ Zs ─ Rt=16k9 ─●── (+) U1B OPA2192 ─── ADC
                      │          (-)←salida
                    Rb=10k
                      │
                     Vb

B: Vu ─ Zs ─ (+) U1
               (-)──●── Rf=9k09 ─ salida ─ ADC
                    └── Rg=1k00 ─ Vc

C: divisor de A → (+) U1
                   (-)──●── Rf=9k09 ─ salida ─ ADC
                        └── Rg=1k00 ─ Vc
   Bajo: realimentación directa, Rg desconectada.
   Alto: Rf/Rg conectadas; cambiar jumpers con captura detenida.
```

Por KCL en el divisor, `(Vu-V+)/[Zs+Rt]=(V+-Vb)/Rb`:

`a(f)=Rb/[Rt+Rb+Zs(f)]`; **A:** `Vo=a*Vu+(1-a)*Vb`, ganancia de señal `a`, noise gain 1.

En B/C, corriente de entrada ideal nula y `V-=V+`; KCL de realimentación da `Vo=N*V+ +(1-N)*Vc`, `N=1+Rf/Rg=10,09`. **B:** `Vo=N*Vu+(1-N)*Vc`. **C:** `Vo=N*a*Vu+N*(1-a)*Vb+(1-N)*Vc`. Dos referencias distintas evitan multiplicar un error de centro inadvertidamente. No se añade amplificador de instrumentación: la interfaz es single-ended.

| Propiedad | A | B | C alto (C bajo=A) |
| --- | --- | --- | --- |
| Ganancia ideal de señal | 0,3717472 | 10,09 | 3,7509294 |
| Valores comerciales E96 | Rt 16k9, Rb 10k0 | Rf 9k09, Rg 1k00 | Los cuatro anteriores |
| Carga de entrada | 26,9 kΩ hacia Vb | Entrada CMOS; depende de capacitancia/fugas reales | 26,9 kΩ hacia Vb |
| Señal máxima a entrada, ADC ±1,5 V | 4,035 V pico | 0,148662 V pico | 0,399901 V pico |
| Máximo ideal SPL pico / RMS senoidal | 131,195 / 128,184 dB | 102,522 / 99,512 dB | 111,117 / 108,107 dB |
| Uso | Fuertes y margen sobre 130 dB pico | Solo rango de señales débiles; recorta a 120 dB | Extender resolución para débiles; conmutación/registro de rango obligatorios |

Estos máximos suponen centro exacto y son límites matemáticos, no especificaciones. Con offset de centro `Δ`, excursión útil es `1,5-|Δ|`; aplicar además tolerancias, ganancia del bloque anterior y variación de VCC. No considerar 130 dB **RMS**: excedería el límite pico de referencia del sensor para una senoide. B sin divisor, centrada a2,5V y excitada con130dB pico, recibiría −1,016 a6,016V: además de saturar salida, excedería los límites de entrada del operacional a5V; protección externa obligatoria antes de ensayar.

### Centro DC: ejemplo con el acoplamiento anterior

El Thévenin DC del modelo existente es 0 V con **Rdc=100 kΩ**, pues su condensador está abierto en DC. Entonces `a_dc=10k/(100k+16k9+10k)=0,0788022`, no el divisor de banda media. Para A, `Vo_DC=(1-a_dc)*Vb`, y necesitamos `Vb=2,5/(1-a_dc)=2,713858 V` (el script conserva la cifra exacta).

Referencia práctica preliminar: 5 V → 8,45 kΩ → nodo → 10 kΩ → masa; U1A OPA2192 como buffer entrega **2,710027 V**. Con el retorno del ejemplo, centro calculado ≈2,49647 V. Ajustar tras medir Rdc/V0; para fuente de generador de 50 Ω DC a 0 V, Vb debe ser aproximadamente 3,97493 V: **no reutilizar la referencia del ejemplo sin recalcular**. Si el bloque entrega ya V0=2,5 V con baja impedancia, usar Vb=2,5 V.

Para ADC STM32, centro 1,65 V: Vb requerido ≈1,791 V en el mismo ejemplo; divisor 8k45/10k alimentado a 3,3 V entrega 1,788618 V, que debe bufferizarse con el operacional aún a 5 V. Cambiar de ADC exige revisar referencia, rango y carga dinámica. Nunca aplicar la salida PCM centrada en 2,5 V ±1,307 V a A0 del STM32.

C alto usa además `Vc=2,5 V` independiente y estable. El error de centro del divisor se multiplica por 10,09; necesita ajuste y otra referencia bufferizada. Cambiar rangos manualmente para este prototipo evita introducir resistencia no lineal de un switch o PGA no seleccionado. PGA comercial queda OPEN hasta justificar ruido, distorsión y stock.

### Carga del acoplamiento existente

Incluyendo exactamente el ejemplo anterior, `Zc=50+1/(jω*1µF)`, `RL=100k || 26k9`, `H=0,371747*RL/(Zc+RL)`. Es evaluación de carga, no rediseño del filtro. Cálculo: |H(20 Hz)|=0,347313 (−0,591 dB frente a divisor ideal), |H(1 kHz)|=0,370862 (−0,021 dB). El corte previo efectivo cambia al conectar la etapa: debe aprobarlo el propietario de acoplamiento. Si la banda exige menor error, ese bloque debe entregar impedancia menor o revisarse conjuntamente; no ocultar la pérdida mediante software.

## Amplitudes calculadas

`p_rms=20µPa*10^(Lrms/20)`, `Vp_sensor=√2*S*p_rms` para seno; `p_peak=20µPa*10^(Lpeak/20)` y `Vp_sensor=S*p_peak` para el caso pico. S=0,0556 V/Pa **PROVISIONAL**. 94 dB exactos son 1,00237 Pa RMS, no exactamente 1 Pa.

| Caso | Presión RMS / pico (Pa) | Sensor Vrms / Vp | A Vp | B Vp | C alto Vp |
| --- | --- | --- | --- | --- | --- |
| 30 dB RMS | 0,00063246 / 0,00089443 | 35,1645 µV / 49,7302 µV | 18,487 µV | 501,78 µV | 186,53 µV |
| 60 dB RMS | 0,020 / 0,028284 | 1,112 mV / 1,57261 mV | 0,58461 mV | 15,8676 mV | 5,89873 mV |
| 94 dB RMS | 1,00237 / 1,41757 | 55,7320 mV / 78,8170 mV | 29,300 mV | 0,79526 V | 0,29564 V |
| 120 dB RMS | 20 / 28,2843 | 1,112 / 1,57261 | 0,58461 V | **15,868 V: recorte** | **5,899 V: recorte** |
| 130 dB pico, seno | 44,7214 / 63,2456 | 2,48651 / 3,51645 | **1,30723 V** | **35,481 V: recorte** | **13,190 V: recorte** |

## Comparación de operacionales reales

Típico **T**; límite de ficha **L** bajo sus condiciones, no garantía del circuito. SOIC-8 y adaptador DIP permiten protoboard corta; el montaje definitivo debe controlar masas/parásitos. Compra/stock/plazo/precio **OPEN** para todos; consultar fabricante/distribuidor autorizado antes de ordenar.

| Parámetro | [OPA192/OPA2192, SBOS620E](https://www.ti.com/lit/ds/symlink/opa192.pdf) | [OPA1652, SBOS477B](https://www.ti.com/lit/ds/symlink/opa1652.pdf) | [OPA1656, SBOS901C](https://www.ti.com/lit/ds/symlink/opa1656.pdf) |
| --- | --- | --- | --- |
| Ruido en / in | 5,5 nV/√Hz a 1k, 1,5 fA/√Hz T; cerca del rail superior 12,5 nV/√Hz T | 4,5 nV/√Hz a 1k, 3 fA/√Hz T | 4,3 nV/√Hz a 1k, 6 fA/√Hz T; 0,53 µVrms integrado 20–20k T |
| Vos / deriva | 25 µV máx a Vcm=V+−3; región superior 40 µV; deriva SOIC hasta 0,8 / región superior 3 µV/°C L, transición requiere gráfica | 1,5 mV L / 2 T, 8 L µV/°C | 1 mV L / 0,3 T, 2 L µV/°C |
| Ib a 25°C | 5 pA T, 20 pA L; hasta 5 nA L a temperatura extrema | 10 pA T, 100 pA L | 10 pA T, 20 pA L |
| GBW / SR T | 10 MHz / 20 V/µs | 18 MHz / 10 V/µs | 53 MHz (G100); unidad 20 MHz / 24 V/µs |
| Alimentación | 4,5–36 V; RRIO | 4,5–36 V; entrada V−+0,5 a V+−2; salida RRO | 4,5–36 V; entrada V− a V+−2,25; salida RRO |
| Excursión | Con 2k: hasta 0,5 V de rail L; con 10k: 0,110 V L | 0,8 V de cada rail con 2k | 0,25 V de cada rail con 2k T |
| THD+N T, no extrapolar | 0,00008 % a 1k, 3,5 Vrms, ±18 V | 0,00005 % a 1k, 3 Vrms, ±15 V | 0,000029 % a 1k; 0,000035 % a 20k, 3,5 Vrms, ±18 V, 2k |
| Iq por canal | 1 mA T, 1,2 L a 25°C, 1,5 L sobre temperatura | 2 mA T, 2,5 L a 25°C | 3,9 mA T, 4,6 L a 25°C |
| Estabilidad | Unidad; carga capacitiva requiere evaluación | Unidad; caracterizado con 100 pF | Unidad; caracterizado con 100 pF |

**Selección:** OPA2192ID, familia OPA192 en dual SOIC para señal + referencia. A 5 V, el máximo del pin no inversor de A es ≈3,81 V: OPA1652 exigiría V+≥5,81 V y OPA1656 ≥6,06 V solo por modo común. Ambos implican otra alimentación; no son RR de entrada. OPA2192 permite 5 V y reduce Vos/consumo; su ruido y distorsión al cruzar regiones de entrada necesitan ensayo. El ahorro de ruido del OPA1656 no justifica todavía alimentación extra frente al piso del micrófono y ADC. Es alternativa si el ensayo de distorsión descarta OPA2192.

## Presupuesto de ruido, error y potencia

Banda rectangular **20 Hz–20 kHz**, 300 K, sin ponderación: representa la banda acústica objetivo preliminar, no un filtro implementado. Integrar `e²(f)`, no densidades linealmente. Para OPA192 se ajusta `en²=a+b/f` a los puntos típicos superiores 32 nV/√Hz a 100 Hz y 12,5 a 1k: integral **1,364 µVrms**. Es estimación, no cota garantizada; la zona de transición del modo común queda OPEN. No convertir ruido pico a pico a RMS sin modelo estadístico.

Para fuente resistiva Rs=50 Ω: `Rp=(Rt+Rs)||Rb=6289,42 Ω`; `Rm=Rf||Rg=900,89 Ω` en alto. `eRout=N*sqrt[4kT*(Rp+Rm)*B]`; `eiout=N*in*sqrt[(Rp²+Rm²)*B]`. Para B, Rp=Rs. `eout²=eVout²+eRout²+eiout²`. Referir a entrada dividiendo por ganancia **cargada** a 1k; `p_eq=e_in/S`, `Leq=20log10(p_eq/20µPa)` siempre RMS. El presupuesto siguiente incluye Rs térmica, no electrónica del micrófono/fuente.

| Típico estimado, referencias ideales | A | B | C alto |
| --- | --- | --- | --- |
| Opamp a salida µVrms | 1,364 | 13,766 | 13,766 |
| Resistencias a salida µVrms | 1,443 | 5,661 | 15,567 |
| Corriente de entrada a salida µVrms | 0,00133 | 0,00193 | 0,01359 |
| Total salida / entrada µVrms | 1,986 / 5,352 | 14,885 / 1,475 | 20,781 / 5,550 |
| Pa equivalentes RMS | 96,25 µPa | 26,53 µPa | 99,83 µPa |
| dB SPL equivalentes RMS | 13,65 | 2,46 | 13,96 |

Referencia real: divisor 8k45/10k tiene Rth=4,580 kΩ y ruido 1,231 µVrms; con buffer estimado 1,364, Vb≈1,838 µVrms, excluyendo ruido de la fuente 5 V. Se transfiere por `N*(1-a)`; el ruido independiente de Vc por `1-N`. En A, total estimado incluyendo Vb ≈2,30 µVrms a salida (≈14,9 dB SPL equivalente). En C con Vb y Vc de 1,838 µVrms cada una, ≈29,1 µVrms a salida (≈16,9 dB SPL). No omitir estas referencias del ensayo; su ruido de alimentación puede dominar.

Con Zs capacitiva real usar la parte real del Thévenin pasivo e integrar su transferencia dependiente de frecuencia; los números anteriores son línea base resistiva, no presupuesto final de la cadena. El script publica el cambio de respuesta causado por el ejemplo existente. No sumar el SNR ponderado A del ADC a este ruido sin ponderación. Orientativamente 99 dB A a seno de escala completa corresponden a 11,9 µVrms A en el ADC: frente a 13,1 µVrms de señal a 30 dB RMS en A, justifican C para débiles, pero **no demuestran** poder medir 30 dB. El propio piso de catálogo del micrófono ronda 32 dB sin ponderar y debe verificarse para la unidad.

Resistencias propuestas: 0,1 %, ≤25 ppm/K, película delgada 0805, ≥0,1 W. Evaluación independiente de extremos con producto `(1±tolerancia)*(1±TCR*ΔT)`: A ±0,126 % inicial, ±0,283 % con ΔT=50 K; B ±0,182 % inicial, ±0,410 % a50K; C ±0,307 % inicial, ±0,691 % incluyendo TCR no correlacionados. No confundir valor E96 con tolerancia. Rs=50 Ω reduce ganancia A 0,186 %; Rs=1k la reduce 3,58 %. Hay que medir Zs, no absorberlo silenciosamente en la calibración.

Vos se multiplica por N: un supuesto de cálculo de 250 µV por amplificador reserva 0,25 mV en A y 2,523 mV en C; no se presenta como garantía de toda la transición Vcm. Deriva hipotética conservadora 3 µV/K por 50 K: 0,15 mV en A, 1,514 mV en C. Ib máximo térmico 5 nA por Rp provoca ≈31,4 µV antes de multiplicar N. Añadir error del buffer/divisor de referencia y ruido de fuente. En la referencia 8k45/10k, tolerancia 0,1 % independiente produce hasta ≈0,092 % de error relativo (≈2,49 mV); TCR/variación de rail desplazan el centro. Una variación de 1 % de 5 V puede moverlo ≈25 mV; C exige ajuste y referencia más estable.

SR requerido para 1,5 Vp a 20k: `2πfVp=0,1885 V/µs`, frente a 20 V/µs típico. Aproximación monopolo: GBW/N≈10 MHz en A y 0,991 MHz en C, muy por encima de 20k; no sustituye el análisis de lazo. A 5 V, excursión 1,19–3,81 V deja margen incluso usando 0,5 V de rail. Mínimo de diseño del opamp 4,5 V por ficha; proponer 5 V nominal. Una salida a 5 V puede dañar ADC STM32 apagado o exceder su rango: la alimentación común no resuelve apagados parciales.

A 130 dB pico senoidal, potencia AC en Rt≈0,144 mW y Rb≈0,085 mW; máxima tensión pico Rt≈2,209 V, Rb≈1,307 V. En alto a su límite, RF≈0,1004 mW y RG≈0,0111 mW. Son potencias de señal, no transitorios. Para un fallo DC de 24 V entre extremos del divisor: corriente≈0,892 mA, Rt≈13,45 mW, Rb≈7,96 mW; aunque las resistencias soporten esa potencia, **el opamp/ADC no están protegidos**. El dual consume típicamente 10 mW a 5 V, hasta 15 mW usando Iq térmica máxima, más 1,355 mW del divisor de referencia y potencia de carga. Desacoplo de alimentación local según fabricante: no forma parte del filtrado de señal.

## Simulación reproducible y resultados

No se encontró LTspice en esta máquina. Se ejecutó **ngspice 46 compartido de KiCad 10**, compatibilidad PSpice, con macromodelo **TI OPAx192 Final 1.7, 26-AUG-2022**, descargado de [SBOM862](https://www.ti.com/lit/zip/SBOM862). Archivo sin modificar, SHA256 `1c438e45e978ffaf5aa13c7e2bb18ad5da70259775522ec41f47633a5db99033`. Sus condiciones de uso se conservan localmente; no se redistribuye el archivo del fabricante. Netlist y scripts son propios.

Desde la raíz (Python del entorno local):

```powershell
python hardware/afe/fetch_model.py
python hardware/afe/calculate.py
python hardware/afe/run_suite.py --dll "C:/Program Files/KiCad/10.0/bin/ngspice.dll"
```

Artefactos: [netlist](../hardware/afe/afe.cir), [cálculos](../hardware/afe/calculations.json), [esquinas de tolerancia](../hardware/afe/tolerance_corners.csv), [resumen SPICE](../hardware/afe/simulation_results.json), [gráficas simuladas](../hardware/afe/simulation_summary.png). `runs/<caso>/` conserva netlist exacta, datos tabulados, log y hashes; se regenera y no se sube el volumen de trazas. `afe.cir` incluye instrucciones AC/transitorio/ruido para abrir en LTspice con el modelo instalado: **esa ejecución LTspice no fue realizada**.

- A nominal, fuente 50 Ω: ganancia simulada 0,3710575 a 1k y 0,3710541 a 20k. A 130 dB pico: salida 1,1952–3,8048 V. Barridos incluyen 30/60/94/120 dB RMS, 130 pico y tonos a 20 Hz/1k/20k.
- Con 60k y **20 pF supuestos**, impedancia de salida simulada 0,0347 Ω a 1k y 0,6925 Ω a 20k. Inyección en lazo: margen aproximado 65,8° en A y 81,7° en alto. Depende de macromodelo, carga y parásitos; no garantiza estabilidad con cable o ADC real. Medir respuesta a escalón/carga antes de añadir ningún aislador.
- Esquinas A de resistencias con tolerancia+50 K: ganancia simulada con Rs50 entre 0,370009 y 0,372107. La esquina máxima necesitó `--nodeset` como estimación inicial2,5V para resolver convergencia del macromodelo; no fuerza tensiones ni sustituye el punto de operación. El log conserva los intentos del solver. Fuentes del opamp de 4,5/5,5 V no recortan el caso nominal; sobrecarga de 10 Vp satura salida cerca de 0,021–4,961 V.
- Se modeló aparte el **acoplamiento ya existente**, con Vb=2,710027 y Vc separado para C: ganancia A 0,347313 a 20 Hz y 0,370862 a 1k. Los transitorios incluyen establecimiento de 250 ms. Esto no valida el acoplamiento físico ni autoriza cambiarlo.
- Arranque: entrada de prueba PWL deliberadamente peligrosa, aproximadamente 2,5+12,69 V, con rampa de alimentación. La salida llega cerca de 4,961 V: supera rango nominal del PCM y es peligrosa para STM32. La PWL es un estímulo de estrés, no una repetición exacta de la simulación IEPE.
- **Ruido SPICE OPEN:** el modelo bajo ngspice exportó ≈36,84 µVrms en A al integrar el espectro, pero su salida integrada interna indicó ≈5,04×10⁴ V. Es inconsistente con la ficha y el cálculo: no se acepta como presupuesto ni resultado de rendimiento. Revalidar ruido en simulador compatible con TI; no se alteró el modelo para forzar coincidencia.

Distorsión THD, protección frente a desconexión, apagado parcial, tolerancias del opamp, temperatura y estabilidad con el ADC dinámico siguen OPEN físicamente. Los bancos SPICE usan referencias ideales: el divisor/U1A práctico está presupuestado analíticamente; su arranque y estabilidad bajo carga siguen OPEN. La simulación no contiene un modelo completo del ADC ni del sensor. La siguiente prueba analógica es montar únicamente A con referencias medidas y generador protegido; el micrófono entra después de cerrar el contrato de interfaz.
