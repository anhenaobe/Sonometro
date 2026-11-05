# Revisión técnica IEPE — propuesta para el 5 de noviembre de 2026

**Estado: PROVISIONAL. Ningún circuito ni captura física validado por esta revisión.** MCU cerrado: STM32L432KC; prototipo NUCLEO-L432KC; entrega final en PCB. Banda propuesta: **20 Hz–20 kHz, sin ponderación**. Objetivos de aceptación de laboratorio propuestos, sujetos al profesor: error eléctrico de amplitud después de calibración ≤0,2 dB, sin clipping hasta 130 dB SPL **pico**; medir fase y ruido, sin prometer certificación IEC 61672.

Se recomienda ensayar **A3: LT3092 + buffer de alta impedancia a 24 V + atenuación 0,371747 + filtro suave + un solo acoplamiento AC al PCM1808 a 96 kSPS**. Reduce la carga sobre el sensor y elimina V_MID externa. No está lista para liberar PCB: protección del ADC, condensador real, ruido sin ponderación, alimentación/reloj y transporte siguen OPEN. Si no se logra su protección y adquisición a tiempo, conservar el prototipo de ADC interno como evidencia parcial, sin presentarlo como sonómetro final.

## 1. Auditoría y trazabilidad

Trabajo sobre `Sonometro`, no VibrationDAQ. Árbol inicial limpio. Se consultaron referencias remotas e historial completo; rama nueva `review/architecture-filters-adc-2026-11-05`, basada en Codex `082dd43`, sin merge a main.

| Referencia auditada | Commit | Aporte y tratamiento |
|---|---|---|
| main | bbe481b | Base integrada; incluye simulación LT3092 b4142ea |
| feature/afe-l432-acquisition-2026-11-04 | 082dd43 | Base elegida; AFE 7274cb9, firmware HAL ADC/DMA y programa PC reales |
| workspace/voxter | d61c941 | Se leyó propuesta/propuesta_sonometro.tex y su antecedente 9abdcee; investigación y esquemas conceptuales, no firmware ni SPICE ejecutable |
| feature/iepe-current-source | c7da0b3 | Trabajo independiente de fuente; se preserva sin modificar |
| docs/lt3092-simulacion-2026-10-27 | b4142ea | Evidencia histórica LTspice; no medición ni validación de la cadena nueva |
| bootstrap | 133f99c | Documentación inicial; F446 era propuesta anterior |

Se revisaron README, decisions, simulacion-lt3092, BOM, hardware/afe (incluidos calculations.json y simulation_results.json), firmware, software y tests. No se encontró otro firmware L432 en Voxter/fuente/main que deba rescatarse. Se conserva el código de adquisición y sus pruebas; esta revisión no cambia fuentes C. Las restricciones históricas de Voxter de through-hole, placa perforada y Pico/ESP32 no se adoptan: fueron sustituidas por la decisión actual del equipo.

Se rescatan de Voxter dos excitaciones independientes (segunda opcional sin poblar), selección después del acoplamiento, investigación de cápsulas y pruebas por bloques. No se copian dibujos, texto ni modelos externos; los bancos equivalentes y derivaciones de esta revisión son originales. El macromodelo TI se obtiene separado y conserva sus condiciones de uso.

## 2. Sensor, presión y margen

ROGA publica para RG-50 alimentación 18–30 V, 2–20 mA, bias aproximado 12,5 V y salida de aproximadamente 50 Ω. Sensibilidad nominal cercana a 50 mV/Pa; **55,6 mV/Pa pertenece provisionalmente a la unidad identificada y exige certificado**. El catálogo indica 130 dB pico, ruido 32 dB SPL 5 Hz–20 kHz / 27 dBA: bandas y ponderaciones distintas. Respuesta publicada ±0,5 dB hasta 4 kHz y ±1,5 dB hasta 30 kHz; el error acústico no se reduce al error eléctrico del AFE. [Ficha ROGA](https://www.roga-instruments.com/downloads/PDF/RG-50-EN.pdf).

`p_rms=20 µPa·10^(L_rms/20)`, `v_rms=S·p_rms`. Para senoide `p_peak=√2 p_rms`. Si L está definido **pico**, usar directamente `p_peak=20 µPa·10^(L_peak/20)`; su RMS senoidal es 3,0103 dB menor. Presión atmosférica no interviene como amplitud acústica.

| Nivel | Definición | Presión RMS (Pa) | Sensor RMS (V) | Sensor pico (V) | Pico con g=0,371747 (V) |
|---|---|---:|---:|---:|---:|
|30|RMS|0,00063246|0,000035165|0,00004973|0,00001849|
|60|RMS|0,020000|0,001112|0,0015726|0,0005846|
|94|RMS|1,002374|0,055732|0,078817|0,029300|
|100|RMS|2,00000|0,111200|0,157260|0,058460|
|120|RMS|20,0000|1,11200|1,57260|0,58460|
|130|pico|44,7214|2,48651|3,51645|1,3072|

Datos exactos: [sensor_amplitudes.csv](../hardware/revision/results/sensor_amplitudes.csv). A 130 pico, nodo IEPE ideal 8,9835…16,0165 V. Una entrada PCM ±1,5 V ofrece aproximadamente 1,19 dB de margen nominal con esta atenuación; no cubre arbitrariamente variaciones de sensibilidad, VCC y tolerancias.

SVANTEK: no equiparar un SV12, un SV12L y una cápsula completa. SV12L figura a **1,5 mA/30 V** y atenuación 0,7 dB en la documentación del fabricante; 28 V/2,5 mA de otro apartado corresponden a la entrada de acelerómetro del instrumento, no a su especificación. [Apéndice SVAN977W, p.6](https://svantek.com/wp-content/uploads/2021/05/svan_977w_appendix_c_2017-03-06.pdf), [manual SVAN958A, pp.191/198](https://svantek.com/wp-content/uploads/2023/01/SVAN958A-Man.EN_v.1.02_2023-03-03.pdf). Fotografiar modelo, conector y cápsula antes de fijar corriente. MK255/ACO 7052 investigados por Voxter siguen candidatos; no constituyen selección física. No conectar dos micrófonos en paralelo: fuentes, retornos y separación independientes; conmutación con adquisición detenida y tiempo de establecimiento.

## 3. Fuentes de corriente: matriz cuantitativa

Ecuaciones y barridos en [current_source_lt3092.csv](../hardware/revision/results/current_source_lt3092.csv), [TL431](../hardware/revision/results/current_source_tl431.csv), [LM334](../hardware/revision/results/current_source_lm334.json) y figura 01. Resistencias nuevas son propuestas de cálculo, no alteración del diseño de otro integrante.

| Criterio | LT3092 previo | LT3092 propuesta a contrastar | TL431 + PNP de Voxter | LM334M/NOPB |
|---|---|---|---|---|
| Programación |20 kΩ/71,5 Ω|120 kΩ/430 Ω|RE=470/750 Ω, RZ=10 kΩ|R=24,3 Ω|
| Nominal calculado |2,80720 mA|2,80070 mA|3,8867/2,4356 mA con VEB=0,65 V, β=100|2,786 mA a25°C|
| Error 25°C incluyendo R0,1% |2,74565…2,86893 mA|2,76252…2,83900 mA|RE665 Ω: 2,507…3,001 mA **envolvente condicional**, no garantía|±8% en rango 1–5 mA, más R|
| Envolvente ΔT=50 K |2,68293…2,93229 mA|2,72312…2,87887 mA|VEB y β dominan; ~+1084 ppm/K si dVEB/dT=−2mV/K supuesto|PTAT ~+3360 ppm/K|
| Sensibilidad a VIN |17,95 típico /69,82 máx25°C ppm/V|5,49 típico /28,30 máx25°C ppm/V|Depende de rZ, β y efecto Early; sin modelo garantizado|0,02%/V típico 5–40 V; máximo OPEN|
| Headroom evaluado |Vset0,2 + dropout|Vset1,2 + dropout|~2,045 V usando VCEsat0,2 **supuesto**, no garantía activa|~1 V; confirmar al punto de operación|
| VIN mínimo a130pico |17,666 V|18,666 V|~18,06 V condicional|~17,02 V orientativo|
| Potencia IC/PNP a bias |31,72 mW|28,85 mW|~26,52 mW con RE665; RZ46,25 mW|~32 mW|
| Ruido integrado comparable |Histórico: 0,464 µV RMS en50Ω,20–20k,modelo anterior|OPEN, no extrapolar del otro Rset|OPEN, ficha a otra corriente no garantiza este montaje|OPEN, referencia cualitativa a shot noise insuficiente|
| Construcción |SOT-223|TSOT-23-8 disponible publicado|SOIC TL431 + SOT23 PNP posibles|SOIC8|
| Selección |Conservar como referencia|Principal **PROVISIONAL**|Respaldo si inventario y medición justifican|No preferido por deriva/error|

LT3092: `Iout=ISET(1+RSET/ROUT)+VOS/ROUT`. ISET típico10µA ±1%@25°C/±2%temperatura; VOS ±2/±4mV. La precisión de ISET **no** es la de Iout. Barrido incluye extremos independientes y TCR±25ppm/K por resistor; envolvente térmica conservadora, no una deriva garantizada lineal de ISET. `dI/dVIN=(1+RSET/ROUT)dISET/dVIN+(1/ROUT)dVOS/dVIN`. Para 120k/430 un cambio2 V produce hasta ~0,00566% a25°C por estos términos. Dropout1,45V máximo citado corresponde a10mA: se utiliza como margen de diseño orientativo, no nuevo límite garantizado a2,8mA. [LT3092 Rev.D](https://www.analog.com/media/en/technical-documentation/data-sheets/lt3092.pdf).

TL431 de Voxter: K y REF a24V, A a basePNP,10k base→GND, RE24V→emisor, colector→sensor. `IC=β/(β+1)(VREF−VEB)/RE`. Su referencia estándar2,495V tiene extremos2,440…2,550V@25°C; versiónB reduce tolerancia inicial pero no elimina VEB/β. El cálculo usa VEB0,55…0,75 y β80…300 como **supuestos**, no límites de 2N3906 a2,8mA. No reutilizar VBE de saturación como VBE activa. [TL431](https://www.ti.com/lit/ds/symlink/tl431.pdf), [2N3906](https://www.onsemi.com/pdf/datasheet/2n3906-d.pdf). RZ conduce ~2,15mA, menos corriente de base; comprobar corriente mínima TL431 y estabilidad con cable/capacitancia, no limitarse al cálculo DC. LM334 tiene compensaciones térmicas posibles pero agregan componentes e incertidumbre; [ficha LM334](https://www.ti.com/lit/ds/symlink/lm334.pdf).

La exactitud de corriente de excitación **no se convierte directamente en error de ganancia acústica**. Mientras la electrónica del micrófono mantenga su régimen y compliance, su transferencia depende de su preamplificador; faltan `dS/dI` y respuesta con cable. Medir sensibilidad/THD frente a corriente. Ruido: `e_sensor²=∫|Zsensor(f)|²·Si(f)df`; 50Ω es aproximación de salida, no impedancia universal. Con cable, `Icap=Ccable·dv/dt`; por ejemplo1nF,3,516Vp,20kHz exige0,442mApico además del consumo interno. Evaluar ambos extremos de carga antes de aceptar2,8mA.

ISETnoise0,7nArms10Hz–100kHz es típico del LT3092 y no corriente de salida ni espectro plano. El resultado previo0,464µV equivale a9,28nArms en50Ω bajo ese modelo y a−7,59dBSPL con S provisional, **no un límite físico**. El modelo LT3092 disponible está cifrado para LTspice; LTspice no está instalado aquí, por lo que no se ha repetido. Mayor Vset reduce error por VOS y cambia filtroCSET100nF: τ2→12ms; no se puede afirmar ruido/arranque equivalente.

Sensor abierto: nodo puede alcanzar24V; corto: disipación IC hasta~64mW a2,8mA (segúnVset). Dimensionar temperatura `Tj=Ta+PθJA` con layout/encapsulado real; no asumir una θJA única. Arranque y desconexión no son análisis DC. La simulación anterior predice12,69V en acout y485ms para bajar de0,1V: evidencia de riesgo, no protección. Con fuente24V±10%, sigue margen nominal de compliance, pero no hay rechazo de ruido de alimentación ni estabilidad de carga medidos.

## 4. ADC STM32L432KC: qué puede medir realmente

[DS11451, §§6.3.19/tablas63–67](https://www.st.com/resource/en/datasheet/stm32l432kc.pdf) y [RM0394, §5.1 y capítulo ADC](https://www.st.com/resource/en/reference_manual/rm0394-stm32l41xxx42xxx43xxx44xxx45xxx46xxx-advanced-armbased-32bit-mcus-stmicroelectronics.pdf) son la evidencia principal. No confundir funciones de otros STM32L4 con las disponibles en este encapsulado.

| Propiedad | Resultado y condición |
|---|---|
| Conversor nativo |SAR12bits; configurable6/8/10/12. Oversampling2…256 con acumulación/desplazamiento hasta16bits almacenados; no16ENOB garantizados |
| Entradas físicas |Single-ended0…VREF+; diferencial también ambas entradas dentro de0…VREF+. Diferencia negativa posible; voltaje físico negativo **no** |
| Diferencial |Diferencia nominal ±VREF; VCM≈(VREF++VREF−)/2 ±0,18V:1,47…1,83V@3,3V |
| Referencia UFQFPN32 |Pin5 VDDA/VREF+ unidos; VREF− unidoVSSA. No pin VREF+ independiente. **VREFBUF no utilizable y debe permanecer deshabilitado**; VREFINT~1,212V sirve para estimar alimentación, no fija fondo de escala |
| Calibración |Salir DEEPPWD, habilitar regulador ADC, esperar hasta20µs; ADC deshabilitado al calibrar. Factores single/differential separados; no elimina INL/ganancia |
| Sample-and-hold |CADC típico5pF. Tabla64@80MHz: fuente máxima100Ω/2,5ciclos;2,2kΩ/47,5;12kΩ/247,5. Validar a reloj/pin reales; no sustituir tabla por un RC ideal |
| Actual firmware |ADC12MHz,47,5+12,5ciclos=5µs; TIM6 TRGO48k nominal; DMA circular. Oversampling256×48k=12,288Mconv/s supera5,33Msps |
| Pines prototipo |PA0 IN5 A0 CN4-12. Diferencial IN5−IN6 requiere PA1 A1 CN4-11, deja de estar disponible comoSPI SCK |
| Errores25°C,3V,tabla65 |SE típico/máx offset1/2,5LSB,ganancia2,5/4,5LSB,DNL1/1,5LSB,INL1,5/2,5LSB; tras calibración |
| Dinámica mismas condiciones |SE ENOB mínimo10,4/típico10,5;SNR65/66dB;SINAD64,4/65dB;THD típico−74/máx−73dB. Diferencial ENOB10,8/10,9,SNR67/68,THD−79/−76 |
| Condiciones más amplias tabla67 |VDDA1,65…3,6V: SE ENOB10/10,4;SNR63/65;SINAD62/64;THD−69/−67;offset2/5LSB;gain4,5/7;DNL1,2/1,5;INL3/3,5. Diferencial ENOB10,6/10,7;SNR66/67;offset2/3,5;gain3,5/4;INL2/2,5 |

Máximos/mínimos de diseño de ficha no son resultados medidos en Nucleo. La fuente de VDDA, referencia/masa, conmutación digital, sample-time, inyección y reloj limitan ruido. Ideal de cuantización12bits a3,3V: LSB805,66µV, `q/√12=232,58µVrms`; ruido equivalente porSNR65dB≈656µVrms, diferente y ya incluye cuantización. No sumarlos de nuevo. Diferencial mejora rechazo común solo si se respetan VCM, simetría e impedancias. El cambio de signo digital no crea un ADC bipolar real.

## 5. ADCs y arquitecturas completas

| Conversor | Entrada / banda | Ruido y exactitud documentada | Auxiliares y riesgo |
|---|---|---|---|
| STM32L432 interno |12bit,0–3,3V;48k piloto|ENOB~10,4 típico tabla67, no12efectivos; referencia ligadaVDDA|Vmid preciso/buffer y antialias externo; limitado para sonidos débiles; disponible en placa, costo incrementalADC0 |
| PCM1808PW |24nominal,3Vppsingle-ended alrededor2,5V;8–96k;Rin60ktyp|SNR99typ/95mín **A**; THD+N−93typ/−87máx; errorFSR±3typ/±6%máx; datos48k512fs|5V/3,3V,oscilador,SAI;acoplamientoAC por polarización interna; canal2 debe tratarse segúnTI |
| ADS8681IPW |16bitSAR,1MSPS,±2,56/±5,12V y otros; bipolar respectoGND con5V únicamente|±5,12V:SNR91,5typ/89,5mín;SINAD91,5/89,4;THD−107typ;offset0,2typ/1máxmV;gain0,01typ/0,025%máx excluye referencia|TSSOP16,SPI,referencia4,096V±1mV@25°C7ppm/Kmáx; **LP interno15kHz−3dB y2,5kHz−0,1dB** descarta respuesta plana20k |
| ADS127L01IPBS |24nominal,diferencial±VREF, cada pin0…AVDD;HR64kWB1|3,79µVrms,SNR113,4typ@VREF2,5V,64k;THDHR−113typ4k;offset±0,1mVtyp,gain0,2%typ;INL2,5typ/10máxppm|TQFP32,FDA(p.ej.THS4551VSSOP),referencia externa,clock16,384MHz,mayor trabajo; no es bipolar respectoGND |

Fuentes: [PCM1808](https://www.ti.com/lit/ds/symlink/pcm1808.pdf), [ADS8681](https://www.ti.com/lit/ds/symlink/ads8681.pdf), [ADS127L01](https://www.ti.com/lit/ds/symlink/ads127l01.pdf). No equiparar cifras ponderadas A/400Hz–20k del PCM con ruido20Hz–20k sin ponderación del AFE. No se extrapolan especificaciones garantizadas48k del PCM a96k. ENOB convencional=`(SINAD−1,76)/6,02`: ADS8681≈14,91; STM≈10,34 usando típicos tabla67. Para ADS127 la cifra de “ENOB” calculada por fabricante como log2(span/ruido) no es la misma definición; no publicamos un ENOB porSINAD inexistente. Tabla calculada completa: [adc_comparison.csv](../hardware/revision/results/adc_comparison.csv).

ModeloADC: `code=clip(round(2^N(Vin−Vmin)/span + offset_code))`; incluir ganancia/ref/INL por separado. Cuantización uniformeq²/12 solo si error suficientemente decorrelacionado; senoides pequeñas pueden dar distorsión determinista. La curva de cuantización de figura09 es **sintética y sin ruido/INL**, no rendimiento medido. Ruido porSNR usa amplitud/condiciones de ensayo (ADS−0,25dBFS); ADCnoise ya contiene cuantización.

ADS8681: Zentrada típico1MΩ, pero `Iin=(Vin−2V)/1MΩ`, no resistor puro aGND enDC. Con retorno100k aGND después del capacitor, DC≈2·100k/(1M+100k)=0,1818V, más efecto de tolerancias. AIN_GND debe mantenerse±0,1V; fuente interna única5V no significa protección contra24V IEPE. El modelo de respuesta usa un Bessel de segundo orden ajustado a15kHz, **no sus polos oficiales**, que no están publicados. Pérdida modelada−5,20dB@20k es ilustrativa; incompatibilidad de banda se demuestra ya con la especificación15k. Si profesor acepta banda≤2,5kHz, A2 pasa a ser alternativa simple y viable.

ADS127L01: fMOD=fCLK;16,384MHz/256=64k. WB1pasabanda0,45fs=28,8k, retardo42/fs=656,25µs, establecimiento84/fs. WB2a48k termina0,4fs=19,2k: no asumir20k plano. Carga conmutada~5k requiereFDA/revisión de asentamiento, no un buffer ideal existente. Propuesta diferencialg0,604, resistencias1k/604Ω en red balanceada; a130picoVDIFF2,124V conVREF2,5 yVCM1,65 da cada pin0,588…2,712V. Es solo rango ideal; driver,referencia,estabilidad y alimentaciones OPEN. [THS4551](https://www.ti.com/lit/ds/symlink/ths4551.pdf).

### Matriz de arquitectura y decisión

| Arquitectura | Error de magnitud de modelo20Hz /20k | Fase/tiempo | Ruido/dinámica | Complejidad, costo base y plazo |
|---|---|---|---|---|
|A1 LT3092→C1µ/100k→divisor16k9/10k+OPA2192→LP75k→PCM48→L432|~−0,60 /−0,042dB; carga baja el extremo grave|HPcargado~7,5Hz;ADC362,5µs constante + dispersiónanalógica|No presupuesto completo comparable;ganancia0,3717,máximo128,18dBRMSideal|Menor cambio; referenciaVb exige ajustar DC;IC~15,77USD usandoLTTSOT+OPA+PCM;captura porráfagas1–2semanas sihardware |
|A2 LT3092→AC4,7µ/100k→ADS8681→L432|~0 /−5,20dB **surrogado**; ficha ya descarta20k|Dispersión LP15k; sinVmid externo|ADC~93,6µVrms ensucondición,38,5dBSPLaprox conSprovisional;±5,12V cubre130pico|IC~19,49USD;SPI más simple, pero banda insuficiente;1–2semanas banda reducida |
|A3 LT3092→OPA2192HV→divisor1k69/1k→SK75k→C4,7µ→PCM96→L432|−0,0394 /−0,0220dB, antes de ripple digital±0,05dB|ADC181,25µs constante; dispersión modelada945,6µs@20Hz→3,20µs@20k|AFE3,777µVreferidos sensor=10,62dBSPL, **solo típicos**;ADC y micrófono dominan previsiblemente, comparación debandas pendiente|IC~15,77USD;sinVmidexterno;protección+clock96k riesgos;objetivo integración11/11,PCB18/11condicional |
|A4 LT3092→AC→FDA→ADS127L01→L432|~−0,0007 /−0,0223dB de modelo ideal|ADC656,25µs constante; bajoHP|ADC3,79µVrms/su ganancia=6,275µVreferidossensor≈15,0dBSPL; faltaFDA/reference|SoloLT+ADC28,19USD;FDA/refextra,PCB más densa;2–3semanas alto riesgo para25/11 |

Costos **solo IC nombrados, no BOM total**, páginas de distribuidor consultadas4/11local–5/11UTC, sin impuestos/envío. Stock publicado: PCM1808PW97/$2,37;OPA2192ID7835/$7,17;ADS8681IPW8/$13,26;ADS127L01IPBS406/$21,96. [Registro con enlaces](../hardware/revision/procurement.csv). LT3092EST SOT2230stock/$6,61; alternativa [LT3092ETS8#TRMPBF TSOT23-8](https://www.digikey.com/en/products/detail/analog-devices-inc/LT3092ETS8-TRMPBF/2136072):12856stock/$6,23. Confirmar compra y entrega Colombia antes de confiar en el plazo. No hay compra realizada ni disponibilidad física confirmada.

A3 es recomendación condicionada por simplicidad frenteA4 y banda frenteA2; **no porque una simulación lineal pruebe precisión acústica**. A1 se conserva como histórico de comparación. El filtro analógico de75k no evita solo elalias; se combina con sobremuestreo/filtro interno del ADC. Falta definir nivel máximo fuera de banda, ruido sobre Nyquist y rechazo efectivo de toda la cadena; no asignar65dB a cualquier interferencia arbitraria.

## 6. Acoplamiento, servo y filtros: ecuaciones y simulación

Para fuente vs con Rs, capacitorC enserie y cargaRL hacia referenciaVr de baja impedancia AC:

`H(s)=s C RL/[1+s C(Rs+RL)]`, `k∞=RL/(Rs+RL)`, `fc=1/[2πC(Rs+RL)]`.

`|H|=k∞·f/√(f²+fc²)`, `φ=atan(fc/f)`, `τg=(1/ωc)/(1+(f/fc)²)`. Escalón: `k∞ΔV exp(−t/[C(Rs+RL)])`. Tiempo a fracciónε: `t=−τ lnε` (1%4,605τ). Carga compleja: reemplazarRLporZL(s); fugasRleak en paraleloC: `Zc=1/(sC+1/Rleak)` y `H=ZL/(Rs+Zc+ZL)`, ya no cero exacto enDC.

A1:RL=100k||(16k9+10k)=21,1978k,Rs50,C1µ→fc~7,49Hz. No usar1,59Hz calculados sin carga. A3:C4,7µ,RL60ktyp,Rs≈1Ω(modeloideal)→fc0,5644Hz,τ0,282s y1%1,30s. PCM añadeHPinterno0,91Hz@48/1,82Hz@96; aquí **aproximado de primer orden**, no coeficientes oficiales. A3@20Hz pérdidaHPexterno~0,0036dB yHPinterno~0,0358dB. El ruido/fase interna del ADC no desaparece usando ADC sinVmidexterno.

Con C±20%, fc0,470…0,706Hz (RintADC también desconocida): pérdida externa20Hz~0,0024…0,0054dB; fase~1,35…2,02°. Fuga1/10/100nA/1µA sobre60k implica60µV/0,6/6/60mV de desplazamiento. Absorción dieléctrica no se obtiene del valorC: escenarios de prueba0,1%/1% de memoria12,5V→12,5/125mV antes de carga/ganancia, no especificaciones de un capacitor real. Falta modelo de ramas RC obtenido de ficha/medición. Preferir película no polar; MPN4,7µ≥50V **OPEN**. PelículaSMD WIMA SMDTD04470YA00MS00 publicada a pedidoMOQ2000 no es disponibilidad útil; X7R4,7µ50V puede ser microfónico y variar conDC. Una película radial sobre PCB convencional es opción a aprobar, sin volver a placa perforada. Confirmar fuga,DA,tolerancia y volumen antes del layout.

Eliminación activa: un restador ideal `Vo=g(VIEPE-VDCref)` conserva banda si la referencia es exacta, pero añade `-g·δVref`, offset, ruido y error de relaciones resistivas. Ejemplo con 20 kΩ/7,5 kΩ por brazo, g=0,375 y resistores independientes de ±0,1%: el barrido de 16 esquinas deja hasta 13,64 mV de residuo por 12,5 V de modo común. No prometer rechazo perfecto. Un servo ideal `H=s/(s+ωservo)` también introduce fase y establecimiento: fc=0,1 Hz, τ=1,59 s y 7,33 s hasta 1%. Su ruido y deriva requieren componentes reales. No se recomienda añadirlo ahora.

Un pasabandas no elimina automáticamente la fase. Figura 03 compara HP pasivo, servo ideal, HP 1,6 Hz + LP Butterworth de orden 4 a 30 kHz, HP + LP Bessel de orden 4 a 30 kHz y Butterworth pasabanda de orden total 4 (prototipo de orden 2). Se iguala el corte LP a -3 dB, sin fingir que todos tienen el mismo orden total. Butterworth prioriza magnitud plana; Bessel aproxima retardo constante a bajas frecuencias, con otra atenuación. Ninguno conserva exactamente magnitud y fase. El ajuste Bessel del ADS8681 es solo un modelo equivalente, no su circuito oficial.

En A3, Sallen-Key unidad: Rt=1690 Ω, Rb=1000 Ω, Rth=628,2528 Ω. R1 física=1370 Ω; Ra=R1+Rth=1998,2528 Ω; R2=2000 Ω. C1=1500 pF entre nodo intermedio y salida; C2=750 pF desde entrada positiva a GND. `D=1+s C2(Ra+R2)+s²RaR2C1C2`, `Hlp=1/D`. Resultan `f0=75059,15 Hz`, `Q=0,707107`. Resistores 0,1% y capacitores C0G 1% propuestos; 64 esquinas se calculan en CSV y figura 10. Opamp finito, protecciones y carga modificarán esta respuesta: no está validada por SPICE o laboratorio.

Figuras 01–10 en [hardware/revision/figures](../hardware/revision/figures). Los CSV evalúan 20/100/1k/4k/10k/20k Hz. Impulso y escalón son de redes analógicas; la cadena completa solo incorpora HP aproximado y retardo documentado del ADC, sin inventar sus coeficientes FIR. En figura 02 se retira el retardo constante para mostrar dispersión; la fase principal en CSV está módulo 360°. Un retardo constante desplaza la onda sin deformarla; retardo de grupo variable dispersa sus componentes.

Por Parseval, para señal estacionaria, sistema LTI estable sin clipping y ventana suficientemente larga, la fase sola no cambia energía RMS de banda completa. Sí cambia forma de onda, picos y RMS en ventanas transitorias o finitas. La magnitud altera RMS/SPL según el espectro. Figura 05 usa multitono sintético de seis frecuencias con períodos enteros. Normalizando por ganancia, A3 cambia RMS en -0,0108 dB; tras quitar solo el retardo constante queda una diferencia temporal de unos 38,2 mV RMS para entrada de 207,8 mV RMS. Esa diferencia por dispersión no es ruido añadido.
## 7. Amplificación y operacionales

Se conservan las tres alternativas Codex como referencia:

- **A:** divisor 16,9 kΩ/10 kΩ + buffer. `a=Rb/(Rt+Rb+Zs)`; `Vo=a Vu+(1-a)Vb`. Carga 26,9 kΩ, ganancia nominal 0,371747.
- **B:** no inversor Rf=9,09 kΩ, Rg=1 kΩ. `N=1+Rf/Rg=10,09`; `Vo=N Vu+(1-N)Vc`. Entrada de alta impedancia, pero rango pequeño.
- **C:** divisor seguido de B. `Vo=N a Vu+N(1-a)Vb+(1-N)Vc`. Bajo 0,371747 / alto 3,75093.

Con margen ADC de 1,5 V pico, máximos senoidales ideales A/B/C: 128,18 / 99,51 / 108,11 dB SPL RMS. Ganancia 11 alcanza solo 98,76 dB RMS. No seleccionar ganancia para llenar escala a 94 dB si se exige registrar 120 dB RMS. Los límites dependen también de sensibilidad real, centro DC y alimentación. Derivaciones del incremento previo: [analog-front-end.md](analog-front-end.md).

En A3 se propone rango fijo atenuado primero. Un rango opcional de ganancia 1 mediante bypass del divisor elevaría sensibilidad para sonidos débiles, con máximo 119,59 dB RMS. Añadir unos 628 Ω de Thevenin para conservar el filtro. El bypass cambia el DC antes del capacitor de 4,65 V a 12,5 V: detener captura, proteger y esperar establecimiento. Un PGA no está justificado hasta medir si el ruido del ADC limita frente al micrófono.

### Red real de Voxter

Después de C=1 µF y retorno de 100 kΩ a Vmid: resistencia 4,7 kΩ hacia la entrada positiva MCP6002. Rf=10 kΩ en paralelo con Cf=470 pF, Rg=1 kΩ hacia Vmid. Salida mediante 1 kΩ al ADC, con 4,7 nF a GND. Vmid procede del divisor 10 kΩ/10 kΩ a 3,3 V, capacitor de 10 µF y segundo MCP6002 como buffer. Los diodos 1N4148 **no generan Vmid**.

Idealmente, `NG(s)=1+10/(1+sτ)=(11+sτ)/(1+sτ)`, con τ=4,7 µs. Polo 33,863 kHz y cero 372,49 kHz. `Vo=NG V+ +(1-NG)Vmid`; la salida añade `Hrc=1/(1+s·4,7 µs)` si la carga ADC es de alta impedancia. No es un integrador: NG tiende a 1. Con impedancia ADC finita debe recalcularse el divisor de salida.

Aproximando el opamp por `A=ωt/s`, ωt=2π·1 MHz:

`Hfb=ωt(11+sτ)/[τs²+(11+ωtτ)s+ωt]`.

Incluyendo acoplamiento y RC de salida, ganancias a 20/100/1k/4k/10k/20k Hz: 10,9599 / 10,9930 / 10,9810 / 10,7835 / 9,8006 / 7,4173. A 20 kHz: pérdida ideal -2,591 dB; con GBW aproximado -3,423 dB y fase -66,85°. Figura 06 y [voxter_response.csv](../hardware/revision/results/voxter_response.csv). Es un modelo dominante de pequeña señal, **no SPICE ni predicción de THD** del MCP6002.

| Operacional | Parámetros de ficha | Consecuencia |
|---|---|---|
| MCP6002, SOIC8 | 1,8–6 V; GBW 1 MHz; SR 0,6 V/µs; ruido ~28 nV/√Hz a 1 kHz; Ib ~1 pA; offset máximo ±4,5 mV; deriva típica ~2 µV/K; ~100 µA/canal | Incompatible con 24 V. A 3,3 V y ganancia 11 presenta error de banda y offset significativo. |
| OPA2192ID, SOIC8 | 4,5–36 V; GBW 10 MHz; SR 20 V/µs; ruido típico 5,5 nV/√Hz a 1 kHz y 10,5 a 100 Hz; Ib 5 pA típico/20 pA máximo a 25°C; offset ±5 µV típico/±25 máximo; deriva 0,2 típica/0,5 máxima µV/K; ~1 mA/canal | RRIO, estable en unidad, apto para los dos buffers a 24 V. Selección provisional. |
| OPA1652ID, SOIC8 | 4,5–36 V; GBW 18 MHz; SR 10 V/µs; ruido típico 4,5 nV/√Hz; offset ~0,5 mV típico/2 máximo; Ib ~10 pA | Algo menos de ruido blanco, mayor offset y entrada no rail-to-rail; revisar modo común. |
| OPA1656ID, SOIC8 | 4,5–36 V; GBW 53 MHz; SR 24 V/µs; ruido típico 2,9 nV/√Hz; offset ~0,5 mV típico/3 máximo; Ib ~10 pA; ~3,9 mA/canal | Mayor consumo y exigencia de layout; su ventaja puede quedar oculta por ruido de micrófono y ADC. |

Fuentes oficiales: [MCP6002](https://www.microchip.com/en-us/product/MCP6002), [OPA192](https://www.ti.com/lit/ds/symlink/opa192.pdf), [OPA1652](https://www.ti.com/lit/ds/symlink/opa1652.pdf), [OPA1656](https://www.ti.com/lit/ds/symlink/opa1656.pdf). Los valores típicos no son límites. La THD de cada ficha corresponde a carga, frecuencia y amplitud propias; no es una garantía de nuestra cadena.

A3 necesita SR mínimo 0,164 V/µs en la salida de 1,307 V pico a 20 kHz y 0,442 V/µs en el buffer del sensor a 3,516 V pico. OPA2192 ofrece margen típico, sin demostrar por ello THD. Entrada del primer buffer: 8,98…16,02 V; segundo: aproximadamente 3,34…5,95 V. Ambos opamps usan **la misma alimentación de 24 V**. El mínimo funcional de la familia es 4,5 V, pero esta topología necesita superar el máximo de 16,02 V del sensor más margen de entrada/salida; no funciona sustituyendo 24 V por 5 V.

La carga del divisor es 2,69 kΩ y demanda hasta 5,95 mA a 16,02 V del buffer; comprobar excursión y THD bajo esa carga. La simulación numérica no validó estabilidad de la realimentación Sallen-Key ni carga capacitiva. No se dispone de margen de fase aceptado para esta cadena. La impedancia de salida cerrada no se supone nula: el modelo LTI usa 1 Ω como parámetro de prueba, a verificar.

Offset de los dos opamps a 25°C: cota aproximada `(1+a)·25 µV=34,3 µV` antes del capacitor. Deriva adicional con 50 K: otros 34,3 µV usando 0,5 µV/K máximo. Son errores DC, no ruido RMS; el capacitor elimina DC estacionario, no transitorios. Ib=20 pA sobre 50 Ω produce 1 nV y sobre unos 4 kΩ, 80 nV; el límite cambia con temperatura.

Divisor con resistencias independientes ±0,1%: `δg/g≈(1-a)(δRb-δRt)` → ±0,12565%, unos ±0,0109 dB. TCR independientes ±25 ppm/K con ΔT=50 K añaden ±0,1571%; no asumir correlación perfecta. El peor caso sistemático se suma como cota, no en RSS con ruido.

Potencia al pico de 16,016 V: Rt≈59,9 mW, Rb≈35,5 mW. Con sensor abierto a 24 V: Rt≈134,5 mW y Rb≈79,6 mW. Proponer **Rt y Rb de al menos 0,25 W**, revisar derating y carga del buffer. OPA dual: ~48 mW de reposo a 24 V; a bias12,5 V el buffer entrega4,65 mA y disipa otros~53,4 mW, total~101,4 mW antes de cargas dinámicas. Evaluar temperatura con θJA y cobre del montaje real, sin trasladar un valor de otra placa. Usar C0G de al menos 50 V para el filtro y verificar tensiones en fallos. La protección y su efecto sobre ruido/distorsión siguen OPEN.

Los diodos de Voxter están en la entrada del opamp: superior ánodo en señal/cátodo a 3,3 V e inferior ánodo a GND/cátodo en señal. Limitan cerca de -Vf y 3,3+Vf, no exactamente 0/3,3 V. Pueden realimentar un riel apagado y **no protegen automáticamente el ADC conectado a la salida**. Una resistencia de 1 kΩ limita corriente, no voltaje. En A3 debe ensayarse protección directa del pin ADC, secuenciación de alimentación, descarga y retención/mute: el opamp a 24 V aumenta la exposición a fallos.

## 8. Referencias: susceptibilidad y simulación corregida

Para Voxter, `Zs=50+1/(s Cac)` y:

`Href=NG·Zs/(100k+Zs)+(1-NG)`.

En banda se aproxima a -10: la referencia entra por la realimentación mientras el sensor fija la entrada positiva. Una perturbación independiente de Vmid de **1 mV pico a 100 Hz** produce ~7,07 mV RMS en salida antes del RC, equivalente a 55,23 dB SPL referidos al sensor. Es un ensayo sintético, no ruido real medido. En Codex A, `Href=1-a≈0,628`; con rango alto y Vb=Vc común, `Href=1-N a≈-2,75`. Si son referencias distintas, sus coeficientes son N(1-a) y 1-N: no se cancelan por su nombre.

Un divisor 10 kΩ/10 kΩ tiene Rth=5 kΩ, ruido Johnson 9,10 nV/√Hz a 300 K sin filtrado y desajuste de ±1,65 mV con resistores independientes de 0,1% a 3,3 V. Un buffer reduce impedancia pero añade ruido, offset, deriva y PSRR finito. El capacitor de 10 µF introduce τ=50 ms, retrasando el seguimiento de VDDA.

Una [REF5025](https://www.ti.com/lit/ds/symlink/ref50.pdf), grado I, ofrece 0,05% y 3 ppm/K máximos; grado AI 0,1% y 8 ppm/K. Confirmar sufijo, corriente, estabilidad y carga antes de escogerla. El ruido especificado en µV pico a pico a 0,1–10 Hz no se transforma en RMS sin un modelo estadístico. En el L432KC no hay un pin VREF+ separado de VDDA: alimentar VDDA con una referencia exige satisfacer su consumo y desacoplo.

La ratiometría cancela el término aditivo **si la topología realmente cumple** `Vin=VDDA/2+g x`: entonces `code≈1/2+g x/VDDA`, y permanece modulación multiplicativa de escala. El caso ideal de seguimiento se grafica separado y no representa Voxter. En Voxter, un rizado compartido de VDDA de 10 mV pico induce Vmid de 5 mV pico con transferencia cercana a -10: aparece un término aditivo aproximado de -55 mV pico después de referirlo al ADC, además de la modulación de amplitud.

Figura 07 y [reference_perturbations.csv](../hardware/revision/results/reference_perturbations.csv) aplican Href a Vmid **antes** de dividir por VDDA, conservando aparte el centro DC. Se comparan referencia independiente, divisor compartido, divisor filtrado y una perturbación de 10 µV pico. Esta última es un nivel de ensayo, no ruido garantizado de REF5025. Para el ejemplo de seno a 94 dB, ganancia 11 y rizado de 100 Hz, el caso ideal de seguimiento deja 1,314 mV RMS de modulación; los casos Voxter tienen además error aditivo y deben leerse en la tabla regenerada.

Un ADC diferencial rechaza ruido común solo hasta su CMRR y dentro de su modo común. Un ADC bipolar elimina Vmid externa, pero conserva referencia interna, offset y corrientes de entrada. A3 evita el circuito externo Vmid, **no** elimina ruido de alimentación ni errores del PCM: su rango nominal es 0,6·VCC. Un error de escala del 1% equivale a unos 0,086 dB. No considerar diodos como referencias de precisión.

## 9. Presupuesto de ruido y errores

Banda del AFE: 20–20 kHz sin ponderación, 300 K. `eR=√(4kTR)`; `eno²=∫Σ|Hi|²Si df`. Se suman en potencia las fuentes aleatorias independientes. Los errores sistemáticos se mantienen separados. La PSD del OPA se aproxima mediante `en²=a+b/f`, ajustada a puntos típicos de 100 Hz y 1 kHz; no es una garantía espectral.

Para el Sallen-Key ideal: `Hsignal=1/D`, `Hopamp=1+s Ra C1/D`, `HRa=1/D`, `HR2=(1+s Ra C1)/D`. Incluye Ra=1370+628,253 Ω. Ruido de corriente de 1,5 fA/√Hz se usa como estimación conservadora sobre las impedancias declaradas. Contribuciones por separado: [noise_budget_afe.csv](../hardware/revision/results/noise_budget_afe.csv), figura 08.

| Contribución | Cifra o ecuación | Estado / tratamiento |
|---|---|---|
| Micrófono | Catálogo 32 dB SPL, 5 Hz–20 kHz; con S provisional serían 44,27 µV RMS | Otra banda; no sumarlo como ruido garantizado 20–20 kHz. 27 dBA no es comparable directamente. |
| Fuente IEPE | Histórico 0,464 µV RMS en 50 Ω, equivalente -7,59 dB SPL | Modelo anterior; nuevos valores de fuente OPEN. |
| Resistencias y OPA A3 | Salida 1,404 µV RMS; referido al sensor 3,777 µV RMS =67,93 µPa RMS ≈10,62 dB SPL | Modelo típico de AFE, excluye ADC, micrófono y fuente. |
| PCM1808 | SNR 99 dBA →11,90 µV RMS a entrada ADC; 32,01 µV referidos al sensor | Equivalente 29,18 dB SPL, con ponderación/banda de ficha distintas; no total sin ponderación. |
| ADS8681 | ~93,60 µV RMS a partir de SNR y estímulo -0,25 dBFS | Equivalente ~38,50 dB SPL; ancho de banda propio distinto. |
| ADS127L01 | 3,79 µV RMS a 64 kSPS WB1 | 6,275 µV referidos al sensor ≈15,03 dB SPL; falta driver y referencia, banda más amplia. |
| Referencias | Figura 07: perturbaciones deterministas conocidas | No convertirlas en ruido aleatorio real. Faltan PSD, PSRR y medidas de VCC. |
| Ganancia AFE | ±0,126% inicial, más ±0,157% de envolvente térmica de 50 K | Cota sistemática conjunta ~0,0246 dB; calibrable. |
| Offset y deriva | ~34,3 µV DC +34,3 µV para 50 K antes del Cac | No expresar como SPL aleatorio; afecta margen y arranque. |
| Ganancia ADC / referencia / INL | PCM hasta ±6% FSR: +0,506/-0,537 dB antes de calibrar | La calibración a una frecuencia no corrige toda la respuesta espectral. |
| Respuesta de frecuencia | A3 -0,0394 dB a 20 Hz; -0,0220 dB a 20 kHz en el modelo | Añadir por separado ripple digital de ficha ±0,05 dB y respuesta acústica del micrófono. |
| THD | Valores de ficha bajo sus propias condiciones | Cadena OPEN. Clipping ideal y límite SR no son THD real. |
| Cuantización ideal RMS | STM 232,58 µV; PCM 0,0516 µV; ADS8681 45,11 µV; ADS127 0,0860 µV | Diagnóstico; no sumar otra vez al ruido total ADC. |
| Tiempo de muestreo | `SNRj=-20log10(2π f σt)` | A 20 kHz: 1 ns→78,02 dB; 100 ps→98,02; 10 ps→118,02. Jitter real OPEN. |

El error fijo de frecuencia del HSI/oscilador desplaza fs y el eje FFT; no equivale a jitter aleatorio. El ruido total requiere condiciones y bandas comunes. No hay una cifra defendible de error total del sonómetro todavía.

Medir 30 dB SPL sin ponderación con un micrófono cuyo catálogo indica 32 dB de ruido es problemático. Ganancia o PGA no recuperan información perdida en el sensor. Para señal y ruido independientes, el sesgo de nivel sin corrección es `10log10[1+(en/es)²]`; se necesita ruido medido en la misma banda antes de fijar un límite inferior útil.

## 10. Simulaciones, reproducción y límites

Se ejecutaron modelos de leyes de circuito y redes LTI con Python 3.11.7, NumPy 2.3.4, SciPy 1.16.3 y Matplotlib 3.10.7. Diez figuras PNG/SVG y CSV/JSON incluyen frecuencia, amplitud, tolerancias, ruido equivalente, referencias, impulso, escalón y multitono. Versiones y hashes en summary.json.

`chain.cir` modela A3 con fuente eléctrica ideal, Rs parametrizable y **macromodelo oficial TI OPAx192** separado. Se intentó ngspice 46: el cálculo del punto de operación falla por matriz singular en nodos internos de clamps. Nodeset y regularización numérica de 1 TΩ no resolvieron el problema. Se guardan log y manifiesto `FAILED_NO_SPICE_RESULT_ACCEPTED`. No se aceptan curvas AC, transitorios, saturación o THD SPICE de esta cadena. No se alteró el modelo TI para forzar resultados.

LTspice no está instalado y el modelo LT3092 anterior está cifrado para ese simulador. No se volvió a simular la fuente. No se recuperó un modelo MCP6002 oficial ejecutable ni modelos completos de ADC/micrófono. No se inventaron sustitutos con aspecto de modelos de fabricante.

Los transitorios de figura 04 son predicciones lineales sin clamps, que pierden validez cuando se superan los rieles. El panel de riesgo con centro 2,5 V y límite PCM solo corresponde a A1/A3. Sirve para detectar necesidad de protección, no para predecir el máximo físico de un pin. Los escenarios de sensor abierto, ADC apagado y secuenciación quedan como pruebas necesarias, no simulaciones de protección aceptadas. Temperatura se analiza mediante envolventes de especificación/TCR; no es simulación electrotérmica. Distorsión solo se calcula para cuantización/clipping ideales; THD analógica completa sigue OPEN.

Desde la raíz, PowerShell:

```powershell
.venv/Scripts/python.exe -m pip install -r hardware/revision/requirements.txt
.venv/Scripts/python.exe hardware/revision/simulate.py
.venv/Scripts/python.exe -m unittest discover -s tests/revision -v
# Descargar modelo con hardware/afe/fetch_model.py y revisar condiciones de uso.
.venv/Scripts/python.exe hardware/revision/spice.py --dll 'C:/Program Files/KiCad/10.0/bin/ngspice.dll' --case ac
# Actualmente devuelve error explícito; NO hay resultado SPICE aceptado.
```

Modelo TI Final 1.7 SHA256: `1c438e45e978ffaf5aa13c7e2bb18ad5da70259775522ec41f47633a5db99033`. [Descarga oficial SBOM862](https://www.ti.com/lit/zip/SBOM862). No se versiona el archivo externo. El netlist puede abrirse en otro simulador ajustando el path, sin asumir que por ello compilará o convergerá.

## 11. Firmware y cableado: reutilizar sin reescribir

El firmware existente se conserva: STM32CubeL4 1.18.1, GCC ARM 12.3.1, ADC interno a 48 kSPS nominales mediante TIM6 y DMA circular. Captura 8192 muestras, detiene adquisición y transfiere bloques binarios por USART2/ST-LINK VCP a 115200. **Adquirir a 48 kSPS no implica transmitir continuamente a esa tasa.** No se cambian fuentes C en esta revisión. La compilación anterior está registrada en [firmware/README.md](../firmware/README.md); no es prueba física. El programa Python existente detecta secuencias y procesa muestras reales cuando se conecte hardware.

| Ruta | Pines NUCLEO-L432KC | Configuración y conflictos |
|---|---|---|
| ADC interno | PA0/A0 CN4-12 | IN5, 0…VDDA, centro 1,65 V. PA1/A1 CN4-11 sería IN6 negativo del par diferencial. |
| ST-LINK VCP | PA2 USART2_TX AF7, PA15 RX AF3 | Mantener puentes de placa; 115200 para transferencia posterior. |
| PCM maestro / SAI1_A RX esclavo | PA8 D9 CN3-12 BCK; PA9 D1 CN3-1 FS; PA10 D0 CN3-2 SD; AF13 | D0/D1 no pueden ser otra UART simultáneamente. MD1/MD0=11 para 256fs; FMT=0 I²S. |
| Reloj PCM | Oscilador externo 24,576 MHz→SCKI para 96 kSPS; 12,288 MHz para 48 | BCK 6,144/3,072 MHz; LRCK 96/48 kHz. PCM maestro evita usar PA3 MCLK A2 CN4-10. |
| USB nativo | PA11 D10 CN3-13 DM; PA12 D2 CN3-5 DP | Necesita conector independiente, VBUS/ESD y reloj 48 MHz. No es el conector ST-LINK. |
| ADC externo SPI1 | PA1 A1 CN4-11 SCK AF5; PB4 D12 CN3-15 MISO AF5; PA7 A6 CN4-6 MOSI AF5; PA4 A3 CN4-9 CS GPIO | Sin conflicto con VCP/USB/LED. PA1 deja de estar disponible para ADC diferencial. |
| ADS127 DRDY | PB0 D3 CN3-6 EXTI | No confundir DRDY de ADS127 con protocolo de disparo ADS8681. |

Verificación: [UM1956 Nucleo32](https://www.st.com/resource/en/user_manual/um1956-stm32-nucleo32-boards-mb1180-stmicroelectronics.pdf), tablas de funciones alternas DS11451 y [esquemático MB1180](https://www.st.com/en/evaluation-tools/nucleo-l432kc.html#cad-resources). Confirmar revisión real de placa y puentes antes de cablear.

Cambios necesarios para A3: habilitar SAI RX + DMA con reloj de kernel compatible con BCK de 6,144 MHz y sus tiempos de ficha; usar reloj externo PCM, sin fingir que PLL actual produce exactamente 24,576 MHz. Verificar I²S, retraso de un bit, signo de 24 bits en contenedores de 32, orden L/R y descarte correcto del canal no acústico. Estos cambios **no están implementados ni validados**.

Para ADS8681 implementar sus comandos, CS/conversión y latencias según ficha; para ADS127 añadir DRDY, configuración WB1/OSR256, reloj 16,384 MHz y CRC si se habilita. No usar bit-banging de audio.

SRAM disponible: 64 kB. El buffer actual ADC de 8192×2 ocupa 16 kB. Un bloque PCM estéreo de 1024 frames×8 bytes ocupa 8 kB. Usar modos excluyentes/union y revisar linker map antes de reservar más buffers. Registrar ID de ADC, fs, ganancia, alimentación, calibración, muestras, pérdidas, secuencias y CRC de bloque.

PCM96 mono en 32 bits exige 384 kB/s; DMA estéreo recibe 768 kB/s. VCP 115200 ofrece como máximo 11,52 kB/s antes de protocolo: solo ráfagas con transferencia posterior. USB Full-Speed puede ser ruta posterior, pero necesita implementación, conexión independiente y medida de caudal con contadores. No declarar continuidad sin esa evidencia.

### Criterios de PCB de dos capas

Proponer plano de GND continuo, retornos de USB/reloj lejos de entrada IEPE, BNC y desacoplos analógicos junto a sus pines. No dividir el plano bajo las señales de reloj ni asumir que una estrella larga reduce impedancia a toda frecuencia. Mantener nodos de alta impedancia cortos, limpiar residuos y separar el riel24V del pinADC; revisar distancias y protecciones con estados de alimentación parciales. Ejemplo de sensibilidad de layout:1mA de corriente digital sobre10mΩ de retorno común produce10µV, mayor que el ruido de salida AFE calculado1,404µVrms; el espectro y la transferencia determinan cuánto se mide realmente. Esto justifica medir el montaje antes de prometer ruido por tener dos capas.

La MCU cerrada STM32L432KC utiliza UFQFPN32. Conservar NUCLEO-L432KC sobre una PCB portadora permite evitar ensamblar manualmente ese encapsulado durante el prototipo; confirmar con el profesor si esa integración cumple su entrega final. Si exige MCU discreta, presupuestar stencil/reflow/inspección para UFQFPN32 en vez de cambiar silenciosamente de MCU. Fuente TSOT23-8, operacional SOIC8 y ADC TSSOP14 siguen ensamblables convencionalmente. No se libera layout con el bloque de protección enOPEN ni con MPN de capacitor/oscilador sin cerrar.
## 12. Pruebas, calendario y preguntas al profesor

La primera prueba física debe ser **la fuente IEPE con cargas, sin micrófono ni ADC**. Fuente 24 V limitada en corriente, cargas de 4,46 kΩ y 5,72 kΩ de al menos 0,25 W, para aproximadamente 12,5/16,0 V a 2,8 mA. Medir corriente, tensión, temperatura, ruido, encendido y desconexión con osciloscopio. Para otras corrientes recalcular R=Vload/I: a4 mA usar3,125/4,0 kΩ para los mismos puntos;5,72 kΩ a4 mA aproxima dropout y no debe exigirse regulación. Repetir 2,4/2,8/4 mA, sin llamar compatible a una corriente hasta identificar el sensor y verificar régimen/compliance.

Después, generador real con offset 12,5 V, Rs=50 Ω y seno 1 kHz/55,73 mV RMS: equivale eléctricamente a 94 dB con sensibilidad provisional, **no es calibración acústica**. Sustituir el ADC por su carga de prueba de 60 kΩ a 2,5 V. Medir ganancia, DC, respuesta en seis frecuencias, THD y amplitud hasta 3,516 V pico. Objetivo provisional de ganancia eléctrica a temperatura ambiente: nominal ±0,3%, antes de calibrar.

Ensayar protección directa del pin antes de conectar ADC: alimentación de 24 V antes/después de 5 V, sensor abierto, ADC apagado, conmutación y recuperación del capacitor. Registrar máximos de tensión y corriente inyectada frente a límites de ficha. Si no se cumplen, no conectar ADC ni liberar PCB.

ADC interno: seno real de 1 kHz, 100 mV pico centrado en 1,65 V a PA0. Capturar 8192 muestras y verificar contador, secuencia/CRC y fs medida. FFT: desviación compatible con resolución fs/N y reloj. RMS usando VDDA medida. PCM: medir SCKI/BCK/LRCK, alineación y signo antes de probar analógico; empezar por ráfagas sin pérdidas. Ruido, THD, rechazo fuera de banda y calibración acústica se ensayan después de protección validada.

Formato mínimo de registro y criterios: [tests/revision/README.md](../tests/revision/README.md). Conservar datos crudos, condiciones, instrumentos/certificados y resultado real. Ninguna prueba física está marcada PASS.

| Fecha | Puerta de avance |
|---|---|
| 5/11 | Presentar propuesta, datos calculados y riesgos. |
| 6–10/11 | Identificar sensores, confirmar compras, ensayar fuente/protección/ADC por separado. |
| 11/11 | Integración eléctrica y calibración inicial si funcionan los bloques. |
| 12–17/11 | Medir respuesta, ruido, alias y corregir esquema. |
| 18/11 | Liberar PCB solo con protección, datos y footprints confirmados. |
| 21–25/11 | Ensamblar, validar y entregar con estado real de cada prueba. |

Si la fabricación no llega, informar el diseño y prototipo parcial reales; placa perforada no satisface la implementación final exigida.

Preguntas al profesor: ¿acepta banda 20–20 kHz y error eléctrico calibrado ≤0,2 dB? ¿Qué error de fase/retardo y ventana RMS exige? ¿El objetivo mínimo de 30 dB es compatible con el ruido publicado del RG50? ¿Consideraría banda ≤2,5 kHz con ADS8681 si reduce el riesgo? ¿Acepta capacitor de película radial sobre PCB si no se consigue SMD adecuado? ¿Presupuesto y plazo de PCB? El segundo dispositivo requiere identificación física antes de aprobar su excitación.
