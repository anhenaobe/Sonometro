# Selección preliminar de fuente de corriente IEPE

**Fecha de trabajo: 27/10/2026. Estado: provisional.**

## Objetivo
Alimentar un micrófono IEPE ROGA RG-50 de un solo canal. La unidad del proyecto presenta datos aún por verificar: sensibilidad indicada 55,6 mV/Pa, bias ~12,5 V, corriente indicada 2,8 mA. Catálogo del sensor: corriente 2-20 mA y tensión 18-30 V. Prototipo con suministro de laboratorio de 24 V.

## Componentes candidatos

| Ref. | Componente | Valor / modelo | Motivo |
| --- | --- | --- | --- |
| U1 | Fuente de corriente ajustable | LT3092EST#PBF (SOT-223) | Pocas piezas; modelo LTspice de ADI; referencia de uso IEPE |
| RSET | Resistencia | 20 kΩ, ±1 % o mejor | 10 µA × 20 kΩ = 200 mV nominales |
| ROUT | Resistencia | 71,5 Ω, ±1 % o mejor | Iout nominal ~2,807 mA |
| PS1 | Fuente DC | 24 V ajustables con límite de corriente | Ensayo inicial y compliance, no fuente final |
| Micrófono | ROGA RG-50 | Externo, pendiente de certificar | No conectar hasta T1/T2 |
| Opcional futuro | RSET/ROUT/CSET | 120 kΩ / 430 Ω / 10 µF | Explorar alternativa de ruido menor, sin validar |
| Alternativa | OPA192 + BSS84 + Rsense 100 Ω | Solo candidata | Mayor flexibilidad, más complejidad y referencia ideal aún no implementada |

La red filtrada del archivo exploratorio 03 usa CSET=100 nF, RCOMP=1 kΩ y CCOMP=10 nF. No se debe confundir con la propuesta de 10 µF derivada del estudio de ADI ni copiar directamente a una PCB.

## Ecuación de programación
Iout = 10 µA × RSET / ROUT + 10 µA. Con RSET=20 kΩ y ROUT=71,5 Ω: Iout calculada = 2,807 mA, no especificación de tolerancia. Temperatura, fugas y ruido quedan por verificar.

## Resultados simulados realmente reportados
| Ensayo | Condiciones | Resultado | Interpretación |
| --- | --- | --- | --- |
| DC LT3092 | 24 V, 4,46 kΩ, LTspice 26.1.1, temperatura nominal 27 °C | I=2,80754 mA; V=12,5216 V | Error nominal respecto a 2,8 mA: +0,269 %, en un punto de carga |
| Transitorio LT3092 | 1 kHz; bias 12,5 V; 50 mV pico; 50 Ω serie; cable 1 nF | I(RMIC)media=2,807533 mA, máx=2,807832 mA, mín=2,807234 mA | Fluctuación de I(RMIC) ~0,598 µApp. Incluye corriente capacitiva del cable |
| Transitorio LT3092 | Igual al anterior | V(IEPE) 12,590377 a 12,690376 V | ~100 mVpp, con emulador idealizado de micrófono |
| Barrido DC | Hasta 9 kΩ | I=2,51270 mA, V=22,6143 V a 9 kΩ | Pérdida de regulación por margen de tensión insuficiente |

Los resultados son transcripciones de registros e imágenes aportados por el usuario. No se ha hecho simulación propia independiente del asistente en LTspice ni test de banco.

## Conclusión técnica
**Priorizar LT3092 básico** para montaje experimental con carga ficticia. La comparación con OPA192+BSS84 queda **OPEN**, al igual que los ensayos de ruido, impedancia de salida AC, temperatura, arranque, transitorios y estabilidad con el cable real. El archivo 03 presenta una topología experimental, no una mejora probada.

**Nunca** usar el bias IEPE directamente sobre la entrada ADC: antes deben estar diseñados/verificados acoplamiento, retorno, limitación y protección.

## Referencias
- [LT3092 - hoja de datos](https://www.analog.com/media/en/technical-documentation/data-sheets/lt3092.pdf).
- [Analog Devices CN0540](https://www.analog.com/en/resources/reference-designs/circuits-from-the-lab/cn0540.html).
- [ROGA RG-50](https://www.roga-instruments.com/downloads/PDF/RG-50-EN.pdf).
- [Decisiones del proyecto](decisions.md).
