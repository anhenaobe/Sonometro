# Pruebas de banco

Estado inicial **OPEN** en todas las pruebas: no ejecutadas. Las cifras de aceptación siguientes son metas **PROVISIONAL**, no especificaciones demostradas ni certificación. Acordar banda/rango y tolerancias con Integración antes de ensayar; cualquier cambio debe quedar fechado.

## Registro común

Guardar un registro por corrida, incluso si falla, y adjuntar CSV/binario crudo, fotos del montaje y capturas del osciloscopio. Los archivos se añadirán cuando existan, no como resultados ficticios.

```text
ID / fecha-hora-zona / responsable / prueba / estado (OPEN, PASS o FAIL):
Commit firmware-software / revisión esquema / configuración y conexionado:
Sensor-serie-certificado / cable-longitud / fuente / carga / ambiente:
Instrumentos: modelo, identificación, calibración e incertidumbre disponible:
Objetivo y límites acordados antes del ensayo / procedimiento aplicado:
Datos crudos y unidades / resultado calculado / incertidumbre o limitación:
Criterio aplicado / conclusión / anomalías / siguiente acción:
Rutas a capturas, archivos y comando o versión del análisis:
```

Campos de cada tabla de datos: `run_id, magnitud, unidad, consigna, medido, limite_inferior, limite_superior, estado, evidencia`. Usar CSV con punto decimal; dejar medidas ausentes vacías y estado OPEN. No escribir cero para datos inexistentes.

## T1 — Corriente y compliance, sin micrófono

Responsable: Electrónica IEPE. Equipo: fuente de banco limitada, DMM, osciloscopio y resistencias/carga electrónica dentro de sus límites. Verificar el esquema y datasheet LT3092 antes de energizar.

1. Configurar por separado 2,4, 2,8 y 4 mA. Usar cargas que produzcan tensión alrededor del bias esperado (12,5 V) y otras que permitan recorrer la zona de compliance. Calcular `R = V/I` y `P = I²R` con margen de potencia; son cálculos, no mediciones.
2. Partir con alimentación desconectada; comprobar conexiones, ajustar límite y subir tensión de forma controlada. Barrer fuente y carga dentro de los límites; medir corriente, tensión del nodo IEPE, caída en la fuente de corriente, rizado y temperatura/tiempo de estabilización.
3. Identificar pérdida de regulación. Ensayar abierto y cortocircuito solo con carga ficticia, fuente limitada y protecciones revisadas; registrar tensión máxima y transitorios al conectar/desconectar.

Registrar: ajuste/resistencias reales, Vs, carga, I, Vnodo, caída, rizado (ancho de banda), duración y temperatura. Meta inicial: error DC ≤5 % respecto a consigna en todo el intervalo de carga/tensión que se pretenda usar; límites térmicos y eléctricos respetados. Definir presupuesto de ruido y margen de compliance antes de declarar PASS. Ningún PASS con carga aprueba por sí solo el micrófono.

## T2 — Bias y autorización de integración del sensor

Responsable: Electrónica IEPE, revisión de Integración. Precondición: T1 aprobada en la condición elegida; ficha/certificado de la unidad y límites aplicables verificados. Si falta información, mantener OPEN y no conectar.

Con alimentación apagada, conectar sensor/cable identificado; encender bajo supervisión. Medir I y bias tras estabilización, rizado y excursión AC con estímulo moderado. Apagar antes de cambiar corriente/cable. Comparar bias y corriente con la documentación de esa unidad; 12,5 V es referencia aproximada, no ventana de aceptación. Confirmar margen para los picos y ausencia de recorte. Registrar sensor, corriente elegida y razón, cable, Vs, I, bias, límites documentales y tiempo. Ante bias anómalo o falta de margen, detener y revisar.

## T3 — Protección, acoplamiento AC y acondicionamiento

Responsable: Electrónica IEPE. Primero usar emulador de señal IEPE con DC+AC conocido, sin sensor y sin ADC conectado; verificar que el generador admita ese montaje. Medir a ambos lados del condensador.

Registrar bias de entrada, offset de salida, ganancia y respuesta en frecuencia; comparar corte inferior con `1/(2*pi*Req*C)`. Barrer banda acordada y señales fuera de banda para evaluar filtrado. Medir arranque, descarga y reconexión para detectar picos. Conectar ADC solo tras verificar amplitud, modo común y transitorios contra sus límites recomendados y absolutos, tanto alimentado como apagado. Meta inicial: ganancia a 1 kHz dentro de ±2 % del valor diseñado; banda y atenuación antialias OPEN hasta definir requisitos. No inyectar fallos destructivos en el ADC para probar protección.

## T4 — Muestreo y DMA

Responsable: Adquisición digital. Inyectar seno de generador con offset/amplitud seguros; comenzar con ADC interno o PCM1808 identificando la ruta. Meta inicial: 48 kSPS; usar menor tasa si hace falta durante arranque y declararla.

Medir reloj/disparos y duración de bloques con osciloscopio/analizador. Para PCM1808 verificar MCLK, BCK, LRCK, formato, signo, orden de canales y alineación 24/32 bits frente al datasheet. Guardar muestras de un tono de 1 kHz a dos amplitudes y entrada silenciosa correctamente terminada; comprobar clipping, continuidad entre bloques y overruns DMA. Meta inicial: frecuencia de muestreo medida dentro de ±0,1 % de consigna; amplitud coherente con ganancia/resolución y cero overruns durante 60 s. Registrar frecuencias medidas, configuración, contadores y datos, sin interpretar 24 bits como resolución efectiva.

## T5 — Transferencia al PC

Responsable: Adquisición digital. Antes del sensor, transmitir patrón determinista/contador y luego muestras reales. Acordar trama versionada con secuencia, número de muestras, fs, formato y contadores de error; CDC binario es candidato, no protocolo implementado.

Ejecutar 10 minutos a la tasa objetivo, registrar bytes/s útiles, bloques, secuencias faltantes/duplicadas, overruns y duración. Meta inicial: cero pérdidas/duplicados y cero overruns. Probar desconexión/reconexión y PC lento; cualquier pérdida debe detectarse y marcarse, nunca ocultarse. Distinguir USB nativo de UART vía ST-LINK. Guardar captura y estadísticas; repetir a 96 kSPS solo si se pretende ofrecer esa tasa.

## T6 — Procesamiento y calibración

Responsable: Adquisición digital; calibración con Electrónica IEPE. Verificar primero con datos sintéticos identificados como tales y seno medido de generador: tiempo en segundos, conversión cuentas→voltios, eliminación de DC, `Vrms = sqrt(mean(v_ac²))`, frecuencia FFT, ventana, corrección de amplitud y unidades. Metas iniciales: RMS dentro de ±1 % del valor esperado sintético; pico FFT a no más de un bin (`fs/N`) del tono; contraste eléctrico sujeto a incertidumbre del generador/DMM.

Conversión PROVISIONAL: `p_rms = Vrms/(G*S)` con ganancia total medida `G` y sensibilidad `S` en V/Pa; `Lp = 20*log10(p_rms/20e-6)` dB. No usar 55,6 mV/Pa como sensibilidad calibrada sin evidencia. Para calibración acústica usar nivel/frecuencia reales del certificado del calibrador y adaptador correcto; registrar coeficiente antes/después, repeticiones, banda, temperatura y límites de incertidumbre. Comparar lectura con nivel certificado; meta inicial ±1 dB, sujeta a revisión del presupuesto de incertidumbre. Si no hay calibrador, reportar voltios y SPL solo como PROVISIONAL. A/C, ponderación temporal y conformidad requieren ensayos adicionales; no quedan cubiertos por una calibración a un tono.
